#!/usr/bin/env python3
"""Validate strict v1.4.18 anime-noref-clip workflow gates."""

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
STORY_STYLE_01 = "style_01_aggressive_youtube_cold_start"
STORY_STYLE_CONFIG_SCHEMA_VERSION = "anime-noref-clip.story_styles.v1.4.14"
STYLE_ANCHOR_BASE = "references/story_styles.json#styles/"
EMBEDDED_STORY_STYLES = {
    "default_style": STORY_STYLE_01,
    "style_anchor_base": STYLE_ANCHOR_BASE,
    "styles": {
        STORY_STYLE_01: {
            "preset_id": STORY_STYLE_01,
            "label": "Aggressive YouTube Cold Start",
            "decision_overlay": {
                "retention_mode": "aggressive_youtube_cold_start",
                "hook_strategy": "multi_hook_with_payoff",
            },
            "creative_qc_profile": {
                "min_hook_candidates": 8,
                "unsupported_claims_count": 0,
                "generic_exposition_lines_max": 1,
                "rehook_interval_max_sec": 10,
                "return_to_main_timeline_max_sec": 8,
                "selected_shot_count_60s": [25, 35],
                "post_hook_min_shot_duration_sec": 1.3,
                "dialogue_scene_min_shot_duration_sec": 1.6,
                "op_ed_overlap_count": 0,
            },
        }
    },
}
ALLOWED_TTS_PROVIDERS = {"ai_tts"}
DEFAULT_TTS_SPEED = 1.2
TTS_SPEED_TOLERANCE = 1e-6
MIN_TTS_DURATION_ESTIMATE_RATIO = 0.9
CONTENT_STYLE_SKILL = "content-style-system"
CONTENT_STYLE_TASK = "anime_clip_reference_review"
CONTENT_STYLE_INITIAL_TASK = "anime_clip_initial_story_write"
CONTENT_STYLE_REFERENCE_MARKER = "script-optimization-reference"
INITIAL_STORY_SEED_BASENAME = "initial_story_seed"
LAZY_TRANSITION_PHRASE = "另一边"
AI_TTS_LANGUAGE_PROFILES = {
    "zh-CN": "zh",
    "zh": "zh",
    "en-US": "en",
    "en": "en",
    "th-TH": "th",
    "th": "th",
}
RETENTION_MODE_COLD_START = "aggressive_youtube_cold_start"
POST_HOOK_MAIN_PATH = "contiguous_source_blocks"
CLONE_PADDING_POLICY = "no_clone_padding_except_final_2_frames"
ALIGNMENT_SOLVE_ORDER = "shot_count_then_speed"
SOURCE_BUFFER_POLICY = "stable_subwindow_only_no_cross_cut_tail_buffer"
WORKFLOW_DEFAULTS_SCHEMA_VERSION = "anime-noref-clip.workflow_defaults.v1.4.13"
EMBEDDED_WORKFLOW_DEFAULTS = {
    "schema_version": WORKFLOW_DEFAULTS_SCHEMA_VERSION,
    "decision_defaults": {
        "source_buffer_policy": SOURCE_BUFFER_POLICY,
        "tts_speed": DEFAULT_TTS_SPEED,
    },
}


def load_story_style_config(project_dir: Path) -> dict[str, Any]:
    candidates = []
    state_local = project_dir / "references" / "story_styles.json"
    candidates.append(state_local)
    script_root = Path(__file__).resolve().parents[1]
    candidates.append(script_root / "references" / "story_styles.json")
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return {"_load_error": f"invalid story style config {path}: {exc}"}
    return EMBEDDED_STORY_STYLES


def load_workflow_defaults(project_dir: Path) -> dict[str, Any]:
    candidates = [project_dir / "references" / "workflow_defaults.json"]
    script_root = Path(__file__).resolve().parents[1]
    candidates.append(script_root / "references" / "workflow_defaults.json")
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return {"_load_error": f"invalid workflow defaults config {path}: {exc}"}
    return EMBEDDED_WORKFLOW_DEFAULTS


def workflow_decision_default(project_dir: Path, key: str, fallback: Any) -> Any:
    config = load_workflow_defaults(project_dir)
    defaults = config.get("decision_defaults", {})
    if isinstance(defaults, dict) and key in defaults:
        return defaults[key]
    return fallback


def story_style_map(project_dir: Path) -> dict[str, dict[str, Any]]:
    config = load_story_style_config(project_dir)
    styles = config.get("styles", {})
    return styles if isinstance(styles, dict) else {}


def current_story_style(data: dict[str, Any], project_dir: Path) -> dict[str, Any] | None:
    style_id = get_value(data, "decisions.story_style")
    styles = story_style_map(project_dir)
    style = styles.get(style_id)
    return style if isinstance(style, dict) else None


def current_style_config(data: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    return load_story_style_config(project_dir)


def style_anchor(data: dict[str, Any], project_dir: Path, style_id: str) -> str:
    config = current_style_config(data, project_dir)
    return f"{config.get('style_anchor_base', STYLE_ANCHOR_BASE)}{style_id}"


def style_override_fields(data: dict[str, Any]) -> set[str]:
    overrides = get_value(data, "decisions.story_style_overrides") or []
    fields: set[str] = set()
    if isinstance(overrides, list):
        for item in overrides:
            if isinstance(item, dict) and isinstance(item.get("field"), str):
                fields.add(item["field"])
    return fields


def style_creative_value(
    data: dict[str, Any], project_dir: Path, key: str, default: Any
) -> Any:
    style = current_story_style(data, project_dir) or {}
    profile = style.get("creative_qc_profile", {}) if isinstance(style, dict) else {}
    if isinstance(profile, dict) and key in profile:
        return profile[key]
    return default


def style_creative_number(
    data: dict[str, Any], project_dir: Path, key: str, default: float
) -> float:
    value = style_creative_value(data, project_dir, key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def style_creative_bool(
    data: dict[str, Any], project_dir: Path, key: str, default: bool
) -> bool:
    return bool(style_creative_value(data, project_dir, key, default))


def style_decision_value(
    data: dict[str, Any], project_dir: Path, key: str, default: Any
) -> Any:
    style = current_story_style(data, project_dir) or {}
    overlay = style.get("decision_overlay", {}) if isinstance(style, dict) else {}
    if isinstance(overlay, dict) and key in overlay:
        return overlay[key]
    return default


def scaled_style_shot_range(data: dict[str, Any], project_dir: Path) -> tuple[int, int] | None:
    style = current_story_style(data, project_dir) or {}
    profile = style.get("creative_qc_profile", {}) if isinstance(style, dict) else {}
    base_range = profile.get("selected_shot_count_60s") if isinstance(profile, dict) else None
    if not (isinstance(base_range, list) and len(base_range) == 2):
        return None
    target = get_value(data, "decisions.target_duration_sec") or 60
    try:
        scale = max(0.1, float(target) / 60.0)
        low = max(1, round(float(base_range[0]) * scale))
        high = max(low, round(float(base_range[1]) * scale))
        return low, high
    except (TypeError, ValueError):
        return None


def parse_numeric_pair(value: Any) -> tuple[float, float] | None:
    if not (isinstance(value, list) and len(value) == 2):
        return None
    try:
        low = float(value[0])
        high = float(value[1])
    except (TypeError, ValueError):
        return None
    if low > high:
        return None
    return low, high


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


def load_json_artifact(path: Path, failures: list[str], label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"artifact does not exist: {label} -> {path}")
    except json.JSONDecodeError as exc:
        failures.append(f"{label} must be valid JSON: {path}: {exc}")
    return None


def artifact_text(path: Path, failures: list[str], label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        failures.append(f"artifact does not exist: {label} -> {path}")
    return ""


def flatten_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(flatten_strings(item))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(flatten_strings(item))
        return out
    return [str(value)]


def variant_ids_from_script_variants(payload: Any) -> list[str]:
    if isinstance(payload, list):
        variants = payload
    elif isinstance(payload, dict):
        variants = payload.get("variants") or payload.get("script_variants") or []
    else:
        variants = []
    ids: list[str] = []
    if isinstance(variants, list):
        for index, variant in enumerate(variants):
            if not isinstance(variant, dict):
                ids.append(f"index_{index}")
                continue
            value = variant.get("variant_id") or variant.get("variant") or variant.get("id")
            ids.append(str(value) if value else f"index_{index}")
    return ids


def candidate_review_ids(review: Any) -> list[str]:
    if not isinstance(review, dict):
        return []
    candidates = review.get("candidate_reviews")
    ids: list[str] = []
    if isinstance(candidates, list):
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                ids.append(f"index_{index}")
                continue
            value = candidate.get("variant_id") or candidate.get("variant") or candidate.get("id")
            ids.append(str(value) if value else f"index_{index}")
    return ids


def is_numeric_pair(value: Any) -> bool:
    if not (isinstance(value, list) and len(value) == 2):
        return False
    try:
        start = float(value[0])
        end = float(value[1])
    except (TypeError, ValueError):
        return False
    return end >= start


def split_script_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    current: list[str] = []
    for char in text:
        if char == "\n":
            fragment = "".join(current).strip()
            if fragment:
                sentences.append(fragment)
            current = []
            continue
        current.append(char)
        if char in "。！？!?；;":
            fragment = "".join(current).strip()
            if fragment:
                sentences.append(fragment)
            current = []
    fragment = "".join(current).strip()
    if fragment:
        sentences.append(fragment)
    return sentences or ([text.strip()] if text.strip() else [])


def script_units_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        units = payload.get("script_units")
        if isinstance(units, list):
            return [unit for unit in units if isinstance(unit, dict)]
        videos = payload.get("videos")
        collected: list[dict[str, Any]] = []
        if isinstance(videos, list):
            for video in videos:
                if not isinstance(video, dict):
                    continue
                video_units = video.get("script_units")
                if isinstance(video_units, list):
                    collected.extend(unit for unit in video_units if isinstance(unit, dict))
        return collected
    return []


def validate_sentence_source_map(
    failures: list[str],
    unit: dict[str, Any],
    *,
    unit_label: str,
) -> None:
    text = str(unit.get("text") or "").strip()
    if not text:
        failures.append(f"{unit_label}.text is required")
        return
    if not is_numeric_pair(unit.get("source_time")):
        failures.append(f"{unit_label}.source_time must be a numeric [start, end] pair")
    sentence_count = len(split_script_sentences(text))
    mappings = unit.get("sentence_source_map")
    if not isinstance(mappings, list) or not mappings:
        failures.append(f"{unit_label}.sentence_source_map is required")
        return
    if len(mappings) < sentence_count:
        failures.append(
            f"{unit_label}.sentence_source_map must cover every sentence: "
            f"{len(mappings)} maps for {sentence_count} sentences"
        )
    for index, mapping in enumerate(mappings, start=1):
        entry_label = f"{unit_label}.sentence_source_map[{index}]"
        if not isinstance(mapping, dict):
            failures.append(f"{entry_label} must be an object")
            continue
        if not str(mapping.get("text") or "").strip():
            failures.append(f"{entry_label}.text is required")
        if not is_numeric_pair(mapping.get("source_time")):
            failures.append(f"{entry_label}.source_time must be a numeric [start, end] pair")
        shot_ids = mapping.get("source_shot_ids") or mapping.get("supporting_shots")
        if not isinstance(shot_ids, list) or not shot_ids:
            failures.append(f"{entry_label}.source_shot_ids must be non-empty")
        plot_function = mapping.get("plot_function") or mapping.get("narrative_function")
        if not str(plot_function or "").strip():
            failures.append(f"{entry_label}.plot_function is required")
        budget = mapping.get("tts_budget_sec", mapping.get("target_seconds"))
        try:
            budget_value = float(budget)
        except (TypeError, ValueError):
            failures.append(f"{entry_label}.tts_budget_sec must be numeric")
            continue
        if budget_value <= 0:
            failures.append(f"{entry_label}.tts_budget_sec must be > 0")
        if mapping.get("caption_only") is True or mapping.get("mode") == "visual_caption":
            failures.append(f"{entry_label} must not be marked as visual-caption-only")


def validate_script_artifact(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    require_true(failures, data, "checks.script_sentence_source_map_done")
    require_true(failures, data, "checks.script_sentence_source_map_coverage_passed")
    require_true(failures, data, "checks.script_sentence_tts_budget_passed")
    require_true(failures, data, "checks.script_plot_explanation_passed")
    require_equals(failures, data, "checks.visual_caption_line_count", 0)
    if not check_exists:
        return
    script_paths = resolve_artifact(project_dir, get_value(data, "artifacts.script"))
    if not script_paths:
        return
    for script_path in script_paths:
        script = load_json_artifact(script_path, failures, "artifacts.script")
        units = script_units_from_payload(script)
        if not units:
            failures.append(f"script must include script_units: {script_path}")
            continue
        for index, unit in enumerate(units, start=1):
            unit_id = unit.get("unit_id", index)
            validate_sentence_source_map(
                failures,
                unit,
                unit_label=f"script_units[{unit_id}]",
            )


def validate_content_style_execution_log(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    require_artifact(
        failures, data, project_dir, "content_style_execution_log", check_exists=check_exists
    )
    require_true(failures, data, "checks.content_style_skill_invoked")
    if not check_exists:
        return
    for path in resolve_artifact(project_dir, get_value(data, "artifacts.content_style_execution_log")):
        text = artifact_text(path, failures, "artifacts.content_style_execution_log")
        if CONTENT_STYLE_SKILL not in text:
            failures.append("content_style_execution_log must record content-style-system")
        if CONTENT_STYLE_TASK not in text:
            failures.append("content_style_execution_log must record anime_clip_reference_review")


def validate_initial_story_execution_log(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    require_artifact(
        failures, data, project_dir, "initial_story_execution_log", check_exists=check_exists
    )
    require_true(failures, data, "checks.content_style_initial_story_invoked")
    if not check_exists:
        return
    for path in resolve_artifact(project_dir, get_value(data, "artifacts.initial_story_execution_log")):
        text = artifact_text(path, failures, "artifacts.initial_story_execution_log")
        if CONTENT_STYLE_SKILL not in text:
            failures.append("initial_story_execution_log must record content-style-system")
        if CONTENT_STYLE_INITIAL_TASK not in text:
            failures.append("initial_story_execution_log must record anime_clip_initial_story_write")


def validate_story_evidence_pack_artifact(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    require_artifact(
        failures, data, project_dir, "story_evidence_pack", check_exists=check_exists
    )
    require_true(failures, data, "checks.story_evidence_pack_done")
    require_true(failures, data, "checks.story_evidence_pack_subagent_closed")
    if not check_exists:
        return
    paths = resolve_artifact(project_dir, get_value(data, "artifacts.story_evidence_pack"))
    if not paths:
        return
    pack = load_json_artifact(paths[0], failures, "artifacts.story_evidence_pack")
    if not isinstance(pack, dict):
        failures.append("story_evidence_pack must be a JSON object")
        return
    videos = pack.get("independent_videos") or pack.get("videos")
    if not isinstance(videos, list) or not videos:
        failures.append("story_evidence_pack.independent_videos must be a non-empty list")
        return
    for index, video in enumerate(videos):
        if not isinstance(video, dict):
            failures.append(f"story_evidence_pack.independent_videos[{index}] must be an object")
            continue
        if not video.get("video_id"):
            failures.append(f"story_evidence_pack.independent_videos[{index}].video_id is required")
        source_map = video.get("source_map") or video.get("source_evidence")
        if not isinstance(source_map, list) or not source_map:
            failures.append(
                f"story_evidence_pack.independent_videos[{index}] must include source shot/time mapping"
            )
        if video.get("narration") or video.get("script") or video.get("final_script"):
            failures.append("story_evidence_pack must not contain narration or final script fields")


def validate_initial_story_seed_artifact(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    require_artifact(failures, data, project_dir, "initial_story_seed", check_exists=check_exists)
    validate_initial_story_execution_log(
        failures, data, project_dir, check_exists=check_exists
    )
    require_true(failures, data, "checks.initial_story_written_by_content_style_skill")
    require_true(failures, data, "checks.initial_story_references_recorded")
    require_true(failures, data, "checks.initial_story_source_support_passed")
    require_equals(failures, data, "checks.initial_story_unsupported_claims_count", 0)
    require_true(failures, data, "checks.initial_story_no_lazy_transition_passed")
    if not check_exists:
        return
    seed_paths = resolve_artifact(project_dir, get_value(data, "artifacts.initial_story_seed"))
    if not seed_paths:
        return
    seed = load_json_artifact(seed_paths[0], failures, "artifacts.initial_story_seed")
    if not isinstance(seed, dict):
        failures.append("initial_story_seed must be a JSON object")
        return
    if seed.get("content_style_skill") != CONTENT_STYLE_SKILL:
        failures.append("initial_story_seed.content_style_skill must be content-style-system")
    if seed.get("content_style_task") != CONTENT_STYLE_INITIAL_TASK:
        failures.append("initial_story_seed.content_style_task must be anime_clip_initial_story_write")
    references = flatten_strings(seed.get("obsidian_references_used")) + flatten_strings(
        seed.get("fallback_references_used")
    )
    if not any(CONTENT_STYLE_REFERENCE_MARKER in item for item in references):
        failures.append("initial_story_seed must record the anime script-optimization reference")
    if not isinstance(seed.get("video_stories"), list) or not seed.get("video_stories"):
        failures.append("initial_story_seed.video_stories must be a non-empty list")
    else:
        for index, story in enumerate(seed["video_stories"]):
            if not isinstance(story, dict):
                failures.append(f"initial_story_seed.video_stories[{index}] must be an object")
                continue
            if not story.get("video_id"):
                failures.append(f"initial_story_seed.video_stories[{index}].video_id is required")
            source_evidence = story.get("source_evidence") or story.get("source_map")
            if not isinstance(source_evidence, list) or not source_evidence:
                failures.append(
                    f"initial_story_seed.video_stories[{index}] must include source_evidence"
                )
    checks = seed.get("checks", {})
    if not isinstance(checks, dict):
        failures.append("initial_story_seed.checks must be an object")
    else:
        if checks.get("source_support_passed") is not True:
            failures.append("initial_story_seed.checks.source_support_passed must be true")
        if checks.get("unsupported_claims_count") != 0:
            failures.append("initial_story_seed.checks.unsupported_claims_count must be 0")
        if checks.get("no_lazy_transition_passed") is not True:
            failures.append("initial_story_seed.checks.no_lazy_transition_passed must be true")
    if any(LAZY_TRANSITION_PHRASE in item for item in flatten_strings(seed)):
        failures.append(f"initial_story_seed must not contain lazy transition phrase: {LAZY_TRANSITION_PHRASE}")


def validate_story_atoms_from_initial_seed(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    require_artifact(failures, data, project_dir, "story_atoms", check_exists=check_exists)
    require_true(failures, data, "checks.story_atoms_done")
    if not check_exists:
        return
    atom_paths = resolve_artifact(project_dir, get_value(data, "artifacts.story_atoms"))
    if not atom_paths:
        return
    atoms = load_json_artifact(atom_paths[0], failures, "artifacts.story_atoms")
    if not isinstance(atoms, dict):
        failures.append("story_atoms must be a JSON object with content-style metadata")
        return
    metadata = atoms.get("metadata", {}) if isinstance(atoms.get("metadata"), dict) else {}
    skill = atoms.get("content_style_skill") or metadata.get("content_style_skill")
    task = atoms.get("content_style_task") or metadata.get("content_style_task")
    source_seed = atoms.get("source_initial_story_seed") or metadata.get("source_initial_story_seed")
    if skill != CONTENT_STYLE_SKILL:
        failures.append("story_atoms must record content_style_skill=content-style-system")
    if task != CONTENT_STYLE_INITIAL_TASK:
        failures.append("story_atoms must record content_style_task=anime_clip_initial_story_write")
    if not source_seed or INITIAL_STORY_SEED_BASENAME not in str(source_seed):
        failures.append("story_atoms must record source_initial_story_seed")


def validate_script_reference_review_artifact(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    require_true(failures, data, "checks.script_reference_review_candidate_reviews_done")
    require_true(failures, data, "checks.script_reference_review_references_recorded")
    require_true(failures, data, "checks.script_reference_initial_story_seed_inherited")
    if not check_exists:
        return
    review_paths = resolve_artifact(project_dir, get_value(data, "artifacts.script_reference_review"))
    if not review_paths:
        return
    review = load_json_artifact(review_paths[0], failures, "artifacts.script_reference_review")
    if not isinstance(review, dict):
        failures.append("script_reference_review must be a JSON object")
        return
    if review.get("content_style_skill") != CONTENT_STYLE_SKILL:
        failures.append("script_reference_review.content_style_skill must be content-style-system")
    if review.get("content_style_task") != CONTENT_STYLE_TASK:
        failures.append("script_reference_review.content_style_task must be anime_clip_reference_review")
    references = flatten_strings(review.get("obsidian_references_used")) + flatten_strings(
        review.get("fallback_references_used")
    )
    if not any(CONTENT_STYLE_REFERENCE_MARKER in item for item in references):
        failures.append("script_reference_review must record the anime script-optimization reference")
    candidates = review.get("candidate_reviews")
    if not isinstance(candidates, list) or not candidates:
        failures.append("script_reference_review.candidate_reviews must review every script variant")
    selected = review.get("selected_variant_id")
    if not selected:
        failures.append("script_reference_review.selected_variant_id is required")
    checks = review.get("checks", {})
    if not isinstance(checks, dict):
        failures.append("script_reference_review.checks must be an object")
    else:
        if checks.get("style_fit_passed") is not True:
            failures.append("script_reference_review.checks.style_fit_passed must be true")
        if checks.get("unsupported_claims_count") != 0:
            failures.append("script_reference_review.checks.unsupported_claims_count must be 0")
        if checks.get("initial_story_seed_inherited") is not True:
            failures.append("script_reference_review.checks.initial_story_seed_inherited must be true")
        if checks.get("sentence_source_map_passed") is not True:
            failures.append("script_reference_review.checks.sentence_source_map_passed must be true")
        if checks.get("tts_budget_passed") is not True:
            failures.append("script_reference_review.checks.tts_budget_passed must be true")
        if checks.get("plot_explanation_passed") is not True:
            failures.append("script_reference_review.checks.plot_explanation_passed must be true")
        if checks.get("visual_caption_line_count") != 0:
            failures.append("script_reference_review.checks.visual_caption_line_count must be 0")
    inheritance = review.get("initial_story_seed_inheritance")
    if not isinstance(inheritance, dict):
        failures.append("script_reference_review.initial_story_seed_inheritance is required")
    else:
        if inheritance.get("passed") is not True:
            failures.append("script_reference_review.initial_story_seed_inheritance.passed must be true")
        if INITIAL_STORY_SEED_BASENAME not in str(inheritance.get("source", "")):
            failures.append("script_reference_review.initial_story_seed_inheritance.source must reference initial_story_seed")
    sentence_audit = review.get("sentence_source_map_audit")
    if not isinstance(sentence_audit, dict):
        failures.append("script_reference_review.sentence_source_map_audit is required")
    elif sentence_audit.get("passed") is not True:
        failures.append("script_reference_review.sentence_source_map_audit.passed must be true")
    plot_audit = review.get("plot_explanation_audit")
    if not isinstance(plot_audit, dict):
        failures.append("script_reference_review.plot_explanation_audit is required")
    else:
        if plot_audit.get("passed") is not True:
            failures.append("script_reference_review.plot_explanation_audit.passed must be true")
        visual_caption_lines = plot_audit.get("visual_caption_lines")
        if isinstance(visual_caption_lines, list) and visual_caption_lines:
            failures.append("script_reference_review.plot_explanation_audit.visual_caption_lines must be empty")

    variant_paths = resolve_artifact(project_dir, get_value(data, "artifacts.script_variants"))
    if not variant_paths:
        return
    variants = load_json_artifact(variant_paths[0], failures, "artifacts.script_variants")
    variant_ids = variant_ids_from_script_variants(variants)
    candidate_ids = candidate_review_ids(review)
    if variant_ids and candidate_ids:
        missing = sorted(set(variant_ids) - set(candidate_ids))
        if missing:
            failures.append(f"script_reference_review.candidate_reviews missing variants: {missing}")
        if selected and str(selected) not in set(variant_ids):
            failures.append("script_reference_review.selected_variant_id must match script_variants")
        if selected and str(selected) not in set(candidate_ids):
            failures.append("script_reference_review.selected_variant_id must be reviewed in candidate_reviews")


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


def require_gte_range_min(
    failures: list[str],
    data: dict[str, Any],
    dotted_path: str,
    range_path: str,
    fallback_minimum: float,
) -> None:
    numeric_range = parse_numeric_pair(get_value(data, range_path))
    minimum = numeric_range[0] if numeric_range else fallback_minimum
    require_gte(failures, data, dotted_path, minimum)


def require_lte_range_max(
    failures: list[str],
    data: dict[str, Any],
    dotted_path: str,
    range_path: str,
    fallback_maximum: float,
) -> None:
    numeric_range = parse_numeric_pair(get_value(data, range_path))
    maximum = numeric_range[1] if numeric_range else fallback_maximum
    require_lte(failures, data, dotted_path, maximum)


def is_vertical_output(data: dict[str, Any]) -> bool:
    aspect = get_value(data, "decisions.output_aspect")
    return aspect in {"vertical", "vertical_9_16", "9:16", "both"}

def tts_provider(data: dict[str, Any]) -> str:
    provider = (
        get_value(data, "decisions.tts_provider")
        or get_value(data, "tts.provider")
        or get_value(data, "tts.provider_name")
        or "ai_tts"
    )
    return str(provider)


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


def validate_tts_provider(failures: list[str], data: dict[str, Any]) -> None:
    provider = tts_provider(data)
    if provider not in ALLOWED_TTS_PROVIDERS:
        failures.append(
            "decisions.tts_provider must be one of "
            f"{sorted(ALLOWED_TTS_PROVIDERS)} when set; got {provider!r}"
        )


def validate_tts_profile(failures: list[str], data: dict[str, Any]) -> None:
    language = (
        get_value(data, "target.language")
        or get_value(data, "decisions.tts_language")
        or get_value(data, "language")
    )
    if language in AI_TTS_LANGUAGE_PROFILES:
        expected = AI_TTS_LANGUAGE_PROFILES[language]
        actual = get_value(data, "decisions.ai_tts_language")
        if actual not in (None, expected):
            failures.append(f"decisions.ai_tts_language expected {expected!r}, got {actual!r}")


def validate_tts_speed_hard_rule(failures: list[str], data: dict[str, Any]) -> None:
    actual = get_value(data, "decisions.tts_speed")
    if actual is None:
        failures.append(
            f"decisions.tts_speed must be {DEFAULT_TTS_SPEED} unless an explicit override is approved"
        )
        return
    try:
        speed = float(actual)
    except (TypeError, ValueError):
        failures.append(f"decisions.tts_speed must be numeric, got {actual!r}")
        return
    if abs(speed - DEFAULT_TTS_SPEED) > TTS_SPEED_TOLERANCE:
        if not is_true(data, "approvals.tts_speed_override"):
            failures.append(
                f"decisions.tts_speed must be {DEFAULT_TTS_SPEED} unless approvals.tts_speed_override=true"
            )
            return
        require_nonempty(failures, data, "decisions.tts_speed_override_reason")
    require_true(failures, data, "checks.tts_speed_hard_rule_passed")


def validate_tts_duration_estimate(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    require_artifact(
        failures, data, project_dir, "tts_duration_estimate", check_exists=check_exists
    )
    require_gte(failures, data, "checks.estimated_tts_duration_sec", 1)
    require_gte(failures, data, "checks.estimated_tts_duration_target_sec", 1)
    require_equals_dynamic(
        failures,
        data,
        "checks.estimated_tts_duration_target_sec",
        "decisions.target_duration_sec",
    )
    require_gte(
        failures,
        data,
        "checks.estimated_tts_duration_ratio",
        MIN_TTS_DURATION_ESTIMATE_RATIO,
    )
    require_true(failures, data, "checks.tts_duration_estimate_passed")


def validate_script_rewrite_after_source_change(
    failures: list[str], data: dict[str, Any]
) -> None:
    if not (
        is_true(data, "checks.source_window_changed_after_script")
        or is_true(data, "checks.material_source_expanded_after_script")
    ):
        return
    require_true(failures, data, "checks.script_rewritten_after_source_window_change")
    require_true(failures, data, "checks.script_reference_review_refreshed_after_source_change")


def validate_tts(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    validate_creative(failures, data, project_dir, check_exists=check_exists)
    require_true(failures, data, "approvals.script_to_shot_review")
    require_equals(failures, data, "decisions.tts_mode", "full_script")
    validate_tts_provider(failures, data)
    validate_tts_profile(failures, data)
    validate_tts_speed_hard_rule(failures, data)
    validate_tts_duration_estimate(
        failures, data, project_dir, check_exists=check_exists
    )
    validate_script_rewrite_after_source_change(failures, data)
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
    workflow_defaults = load_workflow_defaults(project_dir)
    if workflow_defaults.get("_load_error"):
        failures.append(workflow_defaults["_load_error"])
    require_equals(
        failures,
        data,
        "decisions.source_buffer_policy",
        workflow_decision_default(project_dir, "source_buffer_policy", SOURCE_BUFFER_POLICY),
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
    require_gte_range_min(
        failures, data, "checks.hook_min_speed_factor", "decisions.hook_speed_range", 0.75
    )
    require_lte_range_max(
        failures, data, "checks.hook_max_speed_factor", "decisions.hook_speed_range", 1.35
    )
    require_gte_range_min(
        failures, data, "checks.post_hook_min_speed_factor", "decisions.post_hook_speed_range", 0.88
    )
    require_lte_range_max(
        failures, data, "checks.post_hook_max_speed_factor", "decisions.post_hook_speed_range", 1.18
    )
    require_gte_range_min(
        failures, data, "checks.min_non_hook_speed_factor", "decisions.absolute_non_hook_speed_range", 0.75
    )
    require_lte_range_max(
        failures, data, "checks.max_non_hook_speed_factor", "decisions.absolute_non_hook_speed_range", 1.25
    )
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
    require_artifact(
        failures,
        data,
        project_dir,
        "visual_tag_coverage_report",
        check_exists=check_exists,
    )
    require_gte(failures, data, "checks.shot_count", 1)
    require_gte(failures, data, "checks.visual_tagged_shot_count", 1)
    require_equals_dynamic(
        failures, data, "checks.visual_tagged_shot_count", "checks.shot_count"
    )
    require_equals(failures, data, "checks.visual_tag_missing_count", 0)
    require_true(failures, data, "checks.visual_tag_coverage_passed")
    require_true(failures, data, "checks.black_fade_metadata")


def validate_story_style(failures: list[str], data: dict[str, Any], project_dir: Path) -> None:
    config = current_style_config(data, project_dir)
    if config.get("_load_error"):
        failures.append(config["_load_error"])
        return
    styles = story_style_map(project_dir)
    style_id = get_value(data, "decisions.story_style")
    if style_id not in styles:
        failures.append(
            f"decisions.story_style must be one of {sorted(styles)}, got {style_id!r}"
        )
        return
    style = styles[style_id]
    require_equals(failures, data, "decisions.story_style_preset", style_anchor(data, project_dir, style_id))
    require_equals(failures, data, "decisions.story_style_label", style.get("label", style_id))
    require_true(failures, data, "checks.story_style_preset_resolved")
    require_equals(
        failures, data, "decisions.story_style_config", "references/story_styles.json"
    )
    require_equals(
        failures, data, "artifacts.story_styles_config", "references/story_styles.json"
    )

    overrides = style_override_fields(data)
    overlay = style.get("decision_overlay", {})
    if isinstance(overlay, dict):
        for key, expected in overlay.items():
            if key in overrides:
                continue
            require_equals(failures, data, f"decisions.{key}", expected)

    shot_range = scaled_style_shot_range(data, project_dir)
    if shot_range:
        minimum, maximum = shot_range
        require_equals(failures, data, "checks.target_shot_count_min", minimum)
        require_equals(failures, data, "checks.target_shot_count_max", maximum)


def validate_creative(
    failures: list[str],
    data: dict[str, Any],
    project_dir: Path,
    *,
    check_exists: bool,
) -> None:
    validate_story(failures, data, project_dir, check_exists=check_exists)
    validate_story_style(failures, data, project_dir)
    validate_story_evidence_pack_artifact(
        failures, data, project_dir, check_exists=check_exists
    )
    validate_initial_story_seed_artifact(
        failures, data, project_dir, check_exists=check_exists
    )
    validate_story_atoms_from_initial_seed(
        failures, data, project_dir, check_exists=check_exists
    )
    require_artifact(
        failures, data, project_dir, "retention_brief", check_exists=check_exists
    )
    require_true(failures, data, "checks.initial_story_consumed_by_retention_brief")
    require_artifact(
        failures, data, project_dir, "hook_candidates", check_exists=check_exists
    )
    require_true(failures, data, "checks.initial_story_consumed_by_hooks")
    require_gte(failures, data, "checks.hook_candidates_count", style_creative_number(data, project_dir, "min_hook_candidates", 8))
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
    if style_decision_value(data, project_dir, "highlight_edit_plan_required", False):
        require_artifact(
            failures, data, project_dir, "highlight_edit_plan", check_exists=check_exists
        )
        require_true(failures, data, "checks.highlight_edit_plan_done")
        require_true(failures, data, "checks.highlight_edit_plan_multi_beat_structure")
    require_artifact(
        failures, data, project_dir, "script_variants", check_exists=check_exists
    )
    require_true(failures, data, "checks.initial_story_consumed_by_script_variants")
    require_gte(failures, data, "checks.script_variants_count", 3)
    require_artifact(
        failures, data, project_dir, "script_reference_review", check_exists=check_exists
    )
    require_true(failures, data, "checks.script_reference_review_done")
    validate_content_style_execution_log(
        failures, data, project_dir, check_exists=check_exists
    )
    validate_script_reference_review_artifact(
        failures, data, project_dir, check_exists=check_exists
    )
    require_true(failures, data, "checks.script_reference_style_fit_passed")
    require_equals(
        failures, data, "checks.script_reference_unsupported_claims_count", 0
    )
    require_artifact(failures, data, project_dir, "script", check_exists=check_exists)
    validate_script_artifact(failures, data, project_dir, check_exists=check_exists)
    require_artifact(failures, data, project_dir, "final_shots", check_exists=check_exists)
    require_artifact(
        failures, data, project_dir, "retention_qc", check_exists=check_exists
    )
    require_true(failures, data, "checks.creative_retention_qc_passed")
    require_equals(failures, data, "checks.unsupported_claims_count", int(style_creative_number(data, project_dir, "unsupported_claims_count", 0)))
    require_lte(failures, data, "checks.generic_exposition_lines", style_creative_number(data, project_dir, "generic_exposition_lines_max", 1))
    if style_creative_bool(data, project_dir, "first_3s_requires_subject_and_conflict", True):
        require_true(failures, data, "checks.first_3s_visual_salience_passed")
    require_lte(failures, data, "checks.rehook_interval_max_sec", style_creative_number(data, project_dir, "rehook_interval_max_sec", 10))
    require_lte_dynamic(
        failures, data, "checks.cold_open_duration_sec", "decisions.cold_open_max_sec"
    )
    if get_value(data, "decisions.nonlinear_teaser_allowed") is True or float(get_value(data, "checks.nonlinear_exceptions_count") or 0) > 0:
        require_lte(failures, data, "checks.returns_to_main_timeline_sec", style_creative_number(data, project_dir, "return_to_main_timeline_max_sec", 8))
    require_equals(
        failures,
        data,
        "decisions.post_hook_main_path",
        style_decision_value(data, project_dir, "post_hook_main_path", POST_HOOK_MAIN_PATH),
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
    if style_creative_bool(data, project_dir, "post_hook_contiguous_source_blocks", True):
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
    else:
        require_equals(failures, data, "checks.nonlinear_exceptions_count", 0)
    require_true(failures, data, "checks.monotonic_main_path")
    require_equals(
        failures,
        data,
        "checks.op_ed_overlap_count",
        int(style_creative_number(data, project_dir, "op_ed_overlap_count", 0)),
    )
    if style_creative_bool(data, project_dir, "unique_shots", True):
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
    require_true(failures, data, "checks.subtitle_timing_from_real_tts")
    require_lte(failures, data, "checks.subtitle_max_cue_duration_sec", 2.2)
    require_gte(failures, data, "checks.subtitle_min_cue_duration_sec", 0.3)
    require_true(failures, data, "checks.subtitle_word_boundary_cue_merge_done")
    require_true(failures, data, "checks.subtitle_semantic_segmentation_done")
    require_true(failures, data, "checks.subtitle_language_aware_segmentation")
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
    require_true(failures, data, "checks.subtitle_boundary_alignment_checked")
    require_equals(failures, data, "checks.subtitle_cross_sentence_boundary_count", 0)
    require_equals(failures, data, "checks.subtitle_orphan_fragment_count", 0)
    require_equals(failures, data, "checks.subtitle_bad_line_break_count", 0)
    require_true(failures, data, "checks.multilingual_timing_isolated")
    require_equals(
        failures,
        data,
        "decisions.clone_padding_policy",
        style_decision_value(data, project_dir, "clone_padding_policy", CLONE_PADDING_POLICY),
    )
    require_equals(
        failures,
        data,
        "decisions.alignment_solve_order",
        style_decision_value(data, project_dir, "alignment_solve_order", ALIGNMENT_SOLVE_ORDER),
    )
    require_true(failures, data, "checks.alignment_solves_shot_count_before_speed")
    require_gte_range_min(
        failures, data, "checks.hook_min_speed_factor", "decisions.hook_speed_range", 0.75
    )
    require_lte_range_max(
        failures, data, "checks.hook_max_speed_factor", "decisions.hook_speed_range", 1.35
    )
    require_gte_range_min(
        failures, data, "checks.post_hook_min_speed_factor", "decisions.post_hook_speed_range", 0.88
    )
    require_lte_range_max(
        failures, data, "checks.post_hook_max_speed_factor", "decisions.post_hook_speed_range", 1.18
    )
    require_gte_range_min(
        failures, data, "checks.min_non_hook_speed_factor", "decisions.absolute_non_hook_speed_range", 0.75
    )
    require_lte_range_max(
        failures, data, "checks.max_non_hook_speed_factor", "decisions.absolute_non_hook_speed_range", 1.25
    )
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
        choices=("cut", "story", "style", "creative", "tts", "pacing", "compose", "deliver"),
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
    elif args.gate == "style":
        validate_story(failures, data, project_dir, check_exists=check_exists)
        validate_story_style(failures, data, project_dir)
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
