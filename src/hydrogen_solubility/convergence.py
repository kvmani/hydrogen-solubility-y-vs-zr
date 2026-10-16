"""``hsol analyze convergence``: pick ENCUT and k-point spacing from the Stage-1a sweep.

For each system, the ENCUT series (sweep ``encut`` + the shared ``reference``
point) is compared with its highest ENCUT, and the k-point series with its densest
grid. The converged value is the cheapest setting from which *every* more accurate
point stays within the tolerance (default 1 meV/atom); a single lucky crossing of
zero therefore does not count as converged.

Outputs in ``results/analysis/convergence/``: ``convergence_table.csv``,
``summary.md`` (with the snippet for ``configs/campaigns/converged_settings.yaml``)
and, if matplotlib is installed, ``encut.png`` / ``kpoints.png``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from .config_models import SiteConfig
from .paths import analysis_dir
from .provenance import read_json, utc_now
from .results_index import find_runs
from .run_bootstrap import load_config_for_run


@dataclass
class Point:
    run_id: str
    parameter: str
    encut: float
    grid: Tuple[int, int, int]
    spacing: float  # requested k-point spacing (1/A); the grid realises it on this cell
    e_atom: float
    entropy_meV_atom: Optional[float]


@dataclass
class SeriesResult:
    name: str
    points: List[Tuple[Point, float]]  # (point, deviation in meV/atom from the most accurate point)
    converged: Optional[Point]


@dataclass
class SystemResult:
    system: str
    encut: SeriesResult
    kpoints: SeriesResult
    skipped: List[str] = field(default_factory=list)


def _load_points(site: SiteConfig, system: str) -> Tuple[List[Point], List[str]]:
    points, skipped = [], []
    for run_dir in find_runs(site, calc_type="host_convergence", system=system):
        manifest = read_json(run_dir / "manifest.json")
        metrics = read_json(run_dir / "metrics.json")
        config = load_config_for_run(run_dir)
        sweep = manifest.get("sweep") or {}
        if metrics.get("status") != "converged" or config is None or not sweep:
            skipped.append(f"{run_dir.name} ({metrics.get('status', 'unknown')})")
            continue
        energetics = metrics["energetics"]
        nions = metrics["calculation"]["nions"]
        f, e0 = energetics.get("free_energy_eV"), energetics["energy_sigma0_eV"]
        structure = manifest.get("structure", {})
        points.append(
            Point(
                run_id=run_dir.name,
                parameter=sweep["parameter"],
                encut=float(config.vasp.incar["ENCUT"]),
                grid=tuple(structure["kpoints_grid"]),  # type: ignore[arg-type]
                spacing=float(config.vasp.kpoints.spacing or structure["kpoint_spacing_A-1"]),
                e_atom=float(energetics["energy_per_atom_eV"]),
                entropy_meV_atom=abs(f - e0) / nions * 1e3 if f is not None else None,
            )
        )
    return points, skipped


def _series(name: str, points: List[Point], tol_meV: float) -> SeriesResult:
    """Order from cheapest to most accurate and find the converged point."""

    if name == "encut":
        ordered = sorted(points, key=lambda p: p.encut)
    else:
        ordered = sorted(points, key=lambda p: -p.spacing)
    if len(ordered) < 2:
        return SeriesResult(name, [(p, 0.0) for p in ordered], None)
    best = ordered[-1].e_atom
    devs = [(p, (p.e_atom - best) * 1e3) for p in ordered]
    converged = None
    # Walk backwards from the most accurate point while every deviation is within tolerance.
    for p, dev in reversed(devs[:-1]):
        if abs(dev) > tol_meV:
            break
        converged = p
    return SeriesResult(name, devs, converged)


def analyze(site: SiteConfig, *, tolerance_meV: float = 1.0) -> List[SystemResult]:
    results = []
    for system in ("Y", "Zr"):
        points, skipped = _load_points(site, system)
        if not points and not skipped:
            continue
        encut = _series("encut", [p for p in points if p.parameter in ("encut", "reference")], tolerance_meV)
        kpts = _series("kpoints", [p for p in points if p.parameter in ("kpoints", "reference")], tolerance_meV)
        results.append(SystemResult(system, encut, kpts, skipped))
    return results


def recommendation(results: List[SystemResult]) -> Tuple[Optional[float], Optional[float], List[str]]:
    """Common ENCUT (max over systems) and k-spacing (min over systems), plus caveats."""

    notes = []
    encuts, spacings = [], []
    for r in results:
        if r.encut.converged is None:
            notes.append(f"{r.system}: ENCUT not converged within the sweep - extend encut_eV upwards.")
        else:
            encuts.append(r.encut.converged.encut)
        if r.kpoints.converged is None:
            notes.append(f"{r.system}: k-points not converged within the sweep - add denser grids.")
        else:
            spacings.append(r.kpoints.converged.spacing)
    if len(encuts) < len(results) or len(spacings) < len(results) or not results:
        return None, None, notes
    for r in results:
        worst = max((p.entropy_meV_atom or 0.0) for p, _ in r.kpoints.points + r.encut.points)
        if worst > 1.0:
            notes.append(
                f"{r.system}: smearing entropy |F - E0| reaches {worst:.2f} meV/atom - consider a smaller SIGMA."
            )
    return max(encuts), min(spacings), notes


def write_outputs(results: List[SystemResult], tolerance_meV: float, output_dir: Optional[Path] = None) -> Path:
    output_dir = output_dir or analysis_dir() / "convergence"
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "convergence_table.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "system",
                "series",
                "run_id",
                "encut_eV",
                "kpoints_grid",
                "kspacing_A-1",
                "energy_per_atom_eV",
                "deviation_meV_atom",
                "entropy_meV_atom",
            ]
        )
        for r in results:
            for series in (r.encut, r.kpoints):
                for p, dev in series.points:
                    writer.writerow(
                        [
                            r.system,
                            series.name,
                            p.run_id,
                            p.encut,
                            "x".join(map(str, p.grid)),
                            p.spacing,
                            f"{p.e_atom:.6f}",
                            f"{dev:.3f}",
                            "" if p.entropy_meV_atom is None else f"{p.entropy_meV_atom:.3f}",
                        ]
                    )

    encut, spacing, notes = recommendation(results)
    lines = [
        "# Stage 1a convergence summary",
        "",
        f"Generated {utc_now()} by `hsol analyze convergence`; "
        f"tolerance {tolerance_meV} meV/atom relative to the most accurate point of each series.",
        "",
    ]
    for r in results:
        lines += [f"## {r.system}", ""]
        for series, unit in ((r.encut, "ENCUT (eV)"), (r.kpoints, "k-spacing")):
            lines += [
                f"| {unit} | k-spacing (1/A) | k-grid | E/atom (eV) | deviation (meV/atom) |",
                "|---|---|---|---|---|",
            ]
            for p, dev in series.points:
                label = f"{p.encut:g}" if series.name == "encut" else f"{p.spacing:g}"
                mark = " **<- converged**" if series.converged is p else ""
                grid = "x".join(map(str, p.grid))
                lines.append(f"| {label} | {p.spacing:g} | {grid} | {p.e_atom:.6f} | {dev:+.3f}{mark} |")
            lines.append("")
        if r.skipped:
            lines += ["Not used (not converged or not collected): " + ", ".join(r.skipped), ""]
    lines += ["## Recommendation", ""]
    if encut is not None:
        lines += [
            "Use one setting for every system and stage (paste into `configs/campaigns/converged_settings.yaml`):",
            "",
            "```yaml",
            "defaults:",
            "  vasp:",
            "    incar:",
            f"      ENCUT: {encut:g}",
            "    kpoints:",
            f"      spacing: {spacing:g}",
            "```",
            "",
            "ENCUT is the largest converged value over the systems and the spacing the smallest, so both metals "
            "are converged. Hydrogen-containing cells are covered as long as ENCUT also exceeds the H POTCAR "
            "ENMAX (checked by `hsol prepare`).",
            "",
        ]
    else:
        lines += ["No recommendation yet - see the notes below.", ""]
    lines += [f"- {n}" for n in notes]
    summary = output_dir / "summary.md"
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _plots(results, tolerance_meV, output_dir)
    return summary


def _plots(results: List[SystemResult], tol: float, output_dir: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    for name, xlabel in (("encut", "ENCUT (eV)"), ("kpoints", "k-point spacing (1/Å)")):
        fig, ax = plt.subplots(figsize=(5.5, 3.8))
        for r in results:
            series = r.encut if name == "encut" else r.kpoints
            if not series.points:
                continue
            xs = [p.encut if name == "encut" else p.spacing for p, _ in series.points]
            ax.plot(xs, [abs(d) for _, d in series.points], marker="o", label=r.system)
        ax.axhline(tol, color="grey", linestyle="--", linewidth=1, label=f"{tol} meV/atom")
        ax.set_yscale("symlog", linthresh=0.01)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("|ΔE| vs most accurate (meV/atom)")
        if name == "kpoints":
            ax.invert_xaxis()
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / f"{name}.png", dpi=150)
        plt.close(fig)


def run(site: SiteConfig, tolerance_meV: float = 1.0) -> Tuple[Path, List[SystemResult]]:
    results = analyze(site, tolerance_meV=tolerance_meV)
    if not results:
        raise RuntimeError("no host_convergence runs found: plan, prepare, run and collect Stage 1a first.")
    return write_outputs(results, tolerance_meV), results
