"""CLI: python -m converter.cli file.pdf --out docs/converted/my-doc"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pdf_to_md import convert_pdf_to_markdown, slugify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert PDF to MkDocs-ready Markdown with images and formatting"
    )
    parser.add_argument("pdf", type=Path, help="Input PDF path")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: docs/converted/<slug>)",
    )
    parser.add_argument("--title", type=str, default=None, help="Document title")
    parser.add_argument("--slug", type=str, default=None, help="Output folder / file slug")
    args = parser.parse_args(argv)

    pdf: Path = args.pdf
    if not pdf.is_file():
        print(f"File not found: {pdf}", file=sys.stderr)
        return 1
    if pdf.suffix.lower() != ".pdf":
        print("Only PDF is supported by this CLI. Use the web UI for other types.", file=sys.stderr)
        return 1

    slug = args.slug or slugify(pdf.stem)
    root = Path(__file__).resolve().parents[1]
    out = args.out or (root / "docs" / "converted" / slug)
    out.mkdir(parents=True, exist_ok=True)

    result = convert_pdf_to_markdown(
        pdf,
        out,
        doc_slug=slug,
        title=args.title,
    )
    print(f"Markdown : {result['markdown_path']}")
    print(f"Images   : {result['images_dir']} ({result['image_count']} files)")
    print(f"Pages    : {result['page_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
