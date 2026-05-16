#!/usr/bin/env python3
"""Smoke tests for the v1.4.14 story-style schema and CI cleanup."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_python(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, *(str(arg) for arg in args)],
        cwd=SKILL_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def minimal_story_state() -> dict[str, Any]:
    return {
        "skill_version": "v1.4.12",
        "current_phase": "story_style",
        "decisions": {
            "cut_strategy": "detailed",
        },
        "approvals": {
            "cut_strategy": True,
        },
        "artifacts": {
            "shot_metadata": "shots.json",
            "frame_extract_report": "analysis/frame_extract_report.json",
            "visual_tags": "shot_story_tags.json",
        },
        "checks": {
            "project_tools_initialized_from_skill_template": True,
            "project_tools_copied_from_old_project": False,
            "frame_extract_complete": True,
            "frame_extract_missing_count": 0,
            "frame_extract_saved_images": 12,
            "frame_extract_expected_images": 12,
            "long_shot_multi_sample_done": True,
            "render_level_duration_splits_absent": True,
            "gpt_visual_tagging_done": True,
            "black_fade_metadata": True,
        },
    }


def main() -> int:
    run_python("scripts/validate_story_styles.py")

    help_result = run_python("scripts/validate_workflow_state.py", "--help")
    if "style" not in help_result.stdout:
        raise AssertionError("--gate style is missing from validate_workflow_state.py --help")

    story_styles = json.loads((SKILL_ROOT / "references" / "story_styles.json").read_text(encoding="utf-8"))
    required_guide_keys = {"tone", "opening_rotation", "example_lines", "bad_good_examples"}
    for style_id, style in story_styles["styles"].items():
        guide = style.get("script_style_guide")
        if not isinstance(guide, dict):
            raise AssertionError(f"{style_id} missing script_style_guide")
        missing = required_guide_keys - set(guide)
        if missing:
            raise AssertionError(f"{style_id} script_style_guide missing keys: {sorted(missing)}")
        if not guide.get("example_lines"):
            raise AssertionError(f"{style_id} script_style_guide.example_lines must be non-empty")
        if not guide.get("bad_good_examples"):
            raise AssertionError(f"{style_id} script_style_guide.bad_good_examples must be non-empty")

    natural = json.loads(run_python("scripts/resolve_story_style.py", "--style", "natural").stdout)
    if natural["story_style"] != "style_02_natural_plot_explanation":
        raise AssertionError("natural alias did not resolve to style_02_natural_plot_explanation")

    spectacle = json.loads(run_python("scripts/resolve_story_style.py", "--style", "spectacle").stdout)
    if spectacle["story_style"] != "style_06_spectacle_escalation_commentary":
        raise AssertionError("spectacle alias did not resolve to style_06_spectacle_escalation_commentary")

    spectacle_cn = json.loads(run_python("scripts/resolve_story_style.py", "--style", "奇观解说").stdout)
    if spectacle_cn["story_style"] != "style_06_spectacle_escalation_commentary":
        raise AssertionError("奇观解说 alias did not resolve to style_06_spectacle_escalation_commentary")

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1414_state_") as tmp:
        root = Path(tmp)
        state_path = root / "workflow_state.json"
        write_json(state_path, minimal_story_state())
        run_python(
            "scripts/resolve_story_style.py",
            "--style",
            "natural",
            "--project-root",
            root,
            "--write",
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        decisions = state["decisions"]
        artifacts = state["artifacts"]
        checks = state["checks"]
        assert state["skill_version"] == "v1.4.14"
        assert decisions["story_style"] == "style_02_natural_plot_explanation"
        assert decisions["story_style_config"] == "references/story_styles.json"
        assert decisions["source_buffer_policy"] == "stable_subwindow_only_no_cross_cut_tail_buffer"
        assert decisions["ip_reference_policy"] == "hide_ip_names_unless_user_explicitly_requests"
        assert artifacts["story_styles_config"] == "references/story_styles.json"
        assert checks["target_shot_count_min"] == 18
        assert checks["target_shot_count_max"] == 28
        run_python(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "style",
            "--no-exists",
        )

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1414_spectacle_state_") as tmp:
        root = Path(tmp)
        state_path = root / "workflow_state.json"
        write_json(state_path, minimal_story_state())
        run_python(
            "scripts/resolve_story_style.py",
            "--style",
            "spectacle",
            "--project-root",
            root,
            "--write",
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        decisions = state["decisions"]
        checks = state["checks"]
        assert decisions["story_style"] == "style_06_spectacle_escalation_commentary"
        assert decisions["ip_reference_policy"] == "hide_ip_names_unless_user_explicitly_requests"
        assert checks["target_shot_count_min"] == 22
        assert checks["target_shot_count_max"] == 34

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1414_init_") as tmp:
        root = Path(tmp)
        run_python("scripts/init_project_scripts.py", "--project-root", root)
        required = [
            "tools/validate_workflow_state.py",
            "tools/resolve_story_style.py",
            "tools/validate_story_styles.py",
            "references/story_styles.json",
            "references/story_styles.schema.json",
            "references/workflow_defaults.json",
        ]
        missing = [rel for rel in required if not (root / rel).exists()]
        if missing:
            raise AssertionError(f"project initializer missing files: {missing}")

    print("PASS v1.4.14 smoke test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
