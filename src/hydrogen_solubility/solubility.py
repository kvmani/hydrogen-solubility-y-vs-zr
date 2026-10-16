"""``hsol analyze solubility``: from collected DFT runs to H solubility in Y and Zr.

The analysis uses whatever has been computed and states what is missing:

* Stage 2 only               -> static solution energies and dilute (Sieverts) solubility
* + Stage 3 vibrations       -> zero-point and vibrational free-energy corrections
* + Stage 4 hydride (+ vib)  -> hydride-limited terminal solid solubility (TSS) and
                                the plateau pressure

Runs are looked up by their planned run_ids (see :data:`RUN_IDS`); ``--tag`` selects
re-runs whose ids carry a suffix, falling back to untagged runs.

Model assumptions (also written to the summary): ideal lattice gas of independent H
atoms (no H-H interaction), harmonic H vibrations with metal atoms fixed, metal
lattice vibrations unchanged by H, ideal-gas H2, and the configured hydride
structure as the competing phase.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import thermo
from .config_models import SiteConfig
from .paths import analysis_dir
from .provenance import read_json, utc_now
from .run_bootstrap import run_dir_for

#: Planned run_ids (``{s}`` = system) produced by the campaign files.
RUN_IDS = {
    "host_relax": "{s}_stage1_relax",
    "host_supercell": "{s}_stage2_host",
    "h_tetrahedral": "{s}_stage2_hT",
    "h_octahedral": "{s}_stage2_hO",
    "h2": "H2_stage2_molecule",
    "vib_tetrahedral": "{s}_stage3_vib_hT",
    "vib_octahedral": "{s}_stage3_vib_hO",
    "vib_h2": "H2_stage3_vib_molecule",
    "hydride": "{s}_stage4_hydride",
    "vib_hydride": "{s}_stage4_vib_hydride",
}
SITES = ("tetrahedral", "octahedral")
REPORT_TEMPERATURES = (300.0, 600.0, 900.0)


class AnalysisError(RuntimeError):
    pass


@dataclass
class RunData:
    run_id: str
    energy: Optional[float]
    natoms: int
    composition: Dict[str, int]
    modes_meV: List[float]
    n_imaginary: int
    final_site: Optional[str]


@dataclass
class SiteResult:
    site: str
    dE: float  # static solution energy per H vs 1/2 H2 (eV)
    zpe_correction: Optional[float]  # ZPE_site - 1/2 ZPE_H2 (eV)
    modes_meV: List[float]
    usable: bool
    note: str = ""

    def dg(self, temperature: float, h2_modes: Optional[List[float]]) -> float:
        if not self.modes_meV or h2_modes is None:
            return self.dE
        return (
            self.dE
            + thermo.harmonic_free_energy(self.modes_meV, temperature)
            - 0.5 * thermo.harmonic_free_energy(h2_modes, temperature)
        )


@dataclass
class HydrideResult:
    dE: float  # per H vs 1/2 H2 (eV)
    n_h: int
    modes_meV: List[float]
    run_id: str

    def zpe_correction(self, h2_modes: Optional[List[float]]) -> Optional[float]:
        if not self.modes_meV or h2_modes is None:
            return None
        return thermo.zero_point_energy(self.modes_meV) / self.n_h - 0.5 * thermo.zero_point_energy(h2_modes)

    def dg(self, temperature: float, h2_modes: Optional[List[float]]) -> float:
        if not self.modes_meV or h2_modes is None:
            return self.dE
        return (
            self.dE
            + thermo.harmonic_free_energy(self.modes_meV, temperature) / self.n_h
            - 0.5 * thermo.harmonic_free_energy(h2_modes, temperature)
        )


@dataclass
class SystemModel:
    system: str
    sites: Dict[str, SiteResult] = field(default_factory=dict)
    hydride: Optional[HydrideResult] = None
    used_runs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def usable_sites(self) -> Dict[str, SiteResult]:
        return {k: v for k, v in self.sites.items() if v.usable}


# ------------------------------------------------------------------------------ loading


class _Loader:
    def __init__(self, site: SiteConfig, tag: Optional[str]) -> None:
        self.site = site
        self.tag = tag

    def get(self, key: str, system: str = "") -> Tuple[Optional[RunData], str]:
        """Converged run data for a planned run, or (None, reason)."""

        base = RUN_IDS[key].format(s=system)
        candidates = ([f"{base}_{self.tag}"] if self.tag else []) + [base]
        for run_id in candidates:
            run_dir = run_dir_for(run_id, self.site)
            metrics = read_json(run_dir / "metrics.json")
            if not metrics:
                continue
            if metrics.get("status") != "converged":
                return None, f"{run_id} is {metrics.get('status')}"
            manifest = read_json(run_dir / "manifest.json")
            vib = metrics.get("vibrations") or {}
            modes = [m["meV"] for m in vib.get("modes", []) if not m["imaginary"]]
            return RunData(
                run_id=run_id,
                energy=(metrics.get("energetics") or {}).get("energy_sigma0_eV"),
                natoms=int((metrics.get("calculation") or {}).get("nions") or 0),
                composition=(manifest.get("structure") or {}).get("composition", {}),
                modes_meV=modes,
                n_imaginary=int(vib.get("n_imaginary", 0)),
                final_site=(metrics.get("structure_check") or {}).get("final_site"),
            ), ""
        return None, f"{candidates[-1]} not found"


def build_models(
    site: SiteConfig, tag: Optional[str] = None
) -> Tuple[List[SystemModel], Optional[List[float]], List[str]]:
    """Assemble per-system energetics. Returns (models, H2 stretch modes or None, global notes)."""

    load = _Loader(site, tag)
    notes: List[str] = []
    h2, why = load.get("h2")
    if h2 is None or h2.energy is None:
        raise AnalysisError(f"the H2 reference is required: {why}")
    h2_vib, why = load.get("vib_h2")
    h2_modes = [max(h2_vib.modes_meV)] if h2_vib and h2_vib.modes_meV else None
    if h2_modes is None:
        notes.append(f"No H2 vibration ({why}): all results are static (no zero-point energy).")

    models = []
    for system in ("Y", "Zr"):
        model = SystemModel(system, used_runs=[h2.run_id] + ([h2_vib.run_id] if h2_modes else []))
        host, why = load.get("host_supercell", system)
        if host is None or host.energy is None:
            model.notes.append(f"no host supercell ({why}); system skipped")
            models.append(model)
            continue
        model.used_runs.append(host.run_id)
        for site_name in SITES:
            run, why = load.get(f"h_{site_name}", system)
            if run is None or run.energy is None:
                model.notes.append(f"{site_name}: {why}")
                continue
            model.used_runs.append(run.run_id)
            dE = run.energy - host.energy - 0.5 * h2.energy
            result = SiteResult(site_name, dE, None, [], usable=True)
            if run.final_site != site_name:
                result.usable = False
                result.note = f"H relaxed away from the {site_name} site (final: {run.final_site})"
            vib, why = load.get(f"vib_{site_name}", system)
            if vib is not None and h2_modes is not None:
                model.used_runs.append(vib.run_id)
                result.modes_meV = vib.modes_meV
                result.zpe_correction = thermo.zero_point_energy(vib.modes_meV) - 0.5 * thermo.zero_point_energy(
                    h2_modes
                )
                if vib.n_imaginary:
                    result.usable = False
                    result.note = f"{vib.n_imaginary} imaginary mode(s): saddle point, not a minimum"
            elif h2_modes is not None:
                model.notes.append(f"{site_name}: no vibration run ({why}); static energy used")
            model.sites[site_name] = result

        hyd, why = load.get("hydride", system)
        relax, why_relax = load.get("host_relax", system)
        if hyd is None or relax is None or hyd.energy is None or relax.energy is None:
            model.notes.append(f"hydride competition not computed ({why or why_relax})")
        else:
            n_m, n_h = hyd.composition.get(system, 0), hyd.composition.get("H", 0)
            e_metal = relax.energy / relax.natoms
            dE_hyd = (hyd.energy - n_m * e_metal - 0.5 * n_h * h2.energy) / n_h
            hyd_vib, why = load.get("vib_hydride", system)
            modes = hyd_vib.modes_meV if hyd_vib and h2_modes else []
            if h2_modes and not modes:
                model.notes.append(f"hydride vibrations missing ({why}); static hydride energy used")
            model.hydride = HydrideResult(dE_hyd, n_h, modes, hyd.run_id)
            model.used_runs += [hyd.run_id, relax.run_id] + ([hyd_vib.run_id] if modes else [])
            host_atom = host.energy / host.natoms
            mismatch = abs(host_atom - e_metal) * 1e3
            if mismatch > 2.0:
                model.notes.append(
                    f"host energy/atom differs by {mismatch:.1f} meV between supercell and relaxed primitive cell: "
                    "check that both use the same ENCUT and k-point spacing"
                )
        models.append(model)
    return models, h2_modes, notes


# --------------------------------------------------------------------------- curves


def tss(model: SystemModel, h2_modes: Optional[List[float]], temperature: float) -> Optional[float]:
    """Hydride-limited terminal solid solubility (H/M) or None if inputs are missing."""

    sites = model.usable_sites()
    if not sites or model.hydride is None:
        return None
    dg = {name: s.dg(temperature, h2_modes) for name, s in sites.items()}
    return thermo.concentration(dg, model.hydride.dg(temperature, h2_modes), temperature)


def curves(
    models: Sequence[SystemModel], h2_modes: Optional[List[float]], temps: Sequence[float], pressures: Sequence[float]
) -> List[Dict[str, object]]:
    rows = []
    for model in models:
        sites = model.usable_sites()
        if not sites:
            continue
        for t in temps:
            dg = {name: s.dg(t, h2_modes) for name, s in sites.items()}
            row: Dict[str, object] = {"system": model.system, "T_K": t}
            for p in pressures:
                x = thermo.concentration(dg, thermo.delta_mu_h(t, p), t)
                row[f"x_H_at_{p:g}Pa"] = x
            if model.hydride is not None:
                g_hyd = model.hydride.dg(t, h2_modes)
                x_tss = thermo.concentration(dg, g_hyd, t)
                row["x_TSS"] = x_tss
                row["TSS_wppm"] = thermo.atomic_ratio_to_wppm(x_tss, model.system)
                row["plateau_pressure_Pa"] = thermo.plateau_pressure(g_hyd, t)
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------- output


def _fmt(x: Optional[float], digits: int = 3) -> str:
    return "n/a" if x is None else f"{x:+.{digits}f}"


def write_outputs(
    models: List[SystemModel],
    h2_modes: Optional[List[float]],
    notes: List[str],
    temps: Sequence[float],
    pressures: Sequence[float],
    output_dir: Optional[Path] = None,
) -> Path:
    output_dir = output_dir or analysis_dir() / "solubility"
    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / "site_energetics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["system", "site", "dE_static_eV", "dZPE_eV"]
            + [f"dG_{t:g}K_eV" for t in REPORT_TEMPERATURES]
            + ["usable", "note"]
        )
        for m in models:
            for s in m.sites.values():
                writer.writerow(
                    [m.system, s.site, f"{s.dE:.4f}", "" if s.zpe_correction is None else f"{s.zpe_correction:.4f}"]
                    + [f"{s.dg(t, h2_modes):.4f}" for t in REPORT_TEMPERATURES]
                    + [s.usable, s.note]
                )
            if m.hydride:
                writer.writerow(
                    [
                        m.system,
                        "hydride (per H)",
                        f"{m.hydride.dE:.4f}",
                        ""
                        if m.hydride.zpe_correction(h2_modes) is None
                        else f"{m.hydride.zpe_correction(h2_modes):.4f}",
                    ]
                    + [f"{m.hydride.dg(t, h2_modes):.4f}" for t in REPORT_TEMPERATURES]
                    + [True, m.hydride.run_id]
                )

    rows = curves(models, h2_modes, temps, pressures)
    if rows:
        keys = list(dict.fromkeys(k for r in rows for k in r))
        with (output_dir / "solubility_vs_T.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=keys)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})

    lines = [
        "# Hydrogen solubility: Y vs Zr",
        "",
        f"Generated {utc_now()} by `hsol analyze solubility`.",
        "",
        "Energies per H atom relative to 1/2 H2 (negative = H prefers the metal).",
        "",
        "| System | Site | dE static (eV) | dZPE (eV) | "
        + " | ".join(f"dG {t:g} K" for t in REPORT_TEMPERATURES)
        + " | Used |",
        "|---|---|---|---|" + "---|" * len(REPORT_TEMPERATURES) + "---|",
    ]
    for m in models:
        for s in m.sites.values():
            lines.append(
                f"| {m.system} | {s.site} | {_fmt(s.dE)} | {_fmt(s.zpe_correction)} | "
                + " | ".join(_fmt(s.dg(t, h2_modes)) for t in REPORT_TEMPERATURES)
                + f" | {'yes' if s.usable else 'no: ' + s.note} |"
            )
        if m.hydride:
            lines.append(
                f"| {m.system} | hydride | {_fmt(m.hydride.dE)} | {_fmt(m.hydride.zpe_correction(h2_modes))} | "
                + " | ".join(_fmt(m.hydride.dg(t, h2_modes)) for t in REPORT_TEMPERATURES)
                + " | yes |"
            )
    lines.append("")

    # The quantity that sets the TSS: how much less favourable dissolved H is than H in the hydride.
    lines += [
        "## What controls the solubility limit",
        "",
        "At the solvus x_TSS ~ n_s exp(-(dG_site - dG_hydride)/kT): the smaller the gap, the higher the TSS.",
        "",
        "| System | best site | dG_site - dG_hydride at 600 K (eV) |",
        "|---|---|---|",
    ]
    for m in models:
        sites = m.usable_sites()
        if sites and m.hydride:
            best = min(sites.values(), key=lambda s: s.dg(600.0, h2_modes))
            gap = best.dg(600.0, h2_modes) - m.hydride.dg(600.0, h2_modes)
            lines.append(f"| {m.system} | {best.site} | {gap:+.3f} |")
    lines.append("")
    tss_600 = {m.system: tss(m, h2_modes, 600.0) for m in models}
    if tss_600.get("Y") and tss_600.get("Zr"):
        lines += [
            f"Predicted TSS at 600 K: Y {tss_600['Y']:.3g}, Zr {tss_600['Zr']:.3g} H/M "
            f"({thermo.atomic_ratio_to_wppm(tss_600['Y'], 'Y'):.3g} and "
            f"{thermo.atomic_ratio_to_wppm(tss_600['Zr'], 'Zr'):.3g} wppm; "
            f"ratio Y/Zr = **{tss_600['Y'] / tss_600['Zr']:.3g}**).",
            "",
        ]

    lines += ["## Inputs used", ""] + [f"- {m.system}: {', '.join(m.used_runs)}" for m in models] + [""]
    all_notes = notes + [f"{m.system}: {n}" for m in models for n in m.notes]
    if all_notes:
        lines += ["## Missing inputs and warnings", ""] + [f"- {n}" for n in all_notes] + [""]
    lines += [
        "## Model assumptions",
        "",
        "- Independent H atoms on hcp T (2 per metal atom) and O (1 per metal atom) sites; no H-H interaction.",
        "- Harmonic H vibrations with metal atoms fixed; host phonons unchanged by H.",
        "- Ideal-gas H2 (translation + rigid rotor; DFT energy and stretch frequency).",
        "- Hydride = the structure computed in Stage 4 (fluorite MH2 by default; an approximation for Zr).",
        "- Sites that relaxed away or have imaginary modes are excluded from the occupancy sums.",
        "",
    ]
    summary = output_dir / "summary.md"
    summary.write_text("\n".join(lines), encoding="utf-8")
    _plot(rows, pressures, output_dir)
    return summary


def _plot(rows: List[Dict[str, object]], pressures: Sequence[float], output_dir: Path) -> None:
    if not rows:
        return
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    for system in ("Y", "Zr"):
        data = [r for r in rows if r["system"] == system]
        if not data:
            continue
        inv_t = [1000.0 / float(r["T_K"]) for r in data]
        if "x_TSS" in data[0]:
            ax.plot(inv_t, [float(r["x_TSS"]) for r in data], marker="o", label=f"{system}: TSS (hydride-limited)")
        key = f"x_H_at_{pressures[0]:g}Pa"
        ax.plot(
            inv_t, [float(r[key]) for r in data], linestyle="--", label=f"{system}: dilute, p = {pressures[0]:g} Pa"
        )
    ax.set_yscale("log")
    ax.set_xlabel("1000 / T (1/K)")
    ax.set_ylabel("H / metal atom")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_dir / "solubility.png", dpi=150)
    plt.close(fig)


def run(
    site: SiteConfig,
    *,
    tag: Optional[str] = None,
    t_min: float = 300.0,
    t_max: float = 1200.0,
    t_step: float = 50.0,
    pressures: Sequence[float] = (thermo.P_STANDARD,),
) -> Path:
    models, h2_modes, notes = build_models(site, tag)
    temps = thermo.temperatures(t_min, t_max, t_step)
    return write_outputs(models, h2_modes, notes, temps, pressures)
