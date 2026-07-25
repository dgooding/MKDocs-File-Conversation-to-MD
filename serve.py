#!/usr/bin/env python3
"""
Start the all-in-one converter + site server.

  python serve.py
  python serve.py --build   # run mkdocs build first
  python serve.py --port 8080
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build_docs() -> None:
    print("Building MkDocs site…")
    subprocess.check_call(
        [sys.executable, "-m", "mkdocs", "build", "--clean"],
        cwd=ROOT,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="MkDocs File→MD all-in-one server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--build", action="store_true", help="Run mkdocs build before serve")
    parser.add_argument("--reload", action="store_true", help="Dev auto-reload")
    args = parser.parse_args()

    if args.build:
        build_docs()

    try:
        import uvicorn
    except ImportError:
        print("Install dependencies first:\n  python -m venv .venv\n  .\\.venv\\Scripts\\activate\n  pip install -r requirements.txt")
        sys.exit(1)

    print(f"\n  Converter UI : http://{args.host}:{args.port}/convert/")
    print(f"  Docs / site  : http://{args.host}:{args.port}/")
    print(f"  API health   : http://{args.host}:{args.port}/api/health\n")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=str(ROOT),
    )


if __name__ == "__main__":
    main()
