"""Typed config models for stage-1 host validation runs."""

from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


RUN_ID_PATTERN = re.compile(
    r"^(?P<date>\d{8})_(?P<system>[A-Za-z0-9_]+)_(?P<stage>stage[1-6])_(?P<method>[a-z]+)_(?P<seq>\d{3})$"
)


class RunSection(BaseModel):
    """Identity and intent of a single run."""

    run_id: str
    stage: Literal["stage1"]
    system: Literal["Y", "Zr"]
    method: Literal["dft"] = "dft"
    objective: str = Field(min_length=12)

    @field_validator("run_id")
    @classmethod
    def _validate_run_id(cls, value: str) -> str:
        if not RUN_ID_PATTERN.match(value):
            raise ValueError(
                "run_id must match YYYYMMDD_<system>_<stage>_<method>_<seq>, "
                "e.g., 20260302_Y_stage1_dft_001"
            )
        return value

    @model_validator(mode="after")
    def _check_run_id_fields(self) -> "RunSection":
        match = RUN_ID_PATTERN.match(self.run_id)
        if not match:
            return self

        rid_system = match.group("system")
        rid_stage = match.group("stage")
        rid_method = match.group("method")

        if rid_system != self.system:
            raise ValueError(f"run.system ({self.system}) must match run_id system ({rid_system}).")
        if rid_stage != self.stage:
            raise ValueError(f"run.stage ({self.stage}) must match run_id stage ({rid_stage}).")
        if rid_method != self.method:
            raise ValueError(f"run.method ({self.method}) must match run_id method ({rid_method}).")
        return self


class StructureSource(BaseModel):
    """Where the starting crystal structure comes from."""

    kind: Literal["prototype", "file", "database"]
    reference: str = Field(min_length=3)


class StructureSection(BaseModel):
    """Host structure metadata."""

    phase: Literal["alpha_hcp"]
    source: StructureSource
    supercell: tuple[int, int, int]

    @field_validator("supercell")
    @classmethod
    def _validate_supercell(cls, value: tuple[int, int, int]) -> tuple[int, int, int]:
        if any(v <= 0 for v in value):
            raise ValueError("All supercell dimensions must be positive integers.")
        return value


class VaspSection(BaseModel):
    """Core VASP controls for stage-1 host checks."""

    functional: Literal["PBE"]
    precision: Literal["Accurate", "Normal"]
    encut_eV: float = Field(gt=0)
    kpoints_grid: tuple[int, int, int]
    kpoints_offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    ismear: int = Field(ge=-5, le=2)
    sigma_eV: float = Field(ge=0.0)
    ediff: float = Field(gt=0.0)
    ediffg: float
    nsw: int = Field(ge=0)
    isif: int = Field(ge=0, le=7)
    ibrion: int = Field(ge=-1, le=8)
    lasph: bool = True
    lreal: Literal["Auto", "False", "True"] = "Auto"
    spin_polarized: bool = False

    @field_validator("kpoints_grid")
    @classmethod
    def _validate_kpoints(cls, value: tuple[int, int, int]) -> tuple[int, int, int]:
        if any(v <= 0 for v in value):
            raise ValueError("All k-point grid values must be positive integers.")
        return value

    @field_validator("kpoints_offset")
    @classmethod
    def _validate_kpoint_offset(cls, value: tuple[float, float, float]) -> tuple[float, float, float]:
        if any(v < 0.0 or v >= 1.0 for v in value):
            raise ValueError("kpoints_offset values must be in [0, 1).")
        return value


class ConvergenceScanSection(BaseModel):
    """Planned convergence study settings."""

    encut_values_eV: list[float] = Field(min_length=2)
    kpoint_grids: list[tuple[int, int, int]] = Field(min_length=2)
    tolerance_meV_per_atom: float = Field(gt=0.0)

    @field_validator("encut_values_eV")
    @classmethod
    def _validate_encut_scan(cls, values: list[float]) -> list[float]:
        if any(v <= 0 for v in values):
            raise ValueError("All encut_values_eV entries must be positive.")
        if values != sorted(values):
            raise ValueError("encut_values_eV must be sorted ascending.")
        return values

    @field_validator("kpoint_grids")
    @classmethod
    def _validate_kpoint_scan(cls, grids: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
        for grid in grids:
            if any(v <= 0 for v in grid):
                raise ValueError("Each k-point scan grid must have positive integer components.")
        return grids


class HpcSection(BaseModel):
    """Generic scheduler metadata."""

    scheduler: Literal["slurm"]
    nodes: int = Field(ge=1)
    ntasks: int = Field(ge=1)
    walltime: str
    partition: str = Field(min_length=1)
    account: str = Field(min_length=1)

    @field_validator("walltime")
    @classmethod
    def _validate_walltime(cls, value: str) -> str:
        match = re.match(r"^(\d{2}):(\d{2}):(\d{2})$", value)
        if not match:
            raise ValueError("walltime must match HH:MM:SS.")
        _, minutes, seconds = match.groups()
        if int(minutes) >= 60 or int(seconds) >= 60:
            raise ValueError("walltime minutes/seconds must be < 60.")
        return value


class OutputsSection(BaseModel):
    """Output behavior flags."""

    results_root: str = Field(min_length=1)
    write_manifest: bool = True
    write_metrics: bool = True


class ProvenanceSection(BaseModel):
    """Provenance-critical metadata for reproducibility."""

    potcar_labels: list[str] = Field(min_length=1)
    notes: list[str] = Field(default_factory=list)


class Stage1HostConfig(BaseModel):
    """Top-level schema for stage-1 host-only runs."""

    schema_version: Literal["1.0"]
    run: RunSection
    structure: StructureSection
    vasp: VaspSection
    convergence_scan: ConvergenceScanSection
    hpc: HpcSection
    outputs: OutputsSection
    provenance: ProvenanceSection

    @model_validator(mode="after")
    def _cross_validate(self) -> "Stage1HostConfig":
        if self.vasp.encut_eV not in self.convergence_scan.encut_values_eV:
            raise ValueError("vasp.encut_eV must appear in convergence_scan.encut_values_eV.")
        if self.vasp.kpoints_grid not in self.convergence_scan.kpoint_grids:
            raise ValueError("vasp.kpoints_grid must appear in convergence_scan.kpoint_grids.")

        if self.run.system == "Y" and not any(label.startswith("Y") for label in self.provenance.potcar_labels):
            raise ValueError("For system=Y, provenance.potcar_labels must include a Y* POTCAR label.")
        if self.run.system == "Zr" and not any(
            label.startswith("Zr") for label in self.provenance.potcar_labels
        ):
            raise ValueError("For system=Zr, provenance.potcar_labels must include a Zr* POTCAR label.")
        return self


class ConfigValidationError(ValueError):
    """Raised when a config file is missing or invalid."""


def _load_raw_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigValidationError(f"Config file not found: {path}")

    suffix = path.suffix.lower()
    text = path.read_text()

    try:
        if suffix in {".yaml", ".yml"}:
            payload = yaml.safe_load(text)
        elif suffix == ".json":
            payload = json.loads(text)
        else:
            raise ConfigValidationError(
                f"Unsupported config extension '{suffix}'. Use .yaml/.yml or .json."
            )
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise ConfigValidationError(f"Failed to parse {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ConfigValidationError(f"Top-level config payload must be an object: {path}")
    return payload


def load_stage1_host_config(path: str | Path) -> Stage1HostConfig:
    """Load and validate a stage-1 host configuration file."""

    config_path = Path(path)
    payload = _load_raw_config(config_path)
    try:
        return Stage1HostConfig.model_validate(payload)
    except ValidationError as exc:
        raise ConfigValidationError(f"Validation failed for {config_path}:\n{exc}") from exc
