"""Human-readable ``report.html`` for one run.

The report mirrors ``manifest.json`` + ``metrics.json`` + the input deck so a
reviewer can answer four questions without opening raw files: what was the run
for, which inputs governed it, did it converge, and what came out.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .provenance import read_json, utc_now

STATUS_COLOURS = {
    "converged": "#0a7a2f",
    "prepared": "#3a5a80",
    "submitted": "#3a5a80",
    "incomplete": "#8a5a00",
    "unconverged": "#9f1c1c",
    "not_started": "#3a5a80",
}

_CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;margin:24px auto;max-width:1100px;
     padding:0 16px;color:#1a2430;background:#f7f9fc;line-height:1.4}
h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.1rem;margin:22px 0 8px;border-bottom:1px solid #cbd6e2}
.meta{color:#4a5a6b;font-size:.85rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.card{background:#fff;border:1px solid #cbd6e2;border-radius:6px;padding:10px}
.card b{display:block;font-size:.8rem;color:#4a5a6b}
table{border-collapse:collapse;width:100%;background:#fff}
th,td{border:1px solid #cbd6e2;padding:5px 8px;text-align:left;vertical-align:top;font-size:.9rem}th{background:#eaf0f7}
pre{background:#fff;border:1px solid #cbd6e2;padding:10px;overflow-x:auto;font-size:.85rem}.problems li{color:#9f1c1c}
"""


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)


def _table(rows: Iterable[Tuple[str, Any]], headers: Tuple[str, str] = ("Field", "Value")) -> str:
    body = "".join(f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(_fmt(v))}</td></tr>" for k, v in rows)
    if not body:
        return "<p>n/a</p>"
    return f"<table><thead><tr><th>{headers[0]}</th><th>{headers[1]}</th></tr></thead><tbody>{body}</tbody></table>"


def _events_table(events: List[Dict[str, Any]]) -> str:
    if not events:
        return "<p>No events recorded.</p>"
    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(_fmt(e.get(k)))}</td>" for k in ("timestamp_utc", "event", "mode", "status", "message")
        )
        + "</tr>"
        for e in events
    )
    head = "".join(f"<th>{h}</th>" for h in ("UTC", "Event", "Mode", "Status", "Message"))
    return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"


def _read_text(path: Path, limit: int = 4000) -> str:
    if not path.is_file():
        return "(missing)"
    text = path.read_text(errors="replace")
    return text if len(text) <= limit else text[:limit] + "\n... (truncated)"


def render_run_report(run_dir: Path, manifest: Dict[str, Any], metrics: Dict[str, Any]) -> str:
    run_id = metrics.get("run_id") or manifest.get("run_id") or run_dir.name
    status = str(metrics.get("status", "unknown"))
    colour = STATUS_COLOURS.get(status, "#4a5a6b")
    energetics = metrics.get("energetics", {}) or {}
    problems = metrics.get("problems", []) or []

    cards = [
        ("Status", f"<span style='color:{colour};font-weight:700'>{html.escape(status)}</span>"),
        ("System / stage", html.escape(f"{manifest.get('system', 'n/a')} / {manifest.get('stage', 'n/a')}")),
        ("Calculation", html.escape(str(manifest.get("calc_type", "n/a")))),
        ("E0 (eV)", html.escape(_fmt(energetics.get("energy_sigma0_eV")))),
        ("E0 / atom (eV)", html.escape(_fmt(energetics.get("energy_per_atom_eV")))),
        ("Slurm job", html.escape(_fmt((manifest.get("hpc") or {}).get("job_id")))),
    ]
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'/>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'/>",
        f"<title>{html.escape(run_id)}</title><style>{_CSS}</style></head><body>",
        f"<h1>{html.escape(run_id)}</h1>",
        f"<p class='meta'>{html.escape(str(manifest.get('objective', '')))}<br/>Report generated {utc_now()} "
        f"from manifest.json + metrics.json</p>",
        "<div class='cards'>" + "".join(f"<div class='card'><b>{k}</b>{v}</div>" for k, v in cards) + "</div>",
    ]
    if problems:
        items = "".join(f"<li>{html.escape(p)}</li>" for p in problems)
        parts.append(f"<h2>Problems</h2><ul class='problems'>{items}</ul>")
    parts += [
        "<h2>Convergence checks</h2>",
        _table((metrics.get("checks") or {}).items(), ("Check", "Passed")),
        "<h2>Energetics</h2>",
        _table(energetics.items()),
        "<h2>Calculation details</h2>",
        _table((metrics.get("calculation") or {}).items()),
    ]
    if metrics.get("vibrations"):
        vib = metrics["vibrations"]
        modes = [
            (f"mode {i + 1}", f"{m['meV']:.2f} meV{' (imaginary)' if m['imaginary'] else ''}")
            for i, m in enumerate(vib.get("modes", []))
        ]
        parts += ["<h2>Vibrational modes</h2>", _table(modes, ("Mode", "Energy"))]
    if metrics.get("structure_check"):
        parts += ["<h2>Final structure check</h2>", _table(metrics["structure_check"].items())]
    parts += [
        "<h2>Structure</h2>",
        _table((manifest.get("structure") or {}).items()),
        "<h2>POTCAR datasets</h2>",
        _table(
            (
                (p.get("element"), f"{p.get('titel')} (ENMAX {p.get('enmax_eV')} eV)")
                for p in manifest.get("potcars", [])
            ),
            ("Element", "Dataset"),
        ),
        "<h2>INCAR</h2>",
        f"<pre>{html.escape(_read_text(run_dir / 'inputs' / 'INCAR'))}</pre>",
        "<h2>KPOINTS</h2>",
        f"<pre>{html.escape(_read_text(run_dir / 'inputs' / 'KPOINTS'))}</pre>",
        "<h2>Provenance</h2>",
        _table(
            [
                ("config", (manifest.get("config") or {}).get("source")),
                ("git commit", (manifest.get("git") or {}).get("commit")),
                ("git dirty", (manifest.get("git") or {}).get("dirty")),
                ("VASP version", (manifest.get("vasp") or {}).get("version")),
                ("input hash", (manifest.get("inputs") or {}).get("input_hash")),
            ]
        ),
        "<h2>Event history</h2>",
        _events_table(manifest.get("events", [])),
        "</body></html>\n",
    ]
    return "".join(parts)


def write_run_report(run_dir: Path) -> Path:
    """(Re)write ``report.html`` from the JSON files in ``run_dir``."""

    output = run_dir / "report.html"
    output.write_text(
        render_run_report(run_dir, read_json(run_dir / "manifest.json"), read_json(run_dir / "metrics.json")),
        encoding="utf-8",
    )
    return output
