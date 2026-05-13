---
name: anime-noref-clip
description: Create or continue a no-reference anime short-video editing pipeline from source footage only. Use for anime recap edits, YouTube cold-start retention hooks, AssemblyAI diarized transcript plus frame analysis, mandatory GPT subagent visual tags, source-supported story atoms, retention shot pools, contiguous source-block shot mapping, script-to-shot review, full-script TTS, post-TTS pacing repair, stable source sub-windows, internal jump scan, English word budget, TTS boundary-table subtitle planning with subagent boundary grouping, vertical blurred-background layout with centered full 16:9 foreground, foreground-box subtitle placement, workflow_state gates, BGM/watermark QA, and strict narration-to-visual synchronization.
---

# Anime No-Reference Clip

## Version

- Version: `v1.4.14`
- Base purpose: turn source anime footage into a no-reference short-video edit by using AssemblyAI transcription with speaker diarization plus mandatory GPT subagent visual tags, extracting source-supported story atoms, building a retention brief, generating supported hook candidates, scoring shots for retention value, writing a high-retention plot narration, selecting style-appropriate but auditable shots, generating full-script TTS, strictly aligning each narration line to shots, and producing QA-ready output.
- v1.1.0 update: replace local Whisper large-v3 as the default transcription step with AssemblyAI audio transcription plus speaker diarization.
- v1.2.0 update: use `gpt-5.5` subagents with `reasoning_effort: low` as the default visual tagging model; escalate selected difficult sheets to `medium`.
- v1.3.0 update: require cut granularity before shot selection, ask output aspect before composing, default to full-script TTS, strip trailing subtitle punctuation, filter black/fade frames, and standardize BGM, watermark, concat-path, and QA checks.
- v1.3.1 update: add activation protocol, `workflow_state.json` gate tracking, and deterministic validation.
- v1.3.2 update: make cut strategy a hard pause before any cut-dependent work.
- v1.3.3 update: make sequential cutting mandatory unless an approved nonlinear structure exists.
- v1.3.4 update: add fixed language-to-voice defaults and post-render timing validation.
- v1.3.5 update: harden the optional dynamic watermark path.
- v1.3.6 update: make GPT visual tagging a hard gate before story/script generation.
- v1.3.7 update: require a user-visible execution plan table and table-driven progress updates.
- v1.3.8 update: make subagent visual tagging mandatory and explicit; local inspection, subtitle fusion, transcript summaries, or manual notes can prepare prompts but cannot replace subagent JSONL tags or set `checks.gpt_visual_tagging_done=true`.
- v1.4.0 update: add YouTube cold-start retention mode. After dialogue/frame fusion, extract story atoms, build a retention brief, generate multiple supported hook candidates, create a retention shot pool, write script variants, allow limited documented cold-open teaser exceptions, and run creative retention QC before script-to-shot review.
- v1.4.1 update: harden compose and delivery. TTS must be one full-script generation with no unit audio remnants; subtitles must be timed from real TTS boundaries such as Edge TTS `WordBoundary`; vertical output must use blurred background plus intact centered 16:9 foreground, with split-before-scale filtering; subtitle placement must be inside the foreground picture; multilingual outputs must regenerate timing per language; watermark strategy and layout QA frames must be recorded before delivery.
- v1.4.2 update: stabilize post-hook pacing. Cold open may fast-cut for up to 5 seconds, but the main path must return within 6-8 seconds and use contiguous source blocks, not scattered single shots. A 60-second short should usually use 25-35 shots; post-hook shots must be longer and calmer, dialogue/emotion shots slower still. Alignment must solve shot count/source-window fit before speed, keep post-hook speed gentle, and avoid `tpad=clone` except a final 1-2 frame fallback.
- v1.4.3 update: make the step-0 execution table self-protecting. The visible todo table must include a required gate/rule note column, and every row must expose the key constraint that prevents common failures, such as no production before cut approval, mandatory subagent visual tags, contiguous source blocks, full-script TTS only, real TTS subtitle boundaries, vertical foreground layout, and delivery QA checks.
- v1.4.4 update: make vertical layout exact. Vertical output must use blurred background plus a complete 16:9 foreground frame that is horizontally and vertically centered in the canvas. Subtitle coordinates must be computed from the foreground video box and stay inside that box; subtitles must never sit in the blurred background or padding area.
- v1.4.5 update: add post-TTS stabilization. Estimated duration is never authoritative after real TTS exists; run a post-TTS pacing repair gate before compose, rebuild shot count/source windows/speeds from actual audio, require stable source sub-windows, forbid unsafe tail source buffers, scan rendered output for internal shot jumps, isolate each language in its own workflow state, enforce English word budget, and tighten subtitle cue timing.
- v1.4.6 update: make subtitle cue planning semantic-first. Build display cues from script punctuation and language-aware phrase boundaries before applying real TTS `WordBoundary` timing; forbid mechanical character-count splits, cross-sentence cue bleed, orphan fragments, and bad visual line breaks such as splitting Chinese particles away from their phrase.
- v1.4.7 update: remove render-level duration-based shot splitting. Long source shots must remain one real source shot for mapping and rendering; use multi-sample frame extraction for analysis instead of artificial cuts. Frame extraction must use OpenCV for fast batch reads with ffmpeg timestamp fallback for missing frames, and story/tagging gates require zero missing representative frames.
- v1.4.8 update: make subtitle cue planning a subagent step. A Codex subagent produces `subtitles/semantic_cue_plan.json` with language-aware display chunks; the alignment script attaches those chunks to real TTS boundaries. Local rule splitting is diagnostic fallback only for production v1.4.8 projects.
- v1.4.9 update: replace text-chunk subtitle matching with a three-stage boundary workflow. First build `subtitles/tts_boundary_table.json` from real TTS `WordBoundary`, then have a Codex subagent group contiguous `boundary_start/boundary_end` ranges in `subtitles/semantic_cue_plan.json`, then let the alignment script validate coverage and use exact boundary times.
- v1.4.10 update: remove drift between docs, validator, and template scripts. Hook candidate production and creative gates now require at least 8 hooks, cold-start `shot_energy` defaults are unified, `workflow_state` examples use the current version, template TTS writes `tts/narration_full.wav`, and `references/workflow.md` is the canonical source for detailed table rows, schemas, gate thresholds, and state fields.
- v1.4.11 update: introduce story-style presets. The current aggressive YouTube cold-start behavior became `style_01_aggressive_youtube_cold_start` in the initial Markdown-backed preset guide.
- v1.4.12 update: make story-style presets machine-loadable and scalable. `references/story_styles.json` is now canonical for preset definitions, `references/story_styles.md` is the human guide, `scripts/resolve_story_style.py` resolves aliases and records overrides, `scripts/validate_story_styles.py` validates preset coverage, and the workflow validator loads preset thresholds instead of hardcoding a single style.
- v1.4.13 update: converge current instructions around resolved story-style presets. Hook counts, script variants, creative QC thresholds, shot-count ranges, and speed ranges now come from the resolved preset unless a hard production gate overrides them; `references/workflow_defaults.json` stores non-style production defaults such as source buffer policy.
- v1.4.14 update: tighten story-style schema readability and preset shape validation. Story style config now uses schema version `anime-noref-clip.story_styles.v1.4.14`, script and shot-mapping subrules have required non-empty fields, the smoke test is versioned as v1.4.14, and GitHub Actions runs the smoke and preset resolver checks on push and pull request.
- Project tooling update: new projects must initialize local tools from this skill's `templates/project` framework via `scripts/init_project_scripts.py`. The template includes the generic post-TTS alignment builder. Do not copy `tools/` from older episode projects except as a deliberate, reviewed one-off migration.

## Source Of Truth

- `SKILL.md` is the activation and non-negotiable workflow summary: load it first, then load `references/workflow.md` for detailed rows, schemas, thresholds, and state fields.
- `references/workflow.md` is canonical for the 22-row execution table, artifact schemas, `workflow_state.json` shape, and gate thresholds. Do not maintain an independent detailed table or threshold list elsewhere.
- `references/story_styles.json` is canonical for story-style preset definitions; `references/story_styles.md` is the human-readable guide. Resolve a preset before retention brief, hook candidates, shot pool, script variants, or shot mapping.
- `references/workflow_defaults.json` is canonical for non-style production defaults that are still required by hard gates.
- `references/subtitle_semantic_cue_plan.md` is canonical for the subtitle boundary-group subagent output schema.
- `scripts/validate_workflow_state.py` is the machine-checkable gate implementation. When a rule changes, keep `references/workflow.md`, the validator, and template script outputs aligned in the same revision.

## Core Rule

Do not compose before the user has seen and accepted a script-to-shot review. The required order is:

```text
source analysis
-> cut strategy
-> shot detection/frame extraction
-> GPT visual tagging
-> dialogue/frame fusion
-> story atoms
-> story style preset
-> retention brief
-> hook candidates
-> retention shot pool
-> script variants
-> chosen script
-> style-aware shot mapping
-> creative retention QC
-> review artifacts
-> user approval
-> full-script TTS
-> post-TTS pacing repair
-> TTS boundary table plus subagent boundary-group subtitle planning
-> strict alignment
-> output aspect
-> compose
-> internal jump scan
-> layout/subtitle/watermark QA
-> QA
```

If a draft contains OP/ED/preview footage, bad subtitles, weak script, unsupported hooks, unsupported claims, generic exposition, overlong re-hook gaps, bad cold-open exceptions, or mismatched shots, fix the upstream stage before composition.

Visual tagging is mandatory before story generation. Contact sheets must be tagged by `gpt-5.5` Codex subagents that return JSONL for every visible `shot_id`, followed by merge, validation, and normalization. Source subtitles, transcript summaries, local image inspection, and manual notes may help prepare prompts or audit results, but they are not a substitute.

The script must be based only on visible action, dialogue, character emotion, object clues, and inferred plot relationships supported by the transcript plus frame tags. Do not invent plot, motives, lore, backstory, off-screen events, outcomes, or character psychology that the source does not support.

## Story Style Presets

Before retention artifacts or scripts, resolve the story style from `references/story_styles.json`. If the user names a style or alias, use that preset. If no style is specified, use `style_01_aggressive_youtube_cold_start`, which preserves the previous default behavior. Use `scripts/resolve_story_style.py` when a project state file should be patched.

Bundled presets:

- `style_01_aggressive_youtube_cold_start`: default aggressive cold-start Shorts structure.
- `style_02_natural_plot_explanation`: calmer chronological plot explanation.
- `style_03_emotional_reversal`: reaction/emotion-led relationship or reversal structure.
- `style_04_action_battle_escalation`: motion/impact-led battle escalation structure.
- `style_05_highlight_segment_selection`: continuity-first high-conflict highlight segment selection.

```json
{
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
  "cold_open_policy": "allowed_if_supported_and_reviewed"
}
```

For `style_01_aggressive_youtube_cold_start`, every hook must have source support and a payoff or clarification within 6-15 seconds. A hook is valid only if grounded in visible danger, contradiction, dialogue confession, emotional reversal, character choice, object clue, identity mismatch, consequence shown on screen, or a source-supported future outcome used as a reviewed teaser. Add future styles in `references/story_styles.json`, validate them with `scripts/validate_story_styles.py`, and keep `references/story_styles.md` as the human guide.

## Execution Plan Table

At the start of every run or resume, before any production work:

1. Read this file and `references/workflow.md` enough to identify the required flow.
2. Inspect only existing project state and user inputs needed to determine the current phase. Read-only commands are allowed; artifact creation, deletion, rendering, TTS, tagging, scripting, or composition is not allowed yet.
3. Publish a Markdown execution table to the user. Build it from this workflow, `workflow_state.json`, existing artifacts, and stated constraints. The table is step 0 and must expose the safety gates before production work begins.
4. Use the available todo/plan mechanism when present, and keep it synchronized with the visible table.
5. Follow the table in order. Do not start a later row until all required earlier rows are `Done`, explicitly `Blocked`, or already satisfied by verified artifacts.
6. After every major step or gate, send a short updated table or table delta.
7. If a required input, approval, artifact, or gate is missing, mark that row `Blocked`, state the exact missing item, and stop.
8. The visual-tagging row must explicitly say that `gpt-5.5` subagent JSONL tagging is required and that local inspection plus subtitle/transcript fusion is not an acceptable replacement.
9. Every row must include a short visible gate/rule note. Do not hide critical constraints only in prose below the table or in later workflow sections.

The table must include at least:

| # | Phase | Required gate / decision | Todo / artifact | Status | Visible gate / rule note | Evidence / next action |
|---|---|---|---|---|---|---|

Allowed statuses are `Pending`, `In progress`, `Done`, and `Blocked`.

Use the canonical 22-row table in `references/workflow.md` under `Table-Driven Execution`. Reproduce those rows verbatim when publishing a run table, including each row's visible gate/rule note; this file intentionally does not keep a second detailed row list.

## Activation Protocol

When this skill triggers:

1. Announce that `anime-noref-clip` is active and name the current project or episode.
2. Read this file and `references/workflow.md` enough to identify the current phase.
3. Inspect user inputs, existing artifacts, and `workflow_state.json` read-only to determine the current phase. If a state file is missing, create or update it before production work.
4. Publish the execution plan table.
5. Report current phase, completed gates, blocked gates, and next required user decision in or directly below the table.
6. Execute only the next eligible table row and update `workflow_state.json` after every major phase or user approval.
7. Before retention artifacts or story/script generation, confirm that visual tagging passed, resolve the story style, and run the `style` gate when a project state file exists.
8. Before script-to-shot review, produce `retention_qc.json` and pass the creative gate for the resolved style.
9. Before TTS, compose, or delivery, run `scripts/validate_workflow_state.py` for the relevant gate when a project state file exists.

If the validator fails, fix upstream state or ask for the missing decision before continuing.

## Required Decisions

- Before initial shot selection, ask whether the cut should be `rough` or `detailed` unless already specified. If missing, pause after source discovery, `ffprobe`, subtitle checks, and `workflow_state.json` setup.
- Resolve `decisions.story_style` from `references/story_styles.json` before retention artifacts. If unspecified, default to `style_01_aggressive_youtube_cold_start` and record `decisions.story_style`, `decisions.story_style_preset`, `decisions.story_style_label`, `decisions.story_style_config`, `artifacts.story_styles_config`, `checks.story_style_preset_resolved=true`, and scaled `checks.target_shot_count_min/max`.
- The resolved preset's `decision_overlay` controls retention mode, hook strategy, nonlinear teaser allowance, target duration, shot-count range, post-hook duration floor, speed ranges, clone-padding policy, and alignment solve order.
- If the resolved style uses nonlinear shots, document every exception in `nonlinear_exceptions.json`, include it in review, and keep exceptions within `decisions.max_nonlinear_exceptions`.
- For the default cold-start style, cold open may use 0.6-1.0s fast cuts for the first 3-5 seconds, but it must return to the main timeline within 6-8 seconds.
- After the hook, select contiguous source blocks instead of scattered high-energy shots unless the resolved preset explicitly changes that policy.
- For a 60-second short, use the preset's target shot-count range. Prefer fewer, longer, emotionally legible shots over many fast shots when the preset does not require action density.
- Post-hook and dialogue-scene duration floors come from the resolved preset.
- Before final composition, ask whether to output `vertical 9:16`, `horizontal 16:9`, or both unless already specified.
- Use fixed TTS voices by target language unless the user explicitly changes the defaults: `zh-CN -> zh-CN-YunxiNeural`, `th-TH -> th-TH-PremwadeeNeural`.
- TTS must be generated once as a single full-script file. Do not generate or retain `unit_*.mp3`, `unit_*.wav`, or `concat_units.txt` for the main render.
- Real TTS duration overrides all estimated duration. After TTS, run post-TTS pacing repair before subtitle alignment, segment render, or compose.
- For English 60-second shorts, use an independent word budget, usually `130-145` words. If the script is too long, revise before render instead of slowing footage excessively.
- Subtitles must use the three-stage boundary workflow. Build `subtitles/tts_boundary_table.json` from real TTS boundaries, then have a Codex subagent write `subtitles/semantic_cue_plan.json` by grouping contiguous `boundary_start/boundary_end` ranges into readable cues, then let the alignment builder validate coverage and use exact boundary times. For Edge TTS, use `WordBoundary`; do not hard-split subtitles only by script lines, raw character count, raw provider token groups, or proportional text.
- When watermarking is requested and no new text is specified, use `@AlsinCro` with slow dynamic motion and opacity cycling around `5%` to `15%`.
- Default to mandatory subagent GPT visual tagging. If the user opts out, pause before story/script generation and ask for a replacement review method.
- Default to modest speed matching. Use the resolved preset's `hook_speed_range`, `post_hook_speed_range`, and `absolute_non_hook_speed_range`; if a preset omits those fields, fall back to the conservative cold-start ranges in `references/workflow.md`.
- Do not use `tpad=clone` to stretch a short shot. First reduce shot count, extend the source window, or rebalance narration-to-shot ownership; only use clone padding as a final 1-2 frame fallback.
- Do not split long source shots into renderable artificial shots. A `shot` is a real continuous source window between ffmpeg scene cuts. If a real shot is long, extract more representative frames inside it for analysis/contact sheets, but final shot mapping and segment rendering must still reference the original real shot plus a stable `source_window`.

## Workflow

1. **Preprocess and index source**
   - Validate source media with `ffprobe`.
   - For a new project, initialize project-local scripts from this skill template before creating cut-dependent artifacts:
     `python3 ~/.codex/skills/anime-noref-clip/scripts/init_project_scripts.py --project-root <project>`.
     Do not seed new project tools by copying another episode's `tools/` directory.
   - Confirm `rough` versus `detailed` before scene detection, shot preview generation, frame extraction, contact sheets, visual tagging, story scripting, or shot mapping.
   - Detect real shots from ffmpeg scene cuts. Do not add duration-based artificial cuts or use artificial long-shot split points as render boundaries.
   - Extract representative frames from each real shot. Shots up to about 8 seconds use `first/mid/last`; longer shots add evenly spaced sample frames for analysis only, usually every 3-4 seconds with a practical cap around 9-12 total frames per shot.
   - Use OpenCV for fast batch frame extraction, then verify the expected frame manifest. If any frame is missing, automatically backfill the missing paths with ffmpeg timestamp extraction and verify again. Any remaining missing frame blocks contact sheets, subagent visual tagging, story generation, and shot mapping.
   - Scan real shot windows for black/fade/too-dark metadata. Keep shot metadata with `shot_id`, `src_index`, `start`, `end`, `duration`, representative frame paths, and any extra long-shot sample frame paths.

2. **Understand story from dialogue plus frames**
   - Extract audio and transcribe with AssemblyAI by default, enabling speaker diarization.
   - Normalize transcript to `{speaker, start, end, text}` while keeping `Speaker A/B/...` labels stable.
   - Generate contact sheets and tag them with `gpt-5.5` Codex subagents at `reasoning_effort: low`; rerun only difficult batches at `medium`.
   - Merge subagent JSONL, validate missing/duplicate IDs, normalize role/object/story-function terms, align transcript segments to shots, and fuse into story tags.
   - Run `scripts/validate_workflow_state.py <project>/workflow_state.json --gate story` before generating story atoms, scripts, shot maps, or review artifacts.

3. **Exclude non-story ranges**
   - Detect OP, ED, recap, credits, and next-episode preview ranges.
   - Treat exclusions as hard constraints. Cold-open teasers cannot use OP/ED/preview shots unless the user explicitly approves that exact use.

4. **Build retention artifacts**
   - Extract compact `story_atoms.json` from fused dialogue and visual tags before writing narration.
   - Resolve the story style preset from `references/story_styles.json` and record it in `workflow_state.json` before retention brief, hook candidates, shot pool, script variants, or shot mapping.
   - Build `retention_brief.json` with the resolved preset, main viewer question, first 2-second hook or opening situation, first 10-second question/plot promise, midpoint payoff, strongest ending point, skipped source material, allowed operations, and forbidden operations.
   - Generate supported `hook_candidates.json` entries according to the resolved preset's `creative_qc_profile.min_hook_candidates`, then choose one based on source support, visual salience, style fit, and payoff availability.
   - Score `retention_shot_pool.json` for visual salience, emotion, motion, mystery, conflict, reaction, object clues, continuity cost, repetition risk, block membership, spoiler level, and risk flags.
   - Generate `script_variants.json` variants appropriate to the resolved story style. For `style_01_aggressive_youtube_cold_start`, default variants may include `A_clear_plot`, `B_aggressive_retention`, and `C_high_density_reversal`.

5. **Write script from existing content only**
   - Do not add plot, motives, facts, lore, or outcomes that selected shots/dialogue do not support.
   - Rewrite names into relationship or role terms when possible: `少年`, `女孩`, `同伴`, `玩偶男人`, `父亲`, `哥哥`, `家人`.
   - Shape the opening according to the resolved preset's `script_rules.opening`; for `style_01`, lead with conflict, contradiction, danger, confession, or a clear question.
   - Use re-hooks, emotional turns, plot clarifications, action escalation, or other middle beats according to the resolved preset's `script_rules.middle`; for `style_01`, supported micro-hooks should pay off or clarify within 6-15 seconds.
   - Avoid dense punctuation, generic exposition, and unsupported hype. Keep subtitle readability in mind.
   - End wherever retention is strongest; the script does not need to summarize the whole episode.

6. **Map every script line to shots**
   - Each line must own a specific ordered group of shots or a small contiguous source block.
   - Keep the main path chronological, sequential, and contiguous by source block after the hook.
   - Do not use random sampling, shuffled candidates, unrelated filler, or hidden shot reuse.
   - Apply the resolved preset's `shot_mapping_rules`. If nonlinear exceptions are allowed, record and review every exception and keep it within `decisions.max_nonlinear_exceptions`; if the preset forbids nonlinear teasers, keep `checks.nonlinear_exceptions_count=0`.
   - Replace unusable shots with the nearest later suitable shot in the same story beat. Use earlier replacements only when no later option exists and record the reason.
   - Large source jumps after the hook are allowed only at beat/paragraph transitions and must have recorded reasons.
   - Apply a repetition penalty for consecutive same-character/same-framing close-ups unless the hold is an intentional emotional beat.

7. **Run creative retention QC**
   - Create `retention_qc.json` before review.
   - Creative QC thresholds come from the resolved preset's `creative_qc_profile` unless a hard production gate overrides them. Hard gates still include source support, OP/ED exclusion, reviewed nonlinear exceptions, target shot-count bounds, source-block continuity when required, and unique shots when required by the preset.
   - If creative QC fails, revise the script, shot pool, hook choice, or shot mapping before review. Do not proceed to TTS.

8. **Produce review artifacts before TTS or compose**
   - Create a markdown review with unit id, beat role, narration, target duration, hook/payoff function, shot IDs, source timecodes, frame path, visual summary, dialogue summary, scene/action, retention reason, source support, risk flags, and nonlinear exception flags.
   - Create a selected-shots contact sheet.
   - Report resolved story style, chosen variant, chosen hook/opening, hook count, style-specific middle beats/payoffs, max re-hook gap when applicable, first-3-second salience when required, unsupported claims, OP/ED overlap, contiguous source-block count, large jumps and reasons, nonlinear exceptions, unique shots, total shot count, target shot-count range, post-hook minimum shot duration, dialogue/emotion minimum duration, average shot duration, first-10-second shot count when useful, and creative QC result.
   - Mark `approvals.script_to_shot_review=true` only after the user accepts this review.

9. **Generate full-script TTS and rebuild timing from real audio**
   - Run the TTS gate before production TTS. For v1.4.11+ story-style states, TTS requires the creative gate.
   - Generate the approved narration once as one continuous audio file. Do not use per-unit audio or concat manifests for the main render.
   - Write a TTS generation manifest and check that no `unit_*.mp3`, `unit_*.wav`, or `concat_units.txt` remains in the active project output path.
   - Keep real boundary metadata when available. For Edge TTS, use `WordBoundary` as the subtitle timing source.
   - If provider word boundaries are unavailable, derive cue timing from the continuous waveform with forced alignment or ASR timestamps; use proportional text weights only as a documented fallback.
   - Never rely on estimated script duration after TTS exists.

10. **Post-TTS pacing repair**
    - Compare estimated script duration to real TTS duration, but treat the real TTS duration as authoritative.
    - After full-script TTS, build the TTS boundary table:
      `python3 tools/build_tts_boundary_table.py --project-root <project> --language <lang>`.
    - Then run a Codex subagent to create `subtitles/semantic_cue_plan.json` from `subtitles/tts_boundary_table.json`. Use `references/subtitle_semantic_cue_plan.md` as the schema/prompt reference. The subagent must group boundary ids only; it must not invent timestamps.
    - Before pacing validation, frame-quantized segment render, or compose, run the project-local template alignment builder:
      `python3 tools/build_post_tts_alignment_v145.py --project-root <project> --source-media <source-mkv> --language <lang> --require-subtitle-plan`.
      Use the localized project's own TTS directory/workflow state for each language.
    - Recheck shot count, line durations, source-window fit, speed range, subtitle cue range, and language budget before rendering.
    - If speed would exceed limits, repair upstream: shorten or rewrite script, delete duplicate shots, add nearby sequential shots, extend stable source windows, or rebalance narration line ownership.
    - Do not render while any post-TTS speed, shot-count, subtitle, or language-budget check is failing.
    - For each used shot, store `stable_src_start` and `stable_src_end`. If a detected shot contains hidden internal cuts, crop to a stable sub-window or replace it.
    - Do not use global tail source buffers. Only allow a whitelisted `safe_render_tail_buffer` when it stays inside the same stable source shot and does not cross a detected or scanned cut.

11. **Strict line-to-shot alignment**
    - Each narration line starts and ends exactly with its owned shot group.
    - Solve alignment by choosing a suitable number of source shots/windows first, then apply speed. For each narration line, choose 1-3 source shots or a short block whose source duration is already close to the real TTS duration.
    - If speed would leave the allowed range, reduce or replace shots, extend the source window, or rebalance line ownership before using aggressive speed changes.
    - Quantize line and shot durations to the final output frame rate, preferably `24000/1001` for anime BDRip workflows unless the project requires otherwise.
    - Store frame starts/ends, target frames, and frame-quantized durations.
    - Do not use `tpad=clone` to pad visible duration except a final 1-2 frame fallback after all better options fail.
   - Subtitle timing must be derived from real TTS timing.
   - Build `subtitles/tts_boundary_table.json` first. Then have a Codex subagent group contiguous boundary ids into cue text; use those exact boundary ids to attach timing. Do not let provider `WordBoundary` grouping alone decide final cue text when it drifts across narration-line or sentence boundaries.
   - Never create a cue that crosses an original sentence boundary unless a deliberate continuation is recorded. If boundary metadata spills words into the next script sentence, repair the cue plan by cumulative text alignment before rendering.
   - For Chinese, prefer complete semantic chunks of roughly `6-14` characters, with `4-16` allowed when timing requires it. Do not split particles, complements, or fixed phrases away from their head, for example `作为他的妻子`, `皇太子妃`, `杀人不眨眼`, `亲眼见过的温柔`, `低成本商品`, or `治疗他妹妹的药`.
   - Avoid orphan fragments such as `被掳`, `却仍`, `她反问`, `作为他`, or `的妻子活下去`. Merge them with the neighboring phrase even if the cue becomes slightly longer.
   - Build subtitle cues from semantic units plus real word boundaries plus readable length limits; avoid both multi-second hanging lines and unnaturally tiny flashes. Cue duration must be `0.3s` to `2.2s` unless a documented exception is approved.
   - Regenerate subtitle timing separately for every language from that language's own TTS. Do not reuse Chinese timing for English or any other localized output.
   - Strip trailing punctuation from displayed subtitle cues while leaving narration/TTS text unchanged.

12. **Compose and QA**
    - Run compose gate before rendering.
    - For vertical `9:16`, use blurred background plus a complete 16:9 foreground picture centered both horizontally and vertically. Do not fill the vertical canvas by cropping or over-zooming the main anime frame.
    - In ffmpeg filter graphs, split the source before scaling: process the background crop/blur branch and foreground full-frame branch independently so the foreground never inherits background over-scaling.
    - Place subtitles using coordinates derived from the foreground video box, near the bottom inside the actual anime frame, never in the lower blurred background or padding area.
    - Render segments from frame-quantized alignment and probe every segment before final mux.
    - After render, run internal jump scan by frame-difference analysis. Exclude planned edit boundaries; any intra-shot jump above threshold must be reviewed and fixed before delivery.
    - Required timing thresholds: every segment hits its target frame count, max line-boundary drift <= `80ms`, total timeline drift <= `120ms`.
    - Mute source audio unless requested otherwise.
    - Burn readable subtitles with a Chinese-capable font; on macOS, `Arial Unicode MS` with `fontsdir=/System/Library/Fonts/Supplemental` is a reliable fallback.
    - For BGM, trim or loop to final duration, keep it low under narration, fade out, and normalize/limit.
    - For watermarked renders, apply the accepted dynamic default, avoid permanent subtitle overlap, record strategy checks, and verify visibility on multiple QA frames.
    - Verify final video with `ffprobe`, extract QA frames, run black/fade detection, run internal jump scan, check full foreground visibility, horizontal/vertical centering, subtitle placement inside the foreground box, watermark strategy/visibility when applicable, and run delivery gate before final handoff.

## Required Outputs

For a current v1.4.14+ handoff, produce or update:

- `workflow_state.json`
- project-local tools and reference configs initialized from the skill template, not copied from an older episode project
- `references/workflow_defaults.json` copied into the project when project-local tools are initialized
- frame extraction manifest/report with expected frame count, OpenCV saved count, ffmpeg fallback count, and zero missing frames
- `transcript_assemblyai.json` or equivalent structured transcript with speaker labels
- `shot_story_tags.json`
- `story_beats.json`
- `episode_summary.json`
- `story_atoms.json`
- resolved `decisions.story_style`, `decisions.story_style_preset`, `decisions.story_style_label`, `decisions.story_style_config`, `artifacts.story_styles_config`, `checks.story_style_preset_resolved=true`, `checks.target_shot_count_min`, and `checks.target_shot_count_max` in `workflow_state.json`
- `decisions.story_style_overrides` if any preset defaults are intentionally preserved or overridden
- `retention_brief.json`
- `hook_candidates.json`
- `retention_shot_pool.json`
- `source_blocks.json`
- shot-block report / block continuity report
- `script_variants.json`
- `script.json`
- `final_shots.json`
- `nonlinear_exceptions.json` if any nonlinear exception is used
- `retention_qc.json`
- script-to-shot review markdown
- selected-shots contact sheet
- continuous TTS audio plus boundary/timing metadata if TTS was run
- TTS generation manifest and no-unit-audio cleanup check
- TTS boundary table for subtitle planning
- post-TTS pacing repair report
- subagent boundary-group subtitle cue plan
- stable sub-window map
- safe source buffer report if any tail buffer is used
- strict alignment JSON if composing
- alignment QC report with speed ranges and clone-padding frames
- subtitle timing report based on subagent boundary groups plus real TTS boundaries
- internal jump scan report
- frame-quantized alignment JSON and rendered timing drift report if composing
- vertical layout QA frames and layout report if composing vertical output
- pre-compose/pre-delivery validation output when composing
- final video path and QA summary if composing

## References

For detailed artifact schemas, prompt essentials, workflow state fields, and gate rules, read `references/workflow.md`. For machine-loadable story-style presets, read `references/story_styles.json`; for the human guide, read `references/story_styles.md`. For the subtitle subagent JSON schema and prompt constraints, read `references/subtitle_semantic_cue_plan.md`.

## Project Script Framework

The skill-owned script framework lives in `templates/project`. Use it as the clean baseline for new projects:

```bash
python3 ~/.codex/skills/anime-noref-clip/scripts/init_project_scripts.py --project-root <project>
```

This copies baseline tools into `<project>/tools/` and copies the current workflow validator. The copied files may then be adjusted for the specific project, but the starting point must be the skill template. Do not copy tools from a prior episode project as the default path; that preserves stale source paths, old shot rules, and episode-specific patches.

The baseline includes `tools/build_tts_boundary_table.py` and `tools/build_post_tts_alignment_v145.py`. Before calling the alignment builder in production, run the boundary-table builder and then a Codex subagent with `references/subtitle_semantic_cue_plan.md` to write `subtitles/semantic_cue_plan.json` with `boundary_start/boundary_end` cue groups. Then call the alignment builder immediately after single full-script TTS generation and before `validate_workflow_state.py --gate pacing`, frame-quantized segment rendering, or final compose. It reads `script/script.json`, `script/final_shots.json`, `tts/tts_durations.json`, `tts/narration_boundaries.json`, `subtitles/tts_boundary_table.json`, and `subtitles/semantic_cue_plan.json`, then writes:

- `alignment/post_tts_pacing_report.json`
- `alignment/stable_subwindows.json`
- `alignment/source_buffer_report.json`
- `alignment/strict_alignment.json`
- `alignment/strict_alignment_frameq.json`
- `alignment/alignment_qc_report.json`
- `subtitles/tts_boundary_table.json`
- `subtitles/final.ass`
- `subtitles/subtitle_timing_report.json`
- `compose/final_subtitles_frameq.ass`
