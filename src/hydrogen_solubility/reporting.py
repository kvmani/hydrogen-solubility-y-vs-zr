"""Human-readable run reporting utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import html
import json
from typing import Any


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _fmt_scalar(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.8f}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


def _status_class(status: str) -> str:
    lowered = status.strip().lower()
    if lowered in {"success", "ok"}:
        return "status-ok"
    if lowered in {"partial", "initialized", "warn"}:
        return "status-warn"
    return "status-fail"


def _render_events(events: list[dict[str, Any]]) -> str:
    if not events:
        return "<p>No execution events recorded.</p>"

    rows: list[str] = []
    for event in events:
        rows.append(
            "<tr>"
            f"<td>{html.escape(_fmt_scalar(event.get('timestamp_utc')))}</td>"
            f"<td>{html.escape(_fmt_scalar(event.get('mode')))}</td>"
            f"<td>{html.escape(_fmt_scalar(event.get('event')))}</td>"
            f"<td>{html.escape(_fmt_scalar(event.get('status')))}</td>"
            f"<td>{html.escape(_fmt_scalar(event.get('message')))}</td>"
            f"<td>{html.escape(_fmt_scalar(event.get('log_path')))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Timestamp (UTC)</th><th>Mode</th><th>Event</th><th>Status</th><th>Message</th><th>Log Path</th></tr></thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _render_artifacts(artifacts: dict[str, Any]) -> str:
    if not artifacts:
        return "<p>No artifact paths available.</p>"
    rows: list[str] = []
    for key in sorted(artifacts.keys()):
        value = artifacts.get(key)
        value_text = _fmt_scalar(value)
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(key))}</td>"
            f"<td>{html.escape(value_text)}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Artifact</th><th>Path</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def render_run_report(
    *,
    run_dir: Path,
    manifest: dict[str, Any],
    metrics: dict[str, Any],
) -> str:
    """Render a deterministic HTML report for one run directory."""

    run_id = str(metrics.get("run_id") or manifest.get("run_id") or run_dir.name)
    stage = str(manifest.get("stage") or "n/a")
    system = str(manifest.get("system") or "n/a")
    objective = str(manifest.get("objective") or "n/a")
    status = str(metrics.get("status") or "unknown")
    status_css = _status_class(status)

    energetic = metrics.get("energetics", {})
    if not isinstance(energetic, dict):
        energetic = {}
    checks = metrics.get("checks", {})
    if not isinstance(checks, dict):
        checks = {}
    events = manifest.get("execution_events", [])
    if not isinstance(events, list):
        events = []
    inputs = manifest.get("inputs", {})
    if not isinstance(inputs, dict):
        inputs = {}
    artifacts = metrics.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}

    input_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(key))}</td>"
        f"<td>{html.escape(_fmt_scalar(inputs.get(key)))}</td>"
        "</tr>"
        for key in sorted(inputs.keys())
    ) or "<tr><td colspan='2'>n/a</td></tr>"

    check_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(key))}</td>"
        f"<td>{html.escape(_fmt_scalar(checks.get(key)))}</td>"
        "</tr>"
        for key in sorted(checks.keys())
    ) or "<tr><td colspan='2'>n/a</td></tr>"

    report_generated = _iso_now()
    return "".join(
        [
            "<!doctype html><html><head><meta charset='utf-8'/>",
            f"<title>Run Report - {html.escape(run_id)}</title>",
            "<style>",
            "body{font-family:Arial,sans-serif;margin:18px;background:#f7f9fc;color:#1a2430;line-height:1.35;}",
            "h1,h2{margin:10px 0 8px 0;}",
            ".cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;}",
            ".card{background:#fff;border:1px solid #cbd6e2;border-radius:6px;padding:10px;}",
            "table{border-collapse:collapse;width:100%;background:#fff;margin:8px 0 14px 0;}",
            "th,td{border:1px solid #cbd6e2;padding:6px 8px;text-align:left;vertical-align:top;}",
            "th{background:#eaf0f7;}",
            ".status{font-weight:700;}",
            ".status-ok{color:#0a7a2f;}",
            ".status-warn{color:#8a5a00;}",
            ".status-fail{color:#9f1c1c;}",
            ".meta{font-size:12px;color:#4a5a6b;}",
            "</style></head><body>",
            f"<h1>Run Report: {html.escape(run_id)}</h1>",
            f"<p class='meta'>Generated UTC: {html.escape(report_generated)} | Run Dir: {html.escape(str(run_dir))}</p>",
            "<div class='cards'>",
            "<div class='card'>",
            "<b>Status</b><br/>",
            f"<span class='status {status_css}'>{html.escape(status)}</span>",
            "</div>",
            f"<div class='card'><b>Stage</b><br/>{html.escape(stage)}</div>",
            f"<div class='card'><b>System</b><br/>{html.escape(system)}</div>",
            f"<div class='card'><b>Objective</b><br/>{html.escape(objective)}</div>",
            f"<div class='card'><b>Total Energy (eV)</b><br/>{html.escape(_fmt_scalar(energetic.get('total_energy_eV')))}</div>",
            f"<div class='card'><b>Energy / Atom (eV)</b><br/>{html.escape(_fmt_scalar(energetic.get('energy_per_atom_eV')))}</div>",
            "</div>",
            "<h2>Convergence Checks</h2>",
            "<table><thead><tr><th>Check</th><th>Value</th></tr></thead><tbody>",
            check_rows,
            "</tbody></table>",
            "<h2>Input Snapshot</h2>",
            "<table><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>",
            input_rows,
            "</tbody></table>",
            "<h2>Artifacts</h2>",
            _render_artifacts(artifacts),
            "<h2>Execution Events</h2>",
            _render_events([event for event in events if isinstance(event, dict)]),
            "</body></html>\n",
        ]
    )


def write_run_report(
    run_dir: str | Path,
    *,
    manifest: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    output_name: str = "report.html",
) -> Path:
    """Write ``report.html`` in a run directory and return its path."""

    run_path = Path(run_dir).expanduser().resolve()
    run_path.mkdir(parents=True, exist_ok=True)
    manifest_payload = dict(manifest) if isinstance(manifest, dict) else _safe_load_json(run_path / "manifest.json")
    metrics_payload = dict(metrics) if isinstance(metrics, dict) else _safe_load_json(run_path / "metrics.json")
    output_path = run_path / output_name
    output_path.write_text(
        render_run_report(run_dir=run_path, manifest=manifest_payload, metrics=metrics_payload),
        encoding="utf-8",
    )
    return output_path
