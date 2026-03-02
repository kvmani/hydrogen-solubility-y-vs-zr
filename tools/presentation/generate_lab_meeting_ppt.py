#!/usr/bin/env python3
"""One-command runner: draft manifest + build PPTX + convert to PDF."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a lab-meeting deck (.pptx + .pdf) from research artifacts in one command."
    )
    parser.add_argument("--scan-root", required=True, help="Root directory containing artifacts.")
    parser.add_argument(
        "--output-dir",
        default="presentations",
        help="Directory to write manifest, PPTX, and PDF (default: presentations).",
    )
    parser.add_argument(
        "--deck-title",
        default=None,
        help="Deck title (default: '<scan-root-name> Results Summary').",
    )
    parser.add_argument(
        "--basename",
        default=None,
        help="Base output filename without extension (default: derived from deck title).",
    )
    parser.add_argument("--max-results", type=int, default=8, help="Max discovered result slides.")
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Skip PPTX-to-PDF conversion.",
    )
    parser.add_argument(
        "--require-pdf",
        action="store_true",
        help="Fail if PDF conversion cannot be completed.",
    )
    return parser.parse_args()


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "results-summary"


def detect_soffice() -> str | None:
    candidates = [
        shutil.which("soffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def convert_to_pdf(ppt_path: Path, output_dir: Path) -> Path | None:
    soffice = detect_soffice()
    if not soffice:
        return None

    subprocess.run(
        [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(ppt_path),
        ],
        check=True,
    )

    pdf_path = output_dir / f"{ppt_path.stem}.pdf"
    return pdf_path if pdf_path.exists() else None


def main() -> None:
    args = parse_args()

    scan_root = Path(args.scan_root).expanduser().resolve()
    if not scan_root.exists() or not scan_root.is_dir():
        raise SystemExit(f"scan root does not exist or is not a directory: {scan_root}")

    deck_title = args.deck_title or f"{scan_root.name} Results Summary"
    base = args.basename or slugify(deck_title)

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / f"{base}_manifest.json"
    ppt_path = output_dir / f"{base}.pptx"

    scripts_dir = Path(__file__).resolve().parent
    draft_script = scripts_dir / "draft_manifest.py"
    build_script = scripts_dir / "build_ppt_from_manifest.py"

    subprocess.run(
        [
            sys.executable,
            str(draft_script),
            "--scan-root",
            str(scan_root),
            "--output",
            str(manifest_path),
            "--deck-title",
            deck_title,
            "--max-results",
            str(max(1, args.max_results)),
        ],
        check=True,
    )

    subprocess.run(
        [
            sys.executable,
            str(build_script),
            "--manifest",
            str(manifest_path),
            "--output",
            str(ppt_path),
        ],
        check=True,
    )

    pdf_path = None
    if not args.skip_pdf:
        try:
            pdf_path = convert_to_pdf(ppt_path=ppt_path, output_dir=output_dir)
        except subprocess.CalledProcessError as exc:
            if args.require_pdf:
                raise SystemExit(f"PPTX-to-PDF conversion failed: {exc}") from exc
            print(f"[warn] PPTX-to-PDF conversion failed: {exc}")

    if not args.skip_pdf and not pdf_path:
        msg = "No PDF generated (LibreOffice/soffice not available)."
        if args.require_pdf:
            raise SystemExit(msg)
        print(f"[warn] {msg}")

    print(f"[ok] deck title: {deck_title}")
    print(f"[ok] manifest: {manifest_path}")
    print(f"[ok] pptx: {ppt_path}")
    if pdf_path:
        print(f"[ok] pdf: {pdf_path}")


if __name__ == "__main__":
    main()
