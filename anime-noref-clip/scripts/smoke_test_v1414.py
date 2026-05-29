#!/usr/bin/env python3
"""Smoke tests for the v1.4.18 strict AI-tts workflow and skill shape."""

from __future__ import annotations

import json
import importlib.util
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


def run_python_unchecked(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, *(str(arg) for arg in args)],
        cwd=SKILL_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_alignment_tool_module():
    tool_path = SKILL_ROOT / "templates" / "project" / "tools" / "build_post_tts_alignment_v145.py"
    spec = importlib.util.spec_from_file_location("build_post_tts_alignment_v145", tool_path)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load build_post_tts_alignment_v145.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_cjk_bad_boundary_detection() -> None:
    alignment_tool = load_alignment_tool_module()
    tts_units = [{"unit_id": 1, "text": "两个人", "timeline_start": 0.0, "timeline_end": 0.8}]
    boundary_table = {
        "timing_source": "assemblyai_word_boundary",
        "word_boundary_count": 2,
        "units": [
            {
                "unit_id": 1,
                "boundaries": [
                    {"bid": 0, "text": "两个", "start": 0.0, "end": 0.4},
                    {"bid": 1, "text": "人", "start": 0.4, "end": 0.8},
                ],
            }
        ],
    }
    subtitle_plan = {
        "path": "subtitles/semantic_cue_plan.json",
        "unit_boundary_groups": {
            1: [
                {"text": "两个", "boundary_start": 0, "boundary_end": 1},
                {"text": "人", "boundary_start": 1, "boundary_end": 2},
            ]
        },
        "checks": {"bad_line_break_count": 0},
    }
    _, meta = alignment_tool.build_subtitle_cues(
        tts_units,
        "zh-CN",
        subtitle_plan=subtitle_plan,
        boundary_table=boundary_table,
        require_boundary_plan=True,
    )
    if meta.get("computed_bad_line_break_count") != 1:
        raise AssertionError("alignment tool must compute bad Chinese phrase breaks")
    if meta.get("bad_line_break_count") != 1:
        raise AssertionError("computed bad line breaks must fail the subtitle plan")


def touch_declared_artifacts(root: Path, state: dict[str, Any]) -> None:
    artifacts = state.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return
    for value in artifacts.values():
        paths = value if isinstance(value, list) else [value]
        for item in paths:
            if not isinstance(item, str) or not item:
                continue
            path = Path(item)
            if path.is_absolute():
                continue
            target = root / path
            if target.exists():
                continue
            if target.suffix.lower() in {".json", ".jsonl"}:
                write_json(target, {})
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("placeholder\n", encoding="utf-8")


def minimal_story_state() -> dict[str, Any]:
    return {
        "skill_version": "v1.4.18",
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
            "visual_tag_coverage_report": "analysis/visual_tag_merge_report.json",
        },
        "checks": {
            "shot_count": 12,
            "project_tools_initialized_from_skill_template": True,
            "project_tools_copied_from_old_project": False,
            "frame_extract_complete": True,
            "frame_extract_missing_count": 0,
            "frame_extract_saved_images": 12,
            "frame_extract_expected_images": 12,
            "long_shot_multi_sample_done": True,
            "render_level_duration_splits_absent": True,
            "gpt_visual_tagging_done": True,
            "visual_tagged_shot_count": 12,
            "visual_tag_missing_count": 0,
            "visual_tag_coverage_passed": True,
            "black_fade_metadata": True,
        },
    }


def add_minimal_creative_fields(state: dict[str, Any]) -> None:
    state["current_phase"] = "creative_qc"
    state["artifacts"].update(
        {
            "story_evidence_pack": "analysis/story_evidence_pack.json",
            "initial_story_seed": "analysis/initial_story_seed.json",
            "initial_story_execution_log": "analysis/initial_story_execution_log.json",
            "story_atoms": "story_atoms.json",
            "retention_brief": "retention_brief.json",
            "hook_candidates": "hook_candidates.json",
            "retention_shot_pool": "retention_shot_pool.json",
            "source_blocks": "source_blocks.json",
            "shot_block_report": "review/shot_block_report.json",
            "highlight_edit_plan": "review/highlight_edit_plan.json",
            "script_variants": "script_variants.json",
            "script": "script.json",
            "final_shots": "final_shots.json",
            "retention_qc": "retention_qc.json",
        }
    )
    state["checks"].update(
        {
            "story_evidence_pack_done": True,
            "story_evidence_pack_subagent_closed": True,
            "content_style_initial_story_invoked": True,
            "initial_story_written_by_content_style_skill": True,
            "initial_story_references_recorded": True,
            "initial_story_source_support_passed": True,
            "initial_story_unsupported_claims_count": 0,
            "initial_story_no_lazy_transition_passed": True,
            "initial_story_consumed_by_retention_brief": True,
            "initial_story_consumed_by_hooks": True,
            "initial_story_consumed_by_script_variants": True,
            "story_atoms_done": True,
            "retention_brief_done": True,
            "hook_candidates_count": 5,
            "chosen_hook_supported": True,
            "retention_shot_pool_done": True,
            "script_variants_count": 3,
            "script_sentence_source_map_done": True,
            "script_sentence_source_map_coverage_passed": True,
            "script_sentence_tts_budget_passed": True,
            "script_plot_explanation_passed": True,
            "visual_caption_line_count": 0,
            "creative_retention_qc_passed": True,
            "unsupported_claims_count": 0,
            "generic_exposition_lines": 0,
            "first_3s_visual_salience_passed": True,
            "rehook_interval_max_sec": 12,
            "cold_open_duration_sec": 3.8,
            "returns_to_main_timeline_sec": 0,
            "selected_shot_count": 22,
            "post_hook_min_shot_duration_sec": 1.55,
            "dialogue_scene_min_shot_duration_sec": 1.85,
            "source_blocks_count": 2,
            "highlight_edit_plan_done": True,
            "highlight_edit_plan_multi_beat_structure": True,
            "post_hook_contiguous_source_blocks": True,
            "script_units_bound_to_blocks": True,
            "large_jumps_only_at_beat_boundaries": True,
            "large_jump_reasons_recorded": True,
            "repeated_framing_penalty_applied": True,
            "prefer_fewer_longer_shots": True,
            "nonlinear_exceptions_count": 0,
            "monotonic_main_path": True,
            "op_ed_overlap_count": 0,
            "unique_shots": True,
        }
    )


def add_minimal_tts_fields(state: dict[str, Any]) -> None:
    state["current_phase"] = "tts"
    state["approvals"]["script_to_shot_review"] = True
    state["artifacts"].update(
        {
            "script_reference_review": "script_reference_review.json",
            "content_style_execution_log": "review/content_style_execution_log.json",
            "script_to_shot_review": "review/script_to_shot_review.md",
            "selected_contact_sheet": "review/selected_contact_sheet.jpg",
        }
    )
    state["decisions"].update(
        {
            "tts_mode": "full_script",
            "tts_provider": "ai_tts",
            "tts_language": "zh",
            "tts_speed": 1.2,
        }
    )
    state["approvals"]["tts_speed_override"] = False
    state["artifacts"]["tts_duration_estimate"] = "analysis/tts_duration_estimate.json"
    state["checks"].update(
        {
            "script_reference_review_done": True,
            "content_style_skill_invoked": True,
            "script_reference_review_candidate_reviews_done": True,
            "script_reference_review_references_recorded": True,
            "script_reference_style_fit_passed": True,
            "script_reference_unsupported_claims_count": 0,
            "script_reference_initial_story_seed_inherited": True,
            "script_sentence_source_map_done": True,
            "script_sentence_source_map_coverage_passed": True,
            "script_sentence_tts_budget_passed": True,
            "script_plot_explanation_passed": True,
            "visual_caption_line_count": 0,
            "monotonic_shots": True,
            "tts_speed_hard_rule_passed": True,
            "estimated_tts_duration_sec": 60.0,
            "estimated_tts_duration_target_sec": 60.0,
            "estimated_tts_duration_ratio": 1.0,
            "tts_duration_estimate_passed": True,
        }
    )


def write_minimal_script(root: Path) -> None:
    payload = {
        "language": "zh-CN",
        "target_duration_sec": 6.0,
        "script_units": [
            {
                "unit_id": 1,
                "text": "这是第一句测试旁白。",
                "source_time": [1.0, 3.0],
                "evidence_shots": ["shot_0001"],
                "plot_role": "danger_reversal",
                "sentence_source_map": [
                    {
                        "sentence_id": "u01_s01",
                        "text": "这是第一句测试旁白。",
                        "source_time": [1.0, 3.0],
                        "source_shot_ids": ["shot_0001"],
                        "plot_function": "danger_reversal",
                        "tts_budget_sec": 3.0,
                        "source_evidence": ["shot_0001"],
                    }
                ],
            },
            {
                "unit_id": 2,
                "text": "这是第二句，用来检查本地配音路径。",
                "source_time": [3.0, 5.0],
                "evidence_shots": ["shot_0002"],
                "plot_role": "technical_fixture",
                "sentence_source_map": [
                    {
                        "sentence_id": "u02_s01",
                            "text": "这是第二句，用来检查本地配音路径。",
                        "source_time": [3.0, 5.0],
                        "source_shot_ids": ["shot_0002"],
                        "plot_function": "technical_fixture",
                        "tts_budget_sec": 3.0,
                        "source_evidence": ["shot_0002"],
                    }
                ],
            },
        ],
    }
    write_json(root / "script" / "script.json", payload)
    write_json(root / "script.json", payload)


def write_initial_story_artifacts(
    root: Path,
    *,
    lazy_transition: bool = False,
    missing_seed_evidence: bool = False,
    video_count: int = 1,
) -> None:
    transition = "另一边出现新危机" if lazy_transition else "飞船破口处的冷光替换红色荒地"
    evidence_videos = []
    seed_videos = []
    story_atoms = []
    for number in range(1, video_count + 1):
        video_id = f"window_{number:02d}"
        shot_id = f"shot_{number:04d}"
        evidence_videos.append(
            {
                "video_id": video_id,
                "target_duration_sec": 70,
                "candidate_main_line": "角色为了逃离而压下救援选择。",
                "environment_replacement_chain": [
                    {"from": "红色荒地", "to": "飞船破口", "visual_bridge": transition}
                ],
                "role_relationships": [],
                "background_experience": [],
                "cause_effect_chain": [],
                "strong_visual_evidence": ["破口冷光", "角色倒地"],
                "quotable_dialogue": ["这我说了算"],
                "forbidden_inferences": ["不能补写未出现的悔意"],
                "source_map": [{"shot_id": shot_id, "start": 1.0, "end": 3.0}],
            }
        )
        seed_story = {
            "video_id": video_id,
            "selected_story_line": "角色以为压下救援就能逃离，但危险顺着飞船破口追上来。",
            "environment_replacement_chain": [transition],
        }
        if not missing_seed_evidence:
            seed_story["source_evidence"] = [
                {"claim": "危险追上角色", "supporting_shots": [shot_id]}
            ]
        seed_videos.append(seed_story)
        story_atoms.append(
            {
                "atom_id": f"a{number:03d}",
                "event": "角色压下救援选择",
                "supporting_shots": [shot_id],
            }
        )
    write_json(
        root / "analysis" / "story_evidence_pack.json",
        {
            "schema_version": "anime-noref-clip.story_evidence_pack.v1",
            "independent_videos": evidence_videos,
            "checks": {
                "narration_generated": False,
                "all_claims_have_source": True,
                "subagent_closed": True,
            },
        },
    )
    write_json(
        root / "analysis" / "initial_story_execution_log.json",
        {
            "skill": "content-style-system",
            "task": "anime_clip_initial_story_write",
            "source_bundle": "analysis/story_evidence_pack.json",
        },
    )
    write_json(
        root / "analysis" / "initial_story_seed.json",
        {
            "content_style_skill": "content-style-system",
            "content_style_task": "anime_clip_initial_story_write",
            "source_story_evidence_pack": "analysis/story_evidence_pack.json",
            "obsidian_references_used": [
                "30-style-families/viral-video-script/categories/anime-clip/script-optimization-reference.md"
            ],
            "video_stories": seed_videos,
            "checks": {
                "source_support_passed": True,
                "unsupported_claims_count": 0,
                "no_lazy_transition_passed": not lazy_transition,
            },
        },
    )
    write_json(
        root / "story_atoms.json",
        {
            "metadata": {
                "content_style_skill": "content-style-system",
                "content_style_task": "anime_clip_initial_story_write",
                "source_initial_story_seed": "analysis/initial_story_seed.json",
            },
            "story_atoms": story_atoms,
        },
    )


def main() -> int:
    assert_cjk_bad_boundary_detection()
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

    reference_doc = (
        SKILL_ROOT / "references" / "script_reference_optimization.md"
    ).read_text(encoding="utf-8")
    if "content-style-system" not in reference_doc:
        raise AssertionError("script reference optimization must delegate to content-style-system")
    if "Do not duplicate Obsidian file-selection logic" not in reference_doc:
        raise AssertionError("script reference optimization must keep Obsidian routing in content-style-system")
    if "script-optimization-reference.md" not in reference_doc:
        raise AssertionError("anime script optimization must use the single common Obsidian reference")
    legacy_preset_page = "resolved " + "preset page"
    if legacy_preset_page in reference_doc:
        raise AssertionError("script reference optimization must not route to a per-preset Obsidian page")
    if "index + single common script-optimization reference" not in reference_doc:
        raise AssertionError("script reference optimization must name the single common reference route")
    if "thai_food_1000m_viral" not in reference_doc:
        raise AssertionError("script reference optimization must include the Thai viral reference sample anchor")
    if "content_style_execution_log" not in reference_doc:
        raise AssertionError("script reference optimization must require a content-style execution log")
    if "initial_story_seed.json" not in reference_doc:
        raise AssertionError("script reference optimization must verify inheritance from initial_story_seed.json")

    skill_doc = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    workflow_doc = (SKILL_ROOT / "references" / "workflow.md").read_text(encoding="utf-8")
    story_styles_doc = (SKILL_ROOT / "references" / "story_styles.md").read_text(encoding="utf-8")
    legacy_final_narration = "final " + "narration"
    if legacy_final_narration in story_styles_doc:
        raise AssertionError("story_styles.md must not imply presets locally write the final script copy")
    if "row 11 `content-style-system` writing/review gate" not in story_styles_doc:
        raise AssertionError("story_styles.md must route preset guides through the row 11 writing skill")
    if "story_evidence_pack -> content-style-system initial_story_seed/story_atoms" not in story_styles_doc:
        raise AssertionError("story_styles.md v1.4.18 notes must mention early story writing handoff")
    legacy_profile_voice = "profile" + "/voice"
    if legacy_profile_voice in workflow_doc:
        raise AssertionError("workflow.md must use fixed AI-tts language profile")
    legacy_voice_field = '"tts' + '_' + 'voice"'
    if legacy_voice_field in workflow_doc:
        raise AssertionError("workflow.md example state must not include the legacy TTS voice field")
    if "fixed AI-tts language profile" not in workflow_doc:
        raise AssertionError("workflow.md TTS gate must require the fixed AI-tts language profile")
    initial_story_doc_path = SKILL_ROOT / "references" / "initial_story_write.md"
    if not initial_story_doc_path.exists():
        raise AssertionError("initial story write contract must live in references/initial_story_write.md")
    initial_story_doc = initial_story_doc_path.read_text(encoding="utf-8")
    for marker in (
        "story_evidence_pack.json",
        "anime_clip_initial_story_write",
        "initial_story_seed.json",
        "另一边",
        "close_agent",
    ):
        if marker not in initial_story_doc:
            raise AssertionError(f"initial_story_write.md missing marker: {marker}")
    artifact_contracts_path = SKILL_ROOT / "references" / "artifact_contracts.md"
    if not artifact_contracts_path.exists():
        raise AssertionError("artifact JSON examples must live in references/artifact_contracts.md")
    artifact_contracts_doc = artifact_contracts_path.read_text(encoding="utf-8")
    if "## Artifact Schema Targets" not in artifact_contracts_doc:
        raise AssertionError("artifact_contracts.md must own the Artifact Schema Targets section")
    for marker in (
        "Structured transcript from AssemblyAI speaker diarization",
        "TTS generation manifest",
        "Vertical layout QA report",
    ):
        if marker not in artifact_contracts_doc:
            raise AssertionError(f"artifact_contracts.md missing artifact example marker: {marker}")
        if marker in workflow_doc:
            raise AssertionError(f"workflow.md still carries artifact JSON example marker: {marker}")
    if "references/artifact_contracts.md" not in workflow_doc or "references/artifact_contracts.md" not in skill_doc:
        raise AssertionError("workflow and SKILL docs must reference artifact_contracts.md")
    frontmatter = skill_doc.split("---", 2)[1]
    description = next(
        line.split(":", 1)[1].strip()
        for line in frontmatter.splitlines()
        if line.startswith("description:")
    )
    if "Version: `v1.4.18`" not in skill_doc:
        raise AssertionError("SKILL.md must declare v1.4.18")
    if not description.startswith("Use when "):
        raise AssertionError("SKILL.md description must be trigger-only and start with 'Use when'")
    if len(description) > 500:
        raise AssertionError("SKILL.md description must stay under 500 characters")
    forbidden_description_fragments = [
        "Create or continue",
        "strict narration-to-visual synchronization",
        "post-TTS pacing repair",
        "vertical blurred-background layout",
    ]
    for fragment in forbidden_description_fragments:
        if fragment in description:
            raise AssertionError(f"SKILL.md description still summarizes workflow: {fragment}")
    if "AI-tts" not in skill_doc:
        raise AssertionError("SKILL.md must document AI-tts as the TTS path")
    if "content-style-system writing skill" not in skill_doc:
        raise AssertionError("SKILL.md must state the hard copywriting gate uses content-style-system writing skill")
    if "row 11/22 | content-style-system copywriting | writing-skill script gate" not in workflow_doc:
        raise AssertionError("workflow row 11 goal objective must mention content-style-system writing skill copywriting")
    subtitle_cue_doc = (SKILL_ROOT / "references" / "subtitle_semantic_cue_plan.md").read_text(encoding="utf-8")
    template_readme = (SKILL_ROOT / "templates" / "project" / "README.md").read_text(encoding="utf-8")
    for label, text in (
        ("SKILL.md", skill_doc),
        ("workflow.md", workflow_doc),
        ("subtitle_semantic_cue_plan.md", subtitle_cue_doc),
        ("templates/project/README.md", template_readme),
    ):
        if "close_agent" not in text:
            raise AssertionError(f"{label} must require closing subagents after completion")
    if "story evidence pack" not in skill_doc or "initial_story_seed.json" not in skill_doc:
        raise AssertionError("SKILL.md must describe the story evidence pack and initial_story_seed contract")
    if "Story evidence pack subagent" not in workflow_doc:
        raise AssertionError("workflow row 6 must be the Story evidence pack subagent gate")
    if "anime_clip_initial_story_write" not in workflow_doc:
        raise AssertionError("workflow must call content-style-system for initial story writing")
    if "story_beats" in workflow_doc or "episode_summary" in workflow_doc:
        raise AssertionError("workflow must not retain legacy story_beats or episode_summary artifacts")
    if "Local scripts must not rewrite or repair semantic cue grouping" not in workflow_doc:
        raise AssertionError("workflow must keep semantic cue grouping owned by the subagent")
    if "两个 / 人" not in subtitle_cue_doc or "bad_line_break_count > 0" not in subtitle_cue_doc:
        raise AssertionError("subtitle cue plan doc must reject bad Chinese mid-word breaks")
    if "story_evidence_pack" not in template_readme or "initial_story_seed" not in template_readme:
        raise AssertionError("project template README must document early story evidence and initial seed artifacts")
    if "Edge TTS" in skill_doc or "edge_tts" in skill_doc:
        raise AssertionError("SKILL.md must not retain Edge TTS fallback in the active contract")
    if "provider=ai_tts" not in workflow_doc:
        raise AssertionError("workflow must document ai_tts as the default TTS provider")
    if "Edge TTS" in workflow_doc or "edge_tts" in workflow_doc:
        raise AssertionError("workflow must not retain Edge TTS fallback in the active contract")
    if (SKILL_ROOT / "templates" / "project" / "tools" / "generate_tts_edge_v145.py").exists():
        raise AssertionError("Edge TTS generator must not be part of the default project template")
    validator_doc = (SKILL_ROOT / "scripts" / "validate_workflow_state.py").read_text(encoding="utf-8")
    legacy_validator = SKILL_ROOT / "scripts" / "validate_workflow_state_legacy.py"
    if "parse_skill_version" in validator_doc or "requires_boundary_group_subtitle_plan" in validator_doc:
        raise AssertionError("strict validator must not carry version-compatibility branches")
    if "edge_tts" in validator_doc or "FIXED_EDGE_TTS_VOICES" in validator_doc:
        raise AssertionError("strict validator must not accept Edge TTS")
    if not legacy_validator.exists():
        raise AssertionError("legacy validator must be split into validate_workflow_state_legacy.py")
    stale_doc_fragments = [
        "v1.4.16 update:",
        "v1.3.0 update:",
        "Project-specific duration, output aspect, language, TTS speed",
        '"preset_id":',
        '"retention_mode":',
    ]
    for fragment in stale_doc_fragments:
        if fragment in skill_doc:
            raise AssertionError(f"SKILL.md contains stale duplicated workflow fragment: {fragment}")
    for fragment in ('"preset_id":', '"decision_overlay":', '"creative_qc_profile":'):
        if fragment in story_styles_doc:
            raise AssertionError(f"story_styles.md must not duplicate machine preset JSON: {fragment}")
    if "TTS speed is not a style preset override" not in story_styles_doc:
        raise AssertionError("story_styles.md must state that TTS speed is governed by workflow hard gates")
    if "If a state file is missing, create or update it before production work." in skill_doc:
        raise AssertionError("activation protocol must not allow workflow_state mutation before dashboard/goal lock")
    if "Do not create or update workflow_state.json before the dashboard exists and the row 01 goal is active." not in skill_doc:
        raise AssertionError("activation protocol must explicitly protect startup state mutation")
    dashboard_row_15 = next((line for line in workflow_doc.splitlines() if line.startswith("15. ")), "")
    if "duration estimate" not in dashboard_row_15 or "speed 1.2" not in dashboard_row_15:
        raise AssertionError("dashboard row 15 must include the TTS duration estimate speed 1.2 gate")
    for line in workflow_doc.splitlines():
        if "generate_tts_ai_tts_v145.py --project-root <project> --language <zh|en|th>" in line and "--speed 1.2" not in line:
            raise AssertionError("workflow TTS example must include --speed 1.2")
    if "project-local runtime references" not in skill_doc:
        raise AssertionError("SKILL.md project framework must describe copied project-local runtime references")
    alignment_tool = (
        SKILL_ROOT / "templates" / "project" / "tools" / "build_post_tts_alignment_v145.py"
    ).read_text(encoding="utf-8")
    forbidden_alignment_fragments = [
        "LEGACY_TEXT_PLAN_SOURCE",
        "local_rule_fallback",
        "unit_timeline_proportional_fallback",
        "fallback_cue_count",
        "load_optional_json",
    ]
    for fragment in forbidden_alignment_fragments:
        if fragment in alignment_tool:
            raise AssertionError(f"production alignment tool retains old subtitle fallback: {fragment}")
    numbered = []
    in_tts = False
    for line in workflow_doc.splitlines():
        if line.startswith("## Full-Script TTS Alignment"):
            in_tts = True
            continue
        if in_tts and line.startswith("## ") and not line.startswith("## Full-Script"):
            break
        if in_tts and line and line[0].isdigit() and ". " in line:
            numbered.append(int(line.split(".", 1)[0]))
    if numbered and numbered != list(range(1, len(numbered) + 1)):
        raise AssertionError(f"Full-Script TTS Alignment numbering is not sequential: {numbered}")
    combined_goal_docs = skill_doc + "\n" + workflow_doc
    for token in ("get_goal", "create_goal", "update_goal"):
        if token not in combined_goal_docs:
            raise AssertionError(f"goal-driven execution docs missing {token}")
    if "Use the available todo/plan mechanism" in combined_goal_docs:
        raise AssertionError("todo/plan mechanism should not be the execution lock")
    if "Goal-Driven Execution Dashboard" not in workflow_doc:
        raise AssertionError("workflow must define the goal-driven dashboard")
    goal_objective_template = (
        "anime-noref-clip | <project> | row NN/22 | <phase> | "
        "<required gate or decision>"
    )
    if goal_objective_template not in combined_goal_docs:
        raise AssertionError("goal objective template is missing")
    if '"goal_chain"' not in workflow_doc:
        raise AssertionError("workflow_state goal_chain audit field is missing")
    table_rows = [
        line
        for line in workflow_doc.splitlines()
        if line.startswith(tuple(f"{i}. " for i in range(1, 23)))
    ]
    if len(table_rows) < 22:
        raise AssertionError(f"expected 22 dashboard rows, found {len(table_rows)}")

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
        assert state["skill_version"] == "v1.4.18"
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

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1414_reference_gate_") as tmp:
        root = Path(tmp)
        state_path = root / "workflow_state.json"
        write_json(state_path, minimal_story_state())
        run_python(
            "scripts/resolve_story_style.py",
            "--style",
            "style_05_highlight_segment_selection",
            "--project-root",
            root,
            "--write",
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        add_minimal_creative_fields(state)
        write_json(state_path, state)
        missing_review = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
            "--no-exists",
        )
        if missing_review.returncode == 0:
            raise AssertionError("creative gate accepted a state without script_reference_review")
        combined_output = missing_review.stdout + missing_review.stderr
        if "script_reference_review" not in combined_output:
            raise AssertionError(
                "creative gate failure did not mention script_reference_review: "
                + combined_output
            )
        state["artifacts"]["script_reference_review"] = "script_reference_review.json"
        state["checks"]["script_reference_review_done"] = True
        state["checks"]["script_reference_style_fit_passed"] = True
        state["checks"]["script_reference_unsupported_claims_count"] = 0
        write_json(state_path, state)
        missing_writing_skill = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
            "--no-exists",
        )
        if missing_writing_skill.returncode == 0:
            raise AssertionError("creative gate accepted script review without content-style writing skill invocation")
        combined_output = missing_writing_skill.stdout + missing_writing_skill.stderr
        if "content_style_skill_invoked" not in combined_output:
            raise AssertionError(
                "creative gate failure did not mention content_style_skill_invoked: "
                + combined_output
            )
        state["artifacts"]["content_style_execution_log"] = "review/content_style_execution_log.json"
        state["checks"]["content_style_skill_invoked"] = True
        state["checks"]["script_reference_review_candidate_reviews_done"] = True
        state["checks"]["script_reference_review_references_recorded"] = True
        state["checks"]["script_reference_initial_story_seed_inherited"] = True
        write_json(state_path, state)
        run_python(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
            "--no-exists",
        )
        state_without_seed = json.loads(json.dumps(state))
        state_without_seed["artifacts"].pop("story_evidence_pack", None)
        state_without_seed["checks"].pop("story_evidence_pack_done", None)
        write_json(state_path, state_without_seed)
        missing_story_evidence = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
            "--no-exists",
        )
        if missing_story_evidence.returncode == 0:
            raise AssertionError("creative gate accepted a state without story_evidence_pack")
        combined_output = missing_story_evidence.stdout + missing_story_evidence.stderr
        if "story_evidence_pack" not in combined_output:
            raise AssertionError(
                "creative gate failure did not mention story_evidence_pack: "
                + combined_output
            )
        state_unclosed_evidence_pack = json.loads(json.dumps(state))
        state_unclosed_evidence_pack["checks"]["story_evidence_pack_subagent_closed"] = False
        write_json(state_path, state_unclosed_evidence_pack)
        unclosed_evidence_pack = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
            "--no-exists",
        )
        if unclosed_evidence_pack.returncode == 0:
            raise AssertionError("creative gate accepted an unclosed story evidence pack subagent")
        combined_output = unclosed_evidence_pack.stdout + unclosed_evidence_pack.stderr
        if "story_evidence_pack_subagent_closed" not in combined_output:
            raise AssertionError(
                "unclosed evidence-pack failure did not mention story_evidence_pack_subagent_closed: "
                + combined_output
            )

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1418_content_style_artifact_") as tmp:
        root = Path(tmp)
        state_path = root / "workflow_state.json"
        write_json(state_path, minimal_story_state())
        run_python(
            "scripts/resolve_story_style.py",
            "--style",
            "style_05_highlight_segment_selection",
            "--project-root",
            root,
            "--write",
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        add_minimal_creative_fields(state)
        state["artifacts"]["script_reference_review"] = "script_reference_review.json"
        state["artifacts"]["content_style_execution_log"] = "review/content_style_execution_log.json"
        state["checks"]["script_reference_review_done"] = True
        state["checks"]["script_reference_style_fit_passed"] = True
        state["checks"]["script_reference_unsupported_claims_count"] = 0
        state["checks"]["content_style_skill_invoked"] = True
        state["checks"]["script_reference_review_candidate_reviews_done"] = True
        state["checks"]["script_reference_review_references_recorded"] = True
        state["checks"]["script_reference_initial_story_seed_inherited"] = True
        write_json(state_path, state)
        touch_declared_artifacts(root, state)
        write_minimal_script(root)
        write_initial_story_artifacts(root)
        (root / "references" / "story_styles.json").write_text(
            (SKILL_ROOT / "references" / "story_styles.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        write_json(
            root / "script_variants.json",
            {
                "variants": [
                    {"variant_id": "A", "script": [{"text": "A"}]},
                    {"variant_id": "B", "script": [{"text": "B"}]},
                    {"variant_id": "C", "script": [{"text": "C"}]},
                ]
            },
        )
        write_json(
            root / "review" / "content_style_execution_log.json",
            {
                "skill": "content-style-system",
                "task": "anime_clip_reference_review",
                "prompt_summary": "Use content-style-system writing skill to write/rewrite copy.",
            },
        )
        write_json(
            root / "script_reference_review.json",
            {
                "content_style_skill": "content-style-system",
                "content_style_task": "anime_clip_reference_review",
                "obsidian_references_used": [
                    "30-style-families/viral-video-script/categories/anime-clip/script-optimization-reference.md"
                ],
                "selected_variant_id": "B",
                "candidate_reviews": [],
                "initial_story_seed_inheritance": {
                    "source": "analysis/initial_story_seed.json",
                    "passed": True,
                    "missing_seed_claims": [],
                    "new_unseeded_claims": [],
                },
                "sentence_source_map_audit": {
                    "passed": True,
                    "missing_sentence_maps": [],
                    "stale_time_maps": [],
                    "tts_budget_warnings": [],
                },
                "plot_explanation_audit": {
                    "passed": True,
                    "visual_caption_lines": [],
                    "rewritten_to_causality": [],
                },
                "checks": {
                    "style_fit_passed": True,
                    "unsupported_claims_count": 0,
                    "initial_story_seed_inherited": True,
                    "sentence_source_map_passed": True,
                    "tts_budget_passed": True,
                    "plot_explanation_passed": True,
                    "visual_caption_line_count": 0,
                },
            },
        )
        missing_candidates = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
        )
        if missing_candidates.returncode == 0:
            raise AssertionError("creative gate accepted content-style review without candidate_reviews")
        combined_output = missing_candidates.stdout + missing_candidates.stderr
        if "candidate_reviews" not in combined_output:
            raise AssertionError(
                "content-style review failure did not mention candidate_reviews: "
                + combined_output
            )
        write_json(
            root / "script_reference_review.json",
            {
                "content_style_skill": "content-style-system",
                "content_style_task": "anime_clip_reference_review",
                "obsidian_references_used": [
                    "30-style-families/viral-video-script/categories/anime-clip/script-optimization-reference.md"
                ],
                "selected_variant_id": "B",
                "candidate_reviews": [
                    {"variant_id": "A", "unsupported_claims": [], "style_fit": "pass"},
                    {"variant_id": "B", "unsupported_claims": [], "style_fit": "pass"},
                    {"variant_id": "C", "unsupported_claims": [], "style_fit": "pass"},
                ],
                "initial_story_seed_inheritance": {
                    "source": "analysis/initial_story_seed.json",
                    "passed": True,
                    "missing_seed_claims": [],
                    "new_unseeded_claims": [],
                },
                "sentence_source_map_audit": {
                    "passed": True,
                    "missing_sentence_maps": [],
                    "stale_time_maps": [],
                    "tts_budget_warnings": [],
                },
                "plot_explanation_audit": {
                    "passed": True,
                    "visual_caption_lines": [],
                    "rewritten_to_causality": [],
                },
                "checks": {
                    "style_fit_passed": True,
                    "unsupported_claims_count": 0,
                    "initial_story_seed_inherited": True,
                    "sentence_source_map_passed": True,
                    "tts_budget_passed": True,
                    "plot_explanation_passed": True,
                    "visual_caption_line_count": 0,
                },
            },
        )
        write_json(
            root / "script.json",
            {
                "script_units": [
                    {
                        "unit_id": 1,
                        "text": "红发男人站在舱口外。",
                        "source_time": [1.0, 2.0],
                        "evidence_shots": ["shot_0001"],
                    }
                ]
            },
        )
        missing_sentence_map = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
        )
        if missing_sentence_map.returncode == 0:
            raise AssertionError("creative gate accepted final script without sentence_source_map")
        combined_output = missing_sentence_map.stdout + missing_sentence_map.stderr
        if "sentence_source_map" not in combined_output:
            raise AssertionError(
                "missing sentence map failure did not mention sentence_source_map: "
                + combined_output
            )
        write_minimal_script(root)
        review = json.loads((root / "script_reference_review.json").read_text(encoding="utf-8"))
        review["plot_explanation_audit"]["passed"] = False
        review["plot_explanation_audit"]["visual_caption_lines"] = ["红发男人站在舱口外。"]
        review["checks"]["plot_explanation_passed"] = False
        review["checks"]["visual_caption_line_count"] = 1
        write_json(root / "script_reference_review.json", review)
        visual_caption_result = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
        )
        if visual_caption_result.returncode == 0:
            raise AssertionError("creative gate accepted visual-caption-only script review")
        combined_output = visual_caption_result.stdout + visual_caption_result.stderr
        if "visual_caption" not in combined_output and "plot_explanation" not in combined_output:
            raise AssertionError(
                "visual-caption failure did not mention plot_explanation or visual_caption: "
                + combined_output
            )
        review["plot_explanation_audit"]["passed"] = True
        review["plot_explanation_audit"]["visual_caption_lines"] = []
        review["checks"]["plot_explanation_passed"] = True
        review["checks"]["visual_caption_line_count"] = 0
        write_json(root / "script_reference_review.json", review)
        write_initial_story_artifacts(root, missing_seed_evidence=True)
        missing_seed_evidence = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
        )
        if missing_seed_evidence.returncode == 0:
            raise AssertionError("creative gate accepted initial_story_seed without source_evidence")
        combined_output = missing_seed_evidence.stdout + missing_seed_evidence.stderr
        if "source_evidence" not in combined_output:
            raise AssertionError(
                "missing initial-story source evidence failure did not mention source_evidence: "
                + combined_output
            )
        write_initial_story_artifacts(root, video_count=2)
        run_python(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
        )
        write_initial_story_artifacts(root, lazy_transition=True)
        lazy_transition_result = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
        )
        if lazy_transition_result.returncode == 0:
            raise AssertionError("creative gate accepted initial_story_seed with lazy transition")
        combined_output = lazy_transition_result.stdout + lazy_transition_result.stderr
        if "另一边" not in combined_output and "lazy transition" not in combined_output:
            raise AssertionError(
                "lazy transition failure did not mention the forbidden phrase: "
                + combined_output
            )
        write_initial_story_artifacts(root)
        run_python(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "creative",
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
            "tools/validate_workflow_state_legacy.py",
            "tools/resolve_story_style.py",
            "tools/validate_story_styles.py",
            "tools/generate_tts_ai_tts_v145.py",
            "tools/estimate_tts_duration.py",
            "references/story_styles.json",
            "references/story_styles.md",
            "references/story_styles.schema.json",
            "references/subtitle_semantic_cue_plan.md",
            "references/artifact_contracts.md",
            "references/workflow.md",
            "references/workflow_defaults.json",
            "references/tts_duration_calibration.json",
            "references/script_reference_optimization.md",
            "references/initial_story_write.md",
        ]
        missing = [rel for rel in required if not (root / rel).exists()]
        if missing:
            raise AssertionError(f"project initializer missing files: {missing}")
        copied_cache = [
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.name == "__pycache__" or path.suffix == ".pyc"
        ]
        if copied_cache:
            raise AssertionError(f"project initializer copied Python cache files: {copied_cache}")
        if (root / "tools" / "generate_tts_edge_v145.py").exists():
            raise AssertionError("project initializer copied removed Edge TTS generator")

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1416_ai_tts_dry_run_") as tmp:
        root = Path(tmp)
        write_minimal_script(root)
        result = run_python(
            "templates/project/tools/generate_tts_ai_tts_v145.py",
            "--project-root",
            root,
            "--dry-run-config",
        )
        config = json.loads(result.stdout)
        assert config["provider"] == "ai_tts"
        assert config["language"] == "zh"
        assert config["speed"] == 1.2
        assert config["output_audio"] == "tts/narration_full.wav"
        assert config["segments_json_output"] == "tts/ai_tts_segments.json"
        assert config["srt_output"] == "subtitles/ai_tts_timing.srt"
        assert config["script_unit_count"] == 2

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1416_ai_tts_fixture_") as tmp:
        root = Path(tmp)
        write_minimal_script(root)
        estimate_script = json.loads((root / "script" / "script.json").read_text(encoding="utf-8"))
        estimate_script["target_duration_sec"] = 60.0
        write_json(root / "script" / "script.json", estimate_script)
        write_json(
            root / "tts" / "ai_tts_segments.json",
            {
                "segments": [
                    {
                        "index": 1,
                        "start": 0.0,
                        "end": 1.8,
                        "text": "这是第一句测试旁白。",
                        "source_text": "这是第一句测试旁白。",
                    },
                    {
                        "index": 2,
                        "start": 1.8,
                        "end": 4.2,
                        "text": "这是第二句，用来检查本地配音路径。",
                        "source_text": "这是第二句，用来检查本地配音路径。",
                    },
                ]
            },
        )
        write_json(root / "ai_tts_summary.json", {"duration_seconds": 4.2})
        result = run_python(
            "templates/project/tools/estimate_tts_duration.py",
            "--project-root",
            root,
        )
        estimate = json.loads(result.stdout)
        estimate_payload = json.loads((root / "analysis" / "tts_duration_estimate.json").read_text(encoding="utf-8"))
        assert estimate["speed"] == 1.2
        assert estimate["passes"] is False
        assert estimate["estimate_output"] == "analysis/tts_duration_estimate.json"
        assert estimate_payload["min_ratio"] == 0.9
        assert estimate_payload["calibration_source"] == "builtin_language_profile"

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1418_tts_calibration_") as tmp:
        root = Path(tmp)
        write_minimal_script(root)
        write_json(
            root / "references" / "tts_duration_calibration.json",
            {
                "schema_version": "anime-noref-clip.tts_duration_calibration.v1",
                "profiles": {
                    "zh": {
                        "metric": "cjk_chars",
                        "units_per_second_at_speed_1": 3.0,
                        "sample_count": 4,
                    }
                },
            },
        )
        result = run_python(
            "templates/project/tools/estimate_tts_duration.py",
            "--project-root",
            root,
            "--target-duration-sec",
            "6",
        )
        estimate = json.loads(result.stdout)
        assert estimate["calibration_source"] == "references/tts_duration_calibration.json"
        assert estimate["calibration_sample_count"] == 4
        assert estimate["units_per_second_at_speed_1"] == 3.0

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1417_ai_tts_fixture_") as tmp:
        root = Path(tmp)
        write_minimal_script(root)
        write_json(
            root / "tts" / "ai_tts_segments.json",
            {
                "segments": [
                    {
                        "index": 1,
                        "start": 0.0,
                        "end": 1.8,
                        "text": "这是第一句测试旁白。",
                        "source_text": "这是第一句测试旁白。",
                    },
                    {
                        "index": 2,
                        "start": 1.8,
                        "end": 4.2,
                        "text": "这是第二句，用来检查本地配音路径。",
                        "source_text": "这是第二句，用来检查本地配音路径。",
                    },
                ]
            },
        )
        write_json(root / "ai_tts_summary.json", {"duration_seconds": 4.2})
        result = run_python(
            "templates/project/tools/generate_tts_ai_tts_v145.py",
            "--project-root",
            root,
            "--summary-json",
            root / "ai_tts_summary.json",
        )
        summary = json.loads(result.stdout)
        assert summary["segment_boundaries"] == 2
        boundary_table = json.loads((root / "subtitles" / "tts_boundary_table.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / "tts" / "tts_generation_manifest.json").read_text(encoding="utf-8"))
        durations = json.loads((root / "tts" / "tts_durations.json").read_text(encoding="utf-8"))
        boundaries_payload = json.loads((root / "tts" / "narration_boundaries.json").read_text(encoding="utf-8"))
        assert boundary_table["timing_source"] == "assemblyai_segment_boundary"
        assert boundary_table["real_boundary_count"] == 2
        assert boundary_table["passes"] is True
        assert manifest["provider"] == "ai_tts"
        assert manifest["speed"] == 1.2
        assert manifest["boundary_source"] == "assemblyai_segment_boundary"
        assert durations["speed"] == 1.2
        assert boundaries_payload["speed"] == 1.2
        assert boundaries_payload["timing_source"] == "assemblyai_segment_boundary"
        assert summary["speed"] == 1.2
        assert durations["units"][0]["segment_boundaries"][0]["source"] == "assemblyai_segment_boundary"

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1416_ai_tts_raw_words_") as tmp:
        root = Path(tmp)
        write_minimal_script(root)
        write_json(
            root / "tts" / "ai_tts_assemblyai_raw.json",
            {
                "id": "fixture-raw-words",
                "status": "completed",
                "words": [
                    {"text": "这是", "start": 0, "end": 500, "confidence": 0.99},
                    {"text": "第一句", "start": 500, "end": 1200, "confidence": 0.98},
                    {"text": "测试旁白", "start": 1200, "end": 1800, "confidence": 0.97},
                    {"text": "这是第二句", "start": 1800, "end": 2800, "confidence": 0.96},
                    {"text": "用来检查", "start": 2800, "end": 3500, "confidence": 0.95},
                    {"text": "本地配音路径", "start": 3500, "end": 4200, "confidence": 0.94},
                ],
            },
        )
        write_json(
            root / "tts" / "ai_tts_segments.json",
            {
                "raw_transcript_json_output": str(root / "tts" / "ai_tts_assemblyai_raw.json"),
                "word_boundary_count": 6,
                "word_boundaries": [
                    {"text": "这是", "start": 0.0, "end": 0.5, "source": "assemblyai_word_boundary"},
                    {"text": "第一句", "start": 0.5, "end": 1.2, "source": "assemblyai_word_boundary"},
                    {"text": "测试旁白", "start": 1.2, "end": 1.8, "source": "assemblyai_word_boundary"},
                    {"text": "这是第二句", "start": 1.8, "end": 2.8, "source": "assemblyai_word_boundary"},
                    {"text": "用来检查", "start": 2.8, "end": 3.5, "source": "assemblyai_word_boundary"},
                    {"text": "本地配音路径", "start": 3.5, "end": 4.2, "source": "assemblyai_word_boundary"},
                ],
                "segments": [
                    {
                        "index": 1,
                        "start": 0.0,
                        "end": 4.2,
                        "text": "这是第一句测试旁白。这是第二句，用来检查本地配音路径。",
                        "source_text": "这是第一句测试旁白。这是第二句，用来检查本地配音路径。",
                    }
                ],
            },
        )
        write_json(
            root / "ai_tts_summary.json",
            {
                "duration_seconds": 4.2,
                "raw_transcript_json_output": str(root / "tts" / "ai_tts_assemblyai_raw.json"),
            },
        )
        result = run_python(
            "templates/project/tools/generate_tts_ai_tts_v145.py",
            "--project-root",
            root,
            "--summary-json",
            root / "ai_tts_summary.json",
        )
        summary = json.loads(result.stdout)
        boundary_table = json.loads((root / "subtitles" / "tts_boundary_table.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / "tts" / "tts_generation_manifest.json").read_text(encoding="utf-8"))
        durations = json.loads((root / "tts" / "tts_durations.json").read_text(encoding="utf-8"))
        boundaries_payload = json.loads((root / "tts" / "narration_boundaries.json").read_text(encoding="utf-8"))
        assert summary["word_boundaries"] == 6
        assert boundary_table["timing_source"] == "assemblyai_word_boundary"
        assert boundary_table["real_boundary_count"] == 6
        assert manifest["boundary_source"] == "assemblyai_word_boundary"
        assert manifest["raw_transcript_json_output"] == "tts/ai_tts_assemblyai_raw.json"
        assert boundaries_payload["timing_source"] == "assemblyai_word_boundary"
        assert durations["units"][0]["word_boundaries"][0]["source"] == "assemblyai_word_boundary"

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1416_tts_provider_gate_") as tmp:
        root = Path(tmp)
        state_path = root / "workflow_state.json"
        write_json(state_path, minimal_story_state())
        run_python(
            "scripts/resolve_story_style.py",
            "--style",
            "style_05_highlight_segment_selection",
            "--project-root",
            root,
            "--write",
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        add_minimal_creative_fields(state)
        add_minimal_tts_fields(state)
        write_json(state_path, state)
        run_python(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "tts",
            "--no-exists",
        )

        state["decisions"]["tts_speed"] = 1.0
        state["checks"]["tts_speed_hard_rule_passed"] = False
        write_json(state_path, state)
        wrong_speed = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "tts",
            "--no-exists",
        )
        if wrong_speed.returncode == 0:
            raise AssertionError("TTS gate accepted non-1.2 speed without explicit override")
        if "decisions.tts_speed" not in (wrong_speed.stdout + wrong_speed.stderr):
            raise AssertionError("TTS speed failure did not mention decisions.tts_speed")

        state["approvals"]["tts_speed_override"] = True
        state["decisions"]["tts_speed_override_reason"] = "explicit per-task user override"
        state["checks"]["tts_speed_hard_rule_passed"] = True
        write_json(state_path, state)
        run_python(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "tts",
            "--no-exists",
        )

        state["decisions"]["tts_speed"] = 1.2
        state["approvals"]["tts_speed_override"] = False
        state["decisions"].pop("tts_speed_override_reason", None)
        state["checks"]["estimated_tts_duration_sec"] = 53.0
        state["checks"]["estimated_tts_duration_target_sec"] = 60.0
        state["checks"]["estimated_tts_duration_ratio"] = 0.883333
        state["checks"]["tts_duration_estimate_passed"] = False
        write_json(state_path, state)
        short_estimate = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "tts",
            "--no-exists",
        )
        if short_estimate.returncode == 0:
            raise AssertionError("TTS gate accepted an estimated duration below 90% of target")
        if "estimated_tts_duration_ratio" not in (short_estimate.stdout + short_estimate.stderr):
            raise AssertionError("low TTS estimate failure did not mention estimated_tts_duration_ratio")

        state["checks"]["estimated_tts_duration_sec"] = 60.0
        state["checks"]["estimated_tts_duration_target_sec"] = 60.0
        state["checks"]["estimated_tts_duration_ratio"] = 1.0
        state["checks"]["tts_duration_estimate_passed"] = True
        state["decisions"]["tts_provider"] = "edge_tts"
        write_json(state_path, state)
        edge_provider = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "tts",
            "--no-exists",
        )
        if edge_provider.returncode == 0:
            raise AssertionError("strict TTS gate accepted removed Edge TTS provider")
        if "decisions.tts_provider" not in (edge_provider.stdout + edge_provider.stderr):
            raise AssertionError("Edge provider failure did not mention decisions.tts_provider")

    with tempfile.TemporaryDirectory(prefix="anime_noref_v1417_visual_coverage_") as tmp:
        root = Path(tmp)
        state_path = root / "workflow_state.json"
        state = minimal_story_state()
        state["skill_version"] = "v1.4.18"
        state["checks"]["shot_count"] = 443
        state["checks"]["visual_tagged_shot_count"] = 3
        state["checks"]["visual_tag_missing_count"] = 440
        state["checks"]["visual_tag_coverage_passed"] = False
        write_json(state_path, state)
        coverage_result = run_python_unchecked(
            "scripts/validate_workflow_state.py",
            state_path,
            "--gate",
            "story",
            "--no-exists",
        )
        if coverage_result.returncode == 0:
            raise AssertionError("story gate accepted window-level tags without full shot coverage")
        if "visual_tag" not in (coverage_result.stdout + coverage_result.stderr):
            raise AssertionError("visual coverage failure did not mention visual_tag fields")

    print("PASS v1.4.18 smoke test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
