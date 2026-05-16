# Story Style Presets

This file is the human-readable guide for story-style presets. The machine-readable canonical source is `story_styles.json`. A story style controls
script shape, hook strategy, shot-selection bias, source-block mapping, pacing
defaults, and creative QC profile. It does not override hard production gates:
source support, GPT visual tagging, no invented plot, full-script TTS, real TTS
subtitle timing, frame-quantized alignment, layout QA, and delivery QA still apply.

## v1.4.14 Machine-Readable Config

`story_styles.json` is the canonical preset source. Keep this Markdown file aligned with that JSON, or regenerate it from the JSON when adding styles. Validate changes with:

The current schema version is `anime-noref-clip.story_styles.v1.4.14`. v1.4.14 keeps the four existing preset intents unchanged, but upgrades schema readability and requires each preset to provide non-empty `script_rules` and `shot_mapping_rules` subfields.

```bash
python3 scripts/validate_story_styles.py
```

Resolve a style alias and optionally patch workflow state with:

```bash
python3 scripts/resolve_story_style.py --style aggressive --project-root <project> --write
```

## How To Use

Resolve `decisions.story_style` before building `retention_brief.json`,
`hook_candidates.json`, `retention_shot_pool.json`, `script_variants.json`, or
`final_shots.json`.

Resolve style ids and aliases from `story_styles.json`; `scripts/resolve_story_style.py` can write the resolved overlay into `workflow_state.json`. If the user
does not specify a style, use `style_01_aggressive_youtube_cold_start`.

Record the resolved preset in `workflow_state.json`:

```json
{
  "decisions": {
    "story_style": "style_01_aggressive_youtube_cold_start",
    "story_style_preset": "references/story_styles.json#styles/style_01_aggressive_youtube_cold_start",
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

## Preset Index

Full machine-readable definitions live in `story_styles.json`.

- `style_01_aggressive_youtube_cold_start` / Aggressive YouTube Cold Start: default v1.4.11 behavior for cold-traffic Shorts, multi-hook retention, limited reviewed nonlinear teaser use, and 25-35 shots per 60 seconds.
- `style_02_natural_plot_explanation` / Natural Plot Explanation: calmer chronological recap, continuity-first shot selection, no nonlinear teaser by default, and 18-28 shots per 60 seconds.
- `style_03_emotional_reversal` / Emotional Reversal: relationship or emotion-led edit, preserves reaction pauses, allows one reviewed emotional teaser, and targets 20-30 shots per 60 seconds.
- `style_04_action_battle_escalation` / Action Battle Escalation: motion/impact-led battle or danger edit, allows reviewed impact teasers, and targets 28-42 shots per 60 seconds.
- `style_05_highlight_segment_selection` / Highlight Segment Selection: continuity-first high-conflict highlight segment edit, forbids nonlinear teasers, uses medium-low narration density, and targets 18-26 shots per 60 seconds.
- `style_06_spectacle_escalation_commentary` / Spectacle Escalation Commentary: rotating-hook spectacle, world-rule, and task-escalation commentary; allows at most one reviewed opening teaser and keeps the body chronological, targeting 22-34 shots per 60 seconds.

## Script Style Guide Reference

Every preset has a machine-readable `script_style_guide` in `story_styles.json`. Use it when generating `script_variants.json` and final narration. These guides affect wording only; shot selection, pacing ranges, nonlinear policy, and creative QC still come from each preset's existing decision and mapping fields.

- `style_01`: high-conflict cold start. Example: "少年刚以为自己逃过一劫，门外的人已经举起了刀。"
- `style_02`: calm causal explanation. Example: "事情要从这场误会开始说起。"
- `style_03`: visible emotion and relationship reversal. Example: "她没有立刻回答，只是低头攥紧了手里的信。"
- `style_04`: action threat, impact, and consequence. Example: "黑衣敌人刚冲上来，地面就被这一击砸出裂痕。"
- `style_05`: single highlight segment tension. Example: "这段最精彩的地方，不是他冲了上去，而是对方站在原地一动不动。"
- `style_06`: spectacle, world-rule, and task escalation. Example: "这把还没开刃的菜刀，落地的一瞬间竟然把水泥地切出一道缝。"

## style_06_spectacle_escalation_commentary Reference

Use this style for fantasy, food, monster, weapon, ability, secret-place, legendary-expert, or adventure-challenge footage where the visible material can support escalating wonder. It should feel excited, vivid, and surprising, but it must not become unsupported hype.

Default public-facing IP policy:

- Hide anime title, series, official character names, and strongly identifying proper names unless the user explicitly asks to keep them.
- Use role, relationship, appearance, profession, or story-function labels: `蓝发男人`, `小厨师`, `传说中的铸刀师`, `山顶屋主`, `那名少年`, `他的伙伴`.
- Internal audit files and visual metadata may retain source-identifying details for verification.

Opening rotation examples:

- 奇观物件："这把还没开刃的菜刀，落地的一瞬间竟然把水泥地切出一道缝。"
- 秘境地形："眼前这座两万级台阶，不是修出来的，而是被人用刀一阶一阶刻出来的。"
- 危机场面："小厨师刚靠近木屋，一道刀气就贴着他的身体飞了过去。"
- 身份反差："传说中的铁血大师，竟然不是满身伤疤的壮汉，而是眼前这个清秀男人。"
- 世界规则："在这个世界，厨师的菜刀不是普通工具，而是几乎等同于第二条生命。"
- 任务启动："为了修好断掉的爱刀，蓝发男人必须进入人间界最深处的洞穴。"
- 能力展示："这只妖兽不是被打飞的，而是被一道看不见的刀气直接逼退。"

Middle progression examples:

- "更夸张的是，这还不是成品，只是一把还没真正开刃的半成品。"
- "小厨师这才意识到，自己刚才只要慢半秒，就已经被切成两半。"
- "可蓝发男人很快发现不对劲，因为眼前这个人，和传闻中的怪物级大师完全不一样。"
- "误会解开后，真正的问题才出现：想要重新打造菜刀，必须找到传说中的梦幻磨刀石。"

Bad -> Good references:

- Bad: "你敢信吗，这个东西太离谱了，简直无敌。"
- Good: "这把刀甚至还没开刃，落到地上却直接切开了水泥。"
- Bad: "阿鲁心里非常愤怒，决定教训梅尔克。"
- Good: "蓝发男人没有继续追问，而是直接挥出手刀，要求和对方切磋。"
- Bad: "这个大师强到无法想象。"
- Good: "山下的妖兽追到屋前就停了下来，显然连它们都害怕这里的主人。"

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
