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

    # Fail fast with a clear message instead of grinding through doomed API
    # calls when required configuration is missing.
    problems = cfg.validate()
    if problems:
        print("[config] cannot run — fix the following:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nSet these as environment variables or in a local .env file "
            "(see .env.example).",
            file=sys.stderr,
        )
        return 1

    result = run(cfg)
    print(f"[done] {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
