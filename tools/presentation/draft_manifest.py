#!/usr/bin/env python3
"""Draft a scientific presentation manifest from research artifact folders."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".bmp", ".tif", ".tiff", ".gif", ".webp"}
JSON_EXTS = {".json"}
HTML_EXTS = {".html", ".htm"}
IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "build",
    "dist",
    ".mypy_cache",
    ".pytest_cache",
}
METRIC_KEYWORDS = (
    "energy",
    "free_energy",
    "enthalpy",
    "entropy",
    "formation",
    "solution",
    "barrier",
    "diffusion",
    "converged",
    "convergence",
    "encut",
    "kpoint",
    "kmesh",
    "force",
    "stress",
    "volume",
    "lattice",
    "hydrogen",
    "solubility",
    "tss",
    "temperature",
    "pressure",
    "rmse",
    "mae",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draft a JSON manifest for research-results presentations.")
    parser.add_argument("--scan-root", required=True, help="Root directory containing experiment artifacts.")
    parser.add_argument("--output", required=True, help="Output manifest JSON path.")
    parser.add_argument(
        "--deck-title",
        default=None,
        help="Optional deck title. Defaults to '<scan-root-name> Results Summary'.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=8,
        help="Maximum number of result slides to include from discovered figures.",
    )
    return parser.parse_args()


def clean_title(text: str) -> str:
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Untitled"
    return text[0].upper() + text[1:]


def clean_phrase(text: str) -> str:
    text = text.replace("/", " > ")
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Value"
    return text[0].upper() + text[1:]


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value == 0:
            return "0"
        if abs(value) >= 1_000_000 or abs(value) < 1e-3:
            return f"{value:.3e}"
        return f"{value:.4g}"
    return str(value)


def iter_numeric_values(obj: Any, prefix: str = "") -> Iterable[Tuple[str, float]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            next_prefix = f"{prefix}/{key}" if prefix else str(key)
            yield from iter_numeric_values(value, next_prefix)
        return
    if isinstance(obj, list):
        for idx, value in enumerate(obj[:50]):
            next_prefix = f"{prefix}[{idx}]"
            yield from iter_numeric_values(value, next_prefix)
        return
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield prefix or "value", float(obj)


def metric_score(key: str) -> int:
    low = key.lower()
    score = 0
    for keyword in METRIC_KEYWORDS:
        if keyword in low:
            score += 3
    for hint in ("val", "test", "best", "mean", "avg", "final"):
        if hint in low:
            score += 1
    return score


def parse_json_metrics(path: Path, max_metrics: int = 6) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        data = json.loads(path.read_text(errors="ignore"))
    except Exception as exc:  # pragma: no cover - defensive
        return {"path": str(path), "metrics": [], "error": str(exc)}

    candidates: List[Tuple[int, str, float]] = []
    fallback: List[Tuple[str, float]] = []

    for key, value in iter_numeric_values(data):
        if not math.isfinite(value):
            continue
        fallback.append((key, value))
        score = metric_score(key)
        if score > 0:
            candidates.append((score, key, value))

    ranked = sorted(candidates, key=lambda x: (-x[0], len(x[1]), x[1]))
    selected: List[Dict[str, Any]] = []
    seen = set()

    for _, key, value in ranked:
        short = key[-120:]
        if short in seen:
            continue
        seen.add(short)
        selected.append({"name": key, "value": value})
        if len(selected) >= max_metrics:
            break

    if not selected:
        for key, value in fallback[:max_metrics]:
            selected.append({"name": key, "value": value})

    return {"path": str(path), "metrics": selected}


def parse_html_title(path: Path) -> Optional[str]:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    match = re.search(r"<title[^>]*>(.*?)</title>", content, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return title or None


def discover_files(root: Path) -> Tuple[List[Path], List[Path], List[Path]]:
    images: List[Path] = []
    json_files: List[Path] = []
    html_files: List[Path] = []

    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        current_path = Path(current)

        for filename in files:
            if filename.startswith("."):
                continue
            path = current_path / filename
            suffix = path.suffix.lower()
            if suffix in IMAGE_EXTS:
                low_name = path.name.lower()
                if "logo" in low_name or "icon" in low_name or "thumb" in low_name:
                    continue
                images.append(path)
            elif suffix in JSON_EXTS:
                json_files.append(path)
            elif suffix in HTML_EXTS:
                html_files.append(path)

    images.sort()
    json_files.sort()
    html_files.sort()
    return images, json_files, html_files


def build_directory_index(paths: List[Path]) -> Dict[Path, List[Path]]:
    index: Dict[Path, List[Path]] = {}
    for path in paths:
        index.setdefault(path.parent, []).append(path)
    return index


def nearest_paths(start: Path, root: Path, by_dir: Dict[Path, List[Path]], max_items: int = 2) -> List[Path]:
    out: List[Path] = []
    cur = start.parent
    root = root.resolve()

    while True:
        if cur in by_dir:
            out.extend(by_dir[cur])
            if len(out) >= max_items:
                break

        if cur == root:
            break
        if root not in cur.parents:
            break
        cur = cur.parent

    return out[:max_items]


def to_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def choose_first_by_name(paths: List[Path], tokens: Tuple[str, ...]) -> Optional[Path]:
    for path in paths:
        low = path.name.lower()
        if any(token in low for token in tokens):
            return path
    return None


def result_slide_from_image(
    image_path: Path,
    root: Path,
    json_index: Dict[Path, List[Path]],
    html_index: Dict[Path, List[Path]],
    json_summaries: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    slide_title = clean_title(image_path.stem)
    bullets: List[str] = [f"Figure: {clean_title(image_path.stem)}"]

    nearest_json = nearest_paths(image_path, root, json_index, max_items=1)
    nearest_html = nearest_paths(image_path, root, html_index, max_items=1)

    source_files: List[str] = [to_rel(image_path, root)]

    bottom_line = "This figure captures an important quantitative result."

    if nearest_json:
        summary = json_summaries.get(str(nearest_json[0]))
        if summary:
            metrics = summary.get("metrics", [])[:4]
            for metric in metrics:
                metric_name = clean_phrase(str(metric.get("name", "metric")).split("/")[-1])
                metric_value = format_value(metric.get("value"))
                bullets.append(f"{metric_name}: {metric_value}")
            if metrics:
                top_metric = metrics[0]
                top_name = clean_phrase(str(top_metric.get("name", "metric")).split("/")[-1])
                top_value = format_value(top_metric.get("value"))
                bottom_line = f"{top_name} is {top_value} for this result."

        source_files.append(to_rel(nearest_json[0], root))

    if nearest_html:
        html_title = parse_html_title(nearest_html[0])
        if html_title:
            bullets.append(f"HTML summary: {html_title}")
        source_files.append(to_rel(nearest_html[0], root))

    bullets.append(f"Source folder: {to_rel(image_path.parent, root)}")
    bullets = bullets[:6]

    return {
        "section": "result",
        "title": slide_title,
        "bullets": bullets,
        "figure": to_rel(image_path, root),
        "bottom_line": bottom_line,
        "source_files": source_files,
    }


def build_manifest(root: Path, deck_title: str, max_results: int) -> Dict[str, Any]:
    images, json_files, html_files = discover_files(root)

    json_index = build_directory_index(json_files)
    html_index = build_directory_index(html_files)

    json_summaries: Dict[str, Dict[str, Any]] = {}
    for path in json_files:
        json_summaries[str(path)] = parse_json_metrics(path)

    methodology_figure = choose_first_by_name(images, ("pipeline", "workflow", "method", "architecture", "overview"))
    equation_figure = choose_first_by_name(images, ("equation", "formula", "objective", "loss", "math", "eq"))

    result_images: List[Path] = []
    for image in images:
        if image in {methodology_figure, equation_figure}:
            continue
        result_images.append(image)
        if len(result_images) >= max_results:
            break

    slides: List[Dict[str, Any]] = []

    slides.append(
        {
            "section": "objective",
            "title": "Objective and Scope",
            "bullets": [
                "State the Y-vs-Zr hydrogen solubility question.",
                "Define stage scope and assumptions for this run batch.",
                "Specify quantitative pass/fail targets and evidence sources.",
            ],
            "figure": to_rel(methodology_figure, root) if methodology_figure else None,
            "bottom_line": "Objective and scope define the decision criteria for this update.",
            "source_files": [to_rel(methodology_figure, root)] if methodology_figure else [],
        }
    )

    slides.append(
        {
            "section": "methodology",
            "title": "Methodology Overview",
            "bullets": [
                "Summarize DFT/thermodynamic workflow and run stages.",
                "List config, convergence, and provenance controls used.",
                "Describe comparison protocol for Y versus Zr outputs.",
            ],
            "figure": to_rel(methodology_figure, root) if methodology_figure else None,
            "bottom_line": "Methodology links reproducible inputs to defensible conclusions.",
            "source_files": [to_rel(methodology_figure, root)] if methodology_figure else [],
        }
    )

    slides.append(
        {
            "section": "equations",
            "title": "Core Equations",
            "bullets": [
                "Show governing equations and variable definitions.",
                "Highlight assumptions and thermodynamic reference states.",
                "Connect equations to extracted metrics and benchmark data.",
            ],
            "figure": to_rel(equation_figure, root) if equation_figure else None,
            "bottom_line": "Equation choices determine interpretation of Y-vs-Zr contrast.",
            "source_files": [to_rel(equation_figure, root)] if equation_figure else [],
        }
    )

    for image_path in result_images:
        slides.append(result_slide_from_image(image_path, root, json_index, html_index, json_summaries))

    conclusion_sources: List[str] = []
    conclusion_figure = result_images[0] if result_images else None
    if conclusion_figure:
        conclusion_sources.append(to_rel(conclusion_figure, root))

    slides.append(
        {
            "section": "conclusion",
            "title": "Conclusions and Next Steps",
            "bullets": [
                "Summarize strongest quantitative findings from this update.",
                "State limitations, unresolved uncertainty, and risks.",
                "List immediate next runs and decisions required.",
            ],
            "figure": to_rel(conclusion_figure, root) if conclusion_figure else None,
            "bottom_line": "Results define clear next actions for the roadmap stage gate.",
            "source_files": conclusion_sources,
        }
    )

    return {
        "deck_title": deck_title,
        "scan_root": str(root.resolve()),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "style": {
            "font_name": "Arial",
            "title_font_size_pt": 24,
            "body_font_size_pt": 18,
            "bottom_line_font_size_pt": 20,
            "title_bar_bg": "000000",
            "title_text_color": "FFFFFF",
            "bottom_bar_bg": "000000",
            "bottom_text_color": "FFFFFF",
            "left_panel_fraction": 0.20,
        },
        "slides": slides,
        "sources": {
            "images": [to_rel(p, root) for p in images],
            "json": [to_rel(p, root) for p in json_files],
            "html": [to_rel(p, root) for p in html_files],
        },
    }


def main() -> None:
    args = parse_args()
    root = Path(args.scan_root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"scan root does not exist or is not a directory: {root}")

    deck_title = args.deck_title or f"{clean_title(root.name)} Results Summary"
    manifest = build_manifest(root=root, deck_title=deck_title, max_results=max(1, args.max_results))

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[ok] manifest written: {output_path}")
    print(f"[ok] total slides: {len(manifest.get('slides', []))}")


if __name__ == "__main__":
    main()
