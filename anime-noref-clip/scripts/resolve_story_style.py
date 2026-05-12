#!/usr/bin/env python3
"""Resolve a story style alias and optionally patch workflow_state.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = SKILL_ROOT / "references" / "story_styles.json"
DEFAULT_WORKFLOW_DEFAULTS = SKILL_ROOT / "references" / "workflow_defaults.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_decision_defaults(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_json(path)
    defaults = payload.get("decision_defaults", {})
    if not isinstance(defaults, dict):
        raise SystemExit(f"workflow defaults must contain decision_defaults object: {path}")
    return defaults


def resolve_style(config: dict[str, Any], requested: str | None) -> tuple[str, dict[str, Any]]:
    styles = config.get("styles", {})
    default_style = config.get("default_style")
    key = (requested or default_style or "").strip()
    if key in styles:
        return key, styles[key]
    normalized = key.lower()
    for style_id, style in styles.items():
        aliases = [str(alias).lower() for alias in style.get("aliases", [])]
        if normalized in aliases:
            return style_id, style
    raise SystemExit(f"unknown story style {requested!r}; available: {', '.join(sorted(styles))}")


def scaled_shot_count(style: dict[str, Any], target_duration_sec: float) -> tuple[int, int]:
    qc = style.get("creative_qc_profile", {})
    base_range = qc.get("selected_shot_count_60s") or style.get("decision_overlay", {}).get("target_shot_count_60s") or [25, 35]
    scale = max(0.1, float(target_duration_sec) / 60.0)
    lo = max(1, round(float(base_range[0]) * scale))
    hi = max(lo, round(float(base_range[1]) * scale))
    return lo, hi


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve story style and update workflow_state.json.")
    parser.add_argument("--style", default="", help="Style id or alias. Defaults to config default_style.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--workflow-defaults", type=Path, default=DEFAULT_WORKFLOW_DEFAULTS)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--state", default="workflow_state.json")
    parser.add_argument("--write", action="store_true", help="Write the resolved style into workflow_state.json.")
    parser.add_argument("--preserve-existing-overrides", action="store_true", help="Keep existing differing decisions and record style_overrides.")
    args = parser.parse_args()

    config_path = args.config.expanduser().resolve()
    config = load_json(config_path)
    workflow_defaults_path = args.workflow_defaults.expanduser().resolve()
    workflow_defaults = load_decision_defaults(workflow_defaults_path)
    style_id, style = resolve_style(config, args.style or None)
    anchor = f"{config.get('style_anchor_base', 'references/story_styles.json#styles/')}{style_id}"
    overlay = dict(style.get("decision_overlay", {}))
    target_duration = float(overlay.get("target_duration_sec", 60))
    shot_min, shot_max = scaled_shot_count(style, target_duration)

    resolved = {
        "story_style": style_id,
        "story_style_preset": anchor,
        "story_style_label": style.get("label", style_id),
        "decision_overlay": overlay,
        "target_shot_count_min": shot_min,
        "target_shot_count_max": shot_max,
        "style_config": "references/story_styles.json",
        "workflow_defaults": workflow_defaults,
    }

    if not args.write:
        print(json.dumps(resolved, ensure_ascii=False, indent=2))
        return 0

    root = args.project_root.expanduser().resolve()
    state_path = root / args.state
    state = load_json(state_path) if state_path.exists() else {}
    state["skill_version"] = "v1.4.13"
    decisions = state.setdefault("decisions", {})
    checks = state.setdefault("checks", {})
    artifacts = state.setdefault("artifacts", {})

    overrides = []
    for key, value in overlay.items():
        current = decisions.get(key)
        if args.preserve_existing_overrides and current not in (None, value):
            overrides.append({"field": key, "preset_value": value, "final_value": current, "reason": "preserved existing workflow_state decision"})
            continue
        decisions[key] = value

    for key, value in workflow_defaults.items():
        decisions[key] = value

    target_duration = float(decisions.get("target_duration_sec", overlay.get("target_duration_sec", 60)))
    shot_min, shot_max = scaled_shot_count(style, target_duration)

    decisions["story_style"] = style_id
    decisions["story_style_preset"] = anchor
    decisions["story_style_label"] = style.get("label", style_id)
    decisions["story_style_config"] = "references/story_styles.json"
    if overrides:
        decisions["story_style_overrides"] = overrides
    artifacts["story_styles_config"] = "references/story_styles.json"
    checks["story_style_preset_resolved"] = True
    checks["target_shot_count_min"] = shot_min
    checks["target_shot_count_max"] = shot_max

    resolved["target_shot_count_min"] = shot_min
    resolved["target_shot_count_max"] = shot_max
    write_json(state_path, state)
    print(json.dumps({"updated": state_path.as_posix(), **resolved}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
