#!/usr/bin/env python3
"""PaperSage entrypoint.

Usage:
    python main.py            # fetch, summarize, and email the digest
    DRY_RUN=1 python main.py  # print the report instead of emailing
"""
from __future__ import annotations

import sys

from papersage.config import load_config
from papersage.pipeline import run


def main() -> int:
    cfg = load_config()
    result = run(cfg)
    print(f"[done] {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
