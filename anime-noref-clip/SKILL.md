---
name: anime-noref-clip
description: Use when creating or continuing no-reference anime recap clips from source footage, especially workflows needing shot-level visual tags, source-supported story scripts, style presets, AI-tts timing, vertical QA, workflow_state gates, or bilingual anime short-video delivery.
---

# Anime No-Reference Clip

## Version

- Version: `v1.4.18`
- Purpose: convert source anime footage into a source-supported short-video edit with auditable shot selection, script review, AI-tts timing, alignment, layout, and QA gates.

## Source Of Truth

- `references/workflow.md`: detailed workflow rows, artifact contracts, state fields, and gate rules.
- `references/artifact_contracts.md`: artifact JSON examples and schema-shape targets referenced by the workflow.
- `references/story_styles.json`: machine-readable story-style presets.
- `references/story_styles.md`: human guide for preset intent and usage.
- `references/workflow_defaults.json`: non-style hard defaults, including `tts_speed=1.2`.
- `references/tts_duration_calibration.json`: optional local calibration for pre-TTS duration estimates.
- `references/subtitle_semantic_cue_plan.md`: subtitle boundary-group subagent contract.
- `references/initial_story_write.md`: story evidence pack subagent and content-style initial story writing contract.
- `references/script_reference_optimization.md`: handoff to `content-style-system`.
- `scripts/validate_workflow_state.py`: strict current validator for active production projects.
- `scripts/validate_workflow_state_legacy.py`: separated legacy validator entry for old archived states.

Do not duplicate detailed gate rows, thresholds, preset JSON, or historical migration notes in this file. When a rule changes, update the workflow reference, strict validator, template tools, and smoke tests together.

## Non-Negotiable Gates

- Publish the 22-row execution dashboard before production work.
- Use one Codex goal per dashboard row. The active goal is the execution lock.
- Do not create or update workflow_state.json before the dashboard exists and the row 01 goal is active.
- Do not compose before the user accepts a script-to-shot review.
- Do not generate story or script from transcript alone. Shot-level visual tagging must cover every visible `shot_id`.
- Do not locally write initial story atoms. Build a story evidence pack with a closed subagent, then call the content-style-system writing skill to write `initial_story_seed.json` and canonical `story_atoms.json`.
- Resolve a story style before retention artifacts, scripts, or shot mapping.
- For style 5, build a multi-beat highlight edit plan; a highlight window is not automatically one shot.
- The row 11 copywriting gate must use the content-style-system writing skill to write or rewrite the final script copy. A locally written `script_reference_review.json` with stamped fields is not enough.
- Final `script.json` must carry sentence-level source mapping. Every narration sentence needs `sentence_source_map` with source time, source shots, plot function, and TTS budget; row 11 rewrites must regenerate the map instead of leaving stale timing from the old copy.
- Final script copy must explain plot causality, danger, choices, consequences, relationship shifts, questions, or payoffs. Pure frame-caption lines that only describe what is on screen must be rewritten; `visual_caption_line_count` must be zero before TTS.
- Run pre-TTS duration estimation at `speed=1.2`; if the estimate is below 90% of target, rewrite or reselect before synthesis.
- Use local `AI-tts` as the production TTS path. Set `decisions.tts_provider=ai_tts` and `decisions.tts_speed=1.2`.
- A non-1.2 TTS speed is valid only with `approvals.tts_speed_override=true` and a non-empty `decisions.tts_speed_override_reason`.
- If source windows are expanded or replaced after a script is written, refresh the script reference review and rewrite the script against the new visual evidence.
- Build subtitles from real TTS boundary metadata plus a subagent boundary-group cue plan. Production alignment must fail when boundary groups are missing.
- Every subagent task must be closed after its result is collected, merged, or rejected. Call `close_agent` for finished visual-tagging, subtitle-planning, and any other subagent workers before marking the row done.
- Solve shot count and source-window fit before speed changes. `tpad=clone` is limited to a final 1-2 frame recorded fallback.
- For vertical output, keep the full 16:9 foreground visible and centered over a blurred background; subtitles stay inside the foreground box.

## Activation Protocol

When this skill triggers:

1. Announce that `anime-noref-clip` is active and name the project or episode.
2. Read this file plus enough of `references/workflow.md` to identify the current row.
3. Inspect user inputs, existing artifacts, and `workflow_state.json` read-only.
4. Publish the execution dashboard from the canonical rows in `references/workflow.md`.
5. Call `get_goal`, report any active goal, and identify the earliest eligible row.
6. If no goal exists, call `create_goal` using:

```text
anime-noref-clip | <project> | row NN/22 | <phase> | <required gate or decision>
```

7. Execute only the row represented by the active goal.
8. After a row passes, update `workflow_state.json`, send a dashboard delta, then call `update_goal(status=complete)`.
9. If a gate, artifact, approval, or input is missing, mark that row `Blocked`, keep the active goal open, state the missing item, and stop.

## Startup Decisions

- Ask for `rough` or `detailed` cut mode unless already specified.
- Resolve `decisions.story_style`; default to `style_01_aggressive_youtube_cold_start` only when the user does not specify a style.
- Ask for output aspect before compose unless already specified.
- Keep each localized output isolated: separate TTS, subtitle, alignment, compose, and workflow state artifacts per language.
- If watermarking is requested and no new text is specified, use `@AlsinCro` with subtle dynamic visibility.

## Project Script Framework

Initialize new projects from the skill-owned template:

```bash
python3 ~/.codex/skills/anime-noref-clip/scripts/init_project_scripts.py --project-root <project>
```

This copies baseline tools into `<project>/tools/`, copies the strict workflow validator plus the separated legacy entry, and copies project-local runtime references into `<project>/references/`. Do not seed new projects by copying another episode's `tools/` directory.

Required project-local runtime references:

- `references/workflow.md`
- `references/artifact_contracts.md`
- `references/story_styles.json`
- `references/story_styles.md`
- `references/story_styles.schema.json`
- `references/subtitle_semantic_cue_plan.md`
- `references/workflow_defaults.json`
- `references/tts_duration_calibration.json`
- `references/initial_story_write.md`
- `references/script_reference_optimization.md`

## Standard TTS Handoff

Production TTS and alignment use this shape:

```bash
python3 tools/estimate_tts_duration.py --project-root <project> --speed 1.2
python3 tools/generate_tts_ai_tts_v145.py --project-root <project> --language <zh|en|th> --speed 1.2
python3 tools/build_tts_boundary_table.py --project-root <project> --language <lang>
python3 tools/build_post_tts_alignment_v145.py --project-root <project> --source-media <source-mkv> --language <lang> --require-subtitle-plan
```

Before the alignment builder, a Codex subagent must create `subtitles/semantic_cue_plan.json` from `subtitles/tts_boundary_table.json` using the project-local `references/subtitle_semantic_cue_plan.md`.

## Required Current Outputs

For a v1.4.18+ handoff, the active project should produce or update:

- `workflow_state.json`
- project-local tools and project-local runtime references
- frame extraction and visual tag coverage reports
- transcript, shot tags, story evidence pack, `initial_story_seed.json`, story atoms, retention brief, hook candidates, retention shot pool
- resolved story-style state fields
- `highlight_edit_plan.json` for style 5
- script variants, `script_reference_review.json`, final script, final shots, retention QC
- final script units with `source_time` plus `sentence_source_map` for every narration sentence
- script-to-shot review and selected-shot contact sheet
- pre-TTS duration estimate at `speed=1.2`
- continuous AI-tts audio and real boundary metadata
- boundary table, subagent boundary-group cue plan, post-TTS pacing report, strict alignment, subtitle timing report
- compose, layout, internal-jump, watermark, ffprobe, blackdetect, and delivery QA artifacts when rendering
