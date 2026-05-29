# Anime No-Reference Clip Workflow Reference

## Source Of Truth

This file is canonical for `workflow_state.json` fields, gate thresholds, and the 22-row execution table. Artifact JSON examples and schema-shape targets live in `references/artifact_contracts.md`. Early story-writing handoff rules live in `references/initial_story_write.md`. `../SKILL.md` is the activation and summary layer; it should point here instead of carrying independent copies of detailed rows or thresholds. `story_styles.json` is canonical for machine-readable story-style preset definitions, `story_styles.md` is the human guide, and `workflow_defaults.json` is canonical for non-style production defaults required by hard gates. When a production rule changes, update this file, `references/artifact_contracts.md` when artifact shapes are affected, `../scripts/validate_workflow_state.py`, and any affected files in `../templates/project/tools/` together.

## Artifact Contracts

Artifact JSON examples and field-shape targets live in `references/artifact_contracts.md`. Keep this workflow reference focused on execution order, gates, and operational rules; update artifact contracts alongside template tools and validators when output schemas change.

## Project Script Framework

New projects must initialize project-local tools from the skill template instead of copying another episode project's `tools/` directory:

```bash
python3 ~/.codex/skills/anime-noref-clip/scripts/init_project_scripts.py --project-root <project>
```

The initializer copies `templates/project/tools/` without Python cache files, the strict workflow validator, the separated legacy validator entry, story-style resolver/validator scripts, and the current project-local runtime references: `workflow.md`, `artifact_contracts.md`, `story_styles.json`, `story_styles.md`, `story_styles.schema.json`, `subtitle_semantic_cue_plan.md`, `workflow_defaults.json`, `tts_duration_calibration.json`, `initial_story_write.md`, and `script_reference_optimization.md`. After that, project-specific adjustments are allowed inside the project copy. Copying tools from an old project is allowed only as a deliberate migration with review, because old tools may contain hardcoded episode paths, previous shot-splitting behavior, or stale language/render assumptions.

The copied baseline includes `tools/build_tts_boundary_table.py` and `tools/build_post_tts_alignment_v145.py`. For production v1.4.9+ projects, first build `subtitles/tts_boundary_table.json`, then run a Codex subagent using the project-local `references/subtitle_semantic_cue_plan.md`, write `subtitles/semantic_cue_plan.json` with contiguous `boundary_start/boundary_end` groups, and call `close_agent` after collecting the result. Then use the alignment builder as the default producer for the post-TTS pacing and alignment artifacts after single full-script TTS:

```bash
python3 tools/build_tts_boundary_table.py --project-root <project> --language <lang>
python3 tools/build_post_tts_alignment_v145.py --project-root <project> --source-media <source-mkv> --language <lang> --require-subtitle-plan
```

Call it after `tools/generate_tts_ai_tts_v145.py --speed 1.2` plus the boundary-group cue plan, and before `validate_workflow_state.py --gate pacing`, `tools/render_frameq_segments.py`, or final compose. The alignment builder reads `script/script.json`, `script/final_shots.json`, `tts/tts_durations.json`, `tts/narration_boundaries.json`, `subtitles/tts_boundary_table.json`, and `subtitles/semantic_cue_plan.json`; it writes `alignment/post_tts_pacing_report.json`, `alignment/stable_subwindows.json`, `alignment/source_buffer_report.json`, `alignment/strict_alignment.json`, `alignment/strict_alignment_frameq.json`, `alignment/alignment_qc_report.json`, `subtitles/final.ass`, `subtitles/subtitle_timing_report.json`, and `compose/final_subtitles_frameq.ass`.

Record the initialization in `workflow_state.json`:

```json
{
  "artifacts": {
    "project_tool_template": "~/.codex/skills/anime-noref-clip/templates/project",
    "project_tool_initializer": "~/.codex/skills/anime-noref-clip/scripts/init_project_scripts.py"
  },
  "checks": {
    "project_tools_initialized_from_skill_template": true,
    "project_tools_copied_from_old_project": false
  }
}
```

## Preflight Decisions

Before initial shot selection, confirm the cutting strategy unless the user already specified it:

- `rough`: fewer, longer shots; prioritize plot continuity and stable visuals.
- `detailed`: denser cuts; preserve micro-actions, reactions, object inserts, and emotional turns.

This is a hard pause. If the cutting strategy is missing, stop after source discovery, `ffprobe`, subtitle availability checks, and `workflow_state.json` setup. Do not run scene detection, shot preview generation, frame extraction, contact sheet generation, visual tagging, story scripting, or shot mapping.

After the user chooses, use this choice to tune shot detection thresholds and representative-frame sampling density. Do not tune a maximum shot duration by creating renderable artificial cuts, and do not trim long real shots during indexing. Run `scripts/validate_workflow_state.py <project>/workflow_state.json --gate cut` before any cut-dependent work when a state file exists.

Before retention artifacts, resolve a story style preset from machine-loadable `references/story_styles.json`. If the user does not specify a style, use `style_01_aggressive_youtube_cold_start`. Do not duplicate preset overlays in this file; hook counts, pacing ranges, shot-count ranges, nonlinear policy, source-block rules, and style-specific QC values come from the resolved JSON preset and are enforced by `scripts/validate_workflow_state.py`.

Hard production rules still override style presets: source support, full shot-level visual tag coverage, TTS `speed=1.2` unless explicitly overridden, real-TTS subtitle timing, frame-quantized alignment, layout QA, and delivery QA. Future styles must be added in `references/story_styles.json`, validated with `scripts/validate_story_styles.py`, and summarized in `references/story_styles.md`.

Before final composition, confirm output aspect unless the user already specified it for this render:

- `vertical 9:16`: center the anime frame and place subtitles at the bottom of the actual picture area, not in the padded fill area.
- `horizontal 16:9`: keep source framing and use the normal subtitle safe area.
- `both`: render and QA separate layout variants instead of reusing one subtitle/watermark layout blindly.

Record both decisions in the project notes or QA summary.

## Workflow State and Gates

Create or update `workflow_state.json` in the project directory as soon as the skill starts real work. Treat it as the source of truth for current phase, approvals, decisions, and machine-checkable gates.

Minimum shape:

```json
{
  "skill_version": "v1.4.18",
  "project": "轮回7次的恶役千金_EP01",
  "current_phase": "creative_qc",
  "decisions": {
    "cut_strategy": "detailed",
    "story_style": "style_01_aggressive_youtube_cold_start",
    "story_style_preset": "references/story_styles.json#styles/style_01_aggressive_youtube_cold_start",
    "story_style_label": "Aggressive YouTube Cold Start",
    "story_style_config": "references/story_styles.json",
    "retention_mode": "aggressive_youtube_cold_start",
    "hook_strategy": "multi_hook_with_payoff",
    "nonlinear_teaser_allowed": true,
    "max_nonlinear_exceptions": 2,
    "target_duration_sec": 60,
    "script_density": "high",
    "shot_energy": "aggressive_but_stable_after_hook",
    "cold_open_max_sec": 5,
    "cold_open_allow_nonlinear": true,
    "post_hook_main_path": "contiguous_source_blocks",
    "post_hook_min_shot_duration": 1.3,
    "dialogue_scene_min_shot_duration": 1.6,
    "target_shot_count_60s": [25, 35],
    "hook_speed_range": [0.75, 1.35],
    "post_hook_speed_range": [0.88, 1.18],
    "absolute_non_hook_speed_range": [0.75, 1.25],
    "clone_padding_policy": "no_clone_padding_except_final_2_frames",
    "alignment_solve_order": "shot_count_then_speed",
    "source_buffer_policy": "stable_subwindow_only_no_cross_cut_tail_buffer",
    "english_word_budget_60s": [130, 145],
    "output_aspect": "vertical_9_16",
    "vertical_layout_strategy": "blurred_background_full_16_9_foreground",
    "tts_mode": "full_script",
    "tts_provider": "ai_tts",
    "ai_tts_language": "zh",
    "tts_speed": 1.2,
    "watermark_enabled": false,
    "watermark_text": "@AlsinCro",
    "watermark_strategy": "slow dynamic motion with opacity cycling 5%-15%"
  },
  "approvals": {
    "cut_strategy": true,
    "script_to_shot_review": false,
    "creative_retention_review": false,
    "tts_speed_override": false,
    "tts_config": false,
    "output_aspect": true
  },
  "artifacts": {
    "story_styles_config": "references/story_styles.json",
    "source_media": "source/EP01.mkv",
    "shot_metadata": "shots.json",
    "frame_extract_report": "analysis/frame_extract_report.json",
    "visual_tags": "shot_story_tags.json",
    "visual_tag_coverage_report": "analysis/visual_tag_merge_report.json",
    "transcript": "transcript_assemblyai.json",
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
    "script_reference_review": "script_reference_review.json",
    "content_style_execution_log": "review/content_style_execution_log.json",
    "script": "script.json",
    "final_shots": "final_shots.json",
    "nonlinear_exceptions": "nonlinear_exceptions.json",
    "retention_qc": "retention_qc.json",
    "script_to_shot_review": "review/script_to_shot.md",
    "selected_contact_sheet": "review/selected_contact_sheet.jpg",
    "tts_duration_estimate": "analysis/tts_duration_estimate.json",
    "continuous_tts_audio": "tts/narration_full.wav",
    "tts_generation_manifest": "tts/tts_generation_manifest.json",
    "tts_boundaries": "tts/narration_boundaries.json",
    "post_tts_pacing_report": "alignment/post_tts_pacing_report.json",
    "stable_subwindows": "alignment/stable_subwindows.json",
    "source_buffer_report": "alignment/source_buffer_report.json",
    "strict_alignment": "alignment/strict_alignment.json",
    "alignment_qc_report": "alignment/alignment_qc_report.json",
    "frame_quantized_alignment": "alignment/strict_alignment_frameq.json",
    "rendered_timing_drift_report": "alignment/timing_drift_report.json",
    "tts_boundary_table": "subtitles/tts_boundary_table.json",
    "semantic_cue_plan": "subtitles/semantic_cue_plan.json",
    "subtitle_file": "subtitles/final.ass",
    "subtitle_timing_report": "subtitles/subtitle_timing_report.json",
    "internal_jump_scan_report": "qa/internal_jump_scan_report.json",
    "vertical_layout_qa": "qa/vertical_layout_qa.json",
    "layout_qa_frames": ["qa/layout_0002.jpg", "qa/layout_mid.jpg", "qa/layout_end.jpg"],
    "watermark_qa_frames": [],
    "final_video": "output/final.mp4",
    "qa_summary": "output/qa_summary.md"
  },
  "checks": {
    "shot_count": 360,
    "frame_extract_expected_images": 1284,
    "frame_extract_saved_images": 1284,
    "frame_extract_missing_count": 0,
    "frame_extract_ffmpeg_fallback_count": 130,
    "frame_extract_complete": true,
    "long_shot_multi_sample_done": true,
    "render_level_duration_splits_absent": true,
    "gpt_visual_tagging_done": true,
    "visual_tagged_shot_count": 360,
    "visual_tag_missing_count": 0,
    "visual_tag_coverage_passed": true,
    "black_fade_metadata": true,
    "story_style_preset_resolved": true,
    "story_evidence_pack_done": true,
    "story_evidence_pack_subagent_closed": true,
    "content_style_initial_story_invoked": true,
    "initial_story_written_by_content_style_skill": true,
    "initial_story_references_recorded": true,
    "initial_story_source_support_passed": true,
    "initial_story_unsupported_claims_count": 0,
    "initial_story_no_lazy_transition_passed": true,
    "initial_story_consumed_by_retention_brief": true,
    "initial_story_consumed_by_hooks": true,
    "initial_story_consumed_by_script_variants": true,
    "story_atoms_done": true,
    "retention_brief_done": true,
    "hook_candidates_count": 8,
    "chosen_hook_supported": true,
    "retention_shot_pool_done": true,
    "script_variants_count": 3,
    "content_style_skill_invoked": true,
    "script_reference_review_done": true,
    "script_reference_review_candidate_reviews_done": true,
    "script_reference_review_references_recorded": true,
    "script_reference_style_fit_passed": true,
    "script_reference_unsupported_claims_count": 0,
    "script_sentence_source_map_done": true,
    "script_sentence_source_map_coverage_passed": true,
    "script_sentence_tts_budget_passed": true,
    "script_plot_explanation_passed": true,
    "visual_caption_line_count": 0,
    "creative_retention_qc_passed": true,
    "unsupported_claims_count": 0,
    "generic_exposition_lines": 0,
    "first_3s_visual_salience_passed": true,
    "rehook_interval_max_sec": 9.5,
    "cold_open_duration_sec": 4.6,
    "returns_to_main_timeline_sec": 7.2,
    "selected_shot_count": 31,
    "target_shot_count_min": 25,
    "target_shot_count_max": 35,
    "post_hook_min_shot_duration_sec": 1.36,
    "dialogue_scene_min_shot_duration_sec": 1.72,
    "source_blocks_count": 5,
    "highlight_edit_plan_done": true,
    "highlight_edit_plan_multi_beat_structure": true,
    "post_hook_contiguous_source_blocks": true,
    "script_units_bound_to_blocks": true,
    "large_jumps_only_at_beat_boundaries": true,
    "large_jump_reasons_recorded": true,
    "repeated_framing_penalty_applied": true,
    "prefer_fewer_longer_shots": true,
    "nonlinear_exceptions_count": 1,
    "nonlinear_exceptions_reviewed": true,
    "monotonic_main_path": true,
    "op_ed_overlap_count": 0,
    "monotonic_shots": true,
    "unique_shots": true,
    "tts_single_file_only": true,
    "tts_unit_audio_residue_count": 0,
    "tts_concat_manifest_absent": true,
    "tts_real_boundaries_captured": true,
    "tts_word_boundaries_used": true,
    "tts_speed_hard_rule_passed": true,
    "real_tts_duration_used": true,
    "estimated_tts_duration_sec": 60.0,
    "estimated_tts_duration_target_sec": 60.0,
    "estimated_tts_duration_ratio": 1.0,
    "tts_duration_estimate_passed": true,
    "real_tts_duration_sec": 48.744,
    "post_tts_pacing_repair_done": true,
    "post_tts_pacing_repair_passed": true,
    "post_tts_speed_range_passed": true,
    "post_tts_shot_count_passed": true,
    "stable_subwindows_done": true,
    "safe_tail_buffer_policy_applied": true,
    "safe_render_tail_buffer_frames": 0,
    "source_buffer_crosses_cut": false,
    "language_workflow_state_isolated": true,
    "english_word_count": 136,
    "english_word_budget_min": 130,
    "english_word_budget_max": 145,
    "english_word_budget_passed": true,
    "subtitle_timing_from_real_tts": true,
    "subtitle_max_cue_duration_sec": 2.2,
    "subtitle_min_cue_duration_sec": 0.42,
    "subtitle_word_boundary_cue_merge_done": true,
    "subtitle_semantic_segmentation_done": true,
    "subtitle_language_aware_segmentation": true,
    "subtitle_subagent_semantic_plan_done": true,
    "subtitle_subagent_boundary_group_plan_done": true,
    "subtitle_semantic_segmentation_source": "subagent_boundary_group_plan",
    "subtitle_plan_mismatch_count": 0,
    "subtitle_boundary_group_mismatch_count": 0,
    "subtitle_boundary_group_gap_count": 0,
    "subtitle_boundary_group_overlap_count": 0,
    "subtitle_boundary_group_uncovered_count": 0,
    "subtitle_boundary_group_duration_violation_count": 0,
    "subtitle_boundary_alignment_checked": true,
    "subtitle_cross_sentence_boundary_count": 0,
    "subtitle_orphan_fragment_count": 0,
    "subtitle_bad_line_break_count": 0,
    "multilingual_timing_isolated": true,
    "subtitle_trailing_punctuation_removed": true,
    "alignment_solves_shot_count_before_speed": true,
    "hook_min_speed_factor": 0.8,
    "hook_max_speed_factor": 1.32,
    "post_hook_min_speed_factor": 0.91,
    "post_hook_max_speed_factor": 1.14,
    "min_non_hook_speed_factor": 0.91,
    "max_non_hook_speed_factor": 1.18,
    "tpad_clone_total_frames": 0,
    "clone_padding_used_only_final_fallback": true,
    "frame_quantized_alignment": true,
    "rendered_timeline_probe_passed": true,
    "max_line_boundary_drift_ms": 0,
    "internal_jump_scan_done": true,
    "internal_jump_scan_passed": true,
    "internal_jump_count": 0,
    "vertical_layout_full_frame_foreground": true,
    "vertical_layout_blurred_background": true,
    "vertical_filter_split_before_scale": true,
    "foreground_centered_in_vertical_canvas": true,
    "foreground_vertically_centered": true,
    "foreground_vertical_center_error_px": 0,
    "subtitle_position_based_on_foreground_box": true,
    "subtitle_inside_main_picture": true,
    "subtitle_not_in_blurred_background": true,
    "layout_qa_frames_checked": true,
    "watermark_strategy_applied": false,
    "watermark_strategy_recorded": false,
    "watermark_visibility_checked": false,
    "concat_paths_absolute": true,
    "ffprobe_passed": true,
    "blackdetect_passed": true
  }
}
```

Allowed `current_phase` values:

- `source_analysis`
- `cut_strategy`
- `shot_detection`
- `visual_tagging`
- `dialogue_frame_fusion`
- `story_evidence_pack`
- `initial_story`
- `story_style`
- `retention_brief`
- `hook_candidates`
- `retention_shot_pool`
- `script_variants`
- `script_reference_review`
- `chosen_script`
- `shot_mapping`
- `creative_qc`
- `review`
- `tts`
- `pacing_repair`
- `alignment`
- `compose`
- `qa`
- `delivered`

Hard gate rules:

- Cut gate requires `decisions.cut_strategy` to be `rough` or `detailed` and `approvals.cut_strategy=true`. For workflow states using skill version `v1.4.7` or newer, it also requires `checks.project_tools_initialized_from_skill_template=true` and `checks.project_tools_copied_from_old_project=false`. No cut-dependent artifacts should be generated before this gate passes.
- Story gate requires Cut gate plus `artifacts.shot_metadata`, `artifacts.frame_extract_report`, `checks.frame_extract_complete=true`, `checks.frame_extract_missing_count=0`, `checks.frame_extract_saved_images == checks.frame_extract_expected_images`, `checks.long_shot_multi_sample_done=true`, `checks.render_level_duration_splits_absent=true`, subagent-generated `artifacts.visual_tags`, `checks.gpt_visual_tagging_done=true`, `artifacts.visual_tag_coverage_report`, `checks.visual_tagged_shot_count == checks.shot_count`, `checks.visual_tag_missing_count=0`, `checks.visual_tag_coverage_passed=true`, and `checks.black_fade_metadata=true`. No contact sheets, subagent visual tagging, `story_evidence_pack`, `initial_story_seed`, `story_atoms`, `retention_brief`, `hook_candidates`, `retention_shot_pool`, `script_variants`, `script_reference_review`, `script`, `final_shots`, script-to-shot review, or selected-shot contact sheet should be generated before frame extraction completeness passes. Local inspection, subtitle fusion, transcript summaries, manual notes, or window-level candidate labels cannot satisfy this gate.
- Style gate applies to workflow states using skill version `v1.4.11` or newer before retention artifacts. In `v1.4.12+`, run `scripts/validate_workflow_state.py <project>/workflow_state.json --gate style` after resolving the preset. The gate loads `references/story_styles.json`, requires `decisions.story_style`, `decisions.story_style_preset`, `decisions.story_style_label`, `decisions.story_style_config`, `artifacts.story_styles_config`, and `checks.story_style_preset_resolved=true`, validates the preset anchor and label, and checks all non-overridden `decision_overlay` fields plus scaled target shot-count bounds.
- Creative gate applies before review/TTS for v1.4.12+ story-style workflows. It requires Story gate plus the Style gate for `v1.4.11+` states, `artifacts.story_evidence_pack`, `checks.story_evidence_pack_done=true`, `checks.story_evidence_pack_subagent_closed=true`, `artifacts.initial_story_seed`, `artifacts.initial_story_execution_log`, `checks.content_style_initial_story_invoked=true`, `checks.initial_story_written_by_content_style_skill=true`, `checks.initial_story_references_recorded=true`, `checks.initial_story_source_support_passed=true`, `checks.initial_story_unsupported_claims_count=0`, `checks.initial_story_no_lazy_transition_passed=true`, `artifacts.story_atoms`, `checks.story_atoms_done=true`, `artifacts.retention_brief`, `checks.initial_story_consumed_by_retention_brief=true`, `artifacts.hook_candidates`, `checks.initial_story_consumed_by_hooks=true`, `checks.hook_candidates_count` meeting the preset `creative_qc_profile.min_hook_candidates`, `checks.chosen_hook_supported=true`, `artifacts.retention_shot_pool`, `checks.retention_shot_pool_done=true`, `artifacts.source_blocks`, `artifacts.shot_block_report`, style-5 `artifacts.highlight_edit_plan` plus `checks.highlight_edit_plan_done=true` and `checks.highlight_edit_plan_multi_beat_structure=true` when `decisions.highlight_edit_plan_required=true`, `artifacts.script_variants`, `checks.initial_story_consumed_by_script_variants=true`, `checks.script_variants_count >= 3`, `artifacts.script_reference_review`, `artifacts.content_style_execution_log`, `checks.content_style_skill_invoked=true`, `checks.script_reference_review_done=true`, `checks.script_reference_review_candidate_reviews_done=true`, `checks.script_reference_review_references_recorded=true`, `checks.script_reference_style_fit_passed=true`, `checks.script_reference_unsupported_claims_count=0`, `artifacts.script`, `checks.script_sentence_source_map_done=true`, `checks.script_sentence_source_map_coverage_passed=true`, `checks.script_sentence_tts_budget_passed=true`, `checks.script_plot_explanation_passed=true`, `checks.visual_caption_line_count=0`, `artifacts.final_shots`, `artifacts.retention_qc`, `checks.creative_retention_qc_passed=true`, style-profile claim/exposition/rehook thresholds, `checks.cold_open_duration_sec <= decisions.cold_open_max_sec`, return-to-main-timeline checks when nonlinear shots are allowed or used, `checks.selected_shot_count` within `checks.target_shot_count_min/max`, `checks.post_hook_min_shot_duration_sec >= decisions.post_hook_min_shot_duration`, `checks.dialogue_scene_min_shot_duration_sec >= decisions.dialogue_scene_min_shot_duration`, source-block continuity checks required by the preset, `checks.script_units_bound_to_blocks=true`, `checks.large_jumps_only_at_beat_boundaries=true`, `checks.large_jump_reasons_recorded=true`, `checks.repeated_framing_penalty_applied=true`, `checks.prefer_fewer_longer_shots=true`, `checks.nonlinear_exceptions_count <= decisions.max_nonlinear_exceptions`, `checks.monotonic_main_path=true`, preset `op_ed_overlap_count`, and preset `unique_shots` behavior. The initial story and final review artifacts must come from the `content-style-system` writing skill; row 7 must record `anime_clip_initial_story_write`, and row 11 must record the anime optimization reference plus candidate reviews, sentence-source-map audit, and plot-explanation audit for every script variant. If nonlinear teasers are not allowed, `checks.nonlinear_exceptions_count` must be `0`; if they are allowed and used, require `checks.nonlinear_exceptions_reviewed=true`.
- TTS gate requires Story gate plus the Creative gate for v1.4.11+ story-style workflows or when `decisions.retention_mode=aggressive_youtube_cold_start`, `approvals.script_to_shot_review=true`, `artifacts.script`, `artifacts.final_shots`, `artifacts.script_to_shot_review`, `decisions.tts_mode=full_script`, `decisions.tts_speed=1.2`, `checks.tts_speed_hard_rule_passed=true`, `artifacts.tts_duration_estimate`, `checks.estimated_tts_duration_target_sec == decisions.target_duration_sec`, `checks.estimated_tts_duration_ratio >= 0.9`, `checks.tts_duration_estimate_passed=true`, and the fixed AI-tts language profile for the target language. A non-1.2 speed is valid only when `approvals.tts_speed_override=true` and `decisions.tts_speed_override_reason` is non-empty. If `checks.source_window_changed_after_script=true` or `checks.material_source_expanded_after_script=true`, the gate also requires `checks.script_rewritten_after_source_window_change=true` and `checks.script_reference_review_refreshed_after_source_change=true`.
- Post-TTS pacing gate requires TTS gate plus `artifacts.continuous_tts_audio`, `artifacts.tts_generation_manifest`, `artifacts.tts_boundaries`, `artifacts.post_tts_pacing_report`, `artifacts.stable_subwindows`, `artifacts.source_buffer_report`, `decisions.source_buffer_policy` from `references/workflow_defaults.json`, `checks.real_tts_duration_used=true`, `checks.real_tts_duration_sec`, `checks.post_tts_pacing_repair_done=true`, `checks.post_tts_pacing_repair_passed=true`, `checks.post_tts_speed_range_passed=true`, `checks.post_tts_shot_count_passed=true`, `checks.stable_subwindows_done=true`, `checks.safe_tail_buffer_policy_applied=true`, `checks.safe_render_tail_buffer_frames <= 2`, `checks.source_buffer_crosses_cut=false`, `checks.language_workflow_state_isolated=true`, and the same shot-count/speed range checks used by compose. English outputs also require `checks.english_word_budget_passed=true` and `checks.english_word_count` within the configured budget.
- Compose gate requires Post-TTS pacing gate plus `decisions.cut_strategy`, `decisions.output_aspect`, `approvals.output_aspect=true`, `artifacts.strict_alignment`, `artifacts.alignment_qc_report`, `artifacts.subtitle_file`, `artifacts.subtitle_timing_report`, `checks.tts_single_file_only=true`, `checks.tts_unit_audio_residue_count=0`, `checks.tts_concat_manifest_absent=true`, `checks.tts_real_boundaries_captured=true`, `checks.subtitle_timing_from_real_tts=true`, `checks.subtitle_word_boundary_cue_merge_done=true`, `checks.subtitle_semantic_segmentation_done=true`, `checks.subtitle_language_aware_segmentation=true`, `checks.subtitle_boundary_alignment_checked=true`, `checks.subtitle_cross_sentence_boundary_count=0`, `checks.subtitle_orphan_fragment_count=0`, `checks.subtitle_bad_line_break_count=0`, `checks.subtitle_max_cue_duration_sec <= 2.2`, `checks.subtitle_min_cue_duration_sec >= 0.3`, `checks.multilingual_timing_isolated=true`, `checks.alignment_solves_shot_count_before_speed=true`, hook/post-hook/non-hook speed within the resolved preset ranges in `decisions.*_speed_range`, `checks.tpad_clone_total_frames <= 2`, `checks.clone_padding_used_only_final_fallback=true`, `checks.black_fade_metadata=true`, and `checks.subtitle_trailing_punctuation_removed=true`. It also requires `artifacts.tts_boundary_table`, `artifacts.semantic_cue_plan`, `checks.subtitle_subagent_boundary_group_plan_done=true`, `checks.subtitle_semantic_segmentation_source="subagent_boundary_group_plan"`, `checks.subtitle_boundary_group_mismatch_count=0`, `checks.subtitle_boundary_group_gap_count=0`, `checks.subtitle_boundary_group_overlap_count=0`, `checks.subtitle_boundary_group_uncovered_count=0`, and `checks.subtitle_boundary_group_duration_violation_count=0`.
- Delivery gate requires compose gate plus `artifacts.final_video`, `artifacts.qa_summary`, `artifacts.frame_quantized_alignment`, `artifacts.rendered_timing_drift_report`, `artifacts.internal_jump_scan_report`, `checks.frame_quantized_alignment=true`, `checks.rendered_timeline_probe_passed=true`, `checks.max_line_boundary_drift_ms <= 80`, `checks.internal_jump_scan_done=true`, `checks.internal_jump_scan_passed=true`, `checks.internal_jump_count=0`, `checks.ffprobe_passed=true`, and `checks.blackdetect_passed=true`. For `vertical_9_16` or `both`, it also requires `artifacts.vertical_layout_qa`, `artifacts.layout_qa_frames`, `checks.vertical_layout_full_frame_foreground=true`, `checks.vertical_layout_blurred_background=true`, `checks.vertical_filter_split_before_scale=true`, `checks.foreground_centered_in_vertical_canvas=true`, `checks.foreground_vertically_centered=true`, `checks.foreground_vertical_center_error_px <= 4`, `checks.subtitle_position_based_on_foreground_box=true`, `checks.subtitle_inside_main_picture=true`, `checks.subtitle_not_in_blurred_background=true`, and `checks.layout_qa_frames_checked=true`. If `decisions.watermark_enabled=true`, it also requires `decisions.watermark_text`, `decisions.watermark_strategy`, `checks.watermark_strategy_applied=true`, `checks.watermark_strategy_recorded=true`, and `checks.watermark_visibility_checked=true`.

## Goal-Driven Execution Dashboard

Before any production work, publish a user-visible Markdown execution dashboard derived from the required workflow, `workflow_state.json`, existing artifacts, and the user's supplied inputs. Only read-only inspection is allowed before the dashboard exists.

The execution dashboard is a safety surface, not the execution lock. It must make fragile gates visible so resumed runs and parallel windows do not rely on memory. The active Codex goal is the execution lock, and each dashboard row maps to exactly one goal.

Goal objective format:

```text
anime-noref-clip | <project> | row NN/22 | <phase> | <required gate or decision>
```

At run start or resume:

1. Call `get_goal` after read-only inspection and before mutating work.
2. Find the earliest row that is not `Done` and not explicitly `Blocked`.
3. If no active goal exists, call `create_goal` for that row using the objective format above.
4. If an active goal exists and matches that row, continue only that row.
5. If an active goal points to a later row, stop and report a goal/table mismatch. Do not execute the later row.
6. When the active row's gate passes, update `workflow_state.json`, publish a dashboard delta, then call `update_goal(status=complete)`.
7. If continuing immediately, create the next row goal only after the prior goal is complete.
8. If a validator fails or a required artifact/decision is missing, mark the row `Blocked`, keep the active goal open, and stop. Do not create the next goal.

Any row that launches Codex subagents must close them after their results are collected, merged, or rejected. Use `close_agent` before marking that row `Done`; lingering completed subagents are not valid row completion.

For row 11, the active goal objective must explicitly name the writing-skill copywriting gate:

```text
anime-noref-clip | <project> | row 11/22 | content-style-system copywriting | writing-skill script gate
```

Do not use a generic "script optimization" goal for row 11.

Minimum table columns:

```markdown
| # | Phase | Required gate / decision | Todo / artifact | Status | Visible gate / rule note | Evidence / next action |
|---|---|---|---|---|---|---|
```

Rows must preserve this order unless the user explicitly changes the deliverable:

1. Source analysis, state setup, and project tool initialization — project-isolated paths only; inspect read-only before table; new projects must run `init_project_scripts.py` from the skill template and must not copy another episode's `tools/`.
2. Cut strategy decision and cut gate — stop until `rough` or `detailed` is approved.
3. Shot detection, frame extraction, black/fade metadata — no shot work before cut gate; use only real ffmpeg scene cuts as shots; long shots get extra analysis samples; OpenCV extraction plus ffmpeg fallback must leave zero missing frames.
4. GPT visual tagging by `gpt-5.5` subagents and story gate — subagent JSONL required; local notes do not count; close every tagging subagent with `close_agent` after collecting output.
5. Dialogue/frame fusion — fuse transcript plus visual tags; do not write story from transcript alone.
6. Story evidence pack subagent — build `story_evidence_pack.json` from visual tags, dialogue/frame fusion, subtitle alignment, and independent video windows; evidence only, no narration; close the subagent with `close_agent`.
7. Story style preset, content-style initial story, and retention brief — resolve `references/story_styles.json`, call `content-style-system` task `anime_clip_initial_story_write`, save `initial_story_seed.json`, `initial_story_execution_log`, and canonical `story_atoms.json` before hook/payoff/skip rules.
8. Hook candidates — meet the resolved preset's minimum supported hook count; reject unsupported hype.
9. Retention shot pool — score shots and blocks; penalize continuity cost and repetition.
10. Script variants — generate style-appropriate source-supported variants.
11. Reference script optimization and chosen script — active goal must be `row 11/22 | content-style-system copywriting | writing-skill script gate`; call the `content-style-system` writing skill to write/rewrite final copy; create `script_reference_review.json` plus `content_style_execution_log` before final script; choose variant before mapping; no unsupported claims.
12. Style-aware shot mapping — apply the resolved preset's shot mapping rules, nonlinear policy, shot-count range, and source-block requirements.
13. Creative retention QC — must pass shot count, block continuity, OP/ED, uniqueness, support, and pacing checks before review.
14. Review artifacts and user approval — no TTS before accepted script-to-shot review.
15. TTS duration estimate, full-script TTS, and TTS gate — estimate at speed 1.2 first; one continuous TTS only; no `unit_*` audio or concat manifest.
16. Post-TTS pacing repair gate — real TTS duration controls shot count, source windows, speed, and language budget before render.
17. TTS boundary table, subagent boundary-group subtitles, strict/frame-quantized alignment, and subtitle cleanup — build boundary table first, subagent groups contiguous boundary ids, close the subagent with `close_agent`, then script validates coverage and exact timing.
18. Output aspect/layout confirmation and compose gate — vertical means blurred background plus full 16:9 foreground centered left/right and top/bottom; subtitles use foreground-box coordinates.
19. Segment render and timing probe — rendered frame counts must match; drift thresholds apply.
20. Internal jump scan — exclude planned edit boundaries; internal jump count must be 0.
21. Final mux with BGM/watermark/subtitles — watermark strategy must be recorded when enabled.
22. Layout/subtitle/watermark QA checks and delivery gate — QA frames prove centered full foreground, subtitles inside foreground box not blur, timing, watermark, ffprobe, blackdetect, and internal-jump scan.

Status rules:

- `Pending`: the row has not started.
- `In progress`: the current active row. Only one row may be active unless independent read-only inspections are running.
- `Done`: the required artifact exists, approval is recorded, or the relevant validator/gate passed.
- `Blocked`: the row cannot proceed because a required user decision, upstream artifact, or gate is missing.

Do not start a later row until all earlier required rows are `Done` or `Blocked` with an explicit stop, and do not create a later row goal until the current goal is complete. If a row is already satisfied by existing artifacts, mark it `Done` with the artifact path or gate result as evidence. After each major phase or validator run, send an updated dashboard or concise dashboard delta before continuing. Keep the visible gate/rule note present in deltas for any row whose status changed or is about to run.

Record a lightweight audit trail in `workflow_state.json` when real work starts. This is for resume/debug visibility and must not break old projects that lack the field:

```json
{
  "goal_chain": {
    "mode": "per_table_row",
    "total_rows": 22,
    "active_row": 4,
    "active_goal_objective": "anime-noref-clip | EP01 | row 04/22 | GPT visual tagging | story gate",
    "completed_rows": [1, 2, 3],
    "blocked_rows": []
  }
}
```

At the start of every resumed run, report:

```text
Skill active: anime-noref-clip
Project: <project>
Current phase: <phase>
Completed gates: <list>
Blocked gates: <list>
Active goal: <objective or none>
Goal/table status: <matched, no-active-goal, or mismatch>
Next decision or action: <item>
```

Then include the execution dashboard. The dashboard is the visible order; the active goal is the mutating-work lock.

Use `scripts/validate_workflow_state.py` after resolving the story style (`--gate style`), before production TTS (`--gate tts`), after `tools/build_post_tts_alignment_v145.py` finishes post-TTS pacing repair (`--gate pacing`), before compose (`--gate compose`), and before final delivery (`--gate deliver`) whenever `workflow_state.json` exists.

## TTS Provider Defaults

Use local `AI-tts` as the production TTS provider (`provider=ai_tts`).

```json
{
  "provider": "ai_tts",
  "default_speed": 1.2,
  "profiles": {
    "zh-CN": "zh",
    "zh": "zh",
    "en-US": "en",
    "en": "en",
    "th-TH": "th",
    "th": "th"
  }
}
```

Rules:

1. Determine the target language before TTS.
2. Set `decisions.tts_provider=ai_tts`.
3. Set `decisions.tts_speed=1.2`; any other speed requires `approvals.tts_speed_override=true` plus a non-empty `decisions.tts_speed_override_reason`.
4. Before TTS, run `tools/estimate_tts_duration.py --speed 1.2`; it reads `references/tts_duration_calibration.json` when present and records `calibration_source`.
5. For AI-tts, set `decisions.ai_tts_language` to the profile value above and do not require a separate voice decision.
6. Use `full_script` TTS and keep one continuous output file.

## Sequential Shot Selection

Cutting must be chronological by default. In v1.4.2, the main path must be contiguous, not merely monotonic. Build the edit from the resolved preset's `shot_mapping_rules` plus source blocks:

1. Sort all usable candidate shots by `src_index` and `start`.
2. Build an opening segment according to the resolved preset. If nonlinear teaser shots are allowed, keep them documented and within `decisions.max_nonlinear_exceptions`; if they are not allowed, keep the opening chronological.
3. After the opening, choose contiguous source blocks according to the resolved preset. Each block should be a coherent story beat or adjacent set of shots from one source range.
4. Bind each script unit to one small block or a neighboring pair of blocks. Avoid mapping a single unit to scattered unrelated shots.
5. Within each block, consume shots forward. Prefer adjacent shots or the nearest later suitable replacement in the same block.
6. Large source jumps after the hook are allowed only at script beat or paragraph transitions, and every jump must have a recorded reason in `shot_block_report`.
7. Apply repetition penalties for consecutive same-character/same-framing close-ups unless the hold is a deliberate emotional beat.
8. Never shuffle candidate lists, use random sampling, or pull visually interesting shots from unrelated time ranges merely for variety.
9. Before review, flatten all selected shot IDs and verify both monotonic main path and post-hook block continuity. If either fails, rebuild the mapping before asking the user to approve it.

The story may skip weak or repetitive material, but the main selected path must move through contiguous source blocks outside documented style-approved exceptions.

When a preset allows nonlinear exceptions, every exception must be written to `nonlinear_exceptions.json`, counted against `decisions.max_nonlinear_exceptions`, listed in the review, and followed by the preset's return-to-main-path policy. Do not hide nonlinear exceptions from the user.

Resolved preset selection targets:

- First 3 seconds should satisfy the resolved preset's subject/conflict/salience rule when enabled.
- Cold-open duration, nonlinear teaser allowance, return-to-main timing, shot-count range, post-hook duration floor, dialogue/emotion duration floor, and speed ranges come from `references/story_styles.json`.
- Use the preset's source-block policy instead of scattered single-shot sampling. Style 5 additionally requires a multi-beat `highlight_edit_plan`.
- Avoid repeated same-framing shots unless the hold is intentional and recorded.
- Do not use `tpad=clone` to stretch shot duration except the final 1-2 frame fallback allowed by the hard gate.

## Post-Render Timing Validation

Run timing validation after segment rendering and before final subtitle burn-in/mux. This prevents small per-segment rounding errors from accumulating into visible narration drift.

Required approach:

1. Convert each approved narration line duration to integer output frames at the final FPS, usually `24000/1001`.
2. Allocate that line's integer frames across its owned shots.
3. Store `target_frames`, frame start/end, and frame-quantized durations in a derived alignment artifact such as `compose/strict_alignment_frameq.json`.
4. Render each segment with the target frame count enforced. Do not depend only on `-t <seconds>`.
5. Probe every rendered segment with `ffprobe -count_frames`.
6. Write `compose/timing_drift_report.json` or an equivalent artifact with expected frames, actual frames, per-line drift, and total drift.
7. If the probe fails, rebuild frame allocation or rerender segments before final mux.

Pass thresholds:

- every rendered segment must hit `actual_frames == target_frames`
- max line-boundary drift <= `80ms`
- total timeline drift <= `120ms`

QA summary must include the old/new timing drift when a render is regenerated to fix drift.

## Frame Tagging With GPT-5.5 Low Subagents

Generate contact sheets instead of sending individual frames one by one.

Before contact sheets are generated, frame extraction completeness must pass. Use this fixed production path:

1. Use ffmpeg scene detection to create real source shots only.
2. For shots up to about 8 seconds, extract `first`, `mid`, and `last` frames.
3. For shots longer than about 8 seconds, keep one real shot and add analysis-only sample frames at roughly 3-4 second intervals, capped around 9-12 total frames unless the shot contains unusually dense action.
4. Run OpenCV batch extraction first for speed.
5. Verify every expected frame path from the manifest.
6. Backfill only missing paths with ffmpeg timestamp extraction.
7. Verify again and block contact sheets if any frame is still missing.

Do not split long shots into artificial render shots to create more contact-sheet rows. Long-shot samples may appear in contact sheets, but their IDs should remain tied to the parent real shot and must not be treated as independent render candidates.

This step must be performed by Codex subagents. Local inspection, subtitle fusion, transcript summaries, manual scene notes, or non-subagent model output may be used only to prepare prompts or audit results. They must not create the final `shot_story_tags.json`, must not be treated as equivalent to visual tags, and must never be used to set `checks.gpt_visual_tagging_done=true`.

Use batches of about 12 shots per sheet. Ask subagents to output JSONL only, one line per shot. After a subagent returns or is no longer needed, collect its output and call `close_agent`; do this for successful, failed, and superseded tagging agents.

Default model choice:

- Use `gpt-5.5` subagents with `reasoning_effort: low` for both quick screening and production full-episode tagging.
- Treat subagent GPT visual tagging as the required production path. Do not wait for a separate user instruction to start it when visual tags are needed; only skip it if the user explicitly opts out.
- Treat visual tagging as a pre-story hard gate. Transcript-only analysis, manual notes, local inspection, or subtitle summaries may prepare prompts, but they must not produce `story_evidence_pack`, `initial_story_seed`, `story_atoms`, narration scripts, shot mappings, or review artifacts before merged subagent visual tags exist.
- Escalate only selected difficult sheets or key story segments to `gpt-5.5` with `reasoning_effort: medium`.
- Observed quota reference on a 24-sheet / 282-shot episode: full `gpt-5.5 low` tagging used about 3-4% of a Pro 5x five-hour quota window.

Subagent prompt essentials:

```text
Read the contact sheet. For every visible shot_id, output one JSON line with:
shot_id, src_index, characters, scene, objects, key_subject, key_action,
emotion, visual_summary, story_function, confidence.
Use role terms, not IP names. Do not invent what is not visible.
Keep terminology stable across sheets. Prefer `少年`, `成年男性`, `老人`, `怪鸟`, `云海`, `巨树`, and similar reusable terms over many one-off synonyms.
```

Merge all subagent JSONL parts, check duplicates, missing IDs, invalid JSON, and any shot covered only by local/manual notes. If the final batch misses shots, reassign only missing sheet ranges to subagents. Close each completed subagent with `close_agent` before setting `checks.gpt_visual_tagging_done=true`.

After merging, normalize:

- role names: merge near-synonyms such as `成年男性`, `男人`, `高个青年` when they are the same visual role
- object names: merge `怪鸟`, `巨鸟幼鸟`, `雏鸟` when the story role is the same
- story functions: map one-off labels into a stable set such as `setup`, `action`, `dialogue`, `emotion`, `reveal`, `transition`, `object`, `landscape`, `op_ed`, `unknown`

After normalization, update `workflow_state.json` with `checks.gpt_visual_tagging_done=true`, `artifacts.visual_tags`, and any missing-shot count. Run `scripts/validate_workflow_state.py <project>/workflow_state.json --gate story` before the story evidence pack subagent, content-style initial story writing, or shot mapping.

## Retention Subagent Prompt Essentials

Use separate narrow prompts for creative stages so each artifact can be audited:

- Story evidence pack: use a Codex subagent to output `story_evidence_pack.json` from visual tags, dialogue/frame fusion, subtitle alignment, and independent video windows. It must include environment replacement chains, role relationships, background experience, cause-effect chains, strong visual evidence, quotable dialogue, forbidden inferences, and source shot/time mappings; it must not write narration or final story copy, and it must close the subagent with `close_agent`.
- Initial story writing: delegate to `content-style-system` task `anime_clip_initial_story_write` with `references/initial_story_write.md`; save `initial_story_seed.json`, `story_atoms.json`, and `initial_story_execution_log`. `anime-noref-clip` must not locally extract or rewrite `story_atoms.json`.
- Story style preset: resolve a preset from `references/story_styles.json` before retention brief, record it in `workflow_state.json`, run the `style` gate, and apply its decision overlay to downstream prompts.
- Hook candidates: generate at least the resolved preset's `creative_qc_profile.min_hook_candidates` hooks with `hook_id`, `type`, `text`, `first_shots`, `supported_by_atoms`, support dialogue, scores, spoiler risk, payoff availability, and `why_it_hooks`. Reject unsupported sensational hooks.
- Retention shot pool: score only what is visible or strongly supported by nearby dialogue. Penalize OP/ED/preview, black/fade, unclear framing, confusing out-of-order shots, repeated same-framing close-ups, and scattered shots with high continuity cost.
- Source blocks: group adjacent source shots into coherent story blocks and map script units to those blocks. Do not optimize the body by picking isolated high-energy shots one by one.
- Script variants: generate variants appropriate to the resolved story style and its `script_rules`; for style_01, variants may include `A_clear_plot`, `B_aggressive_retention`, and `C_high_density_reversal`.
- Reference script optimization: after `script_variants.json`, the active row 11 goal must name `content-style-system` copywriting. Delegate candidate review and final copy rewrite to the `content-style-system` writing skill using `references/script_reference_optimization.md`; write the returned result as `script_reference_review.json` and save `content_style_execution_log` before final script or shot mapping.
- Creative retention QC: use the resolved preset's `creative_qc_profile`, fail unsupported claims, undocumented nonlinear exceptions, non-monotonic main path, OP/ED overlap, or unrelated filler shots, and return concrete revision suggestions when failing.

## AssemblyAI Transcript With Speaker Diarization

Use AssemblyAI as the default production transcription path.

Inputs:

- extracted audio from the source video
- `speaker_labels` / diarization enabled
- language configured when known

Outputs:

- raw AssemblyAI response for audit
- normalized `transcript_assemblyai.json`
- optional plain markdown script for human review

Normalization rules:

- Convert millisecond timestamps to seconds.
- Preserve `Speaker A/B/...` labels exactly until a later role-mapping stage.
- Keep every utterance as `{speaker, start, end, text}`.
- Merge only obvious continuation fragments from the same speaker when they are adjacent and semantically continuous.
- Do not infer character names during transcription normalization.

Use the structured transcript in story analysis. Ask the model to infer:

- speaker relationships
- who asks and who answers
- emotional changes across turns
- dialogue-driven plot beats
- dialogue-to-shot alignment risks

Fallback:

- Use local Whisper or faster-whisper only when AssemblyAI is unavailable, too costly, or explicitly requested.

## OP/ED/Preview Exclusion

Before selecting shots, configure hard exclude ranges:

```json
"exclude_ranges": [
  {"label": "opening_song", "start": 56, "end": 135},
  {"label": "ending_song", "start": 1282, "end": 1401},
  {"label": "next_episode_preview", "start": 1401, "end": 1426}
]
```

These values are episode-specific examples. Always inspect the current source and adjust.

Validation:

```python
bad = []
for pick in final["picks"]:
    for r in cfg["selection"]["exclude_ranges"]:
        if max(pick["src_start"], r["start"]) < min(pick["src_end"], r["end"]):
            bad.append((pick["shot_id"], r["label"]))
assert not bad
```

Cold-open teaser exceptions are not allowed to use OP/ED/preview shots unless the user explicitly approves that exact use. Record all exclude ranges in the project config or `workflow_state.json`.

## Retention Pipeline

Run these creative stages after dialogue/frame fusion and before script-to-shot review. The artifact sequence is shared across styles; prompt bias, shot-selection bias, nonlinear policy, shot-count range, and QC profile come from the resolved preset in `references/story_styles.json`.

1. Build `story_evidence_pack.json` with an independent Codex subagent. The pack is evidence only, grouped per independent video, and must include visual/dialogue support, background experience, environment replacement chains, forbidden inferences, and source shot/time mapping.
2. Resolve `decisions.story_style` from `references/story_styles.json`. If unspecified, use `style_01_aggressive_youtube_cold_start`; record `story_style`, `story_style_preset`, `story_style_label`, `story_style_config`, `artifacts.story_styles_config`, `checks.story_style_preset_resolved=true`, and scaled target shot-count bounds.
3. Delegate initial story writing to `content-style-system` task `anime_clip_initial_story_write` using `references/initial_story_write.md`. Save `initial_story_seed.json`, `story_atoms.json`, and `initial_story_execution_log`; reject any seed with unsupported claims or lazy transitions such as `另一边`.
4. Build `retention_brief.json` from `initial_story_seed.json` and the resolved preset. It must define the main reason to keep watching, first 2-second hook, first 10-second question, midpoint payoff, strongest ending point, spoiler policy, skipped source ranges, allowed operations, and forbidden operations.
5. Generate at least the preset's required number of supported hooks in `hook_candidates.json` from `initial_story_seed.json`. Choose the hook/opening with the best mix of source support, visual salience, style fit, and payoff availability. Reject loud but unsupported hooks.
6. Score `retention_shot_pool.json`. Reserve the strongest clear shots for the first 3 seconds, re-hooks, reveals, and payoffs. Prefer emotionally or visually legible shots over neutral connective shots.
7. Generate style-appropriate script variants in `script_variants.json` from `initial_story_seed.json`. For style_01, default variants may include `A_clear_plot`, `B_aggressive_retention`, and `C_high_density_reversal`; other styles should use variants that match their `script_rules` and `selection_bias`.
8. Run reference script optimization by delegating to the `content-style-system` writing skill with `references/script_reference_optimization.md`, the resolved preset, `initial_story_seed.json`, source evidence, and every script variant. The writing skill should use the single common anime optimization reference, not multiple preset pages, and it owns the selected/revised final copy recommendation. Save its JSON-compatible result as `script_reference_review.json`, save a `content_style_execution_log` that records the writing skill invocation, and require `candidate_reviews` to cover every variant. If no real Obsidian AI-vs-human samples exist, pass `script_style_guide.example_lines` and `script_style_guide.bad_good_examples` from `references/story_styles.json` as fallback references for the writing skill.
9. Select the final `script.json`, map it to `final_shots.json`, document any nonlinear shots in `nonlinear_exceptions.json`, then run `retention_qc.json`.

When mapping shots, select real shot IDs and stable source windows only. Long-shot sample frames may justify why a region is useful, but they are not selectable shots and must not appear as cut boundaries. If multiple useful moments live inside one long real shot, represent them as `source_window` ranges inside the same real shot; merge adjacent ranges from the same real shot when continuity would otherwise create a visible same-scene stutter.

Hook types may include `contradiction`, `outcome_first`, `identity_mismatch`, `moral_dilemma`, `danger_countdown`, `emotional_betrayal`, `confession`, and `object_clue`.

Creative QC pass thresholds come from the resolved preset unless a hard production gate overrides them. The validator loads the active preset and checks unsupported claims, generic exposition, first-3-second salience when required, cold-open duration, nonlinear exceptions and review, target shot count, post-hook/dialogue duration floors, source-block policy, script-unit binding, large-jump reasons, repetition penalty, OP/ED overlap, monotonic main path, unique-shot policy, and any style-specific fields such as style 5 `highlight_edit_plan_required`.

If creative QC fails, revise the script, shot pool, hook choice, or shot mapping before review. Do not proceed to TTS.

## Script Rewrite Rules

Use these hard rules when creating short-video plot narration:

- No extra content.
- No lore that is not visible or in dialogue.
- No filling gaps with assumptions.
- Prefer relationship words over proper names.
- Unless the user explicitly asks to keep IP names, public-facing scripts, subtitles, title drafts, and description drafts must hide anime title, series, official character names, and strongly identifying proper names. Use role, relationship, appearance, profession, or story-function labels instead. Internal audit files, source paths, shot metadata, and visual tags may keep source-identifying details for verification.
- Make it understandable without fandom knowledge.
- Cut slow setup.
- In natural plot mode, use at most one light opening hook, then move directly into plot causality.
- Shape the opening according to the resolved preset's `script_rules.opening`; in cold-start mode, lead with a source-supported conflict, contradiction, danger, confession, or clear question in the first 1-2 seconds.
- Use supported middle beats according to the resolved preset's `script_rules.middle`. In style_01, a micro-hook is a source-supported question, reversal, danger, decision, confession, object clue, or emotional contradiction.
- Style_01 micro-hooks must have a payoff, clarification, or escalation within 6-15 seconds; other styles follow their preset payoff cadence.
- Explain character actions, discoveries, and stakes in source order unless reordering clearly improves comprehension.
- Every final script unit must include `source_time` plus `sentence_source_map`. Each sentence map must record the sentence text, source time range, source shot IDs, plot function, and a TTS budget in seconds. When row 11 rewrites copy, it must update this map before shot mapping, not leave stale timings from the old sentence.
- Write plot explanation, not visual captions. A valid sentence explains a cause, choice, consequence, danger, relationship shift, question, or payoff supported by the shot/dialogue. A line that only says what is visibly on screen without why it matters is counted as `visual_caption_line_count` and must be rewritten to zero before TTS.
- Avoid over-amplified phrasing such as repeating "more shocking", "the biggest twist", or "most absurd" unless the current shots and dialogue directly support it.
- Avoid "actually / more shocking / biggest twist" style phrases without source support.
- Keep sentences short enough for subtitles.
- End at the strongest retention point; the script does not need to cover the whole source.

Allowed operations:

- delete
- reorder
- compress
- replace proper names with roles
- speed up

Forbidden operations:

- inventing backstory
- adding unseen motives
- explaining off-screen lore
- selecting shots after writing unsupported narration
- writing narration first and then forcing mismatched shots to fit

Recommended cold-start beat roles:

```text
cold_hook
context_snap
first_stakes
escalation
micro_reveal
choice
consequence
reaction
payoff
cliffhanger
```

## Script-to-Shot Review

Always create review artifacts before composing. The markdown table should include:

```text
unit id
beat role
narration
target seconds
hook/payoff function
shot id
source time range
frame path
visual summary
dialogue summary
scene/action
retention reason
source support
score or reason
flags
nonlinear exception flag if applicable
```

Also create a selected-shot contact sheet for fast visual review.

Report:

```text
units=N
selected shots=N
target duration=N
chosen variant=<style-appropriate variant id>
script reference review=pass/fail
script reference unsupported claims=0
chosen hook=h03
hook candidates=N
micro-hooks=N
payoffs=N
max re-hook gap=N sec
first 3s visual salience pass=True/False
unsupported claims=0
generic exposition lines=N
OP/ED/preview overlap=0
main path monotonic=True
post-hook contiguous blocks=True
source blocks=N
large jumps at beat boundaries=True
large jump reasons recorded=True
nonlinear exceptions=N
nonlinear exceptions reviewed=True/False
unique shots=True
selected shot count=N
target shot count range=<preset-scaled min-max>
average shot duration=N sec
post-hook min shot duration=N sec
dialogue/emotion min shot duration=N sec
first 10s shot count=N
creative retention QC=pass/fail
```

## Full-Script TTS Alignment

After TTS, rebuild timing from the real continuous audio:

1. Before production TTS, estimate duration at the anime default speed:
   `python3 tools/estimate_tts_duration.py --project-root <project> --speed 1.2`.
2. If `estimated_tts_duration_ratio < 0.9`, choose a longer/stronger source window or rewrite the script before synthesis.
3. Generate the approved narration exactly once as one continuous audio file, with `AI-tts` by default:
   `python3 tools/generate_tts_ai_tts_v145.py --project-root <project> --language <zh|en|th> --speed 1.2`.
4. Write `tts_generation_manifest.json` with provider, language/profile, speed, text source, output file, boundary source, and cleanup scan results.
5. Before compose, scan the active project TTS/output paths for `unit_*.mp3`, `unit_*.wav`, and `concat_units.txt`. These must not exist for the main render. Set `checks.tts_single_file_only=true`, `checks.tts_unit_audio_residue_count=0`, and `checks.tts_concat_manifest_absent=true`.
6. Preserve real boundary metadata from AI-tts. Prefer raw AssemblyAI word timing with `timing_source=assemblyai_word_boundary`; use `assemblyai_segment_boundary` only when word boundaries are unavailable.
7. If real provider boundaries are unavailable, stop and regenerate timing from AI-tts/AssemblyAI before subtitle planning.
8. Build `subtitles/tts_boundary_table.json` from the target language's real TTS boundaries with `tools/build_tts_boundary_table.py` when the TTS adapter has not already produced it.
9. Run a Codex subagent to generate `subtitles/semantic_cue_plan.json` from `subtitles/tts_boundary_table.json`. Use the project-local `references/subtitle_semantic_cue_plan.md`; the subagent groups contiguous `boundary_start/boundary_end` ranges only and must preserve all boundary text after normalization. After collecting the cue plan, call `close_agent` for that subagent before continuing.
10. Attach the subagent boundary groups to exact real-boundary timing with `tools/build_post_tts_alignment_v145.py --require-subtitle-plan`. Do not split only by script lines, raw character count, provider token groups, or raw text proportion.
11. Write `subtitle_timing_report.json` with timing source, boundary-table path, semantic segmentation source, cue count, max/min cue durations, max visual line length, subagent boundary-group status, coverage/mismatch counts, cross-sentence/orphan/bad-break counts, and punctuation cleanup status.
12. For each narration line or cue group, get its owned shots.
13. Solve shot count before speed: for a 4-second narration line, choose 1-3 real source shots, one stable window inside a long real shot, or one small contiguous block whose source duration is already near 4 seconds. Do not use analysis sample points as edit boundaries.
14. Set the line's shot group duration equal to the real continuous-audio interval, including natural pauses.
15. Split duration across owned shots.
16. Trim or extend source windows before using speed changes.
17. Use modest speed changes to match audio. Hook, post-hook, and non-hook extremes must remain within the resolved preset's `hook_speed_range`, `post_hook_speed_range`, and `absolute_non_hook_speed_range`.
18. If speed factor falls outside range, reduce shot count, replace a shot, extend the source window, rebalance narration-to-shot ownership, or revise text before composing.
19. Do not compress post-hook shots below `1.3s` or dialogue/emotion shots below `1.6s` to force a prechosen shot count.
20. Do not use `tpad=clone` to make a short shot fit. Only after all better options fail may final fallback padding add 1-2 frames total, and it must be recorded in `alignment_qc_report.json`.

Post-TTS pacing repair is mandatory before render:

- Estimated script duration is diagnostic only. Once real TTS exists, the real TTS duration is the timeline source of truth.
- In projects initialized from the skill template, run `tools/build_tts_boundary_table.py` immediately after full-script TTS, then run a Codex subagent to group contiguous boundary ids into `subtitles/semantic_cue_plan.json`, close it with `close_agent` after collecting the plan, then run `tools/build_post_tts_alignment_v145.py --require-subtitle-plan`. This trio is the standard handoff from TTS to pacing/alignment/subtitles and must run before the pacing validator, segment render, or compose.
- Write `post_tts_pacing_report.json` comparing estimated duration, real TTS duration, selected shot count, speed range, and repair actions.
- If speed exceeds allowed ranges, do not render. Repair by revising script length, deleting duplicate shots, extending stable source windows, adding nearby sequential shots, or reassigning line ownership.
- If a line cannot fit without bad speed, change shot count/source windows first; do not force 1.7x playback or 0.7x drag.
- Store every selected shot's `stable_src_start` and `stable_src_end` in `stable_subwindows.json`.
- If a detected shot contains a hidden internal cut, use only a stable sub-window or replace the shot.
- Tail source buffers are forbidden globally. `safe_render_tail_buffer` may be used only when the buffer remains inside the same stable source shot, does not cross a detected/scanned cut, is recorded in `source_buffer_report.json`, and is <= 2 frames unless explicitly approved.

Avoid sentence-by-sentence TTS for the main render because stitched clips can sound disconnected and corrupt subtitle/video alignment. Do not leave per-line/per-cue audio artifacts in the active project path. Use per-line/per-cue TTS only for temporary diagnosis or an explicitly approved fallback render, and note that fallback in QA.

For multilingual versions:

- keep each language in an isolated project/output directory
- keep a separate `workflow_state*.json` per language, such as `workflow_state_zh.json` and `workflow_state_en.json`
- generate that language's own continuous TTS
- capture that language's own boundary metadata
- regenerate subtitle timing and strict alignment from that language's TTS
- do not reuse subtitle timing from another language, even when the shot list is reused
- for English 60-second shorts, check a script word budget before TTS; usually target 130-145 words and revise before render if the budget fails

Line QA:

```text
line.voice_start == first_owned_shot.timeline_start
line.voice_end == last_owned_shot.timeline_end
alignment_solve_order == "shot_count_then_speed"
post_hook_speed_factor in 0.88..1.18
tpad_clone_total_frames <= 2
```

## Black/Fade Filtering

Before final shot mapping and again before final delivery:

- scan candidate shot windows for black frames, fade transitions, and extremely low luma
- avoid using the first or last frames of fade-heavy shots as representative content
- when a selected shot contains a dark transition, move the trim window inward or replace the shot
- run final black detection on the rendered output and report zero known black events unless the source story intentionally contains black frames

Keep luma/black metadata with shot picks so suspicious shots can be audited later.

## Internal Jump Scan

Run an internal jump scan after segment render and before delivery. This catches hidden cuts inside source windows that normal `ffprobe`, blackdetect, and frame counts can miss.

Required approach:

1. Build the planned edit-boundary list from `strict_alignment_frameq.json`.
2. Run frame-difference scanning over the rendered output.
3. Ignore planned cut boundaries with a small tolerance, usually 2 frames.
4. Any high-diff event inside a single selected shot or stable sub-window is an internal jump candidate.
5. Write `internal_jump_scan_report.json` with method, threshold, planned-boundary tolerance, events, and `internal_jump_count`.
6. Delivery requires `internal_jump_count == 0`.

If internal jumps are found, repair upstream by shrinking to a stable sub-window, replacing the shot, or adjusting the source block. Do not explain the jump in QA and deliver anyway.

## Subtitle QA

On macOS, if Chinese burns as boxes:

- Use `Arial Unicode MS`.
- Pass `fontsdir=/System/Library/Fonts/Supplemental` to the ASS filter.
- Extract a frame after muxing and inspect it.

Subtitle content rules:

- Display subtitle fragments must not end with punctuation.
- Strip trailing display punctuation such as `，。！？、；：,.!?;:` and locale equivalents from subtitle cues and wrapped visual lines.
- Do not remove punctuation from the narration/TTS source text solely for this display cleanup.
- Keep cues short enough for one or two readable visual lines. Cue duration must be `>= 0.3s` and `<= 2.2s` unless an emotional hold exception is intentional and recorded; merge very short cues instead of letting them flash.
- Plan cue text semantically with a Codex subagent before final ASS generation. The subagent must group contiguous entries from `subtitles/tts_boundary_table.json` by `boundary_start/boundary_end`; close it with `close_agent` after collecting or rejecting the plan. The script then uses those exact real TTS boundary times. Do not let raw provider token grouping alone decide cue text if it spills across narration units or sentence boundaries.
- Use script punctuation, real TTS word boundaries, and visual character limits together. Do not make subtitle timing from script-line boundaries alone.
- For production `v1.4.9+` projects, both `subtitles/tts_boundary_table.json` and `subtitles/semantic_cue_plan.json` must exist. The cue plan must be generated by a subagent, must group contiguous boundary ids, and must preserve all boundary text after normalization. Local scripts must not rewrite or repair semantic cue grouping; if validation finds bad phrase boundaries, regenerate the cue plan with the subagent.
- Do not cross original sentence boundaries in one displayed cue unless a continuation is intentional and recorded. If TTS boundary grouping shifts words into the next sentence, repair by cumulative text alignment before render.
- Record and require zero `subtitle_cross_sentence_boundary_count`, `subtitle_orphan_fragment_count`, and `subtitle_bad_line_break_count` before compose.
- For Chinese, prefer complete semantic chunks of roughly `6-14` characters, with `4-16` allowed for timing. Avoid orphan fragments such as `被掳`, `却仍`, `她反问`, `作为他`, or `的妻子活下去`; merge them with neighboring words. Never split fixed phrases such as `皇太子妃`, `杀人不眨眼`, `亲眼见过的温柔`, `作为他的妻子`, `低成本商品`, or `治疗他妹妹的药`. Also reject mid-word/subphrase breaks such as `两个 / 人`, `已经不 / 对`, `起不 / 来`, `浅发 / 男人`, `求救 / 声`, `白色 / 装置`, `台 / 面上`, `放我 / 出去`, `蓝白色 / 星体`, and `一 / 招`.
- For English, keep visual line length around 32 characters or less where possible.
- Split subtitles with language-aware boundaries. For Thai, prefer word or phrase boundaries and timing windows; do not hard-slice by character count.
- For English, split on natural phrase/word boundaries and avoid awkward orphan words.

Placement rules:

- Prefer subtitle placement above source subtitles when source already has baked subtitles.
- For vertical 9:16 output with a centered horizontal anime frame, place subtitles near the bottom of the actual video picture, not the bottom padding/fill area.
- For horizontal 16:9 output, use the normal lower safe area.
- Compute subtitle coordinates from the foreground picture box, not from the full vertical canvas.
- Subtitles must remain inside the foreground video box. They must not sit on the blurred background, top/bottom padding, or any area outside the actual 16:9 anime frame.

## Compose Options

Use absolute paths in ffmpeg concat lists, audio manifests, and generated command files. This avoids duplicated relative prefixes such as `tts/tts/...`.

Vertical `9:16` layout rules:

- Default layout is blurred background plus complete centered 16:9 foreground picture.
- Do not scale/crop the foreground to fill the vertical canvas. The main anime frame must preserve its full 16:9 information.
- Center the foreground box both horizontally and vertically. Top and bottom blur margins should be equal within a small rounding tolerance, normally `<= 4px`.
- In ffmpeg, split the source first, then process branches independently. The background branch may scale/crop/blur to fill 9:16; the foreground branch must scale by containment and preserve aspect ratio.
- Do not let the foreground inherit the background branch's over-scaled dimensions. If the filter graph is ambiguous, rewrite it before rendering.
- Compute the foreground picture box and store it in `vertical_layout_qa.json`; subtitle coordinates must be based on and inside that box.
- Extract QA frames from early, middle, and late output. Check that the foreground is complete, centered vertically, not over-zoomed, and subtitles are inside the foreground frame rather than in the blurred background.

When BGM is requested:

- trim or loop it to the exact final duration
- keep it under narration, usually around `0.15` to `0.20` relative volume unless the mix needs adjustment
- fade it out at the end
- apply limiter or normalization so narration stays clear
- output final audio at a normal delivery sample rate such as 48 kHz

When watermarking is requested:

- use `@AlsinCro` when no new text is specified
- use slow dynamic movement with enough range to reduce easy cropping, usually spanning most of the safe visible canvas while avoiding permanent overlap with the subtitle band
- default opacity cycling is `5%` to `15%`; the watermark should be subtle on bright scenes and still faintly discoverable on dark scenes
- use separate slow periods for horizontal motion, vertical motion, and opacity so the pattern is not visually static
- test several frames before full render, and verify first/middle/late QA frames after final render
- do not use smart-invert watermarking unless the user explicitly asks for it again
- record `watermark_enabled`, `watermark_text`, `watermark_strategy`, `watermark_strategy_applied`, `watermark_strategy_recorded`, `watermark_visibility_checked`, and any `watermark_qa_frames` in `workflow_state.json`

For multilingual versions:

- keep each language in an isolated project/output directory
- do not overwrite source-language TTS, subtitles, alignment, or final renders
- localize the narration naturally instead of literal translation when the target platform/language benefits from it
- regenerate timing from that language's own continuous TTS audio before matching shots
- set `checks.multilingual_timing_isolated=true` only after confirming subtitles, boundaries, alignment, and final renders were generated from that language's own TTS artifacts

## Final QA

Run `ffprobe` and report:

- final path
- video duration
- audio duration
- resolution
- fps
- audio/video stream presence
- TTS generation mode and unit-audio cleanup result
- TTS boundary source and subtitle timing report
- strict alignment line count and shot count
- speed min/max
- subtitle screenshot path
- vertical foreground box, top/bottom centering check, subtitle foreground-box check, and layout QA frame paths when vertical output is rendered
- BGM path and mix choice if BGM was used
- watermark strategy, opacity/motion settings, and QA frame paths if watermark was used
- black/fade detection result
- output aspect and subtitle placement rule

Do not leave known long-running TTS or transcription processes in the background.

Always write a `qa_summary*.md` for completed renders.
