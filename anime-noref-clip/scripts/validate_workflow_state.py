#!/usr/bin/env python3
"""Validate anime-noref-clip workflow gates from workflow_state.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_CUT_STRATEGIES = {"rough", "detailed"}
ALLOWED_OUTPUT_ASPECTS = {
    "vertical",
    "vertical_9_16",
    "9:16",
    "horizontal",
    "horizontal_16_9",
    "16:9",
    "both",
}
ALLOWED_STORY_STYLES = {
    "style_01_aggressive_youtube_cold_start",
}
STORY_STYLE_01 = "style_01_aggressive_youtube_cold_start"
FIXED_TTS_VOICES = {
    "zh-CN": "zh-CN-YunxiNeural",
    "zh": "zh-CN-YunxiNeural",
    "th-TH": "th-TH-PremwadeeNeural",
    "th": "th-TH-PremwadeeNeural",
}
RETENTION_MODE_COLD_START = "aggressive_youtube_cold_start"
POST_HOOK_MAIN_PATH = "contiguous_source_blocks"
CLONE_PADDING_POLICY = "no_clone_padding_except_final_2_frames"
ALIGNMENT_SOLVE_ORDER = "shot_count_then_speed"
SOURCE_BUFFER_POLICY = "stable_subwindow_only_no_cross_cut_tail_buffer"


def get_value(data: dict[str, Any], dotted_path: str) -> Any:
    value: Any = data
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def is_true(data: dict[str, Any], dotted_path: str) -> bool:
    return get_value(data, dotted_path) is True


def is_nonempty(data: dict[str, Any], dotted_path: str) -> bool:
    value = get_value(data, dotted_path)
    return value not in (None, "", [], {})


def resolve_artifact(project_dir: Path, value: Any) -> list[Path]:
    if isinstance(value, str):
        path = Path(value)
        return [path if path.is_absolute() else project_dir / path]
    if isinstance(value, list):
        paths: list[Path] = []
        for item in value:
            paths.extend(resolve_artifact(project_dir, item))
        return paths
    return []


def require_artifact(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    key: str,
    *,
    check_exists: bool,
) -> None:
    dotted = f"artifacts.{key}"
    value = get_value(data, dotted)
    if value in (None, "", [], {}):
        failures.append(f"missing {dotted}")
        return
    if not check_exists:
        return
    for path in resolve_artifact(project_dir, value):
        if not path.exists():
            failures.append(f"artifact does not exist: {dotted} -> {path}")


def require_true(failures: list[str], data: dict[str, Any], dotted_path: str) -> None:
    if not is_true(data, dotted_path):
        failures.append(f"{dotted_path} must be true")


def require_nonempty(failures: list[str], data: dict[str, Any], dotted_path: str) -> None:
    if not is_nonempty(data, dotted_path):
        failures.append(f"missing {dotted_path}")


def require_equals(
    failures: list[str], data: dict[str, Any], dotted_path: str, expected: Any
) -> None:
    actual = get_value(data, dotted_path)
    if actual != expected:
        failures.append(f"{dotted_path} must be {expected!r}, got {actual!r}")


def require_in(
    failures: list[str], data: dict[str, Any], dotted_path: str, allowed: set[str]
) -> None:
    actual = get_value(data, dotted_path)
    if actual not in allowed:
        failures.append(
            f"{dotted_path} must be one of {sorted(allowed)}, got {actual!r}"
        )


def require_lte(
    failures: list[str], data: dict[str, Any], dotted_path: str, maximum: float
) -> None:
    actual = get_value(data, dotted_path)
    if actual is None:
        failures.append(f"missing {dotted_path}")
        return
    try:
        numeric = float(actual)
    except (TypeError, ValueError):
        failures.append(f"{dotted_path} must be numeric, got {actual!r}")
        return
    if numeric > maximum:
        failures.append(f"{dotted_path} must be <= {maximum}, got {numeric}")


def require_gte(
    failures: list[str], data: dict[str, Any], dotted_path: str, minimum: float
) -> None:
    actual = get_value(data, dotted_path)
    if actual is None:
        failures.append(f"missing {dotted_path}")
        return
    try:
        numeric = float(actual)
    except (TypeError, ValueError):
        failures.append(f"{dotted_path} must be numeric, got {actual!r}")
        return
    if numeric < minimum:
        failures.append(f"{dotted_path} must be >= {minimum}, got {numeric}")


def require_lte_dynamic(
    failures: list[str],
    data: dict[str, Any],
    dotted_path: str,
    maximum_path: str,
) -> None:
    maximum = get_value(data, maximum_path)
    if maximum is None:
        failures.append(f"missing {maximum_path}")
        return
    try:
        numeric_maximum = float(maximum)
    except (TypeError, ValueError):
        failures.append(f"{maximum_path} must be numeric, got {maximum!r}")
        return
    require_lte(failures, data, dotted_path, numeric_maximum)


def require_gte_dynamic(
    failures: list[str],
    data: dict[str, Any],
    dotted_path: str,
    minimum_path: str,
) -> None:
    minimum = get_value(data, minimum_path)
    if minimum is None:
        failures.append(f"missing {minimum_path}")
        return
    try:
        numeric_minimum = float(minimum)
    except (TypeError, ValueError):
        failures.append(f"{minimum_path} must be numeric, got {minimum!r}")
        return
    require_gte(failures, data, dotted_path, numeric_minimum)


def require_equals_dynamic(
    failures: list[str],
    data: dict[str, Any],
    dotted_path: str,
    expected_path: str,
) -> None:
    expected = get_value(data, expected_path)
    if expected is None:
        failures.append(f"missing {expected_path}")
        return
    actual = get_value(data, dotted_path)
    if actual != expected:
        failures.append(
            f"{dotted_path} must equal {expected_path} ({expected!r}), got {actual!r}"
        )


def parse_skill_version(value: Any) -> tuple[int, int, int]:
    if not isinstance(value, str):
        return (0, 0, 0)
    value = value.strip().lower().removeprefix("v")
    parts = value.split(".")
    parsed = []
    for part in parts[:3]:
        try:
            parsed.append(int(part))
        except ValueError:
            parsed.append(0)
    while len(parsed) < 3:
        parsed.append(0)
    return tuple(parsed)  # type: ignore[return-value]


def requires_project_template_tools(data: dict[str, Any]) -> bool:
    return parse_skill_version(get_value(data, "skill_version")) >= (1, 4, 7)


def requires_subagent_subtitle_plan(data: dict[str, Any]) -> bool:
    return parse_skill_version(get_value(data, "skill_version")) >= (1, 4, 8)


def requires_boundary_group_subtitle_plan(data: dict[str, Any]) -> bool:
    return parse_skill_version(get_value(data, "skill_version")) >= (1, 4, 9)


def requires_story_style_preset(data: dict[str, Any]) -> bool:
    return parse_skill_version(get_value(data, "skill_version")) >= (1, 4, 11)


def is_vertical_output(data: dict[str, Any]) -> bool:
    aspect = get_value(data, "decisions.output_aspect")
    return aspect in {"vertical", "vertical_9_16", "9:16", "both"}


def is_edge_tts(data: dict[str, Any]) -> bool:
    provider = (
        get_value(data, "decisions.tts_provider")
        or get_value(data, "tts.provider")
        or get_value(data, "tts.provider_name")
    )
    return isinstance(provider, str) and "edge" in provider.lower()


def is_english_output(data: dict[str, Any]) -> bool:
    language = (
        get_value(data, "target.language")
        or get_value(data, "decisions.tts_language")
        or get_value(data, "language")
        or ""
    )
    return isinstance(language, str) and language.lower().startswith("en")


def validate_no_unit_tts_residue(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    if not check_exists:
        return

    scan_dirs = {project_dir / "tts"}
    for key in ("continuous_tts_audio", "tts_boundaries", "tts_generation_manifest"):
        for artifact_path in resolve_artifact(project_dir, get_value(data, f"artifacts.{key}")):
            scan_dirs.add(artifact_path.parent)

    residue: list[Path] = []
    for directory in sorted(scan_dirs):
        if not directory.exists() or not directory.is_dir():
            continue
        residue.extend(directory.glob("unit_*.mp3"))
        residue.extend(directory.glob("unit_*.wav"))
        concat_manifest = directory / "concat_units.txt"
        if concat_manifest.exists():
            residue.append(concat_manifest)

    if residue:
        formatted = ", ".join(str(path) for path in sorted(residue))
        failures.append(f"unit TTS residue found in active project path: {formatted}")


def validate_fixed_tts_voice(failures: list[str], data: dict[str, Any]) -> None:
    language = (
        get_value(data, "target.language")
        or get_value(data, "decisions.tts_language")
        or get_value(data, "language")
    )
    if language not in FIXED_TTS_VOICES:
        return
    expected = FIXED_TTS_VOICES[language]
    require_equals(failures, data, "decisions.tts_voice", expected)


def validate_tts(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    if get_value(data, "decisions.retention_mode") == RETENTION_MODE_COLD_START:
        validate_creative(failures, data, project_dir, check_exists=check_exists)
    else:
        validate_story(failures, data, project_dir, check_exists=check_exists)
    require_true(failures, data, "approvals.script_to_shot_review")
    require_equals(failures, data, "decisions.tts_mode", "full_script")
    validate_fixed_tts_voice(failures, data)
    require_artifact(failures, data, project_dir, "script", check_exists=check_exists)
    require_artifact(failures, data, project_dir, "final_shots", check_exists=check_exists)
    require_artifact(
        failures, data, project_dir, "script_to_shot_review", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "selected_contact_sheet", check_exists=check_exists
    )
    require_equals(failures, data, "checks.op_ed_overlap_count", 0)
    require_true(failures, data, "checks.monotonic_shots")
    require_true(failures, data, "checks.unique_shots")


def validate_pacing(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    validate_tts(failures, data, project_dir, check_exists=check_exists)
    require_artifact(
        failures, data, project_dir, "continuous_tts_audio", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "tts_generation_manifest", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "tts_boundaries", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "post_tts_pacing_report", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "stable_subwindows", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "source_buffer_report", check_exists=check_exists
    )
    require_true(failures, data, "checks.real_tts_duration_used")
    require_gte(failures, data, "checks.real_tts_duration_sec", 1)
    require_true(failures, data, "checks.post_tts_pacing_repair_done")
    require_true(failures, data, "checks.post_tts_pacing_repair_passed")
    require_true(failures, data, "checks.post_tts_speed_range_passed")
    require_true(failures, data, "checks.post_tts_shot_count_passed")
    require_true(failures, data, "checks.stable_subwindows_done")
    require_equals(
        failures, data, "decisions.source_buffer_policy", SOURCE_BUFFER_POLICY
    )
    require_true(failures, data, "checks.safe_tail_buffer_policy_applied")
    require_lte(failures, data, "checks.safe_render_tail_buffer_frames", 2)
    require_equals(failures, data, "checks.source_buffer_crosses_cut", False)
    require_true(failures, data, "checks.language_workflow_state_isolated")
    require_gte_dynamic(
        failures, data, "checks.selected_shot_count", "checks.target_shot_count_min"
    )
    require_lte_dynamic(
        failures, data, "checks.selected_shot_count", "checks.target_shot_count_max"
    )
    require_gte(failures, data, "checks.hook_min_speed_factor", 0.75)
    require_lte(failures, data, "checks.hook_max_speed_factor", 1.35)
    require_gte(failures, data, "checks.post_hook_min_speed_factor", 0.88)
    require_lte(failures, data, "checks.post_hook_max_speed_factor", 1.18)
    require_gte(failures, data, "checks.min_non_hook_speed_factor", 0.75)
    require_lte(failures, data, "checks.max_non_hook_speed_factor", 1.25)
    if is_english_output(data):
        require_true(failures, data, "checks.english_word_budget_passed")
        require_gte_dynamic(
            failures, data, "checks.english_word_count", "checks.english_word_budget_min"
        )
        require_lte_dynamic(
            failures, data, "checks.english_word_count", "checks.english_word_budget_max"
        )


def validate_cut(failures: list[str], data: dict[str, Any]) -> None:
    require_in(failures, data, "decisions.cut_strategy", ALLOWED_CUT_STRATEGIES)
    require_true(failures, data, "approvals.cut_strategy")
    if requires_project_template_tools(data):
        require_true(failures, data, "checks.project_tools_initialized_from_skill_template")
        require_equals(failures, data, "checks.project_tools_copied_from_old_project", False)


def validate_story(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    validate_cut(failures, data)
    require_artifact(
        failures, data, project_dir, "shot_metadata", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "frame_extract_report", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "visual_tags", check_exists=check_exists
    )
    require_true(failures, data, "checks.frame_extract_complete")
    require_equals(failures, data, "checks.frame_extract_missing_count", 0)
    require_equals_dynamic(
        failures,
        data,
        "checks.frame_extract_saved_images",
        "checks.frame_extract_expected_images",
    )
    require_true(failures, data, "checks.long_shot_multi_sample_done")
    require_true(failures, data, "checks.render_level_duration_splits_absent")
    require_true(failures, data, "checks.gpt_visual_tagging_done")
    require_true(failures, data, "checks.black_fade_metadata")


def validate_story_style(failures: list[str], data: dict[str, Any]) -> None:
    if not requires_story_style_preset(data):
        return
    require_in(failures, data, "decisions.story_style", ALLOWED_STORY_STYLES)
    require_nonempty(failures, data, "decisions.story_style_preset")
    require_nonempty(failures, data, "decisions.story_style_label")
    require_true(failures, data, "checks.story_style_preset_resolved")
    if get_value(data, "decisions.story_style") == STORY_STYLE_01:
        require_equals(
            failures,
            data,
            "decisions.retention_mode",
            RETENTION_MODE_COLD_START,
        )
        require_equals(
            failures,
            data,
            "decisions.hook_strategy",
            "multi_hook_with_payoff",
        )


def validate_creative(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    validate_story(failures, data, project_dir, check_exists=check_exists)
    validate_story_style(failures, data)
    require_artifact(
        failures, data, project_dir, "story_atoms", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "retention_brief", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "hook_candidates", check_exists=check_exists
    )
    require_gte(failures, data, "checks.hook_candidates_count", 8)
    require_true(failures, data, "checks.chosen_hook_supported")
    require_artifact(
        failures, data, project_dir, "retention_shot_pool", check_exists=check_exists
    )
    require_true(failures, data, "checks.retention_shot_pool_done")
    require_artifact(
        failures, data, project_dir, "source_blocks", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "shot_block_report", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "script_variants", check_exists=check_exists
    )
    require_gte(failures, data, "checks.script_variants_count", 3)
    require_artifact(failures, data, project_dir, "script", check_exists=check_exists)
    require_artifact(failures, data, project_dir, "final_shots", check_exists=check_exists)
    require_artifact(
        failures, data, project_dir, "retention_qc", check_exists=check_exists
    )
    require_true(failures, data, "checks.creative_retention_qc_passed")
    require_equals(failures, data, "checks.unsupported_claims_count", 0)
    require_lte(failures, data, "checks.generic_exposition_lines", 1)
    require_true(failures, data, "checks.first_3s_visual_salience_passed")
    require_lte(failures, data, "checks.rehook_interval_max_sec", 10)
    require_lte_dynamic(
        failures, data, "checks.cold_open_duration_sec", "decisions.cold_open_max_sec"
    )
    require_lte(failures, data, "checks.returns_to_main_timeline_sec", 8)
    require_equals(
        failures, data, "decisions.post_hook_main_path", POST_HOOK_MAIN_PATH
    )
    require_gte_dynamic(
        failures,
        data,
        "checks.post_hook_min_shot_duration_sec",
        "decisions.post_hook_min_shot_duration",
    )
    require_gte_dynamic(
        failures,
        data,
        "checks.dialogue_scene_min_shot_duration_sec",
        "decisions.dialogue_scene_min_shot_duration",
    )
    require_gte_dynamic(
        failures, data, "checks.selected_shot_count", "checks.target_shot_count_min"
    )
    require_lte_dynamic(
        failures, data, "checks.selected_shot_count", "checks.target_shot_count_max"
    )
    require_true(failures, data, "checks.post_hook_contiguous_source_blocks")
    require_true(failures, data, "checks.script_units_bound_to_blocks")
    require_true(failures, data, "checks.large_jumps_only_at_beat_boundaries")
    require_true(failures, data, "checks.large_jump_reasons_recorded")
    require_true(failures, data, "checks.repeated_framing_penalty_applied")
    require_true(failures, data, "checks.prefer_fewer_longer_shots")
    require_lte_dynamic(
        failures,
        data,
        "checks.nonlinear_exceptions_count",
        "decisions.max_nonlinear_exceptions",
    )
    if get_value(data, "decisions.nonlinear_teaser_allowed") is True:
        require_true(failures, data, "checks.nonlinear_exceptions_reviewed")
    require_true(failures, data, "checks.monotonic_main_path")
    require_equals(failures, data, "checks.op_ed_overlap_count", 0)
    require_true(failures, data, "checks.unique_shots")


def validate_compose(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    validate_pacing(failures, data, project_dir, check_exists=check_exists)
    require_in(failures, data, "decisions.cut_strategy", ALLOWED_CUT_STRATEGIES)
    require_in(failures, data, "decisions.output_aspect", ALLOWED_OUTPUT_ASPECTS)
    require_true(failures, data, "approvals.output_aspect")
    require_artifact(
        failures, data, project_dir, "strict_alignment", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "alignment_qc_report", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "subtitle_file", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "subtitle_timing_report", check_exists=check_exists
    )
    require_true(failures, data, "checks.tts_single_file_only")
    require_equals(failures, data, "checks.tts_unit_audio_residue_count", 0)
    require_true(failures, data, "checks.tts_concat_manifest_absent")
    require_true(failures, data, "checks.tts_real_boundaries_captured")
    if is_edge_tts(data):
        require_true(failures, data, "checks.tts_word_boundaries_used")
    require_true(failures, data, "checks.subtitle_timing_from_real_tts")
    require_lte(failures, data, "checks.subtitle_max_cue_duration_sec", 2.2)
    require_gte(failures, data, "checks.subtitle_min_cue_duration_sec", 0.3)
    require_true(failures, data, "checks.subtitle_word_boundary_cue_merge_done")
    require_true(failures, data, "checks.subtitle_semantic_segmentation_done")
    require_true(failures, data, "checks.subtitle_language_aware_segmentation")
    if requires_boundary_group_subtitle_plan(data):
        require_artifact(
            failures,
            data,
            project_dir,
            "tts_boundary_table",
            check_exists=check_exists,
        )
        require_artifact(
            failures,
            data,
            project_dir,
            "semantic_cue_plan",
            check_exists=check_exists,
        )
        require_true(failures, data, "checks.subtitle_subagent_boundary_group_plan_done")
        require_equals(
            failures,
            data,
            "checks.subtitle_semantic_segmentation_source",
            "subagent_boundary_group_plan",
        )
        require_equals(failures, data, "checks.subtitle_boundary_group_mismatch_count", 0)
        require_equals(failures, data, "checks.subtitle_boundary_group_gap_count", 0)
        require_equals(failures, data, "checks.subtitle_boundary_group_overlap_count", 0)
        require_equals(failures, data, "checks.subtitle_boundary_group_uncovered_count", 0)
        require_equals(
            failures, data, "checks.subtitle_boundary_group_duration_violation_count", 0
        )
    elif requires_subagent_subtitle_plan(data):
        require_artifact(
            failures,
            data,
            project_dir,
            "semantic_cue_plan",
            check_exists=check_exists,
        )
        require_true(failures, data, "checks.subtitle_subagent_semantic_plan_done")
        require_equals(
            failures,
            data,
            "checks.subtitle_semantic_segmentation_source",
            "subagent_semantic_cue_plan",
        )
        require_equals(failures, data, "checks.subtitle_plan_mismatch_count", 0)
    require_true(failures, data, "checks.subtitle_boundary_alignment_checked")
    require_equals(failures, data, "checks.subtitle_cross_sentence_boundary_count", 0)
    require_equals(failures, data, "checks.subtitle_orphan_fragment_count", 0)
    require_equals(failures, data, "checks.subtitle_bad_line_break_count", 0)
    require_true(failures, data, "checks.multilingual_timing_isolated")
    require_equals(
        failures, data, "decisions.clone_padding_policy", CLONE_PADDING_POLICY
    )
    require_equals(
        failures, data, "decisions.alignment_solve_order", ALIGNMENT_SOLVE_ORDER
    )
    require_true(failures, data, "checks.alignment_solves_shot_count_before_speed")
    require_gte(failures, data, "checks.hook_min_speed_factor", 0.75)
    require_lte(failures, data, "checks.hook_max_speed_factor", 1.35)
    require_gte(failures, data, "checks.post_hook_min_speed_factor", 0.88)
    require_lte(failures, data, "checks.post_hook_max_speed_factor", 1.18)
    require_gte(failures, data, "checks.min_non_hook_speed_factor", 0.75)
    require_lte(failures, data, "checks.max_non_hook_speed_factor", 1.25)
    require_lte(failures, data, "checks.tpad_clone_total_frames", 2)
    require_true(failures, data, "checks.clone_padding_used_only_final_fallback")
    require_true(failures, data, "checks.black_fade_metadata")
    require_true(failures, data, "checks.subtitle_trailing_punctuation_removed")
    validate_no_unit_tts_residue(
        failures, data, project_dir, check_exists=check_exists
    )


def validate_deliver(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    validate_compose(failures, data, project_dir, check_exists=check_exists)
    require_artifact(
        failures, data, project_dir, "final_video", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "qa_summary", check_exists=check_exists
    )
    require_artifact(
        failures,
        data,
        project_dir,
        "frame_quantized_alignment",
        check_exists=check_exists,
    )
    require_artifact(
        failures,
        data,
        project_dir,
        "rendered_timing_drift_report",
        check_exists=check_exists,
    )
    require_artifact(
        failures,
        data,
        project_dir,
        "internal_jump_scan_report",
        check_exists=check_exists,
    )
    require_true(failures, data, "checks.frame_quantized_alignment")
    require_true(failures, data, "checks.rendered_timeline_probe_passed")
    require_lte(failures, data, "checks.max_line_boundary_drift_ms", 80.0)
    require_true(failures, data, "checks.internal_jump_scan_done")
    require_true(failures, data, "checks.internal_jump_scan_passed")
    require_equals(failures, data, "checks.internal_jump_count", 0)
    require_true(failures, data, "checks.ffprobe_passed")
    require_true(failures, data, "checks.blackdetect_passed")
    validate_vertical_layout(failures, data, project_dir, check_exists=check_exists)
    validate_optional_watermark(failures, data)


def validate_vertical_layout(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    if not is_vertical_output(data):
        return
    require_equals(
        failures,
        data,
        "decisions.vertical_layout_strategy",
        "blurred_background_full_16_9_foreground",
    )
    require_artifact(
        failures, data, project_dir, "vertical_layout_qa", check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "layout_qa_frames", check_exists=check_exists
    )
    require_true(failures, data, "checks.vertical_layout_full_frame_foreground")
    require_true(failures, data, "checks.vertical_layout_blurred_background")
    require_true(failures, data, "checks.vertical_filter_split_before_scale")
    require_true(failures, data, "checks.foreground_centered_in_vertical_canvas")
    require_true(failures, data, "checks.foreground_vertically_centered")
    require_lte(failures, data, "checks.foreground_vertical_center_error_px", 4)
    require_true(failures, data, "checks.subtitle_position_based_on_foreground_box")
    require_true(failures, data, "checks.subtitle_inside_main_picture")
    require_true(failures, data, "checks.subtitle_not_in_blurred_background")
    require_true(failures, data, "checks.layout_qa_frames_checked")


def validate_optional_watermark(failures: list[str], data: dict[str, Any]) -> None:
    if get_value(data, "decisions.watermark_enabled") is not True:
        return
    require_nonempty(failures, data, "decisions.watermark_text")
    require_nonempty(failures, data, "decisions.watermark_strategy")
    require_true(failures, data, "checks.watermark_strategy_applied")
    require_true(failures, data, "checks.watermark_strategy_recorded")
    require_true(failures, data, "checks.watermark_visibility_checked")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate anime-noref-clip workflow_state.json gates."
    )
    parser.add_argument("state", type=Path, help="Path to workflow_state.json")
    parser.add_argument(
        "--gate",
        choices=("cut", "story", "creative", "tts", "pacing", "compose", "deliver"),
        default="compose",
        help="Workflow gate to validate.",
    )
    parser.add_argument(
        "--no-exists",
        action="store_true",
        help="Validate required fields without checking artifact path existence.",
    )
    args = parser.parse_args()

    state_path = args.state.expanduser().resolve()
    if not state_path.exists():
        print(f"FAIL {args.gate}: state file does not exist: {state_path}")
        return 1

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL {args.gate}: invalid JSON: {exc}")
        return 1

    failures: list[str] = []
    project_dir = state_path.parent
    check_exists = not args.no_exists

    require_nonempty(failures, data, "skill_version")
    require_nonempty(failures, data, "current_phase")

    if args.gate == "cut":
        validate_cut(failures, data)
    elif args.gate == "story":
        validate_story(failures, data, project_dir, check_exists=check_exists)
    elif args.gate == "creative":
        validate_creative(failures, data, project_dir, check_exists=check_exists)
    elif args.gate == "tts":
        validate_tts(failures, data, project_dir, check_exists=check_exists)
    elif args.gate == "pacing":
        validate_pacing(failures, data, project_dir, check_exists=check_exists)
    elif args.gate == "compose":
        validate_compose(failures, data, project_dir, check_exists=check_exists)
    else:
        validate_deliver(failures, data, project_dir, check_exists=check_exists)

    if failures:
        print(f"FAIL {args.gate}: {len(failures)} issue(s)")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"PASS {args.gate}: workflow_state.json gate satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
