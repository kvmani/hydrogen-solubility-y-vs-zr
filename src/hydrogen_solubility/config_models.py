"""Typed configuration models.

Two kinds of configuration exist:

* **Run config** (``schema_version: "2.0"``): one file describes exactly one VASP
  calculation. Run configs are normally *generated* by ``hsol plan`` from a
  campaign file, so they are fully explicit -- every INCAR tag that VASP will see
  is written in the config itself. The schema is documented in
  ``docs/config_schema.md``.
* **Site config** (``configs/site.yaml``): cluster-specific settings shared by all
  runs (Slurm partition/account, modules, launcher, POTCAR library). It is kept
  out of git because it differs per user and per machine.

Pydantic models use ``typing.Optional``/``Dict``/``List`` rather than ``X | Y`` so
the package also runs on the older Python versions common on HPC login nodes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, field_validator, model_validator

SCHEMA_VERSION = "2.0"

#: Chemical systems handled by the project. ``H2`` is the gas-phase reference.
SYSTEMS = ("Y", "Zr", "H2")
STAGES = ("stage1", "stage2", "stage3", "stage4", "stage5", "stage6")

#: calc_type -> structure builders that make sense for it.
CALC_TYPE_BUILDERS: Dict[str, Tuple[str, ...]] = {
    "host_convergence": ("hcp_primitive", "file"),
    "host_relax": ("hcp_primitive", "file"),
    "host_supercell": ("hcp_supercell", "file"),
    "h_interstitial": ("hcp_supercell", "file"),
    "h2_reference": ("h2_molecule", "file"),
    "hydride_relax": ("fluorite_dihydride", "file"),
    "vibration": ("from_run",),
}
CALC_TYPES = tuple(CALC_TYPE_BUILDERS)

#: INCAR tags every run must set explicitly (no hidden VASP defaults for these).
REQUIRED_INCAR_TAGS = ("ENCUT", "PREC", "EDIFF", "ISMEAR", "SIGMA", "IBRION", "NSW")

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
WALLTIME_PATTERN = re.compile(r"^(?:(\d+)-)?(\d+):(\d{2}):(\d{2})$")

IncarValue = Union[bool, int, float, str]


class ConfigValidationError(ValueError):
    """Raised when a config file is missing, unparsable, or invalid."""


class _Strict(BaseModel):
    # Unknown keys are errors: a typo such as ``kpoint_grid`` must not be ignored.
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- run config


class SweepInfo(_Strict):
    """Which convergence series this run belongs to (set by the planner).

    ``reference`` is the base point shared by the ENCUT and k-point series.
    """

    parameter: Literal["encut", "kpoints", "reference"]
    value: str


class RunSection(_Strict):
    """Identity and intent of one calculation."""

    run_id: str
    stage: Literal["stage1", "stage2", "stage3", "stage4", "stage5", "stage6"]
    system: Literal["Y", "Zr", "H2"]
    calc_type: Literal[
        "host_convergence",
        "host_relax",
        "host_supercell",
        "h_interstitial",
        "h2_reference",
        "hydride_relax",
        "vibration",
    ]
    objective: str = Field(min_length=12)
    campaign: Optional[str] = None
    sweep: Optional[SweepInfo] = None
    notes: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_run_id(self) -> "RunSection":
        if not RUN_ID_PATTERN.match(self.run_id):
            raise ValueError("run_id may only contain letters, digits, '_', '.', '-'.")
        prefix = f"{self.system}_{self.stage}_"
        if not self.run_id.startswith(prefix):
            raise ValueError(f"run_id must start with '{prefix}' (system_stage_label), got '{self.run_id}'.")
        return self


class StructureSection(_Strict):
    """How the starting POSCAR is built. See ``hydrogen_solubility.structures``."""

    builder: Literal["hcp_primitive", "hcp_supercell", "h2_molecule", "fluorite_dihydride", "from_run", "file"]
    source: str = Field(min_length=3, description="Where the geometry comes from (provenance text).")
    a_A: Optional[float] = Field(default=None, gt=0)
    c_A: Optional[float] = Field(default=None, gt=0)
    lattice_from_run: Optional[str] = None
    supercell: Tuple[int, int, int] = (1, 1, 1)
    h_site: Optional[Literal["tetrahedral", "octahedral"]] = None
    box_A: Optional[Tuple[float, float, float]] = None
    bond_A: float = Field(default=0.75, gt=0)
    from_run: Optional[str] = None
    free_species: List[str] = Field(default_factory=lambda: ["H"])
    file: Optional[str] = None

    @field_validator("supercell")
    @classmethod
    def _positive_supercell(cls, value: Tuple[int, int, int]) -> Tuple[int, int, int]:
        if any(v < 1 for v in value):
            raise ValueError("supercell entries must be >= 1.")
        return value

    @model_validator(mode="after")
    def _check_builder_inputs(self) -> "StructureSection":
        b = self.builder
        has_lattice = self.a_A is not None
        if b in ("hcp_primitive", "hcp_supercell"):
            if has_lattice == bool(self.lattice_from_run):
                raise ValueError(f"{b}: give either a_A/c_A or lattice_from_run (exactly one).")
            if has_lattice and self.c_A is None:
                raise ValueError(f"{b}: c_A is required together with a_A.")
        if b == "hcp_primitive" and self.supercell != (1, 1, 1):
            raise ValueError("hcp_primitive: supercell must be [1, 1, 1]; use hcp_supercell instead.")
        if b == "fluorite_dihydride" and not has_lattice:
            raise ValueError("fluorite_dihydride: a_A (cubic lattice parameter) is required.")
        if b == "h2_molecule" and self.box_A is None:
            raise ValueError("h2_molecule: box_A is required (use an asymmetric box, e.g. [10, 11, 12]).")
        if b == "from_run" and not self.from_run:
            raise ValueError("from_run: the from_run field (parent run_id) is required.")
        if b == "file" and not self.file:
            raise ValueError("file: the file field (path to a POSCAR) is required.")
        return self


class KpointsSection(_Strict):
    """Either an explicit ``grid`` or a ``spacing`` (exactly one).

    ``spacing`` is the largest allowed reciprocal-space distance between k-points in
    1/Angstrom, including the 2*pi factor (the same convention as VASP's KSPACING).
    ``hsol prepare`` converts it into a grid for the actual cell, which keeps the
    k-point density identical across primitive cells, supercells and hydrides.
    """

    grid: Optional[Tuple[int, int, int]] = None
    spacing: Optional[float] = Field(default=None, gt=0)
    style: Literal["Gamma", "Monkhorst-Pack"] = "Gamma"

    @field_validator("grid")
    @classmethod
    def _positive_grid(cls, value: Optional[Tuple[int, int, int]]) -> Optional[Tuple[int, int, int]]:
        if value is not None and any(v < 1 for v in value):
            raise ValueError("k-point grid entries must be >= 1.")
        return value

    @model_validator(mode="after")
    def _one_of(self) -> "KpointsSection":
        if (self.grid is None) == (self.spacing is None):
            raise ValueError("give exactly one of kpoints.grid or kpoints.spacing (set the other to null).")
        return self


class VaspSection(_Strict):
    """Literal VASP settings. ``incar`` keys are real INCAR tags (see the VASP wiki)."""

    incar: Dict[str, IncarValue]
    kpoints: KpointsSection
    binary: Literal["std", "gam"] = "std"

    @field_validator("incar")
    @classmethod
    def _check_incar(cls, incar: Dict[str, IncarValue]) -> Dict[str, IncarValue]:
        bad = [k for k in incar if not re.fullmatch(r"[A-Z][A-Z0-9_]*", k)]
        if bad:
            raise ValueError(f"INCAR tags must be upper-case VASP tag names: {bad}")
        missing = [k for k in REQUIRED_INCAR_TAGS if k not in incar]
        if missing:
            raise ValueError(f"INCAR is missing required tags {missing} (no hidden defaults allowed).")
        if "SYSTEM" in incar:
            raise ValueError("Do not set SYSTEM; it is written automatically from run_id.")
        encut = incar["ENCUT"]
        if isinstance(encut, bool) or not isinstance(encut, (int, float)) or encut <= 0:
            raise ValueError("ENCUT must be a positive number (eV).")
        return incar

    @model_validator(mode="after")
    def _gamma_binary(self) -> "VaspSection":
        if self.binary == "gam" and (self.kpoints.grid != (1, 1, 1) or self.kpoints.style != "Gamma"):
            raise ValueError("binary 'gam' (vasp_gam) requires a 1x1x1 Gamma k-point grid.")
        return self


class HpcSection(_Strict):
    """Per-run resource request. Partition/account/modules live in configs/site.yaml."""

    nodes: int = Field(default=1, ge=1)
    ntasks: int = Field(ge=1)
    walltime: str

    @field_validator("walltime", mode="before")
    @classmethod
    def _sexagesimal(cls, value: Any) -> Any:
        # YAML 1.1 reads an unquoted 12:00:00 as the integer 43200 (seconds); undo that.
        if isinstance(value, int) and not isinstance(value, bool):
            return f"{value // 3600:02d}:{value % 3600 // 60:02d}:{value % 60:02d}"
        return value

    @field_validator("walltime")
    @classmethod
    def _check_walltime(cls, value: str) -> str:
        match = WALLTIME_PATTERN.match(value)
        if not match or int(match.group(3)) >= 60 or int(match.group(4)) >= 60:
            raise ValueError("walltime must look like HH:MM:SS or D-HH:MM:SS.")
        return value


class RunConfig(_Strict):
    """Top-level schema of one generated run config."""

    schema_version: Literal["2.0"]
    run: RunSection
    structure: StructureSection
    vasp: VaspSection
    potcars: Dict[str, str] = Field(min_length=1)
    hpc: HpcSection

    @model_validator(mode="after")
    def _cross_checks(self) -> "RunConfig":
        allowed = CALC_TYPE_BUILDERS[self.run.calc_type]
        if self.structure.builder not in allowed:
            raise ValueError(
                f"calc_type '{self.run.calc_type}' expects structure.builder in {list(allowed)}, "
                f"got '{self.structure.builder}'."
            )
        if self.run.calc_type == "h_interstitial" and self.structure.builder == "hcp_supercell":
            if self.structure.h_site is None:
                raise ValueError("h_interstitial needs structure.h_site (tetrahedral or octahedral).")
        elif self.structure.h_site is not None:
            raise ValueError("structure.h_site is only meaningful for calc_type h_interstitial.")

        for element in self.expected_elements():
            if element not in self.potcars:
                raise ValueError(f"potcars must map element '{element}' to a POTCAR label (e.g. Y_sv, H).")
        return self

    def expected_elements(self) -> List[str]:
        """Elements implied by the system/calc type (a ``file``/``from_run`` POSCAR is checked later)."""

        if self.run.system == "H2":
            return ["H"]
        elements = [self.run.system]
        if self.run.calc_type in ("h_interstitial", "hydride_relax"):
            elements.append("H")
        return elements

    def dependencies(self) -> List[str]:
        """run_ids whose finished outputs are needed to build this run's inputs."""

        deps = [self.structure.lattice_from_run, self.structure.from_run]
        return [d for d in deps if d]

    @property
    def run_id(self) -> str:
        return self.run.run_id

    def science_hash(self) -> str:
        """Fingerprint of everything that determines the physics of the run.

        Resource requests (``hpc``) and descriptive text (objective, notes) are
        excluded, so a longer walltime never forces a new run_id.
        """

        import hashlib

        relevant = {
            "run_id": self.run.run_id,
            "system": self.run.system,
            "calc_type": self.run.calc_type,
            "structure": self.structure.model_dump(mode="json"),
            "vasp": self.vasp.model_dump(mode="json"),
            "potcars": self.potcars,
        }
        return hashlib.sha256(json.dumps(relevant, sort_keys=True).encode("utf-8")).hexdigest()


# -------------------------------------------------------------------------- site config


class SlurmSite(_Strict):
    partition: str = "<partition>"
    account: str = "<account>"
    extra_directives: List[str] = Field(
        default_factory=list, description="Extra '#SBATCH' options, e.g. '--qos=normal'."
    )


class EnvironmentSite(_Strict):
    login_shell: bool = Field(
        default=False, description="Run jobs with `bash -l` (needed on some clusters for `module`)."
    )
    module_purge: bool = True
    modules: List[str] = Field(default_factory=list)
    setup_commands: List[str] = Field(default_factory=list)


class VaspSite(_Strict):
    launch_command: str = "srun"
    binary_std: str = "vasp_std"
    binary_gam: str = "vasp_gam"
    potcar_root: Optional[str] = None


class PathsSite(_Strict):
    results_root: str = "results/runs"


class SiteConfig(_Strict):
    """Cluster-specific settings (``configs/site.yaml``)."""

    slurm: SlurmSite = Field(default_factory=SlurmSite)
    environment: EnvironmentSite = Field(default_factory=EnvironmentSite)
    vasp: VaspSite = Field(default_factory=VaspSite)
    paths: PathsSite = Field(default_factory=PathsSite)
    python: Optional[str] = Field(
        default=None, description="Python used inside jobs for automatic collection (default: current one)."
    )

    _loaded_from: Optional[str] = PrivateAttr(default=None)

    @property
    def loaded_from(self) -> Optional[str]:
        """Path of the site file this config came from (None: built-in defaults)."""

        return self._loaded_from

    def fingerprint(self) -> str:
        """Hash of the site settings; a smoke test is only valid for the settings it tested."""

        import hashlib

        return hashlib.sha256(json.dumps(self.model_dump(mode="json"), sort_keys=True).encode("utf-8")).hexdigest()

    def placeholder_fields(self) -> List[str]:
        """Names of settings that still hold template placeholders."""

        found = []
        for name, value in (("slurm.partition", self.slurm.partition), ("slurm.account", self.slurm.account)):
            if is_placeholder(value):
                found.append(name)
        return found


def is_placeholder(value: Optional[str]) -> bool:
    """True for empty values and template markers such as ``<partition>``."""

    if value is None:
        return True
    text = value.strip()
    return not text or ("<" in text and ">" in text) or text.lower() in {"placeholder", "tbd", "todo", "replace_me"}


# ------------------------------------------------------------------------------ loading


def load_mapping(path: Path) -> Dict[str, Any]:
    """Read a YAML/JSON file that must contain a mapping at the top level."""

    if not path.exists():
        raise ConfigValidationError(f"File not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        if path.suffix.lower() in (".yaml", ".yml"):
            payload = yaml.safe_load(text)
        elif path.suffix.lower() == ".json":
            payload = json.loads(text)
        else:
            raise ConfigValidationError(f"Unsupported extension '{path.suffix}' (use .yaml or .json): {path}")
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise ConfigValidationError(f"Could not parse {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigValidationError(f"Top level of {path} must be a mapping.")
    return payload


def _format_validation_error(path: Path, exc: ValidationError) -> str:
    lines = [f"Invalid config {path}:"]
    for err in exc.errors():
        location = ".".join(str(p) for p in err["loc"]) or "<root>"
        lines.append(f"  - {location}: {err['msg']}")
    return "\n".join(lines)


def parse_run_config(payload: Dict[str, Any], *, origin: str = "<memory>") -> RunConfig:
    """Validate an in-memory run config mapping."""

    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ConfigValidationError(
            f"{origin}: schema_version must be '{SCHEMA_VERSION}' (found {version!r}). "
            "Regenerate configs with `hsol plan`."
        )
    try:
        return RunConfig.model_validate(payload)
    except ValidationError as exc:
        raise ConfigValidationError(_format_validation_error(Path(origin), exc)) from exc


def load_run_config(path: Union[str, Path]) -> RunConfig:
    """Load and validate one run config file."""

    config_path = Path(path)
    return parse_run_config(load_mapping(config_path), origin=str(config_path))


def load_site_config(path: Optional[Path] = None) -> SiteConfig:
    """Load ``configs/site.yaml``; return defaults (with placeholders) if it does not exist."""

    from .paths import site_config_path

    site_path = path or site_config_path()
    if not site_path.exists():
        return SiteConfig()
    try:
        site = SiteConfig.model_validate(load_mapping(site_path))
    except ValidationError as exc:
        raise ConfigValidationError(_format_validation_error(site_path, exc)) from exc
    site._loaded_from = str(site_path)
    return site


def collect_config_paths(inputs: List[str]) -> List[Path]:
    """Expand files and directories (recursively) into a sorted list of run config files."""

    from .paths import resolve_repo_path

    found: Dict[Path, None] = {}
    for raw in inputs:
        path = resolve_repo_path(raw)
        if path.is_dir():
            for child in sorted(path.rglob("*.yaml")):
                found[child] = None
        elif path.is_file():
            found[path] = None
        else:
            raise ConfigValidationError(f"No such config file or directory: {raw}")
    if not found:
        raise ConfigValidationError(f"No .yaml config files found in: {' '.join(inputs)}")
    return list(found)
