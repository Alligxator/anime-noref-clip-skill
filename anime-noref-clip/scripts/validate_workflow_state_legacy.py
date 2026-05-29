#!/usr/bin/env python3
"""Legacy validator entry for archived pre-v1.4.18 anime-noref-clip states.

Active production projects should use `validate_workflow_state.py`, which is
strict and only models the current workflow contract. This legacy entry is kept
outside the default production path so old archived states fail explicitly
instead of silently relaxing current gates.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Explain how to validate archived pre-v1.4.18 workflow states."
    )
    parser.add_argument("state", type=Path, help="Path to an archived workflow_state.json")
    parser.add_argument("--gate", default="compose", help="Accepted for CLI compatibility.")
    parser.add_argument("--no-exists", action="store_true", help="Accepted for CLI compatibility.")
    args = parser.parse_args()
    print(
        "FAIL legacy: pre-v1.4.18 compatibility validation is no longer part of "
        "the active anime-noref-clip production validator. Re-run the archived "
        "project with the matching historical skill checkout, or migrate the "
        f"state to v1.4.18 strict fields before validating: {args.state}"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
