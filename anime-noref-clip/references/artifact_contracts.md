# Anime No-Reference Clip Artifact Contracts

## Artifact Schema Targets

Structured transcript from AssemblyAI speaker diarization:

```json
{
  "provider": "assemblyai",
  "source_audio": "output/source/audio.wav",
  "language": "zh",
  "utterances": [
    {
      "speaker": "Speaker A",
      "start": 12.34,
      "end": 15.67,
      "text": "你真正想要的到底是什么"
    },
    {
      "speaker": "Speaker B",
      "start": 15.92,
      "end": 21.4,
      "text": "我想要的是眼前还不存在的东西"
    }
  ]
}
```

Keep AssemblyAI speaker labels stable during the first pass. After visual tags and dialogue context are available, a stronger model may map them to role labels such as `少年`, `父亲`, `老人`, or `同伴`.

Shot metadata:

```json
{
  "shot_id": "shot_0000",
  "src_index": 0,
  "cut_source": "scene",
  "start": 0.0,
  "end": 12.4,
  "duration": 12.4,
  "frames": {
    "first": "frames/shot_0000_first.jpg",
    "mid": "frames/shot_0000_mid.jpg",
    "last": "frames/shot_0000_last.jpg"
  },
  "sample_frames": [
    {"time": 3.8, "path": "frames/shot_0000_sample_01.jpg"},
    {"time": 7.2, "path": "frames/shot_0000_sample_02.jpg"}
  ],
  "render_boundary_policy": "real_scene_cut_only_no_duration_based_render_splits"
}
```

Shot IDs represent real continuous source windows between ffmpeg scene cuts. Do not create renderable duration-based artificial shots for long source shots. Extra `sample_frames` are analysis-only frames used for contact sheets and visual tagging; they must not become cut boundaries or standalone render shots.

Frame extraction report:

```json
{
  "method": "opencv_batch_then_ffmpeg_timestamp_backfill",
  "shot_count": 360,
  "expected_images": 1284,
  "opencv_saved_images": 1154,
  "ffmpeg_backfill_images": 130,
  "saved_images": 1284,
  "missing_images": [],
  "passes": true
}
```

Story generation, contact sheets, visual tagging, and shot mapping must not start unless `passes=true`, `saved_images == expected_images`, and `missing_images` is empty.

Fused story tag:

```json
{
  "shot_id": "shot_0000",
  "src_index": 0,
  "start": 0.0,
  "end": 3.2,
  "characters": ["少年"],
  "scene": "客厅",
  "objects": ["茶杯"],
  "key_subject": "少年",
  "key_action": "道歉",
  "emotion": "愧疚",
  "visual_summary": "少年站在客厅里低头说话。",
  "dialogue_summary": "对不起，我还不够强。",
  "story_function": ["dialogue", "emotion"],
  "confidence": 0.75
}
```

Story evidence pack:

```json
{
  "schema_version": "anime-noref-clip.story_evidence_pack.v1",
  "source_visual_tags": "analysis/shot_story_tags.json",
  "source_dialogue_frame_fusion": "analysis/dialogue_frame_fusion.json",
  "content_rule": "evidence_only_no_narration",
  "independent_videos": [
    {
      "video_id": "window_01",
      "target_duration_sec": 70,
      "candidate_main_line": "幸存者为了逃离废墟而放弃救援，最终把危险带回自己身边。",
      "environment_replacement_chain": [
        {
          "from": "红色荒地坠落点",
          "to": "破损飞船控制区",
          "visual_bridge": "坠落残骸、控制台、破口光源连续出现"
        }
      ],
      "role_relationships": [
        {
          "role": "黑发男子",
          "relationship": "与克里斯共同推进逃离计划",
          "supported_by": ["shot_0183", "dialogue_primary_0062"]
        }
      ],
      "background_experience": [
        {
          "claim": "克里斯长期把货物和逃离优先于救援",
          "supporting_dialogue": ["不关我们的事，走吧", "这我说了算"],
          "supporting_shots": ["shot_0119", "shot_0307"]
        }
      ],
      "cause_effect_chain": [
        {
          "cause": "克里斯选择继续装货离开",
          "effect": "求救声和爆破事故同时升级",
          "supporting_shots": ["shot_0303", "shot_0318"]
        }
      ],
      "strong_visual_evidence": ["红色囊状结构爆发", "人物被抛入太空"],
      "quotable_dialogue": ["他们就在那", "这我说了算"],
      "forbidden_inferences": ["不能写成所有人都已死亡", "不能替角色补未说出口的悔意"],
      "source_map": [
        {"shot_id": "shot_0307", "start": 1002.1, "end": 1005.8}
      ]
    }
  ],
  "checks": {
    "narration_generated": false,
    "all_claims_have_source": true,
    "subagent_closed": true
  }
}
```

The evidence pack is prepared by a Codex subagent and must be closed with `close_agent`. It is not final writing; it is the source bundle for `content-style-system`.

Initial story seed:

```json
{
  "content_style_skill": "content-style-system",
  "content_style_task": "anime_clip_initial_story_write",
  "source_story_evidence_pack": "analysis/story_evidence_pack.json",
  "obsidian_references_used": [
    "/Users/gxator.alli/Documents/Obsidian/content-style-vault/30-style-families/viral-video-script/categories/anime-clip/script-optimization-reference.md"
  ],
  "video_stories": [
    {
      "video_id": "window_01",
      "target_duration_sec": 70,
      "selected_story_line": "克里斯以为只要带走货物就能逃生，但每次放弃救援，危险都更快追上他。",
      "conflict_points": ["救援与自保冲突", "货物目标与生存危机冲突"],
      "hook_directions": ["outcome_first", "moral_dilemma"],
      "weak_information_compression": ["压缩控制台操作细节，把篇幅留给抛弃救援与怪物袭击"],
      "forbidden_phrasing_hits": [],
      "source_evidence": [
        {
          "claim": "克里斯压下救援选择",
          "supporting_dialogue": ["这我说了算"],
          "supporting_shots": ["shot_0307"]
        }
      ]
    }
  ],
  "checks": {
    "source_support_passed": true,
    "unsupported_claims_count": 0,
    "no_lazy_transition_passed": true
  }
}
```

`story_atoms.json` is the machine-friendly atom view derived from `initial_story_seed.json` by `content-style-system`. It must preserve source evidence for every atom.

Story atom:

```json
{
  "atom_id": "a012",
  "source_time": [164.6, 181.2],
  "characters": ["少年", "玩偶男人"],
  "event": "玩偶男人承认上一世杀过人",
  "conflict": "他看似在告别，实际暴露了无法逃避的罪",
  "question": "他为什么要在这时坦白",
  "payoff": "这句话改变了少年对他的判断",
  "supporting_dialogue": ["..."],
  "supporting_shots": ["shot_0058", "shot_0060"],
  "retention_type": ["confession", "mystery", "moral_conflict"],
  "risk": "medium_spoiler"
}
```

Retention brief:

```json
{
  "story_style": "style_01_aggressive_youtube_cold_start",
  "story_style_preset": "references/story_styles.json#styles/style_01_aggressive_youtube_cold_start",
  "platform": "youtube_cold_start",
  "target_duration_sec": 60,
  "opening_goal": "2秒内制造反常识冲突",
  "main_question": "这个男人为什么主动承认自己杀过人",
  "stakes": "如果少年相信他，就会被拖进上一世的罪",
  "spoiler_policy": "允许开头预告中段冲突，但不提前说最终结果",
  "rhythm": {
    "first_hook_sec": 2,
    "rehook_interval_sec": 8,
    "payoff_interval_sec": 20
  },
  "allowed_operations": [
    "delete",
    "compress",
    "reorder_within_supported_context",
    "relationship-name rewriting",
    "cold-open teaser if documented"
  ],
  "forbidden_operations": [
    "inventing motives",
    "inventing lore",
    "unsupported outcome",
    "unrelated filler shots",
    "empty sensationalism"
  ]
}
```

Hook candidate:

```json
{
  "hook_id": "h03",
  "type": "outcome_first",
  "text": "这个玩偶男人不是来告别的，他一开口就承认自己杀过人",
  "first_shots": ["shot_0058", "shot_0060"],
  "supported_by_atoms": ["a012"],
  "supporting_dialogue": ["..."],
  "strength": 0.86,
  "visual_salience": 0.82,
  "mystery_value": 0.84,
  "spoiler_risk": "medium",
  "payoff_available": true,
  "why_it_hooks": "身份反差 + 道德冲突 + 观众想知道原因"
}
```

Retention shot score:

```json
{
  "shot_id": "shot_0058",
  "src_index": 58,
  "start": 164.6,
  "end": 169.4,
  "visual_salience": 0.86,
  "emotion_intensity": 0.78,
  "motion_energy": 0.71,
  "mystery_value": 0.83,
  "conflict_value": 0.76,
  "reaction_value": 0.69,
  "object_clue_value": 0.55,
  "continuity_cost": 0.32,
  "repetition_risk": 0.18,
  "source_block_id": "blk_003",
  "spoiler_level": "medium",
  "hook_candidate": true,
  "rehook_candidate": true,
  "payoff_candidate": false,
  "risk_flags": []
}
```

Source block:

```json
{
  "block_id": "blk_003",
  "source_time": [312.4, 329.8],
  "shot_ids": ["shot_0121", "shot_0122", "shot_0123", "shot_0124"],
  "story_function": "confession",
  "characters": ["少年", "成年男性"],
  "use_for_units": [5, 6],
  "continuity_role": "main_path",
  "large_jump_before": false,
  "large_jump_reason": "",
  "repetition_notes": "two close-ups separated by reaction insert"
}
```

Script unit:

```json
{
  "unit_id": 1,
  "beat_id": 1,
  "beat_role": "hook",
  "beat_type": "reveal",
  "text": "这个玩偶男人不是来告别的。他一开口，就承认上一世的自己，亲手杀过人。",
  "source_time": [164.6, 181.2],
  "evidence_shots": ["shot_0058", "shot_0060"],
  "plot_role": "confession_reveal",
  "target_seconds": 7.0,
  "shot_ids": ["shot_0058", "shot_0060"],
  "sentence_source_map": [
    {
      "sentence_id": "u01_s01",
      "text": "这个玩偶男人不是来告别的。",
      "source_time": [164.6, 169.4],
      "source_shot_ids": ["shot_0058"],
      "plot_function": "misdirection",
      "tts_budget_sec": 2.6,
      "source_evidence": ["shot_0058 visible farewell posture"]
    },
    {
      "sentence_id": "u01_s02",
      "text": "他一开口，就承认上一世的自己，亲手杀过人。",
      "source_time": [169.4, 181.2],
      "source_shot_ids": ["shot_0060"],
      "plot_function": "confession_payoff",
      "tts_budget_sec": 4.4,
      "source_evidence": ["dialogue confession", "shot_0060 reaction"]
    }
  ]
}
```

`source_time` on a script unit is the outer source bound for the unit. `sentence_source_map` is mandatory for final `script.json`: it maps every narration sentence to the narrower source time window, source shots, plot function, and TTS budget used by shot mapping and post-rewrite pacing. Do not treat a sentence that only names what is visible as enough; `plot_function` must explain why the sentence advances causality, danger, choice, relationship, question, or payoff.

Script variant summary:

```json
{
  "variant": "B_aggressive_retention",
  "target_duration_sec": 58,
  "hook_density": "high",
  "line_count": 18,
  "avg_line_sec": 3.2,
  "chosen_hook_id": "h03",
  "rehook_points": [0, 8, 17, 28, 41],
  "payoff_points": [19, 43, 56],
  "risk_flags": ["opening uses later shot as teaser"],
  "unsupported_claims_count": 0,
  "generic_exposition_lines": 0,
  "script": []
}
```

Final pick:

```json
{
  "beat_id": 1,
  "beat_role": "hook",
  "beat_type": "reveal",
  "shot_id": "shot_0058",
  "src_index": 58,
  "src_start": 164.6,
  "src_end": 169.4,
  "src_duration": 4.8,
  "target_duration": 2.5,
  "reason": "matches confession setup"
}
```

Nonlinear exception:

```json
{
  "exception_id": "nl_001",
  "type": "cold_open_teaser",
  "shot_id": "shot_0188",
  "source_time": [612.4, 614.9],
  "used_at_timeline": [0.0, 2.1],
  "returns_to_shot_id": "shot_0042",
  "reason": "strongest visible conflict; used only as opening question",
  "supporting_script_line": "他还不知道，自己救下的人会在今晚背叛他",
  "supported_by_atoms": ["a022"],
  "spoiler_risk": "medium",
  "approved_for_review": true
}
```

Strict alignment shot:

```json
{
  "shot_id": "shot_0058",
  "beat_id": 1,
  "src_start": 164.6,
  "src_end": 167.7,
  "duration": 2.485,
  "timeline_start": 0.0,
  "timeline_end": 2.485,
  "speed_factor": 1.25
}
```

Creative retention QC:

```json
{
  "first_3s": {
    "has_clear_subject": true,
    "has_conflict_or_question": true,
    "visual_salience_min": 0.75,
    "line_char_count_max": 26,
    "passes": true
  },
  "script": {
    "unsupported_claims_count": 0,
    "generic_exposition_lines": 0,
    "max_line_duration_sec": 4.8,
    "rehook_interval_max_sec": 9.5,
    "micro_hooks_count": 6,
    "payoff_count": 3,
    "passes": true
  },
  "shots": {
    "avg_shot_duration_sec": 1.35,
    "selected_shot_count": 31,
    "first_10s_shot_count": 7,
    "cold_open_duration_sec": 4.6,
    "returns_to_main_timeline_sec": 7.2,
    "post_hook_min_shot_duration_sec": 1.36,
    "dialogue_scene_min_shot_duration_sec": 1.72,
    "source_blocks_count": 5,
    "post_hook_contiguous_source_blocks": true,
    "script_units_bound_to_blocks": true,
    "large_jumps_only_at_beat_boundaries": true,
    "large_jump_reasons_recorded": true,
    "repeated_framing_penalty_applied": true,
    "same_scene_run_max": 3,
    "black_fade_risk_count": 0,
    "op_ed_overlap_count": 0,
    "nonlinear_exceptions_count": 1,
    "monotonic_main_path": true,
    "passes": true
  },
  "result": "pass"
}
```

Alignment QC:

```json
{
  "solve_order": "shot_count_then_speed",
  "target_duration_sec": 60,
  "selected_shot_count": 31,
  "cold_open": {
    "duration_sec": 4.6,
    "min_shot_duration_sec": 0.68,
    "min_speed_factor": 0.8,
    "max_speed_factor": 1.32
  },
  "post_hook": {
    "min_shot_duration_sec": 1.36,
    "dialogue_scene_min_shot_duration_sec": 1.72,
    "min_speed_factor": 0.91,
    "max_speed_factor": 1.14,
    "max_non_hook_speed_factor": 1.18
  },
  "padding": {
    "tpad_clone_total_frames": 0,
    "clone_padding_used_only_final_fallback": true
  },
  "passes": true
}
```

Post-TTS pacing repair report:

```json
{
  "estimated_duration_sec": 65.0,
  "real_tts_duration_sec": 48.744,
  "duration_delta_sec": -16.256,
  "real_tts_duration_used": true,
  "repair_actions": [
    "deleted repeated reaction shots",
    "extended stable source windows",
    "rebalanced unit 9 shot ownership"
  ],
  "selected_shot_count_before": 38,
  "selected_shot_count_after": 31,
  "speed_range_before": [0.906, 1.723],
  "speed_range_after": [0.906, 1.18],
  "passes": true
}
```

Stable sub-window map:

```json
{
  "shot_id": "shot_0235",
  "src_start": 582.420,
  "src_end": 586.100,
  "stable_src_start": 582.520,
  "stable_src_end": 584.960,
  "reason": "internal visual jump detected near shot tail",
  "internal_cut_risk": true,
  "safe_tail_buffer_frames": 0,
  "crosses_source_cut": false
}
```

Internal jump scan report:

```json
{
  "method": "frame_diff_scan_excluding_planned_boundaries",
  "diff_threshold": 0.42,
  "planned_boundary_tolerance_frames": 2,
  "internal_jump_count": 0,
  "flagged_events": [],
  "passes": true
}
```

Language budget report:

```json
{
  "language": "en-US",
  "script_word_count": 136,
  "budget_min": 130,
  "budget_max": 145,
  "budget_passed": true,
  "workflow_state": "workflow_state_en.json"
}
```

TTS generation manifest:

```json
{
  "mode": "full_script",
  "provider": "ai_tts",
  "language": "zh-CN",
  "ai_tts_language": "zh",
  "speed": 1.2,
  "text_source": "script.json",
  "output_audio": "tts/narration_full.wav",
  "word_boundary_source": "assemblyai_word_boundary",
  "unit_audio_glob_checked": ["tts/unit_*.mp3", "tts/unit_*.wav"],
  "concat_units_checked": "tts/concat_units.txt",
  "unit_audio_residue_count": 0,
  "single_generation": true
}
```

TTS boundary table:

```json
{
  "schema_version": "anime-noref-clip.tts_boundary_table.v1.4.9",
  "language": "zh-CN",
  "timing_source": "assemblyai_word_boundary",
  "unit_count": 12,
  "word_boundary_count": 180,
  "boundary_text_mismatch_units": 0,
  "units": [
    {
      "unit_id": 1,
      "source_text": "戒指做好后，皇太子却先说：你没必要戴上它",
      "boundary_count": 3,
      "boundaries": [
        {"bid": 0, "text": "戒指做好后", "start": 0.0, "end": 0.32},
        {"bid": 1, "text": "皇太子却先说", "start": 0.32, "end": 0.78},
        {"bid": 2, "text": "你没必要戴上它", "start": 0.78, "end": 1.48}
      ]
    }
  ],
  "passes": true
}
```

Subtitle timing report:

```json
{
  "language": "zh-CN",
  "timing_source": "assemblyai_word_boundary",
  "cue_strategy": "semantic display cues first, then real word-boundary timing",
  "cue_count": 42,
  "max_cue_duration_sec": 2.2,
  "min_cue_duration_sec": 0.42,
  "max_visual_line_chars": 16,
  "semantic_segmentation_done": true,
  "language_aware_segmentation": true,
  "semantic_segmentation_source": "subagent_boundary_group_plan",
  "subagent_semantic_segmentation_done": true,
  "subagent_boundary_group_plan_done": true,
  "subagent_plan_units_used": 12,
  "boundary_group_plan_units_used": 12,
  "local_rule_units_used": 0,
  "boundary_table_path": "subtitles/tts_boundary_table.json",
  "subtitle_plan_path": "subtitles/semantic_cue_plan.json",
  "subtitle_plan_mismatch_count": 0,
  "boundary_group_mismatch_count": 0,
  "boundary_group_gap_count": 0,
  "boundary_group_overlap_count": 0,
  "boundary_group_uncovered_count": 0,
  "boundary_group_duration_violation_count": 0,
  "cross_sentence_boundary_count": 0,
  "orphan_fragment_count": 0,
  "bad_line_break_count": 0,
  "plan_bad_line_break_count": 0,
  "computed_bad_line_break_count": 0,
  "bad_line_break_examples": [],
  "boundary_alignment_checked": true,
  "trailing_punctuation_removed": true,
  "uses_real_tts_boundaries": true
}
```

Vertical layout QA report:

```json
{
  "layout": "vertical_9_16_blur_bg_full_16_9_foreground",
  "canvas": [1080, 1920],
  "foreground_box": {"x": 0, "y": 656, "w": 1080, "h": 608},
  "top_blur_margin_px": 656,
  "bottom_blur_margin_px": 656,
  "foreground_vertical_center_error_px": 0,
  "source_aspect_preserved": true,
  "foreground_complete_frame": true,
  "foreground_centered": true,
  "foreground_vertically_centered": true,
  "filter_order": "split source first, then process bg and fg branches separately",
  "subtitle_position_basis": "foreground_box",
  "subtitle_box_inside_foreground": true,
  "subtitle_not_in_blurred_background": true,
  "qa_frames": [
    "qa_frames/layout_0002.jpg",
    "qa_frames/layout_mid.jpg",
    "qa_frames/layout_end.jpg"
  ],
  "passes": true
}
```
