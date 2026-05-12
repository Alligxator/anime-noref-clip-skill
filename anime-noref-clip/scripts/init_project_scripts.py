#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "templates" / "project"


def copy_file(src: Path, dst: Path, *, force: bool) -> str:
    if dst.exists() and not force:
        return "skipped"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return "copied"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize project-local anime-noref-clip tools from the skill template."
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="overwrite existing project tools")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    if not TEMPLATE_ROOT.exists():
        raise RuntimeError(f"missing template root: {TEMPLATE_ROOT}")

    results: list[tuple[str, str]] = []
    for src in sorted(TEMPLATE_ROOT.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(TEMPLATE_ROOT)
        status = copy_file(src, project_root / rel, force=args.force)
        results.append((status, rel.as_posix()))

    validator_src = SKILL_ROOT / "scripts" / "validate_workflow_state.py"
    status = copy_file(
        validator_src,
        project_root / "tools" / "validate_workflow_state.py",
        force=args.force,
    )
    results.append((status, "tools/validate_workflow_state.py"))

    for script_name in ("resolve_story_style.py", "validate_story_styles.py"):
        script_src = SKILL_ROOT / "scripts" / script_name
        if script_src.exists():
            status = copy_file(
                script_src,
                project_root / "tools" / script_name,
                force=args.force,
            )
            results.append((status, f"tools/{script_name}"))

    for rel in ("story_styles.json", "story_styles.schema.json", "workflow_defaults.json"):
        ref_src = SKILL_ROOT / "references" / rel
        if ref_src.exists():
            status = copy_file(
                ref_src,
                project_root / "references" / rel,
                force=args.force,
            )
            results.append((status, f"references/{rel}"))

    for status, rel in results:
        print(f"{status}\t{rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
