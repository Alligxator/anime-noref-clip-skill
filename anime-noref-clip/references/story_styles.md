# Story Style Presets

This file is canonical for story-style preset definitions. A story style controls
script shape, hook strategy, shot-selection bias, source-block mapping, pacing
defaults, and creative QC profile. It does not override hard production gates:
source support, GPT visual tagging, no invented plot, full-script TTS, real TTS
subtitle timing, frame-quantized alignment, layout QA, and delivery QA still apply.

## How To Use

Resolve `decisions.story_style` before building `retention_brief.json`,
`hook_candidates.json`, `retention_shot_pool.json`, `script_variants.json`, or
`final_shots.json`.

If the user names a style, map the name or alias to a `preset_id`. If the user
does not specify a style, use `style_01_aggressive_youtube_cold_start`.

Record the resolved preset in `workflow_state.json`:

```json
{
  "decisions": {
    "story_style": "style_01_aggressive_youtube_cold_start",
    "story_style_preset": "references/story_styles.md#style_01_aggressive_youtube_cold_start",
    "story_style_label": "Aggressive YouTube Cold Start"
  },
  "checks": {
    "story_style_preset_resolved": true
  }
}
```

Project-specific duration, output aspect, language, TTS speed, BGM, and
watermark settings may override a preset. If a creative default is changed, such
as nonlinear teaser allowance, hook strategy, shot-count range, or post-hook
pacing, record the reason in the review and QC artifacts.

## Preset Schema

Each preset should define:

- `preset_id`: stable id used in `workflow_state.json`
- `label`: user-facing name
- `aliases`: short names the user may type
- `use_when`: source or platform situations where the style fits
- `decision_overlay`: workflow decision defaults
- `selection_bias`: shot/story signals to prefer
- `avoid`: signals or tactics to penalize
- `script_rules`: narration rules
- `shot_mapping_rules`: shot/block mapping rules
- `creative_qc_profile`: style-specific QC thresholds and checks

## style_01_aggressive_youtube_cold_start

```json
{
  "preset_id": "style_01_aggressive_youtube_cold_start",
  "label": "Aggressive YouTube Cold Start",
  "aliases": [
    "preset1",
    "style1",
    "cold_start",
    "aggressive",
    "youtube_retention",
    "current_default"
  ],
  "use_when": [
    "YouTube Shorts or similar cold traffic",
    "the first seconds must create a strong reason to keep watching",
    "the source has visible conflict, danger, confession, reversal, choice, consequence, or object clues"
  ],
  "decision_overlay": {
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
    "cold_open_policy": "allowed_if_supported_and_reviewed"
  },
  "selection_bias": [
    "conflict",
    "danger",
    "confession",
    "emotional reversal",
    "character choice",
    "visible consequence",
    "object clue",
    "strong reaction",
    "visual salience",
    "payoff availability"
  ],
  "avoid": [
    "unsupported hype",
    "invented motive",
    "generic exposition",
    "unrelated filler shots",
    "scattered post-hook single-shot sampling",
    "OP/ED/preview overlap",
    "repeated same-framing close-ups without emotional purpose",
    "post-hook overcutting"
  ],
  "script_rules": {
    "opening": "start with a source-supported conflict, danger, contradiction, confession, or clear question in the first 1-2 seconds",
    "middle": "add supported micro-hooks every 6-10 seconds and pay off or escalate each within 6-15 seconds",
    "ending": "end at the strongest retention point; do not require full episode closure",
    "support": "use only visible action, dialogue, emotion, objects, and transcript/frame-supported relationships"
  },
  "shot_mapping_rules": {
    "cold_open": "may use up to 5 seconds of fast cuts and at most 2 documented nonlinear exceptions",
    "return_to_main_path": "return to the main source timeline within 6-8 seconds",
    "body": "use 3-6 contiguous source blocks for a 60-second short",
    "unit_binding": "bind each script unit to one small source block or adjacent block pair",
    "replacement": "prefer the nearest later suitable shot in the same story beat",
    "large_jumps": "allow only at beat or paragraph transitions with recorded reasons"
  },
  "creative_qc_profile": {
    "min_hook_candidates": 8,
    "unsupported_claims_count": 0,
    "generic_exposition_lines_max": 1,
    "first_3s_requires_subject_and_conflict": true,
    "rehook_interval_max_sec": 10,
    "cold_open_max_sec": 5,
    "return_to_main_timeline_max_sec": 8,
    "selected_shot_count_60s": [25, 35],
    "post_hook_min_shot_duration_sec": 1.3,
    "dialogue_scene_min_shot_duration_sec": 1.6,
    "post_hook_contiguous_source_blocks": true,
    "unique_shots": true,
    "op_ed_overlap_count": 0
  }
}
```
