#!/usr/bin/env python3
"""Validate machine-loadable anime-noref-clip story style presets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_STYLE_KEYS = {
    "preset_id",
    "label",
    "aliases",
    "use_when",
    "decision_overlay",
    "selection_bias",
    "avoid",
    "script_rules",
    "shot_mapping_rules",
    "creative_qc_profile",
}
REQUIRED_OVERLAY_KEYS = {
    "retention_mode",
    "hook_strategy",
    "nonlinear_teaser_allowed",
    "max_nonlinear_exceptions",
    "target_duration_sec",
    "script_density",
    "shot_energy",
    "cold_open_max_sec",
    "cold_open_allow_nonlinear",
    "post_hook_main_path",
    "post_hook_min_shot_duration",
    "dialogue_scene_min_shot_duration",
    "target_shot_count_60s",
    "hook_speed_range",
    "post_hook_speed_range",
    "absolute_non_hook_speed_range",
    "clone_padding_policy",
    "alignment_solve_order",
    "cold_open_policy",
}
REQUIRED_QC_KEYS = {
    "min_hook_candidates",
    "unsupported_claims_count",
    "generic_exposition_lines_max",
    "rehook_interval_max_sec",
    "cold_open_max_sec",
    "return_to_main_timeline_max_sec",
    "selected_shot_count_60s",
    "post_hook_min_shot_duration_sec",
    "dialogue_scene_min_shot_duration_sec",
    "post_hook_contiguous_source_blocks",
    "unique_shots",
    "op_ed_overlap_count",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, failures: list[str], message: str) -> None:
    if not condition:
        failures.append(message)


def validate_range(value: Any, failures: list[str], where: str) -> None:
    require(isinstance(value, list) and len(value) == 2, failures, f"{where} must be a two-item list")
    if not (isinstance(value, list) and len(value) == 2):
        return
    try:
        lo = float(value[0])
        hi = float(value[1])
    except (TypeError, ValueError):
        failures.append(f"{where} values must be numeric")
        return
    require(lo <= hi, failures, f"{where} min must be <= max")
    require(lo >= 0, failures, f"{where} min must be non-negative")


def validate(config: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    require(
        config.get("schema_version") == "anime-noref-clip.story_styles.v1.4.12",
        failures,
        "schema_version must be anime-noref-clip.story_styles.v1.4.12",
    )
    require(
        isinstance(config.get("style_anchor_base"), str) and bool(config.get("style_anchor_base")),
        failures,
        "style_anchor_base must be a non-empty string",
    )
    styles = config.get("styles")
    require(isinstance(styles, dict) and bool(styles), failures, "styles must be a non-empty object")
    if not isinstance(styles, dict):
        return failures

    default_style = config.get("default_style")
    require(default_style in styles, failures, "default_style must exist in styles")

    aliases: dict[str, str] = {}
    for style_id, style in styles.items():
        where = f"styles.{style_id}"
        require(isinstance(style, dict), failures, f"{where} must be object")
        if not isinstance(style, dict):
            continue
        missing = REQUIRED_STYLE_KEYS - set(style)
        require(not missing, failures, f"{where} missing keys: {sorted(missing)}")
        require(style.get("preset_id") == style_id, failures, f"{where}.preset_id must equal object key")
        require(bool(style.get("label")), failures, f"{where}.label must be non-empty")

        style_aliases = style.get("aliases", [])
        require(isinstance(style_aliases, list), failures, f"{where}.aliases must be list")
        if isinstance(style_aliases, list):
            for alias in style_aliases:
                require(isinstance(alias, str) and alias, failures, f"{where}.aliases contains invalid alias")
                normalized = alias.lower() if isinstance(alias, str) else ""
                if normalized in aliases:
                    failures.append(f"alias {alias!r} is used by both {aliases[normalized]} and {style_id}")
                elif normalized:
                    aliases[normalized] = style_id

        overlay = style.get("decision_overlay", {})
        require(isinstance(overlay, dict), failures, f"{where}.decision_overlay must be object")
        if isinstance(overlay, dict):
            missing_overlay = REQUIRED_OVERLAY_KEYS - set(overlay)
            require(not missing_overlay, failures, f"{where}.decision_overlay missing keys: {sorted(missing_overlay)}")
            validate_range(overlay.get("target_shot_count_60s"), failures, f"{where}.decision_overlay.target_shot_count_60s")
            validate_range(overlay.get("hook_speed_range"), failures, f"{where}.decision_overlay.hook_speed_range")
            validate_range(overlay.get("post_hook_speed_range"), failures, f"{where}.decision_overlay.post_hook_speed_range")
            validate_range(overlay.get("absolute_non_hook_speed_range"), failures, f"{where}.decision_overlay.absolute_non_hook_speed_range")
            if overlay.get("nonlinear_teaser_allowed") is False:
                require(overlay.get("max_nonlinear_exceptions") == 0, failures, f"{where} nonlinear=false requires max_nonlinear_exceptions=0")

        qc = style.get("creative_qc_profile", {})
        require(isinstance(qc, dict), failures, f"{where}.creative_qc_profile must be object")
        if isinstance(qc, dict):
            missing_qc = REQUIRED_QC_KEYS - set(qc)
            require(not missing_qc, failures, f"{where}.creative_qc_profile missing keys: {sorted(missing_qc)}")
            validate_range(qc.get("selected_shot_count_60s"), failures, f"{where}.creative_qc_profile.selected_shot_count_60s")
            require(int(qc.get("min_hook_candidates", 0)) >= 0, failures, f"{where}.creative_qc_profile.min_hook_candidates must be non-negative")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate story style preset config.")
    default_path = Path(__file__).resolve().parents[1] / "references" / "story_styles.json"
    parser.add_argument("config", type=Path, nargs="?", default=default_path)
    args = parser.parse_args()

    path = args.config.expanduser().resolve()
    if not path.exists():
        print(f"FAIL story styles: missing config {path}")
        return 1
    failures = validate(load_json(path))
    if failures:
        print(f"FAIL story styles: {path}")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"PASS story styles: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
