#!/usr/bin/env python3
"""Backward-compatible wrapper for the src/ package CLI.

The actual implementation lives in ``src/receipts_parser_poc/cli.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    src_path = repo_root / "src"
    sys.path.insert(0, str(src_path))

    from receipts_parser_poc.cli import main as _main  # type: ignore[import-not-found]

    _main()


if __name__ == "__main__":
    main()
