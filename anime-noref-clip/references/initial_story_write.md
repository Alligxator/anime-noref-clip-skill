# Initial Story Writing Contract

Use this contract after dialogue/frame fusion and before retention brief, hook candidates, retention shot pool, or script variants. The goal is to make the initial story writing come from `content-style-system`, while keeping every claim grounded in shot-level visual tags and aligned dialogue.

## Story Evidence Pack Subagent

Row 6 is the `story_evidence_pack.json` gate. Launch an independent Codex subagent to prepare evidence from:

- `shot_story_tags.json`
- `dialogue_frame_fusion.json`
- subtitle-shot alignment artifacts
- the approved independent video windows or candidate windows

The evidence pack subagent must output JSON only. It may organize evidence, but it must not write narration, produce final story prose, create motives, or invent events outside the source.

For each independent video, `story_evidence_pack.json` must include:

- `video_id`
- `target_duration_sec`, normally about 70 seconds when the user asks for independent 70-second videos
- candidate main line
- environment replacement chain, describing location/state changes with concrete visual transitions instead of lazy connectors such as `另一边`
- character roles and relationship/background experience supported by dialogue or visible context
- cause-effect chain
- strong visual evidence
- quotable dialogue
- forbidden inferences
- source `shot_id`, time range, and dialogue/event id mapping

The subagent must call `close_agent` after its result is collected, rejected, or superseded. A completed but unclosed evidence-pack subagent cannot pass the row.

## Content-Style Initial Story Write

Row 7 must call `content-style-system` with task `anime_clip_initial_story_write`. `anime-noref-clip` passes the evidence pack, resolved story style, target duration, independent-video split, and source-support constraints. It must not hardcode Obsidian file choices; `content-style-system` owns vault routing.

The writing skill returns:

- `initial_story_seed.json`
- canonical `story_atoms.json`
- `initial_story_execution_log`

`initial_story_seed.json` must include:

- `content_style_skill`: `content-style-system`
- `content_style_task`: `anime_clip_initial_story_write`
- `video_stories`, one entry per independent video
- selected story line, conflict, reversal/danger points, hook directions, weak-information compression suggestions, and forbidden phrasing hits
- source evidence mapping for every written story claim
- checks proving source support and no unsupported claims

`story_atoms.json` is no longer locally extracted by `anime-noref-clip`. It is the machine-friendly atom view of `initial_story_seed.json`, written by `content-style-system` and consumed by `retention_brief.json`, `hook_candidates.json`, and `script_variants.json`.

## Downstream Consumption

After row 7:

- `retention_brief.json` must cite `initial_story_seed.json`.
- `hook_candidates.json` must cite `initial_story_seed.json` and reject hooks unsupported by the seed.
- `script_variants.json` must cite `initial_story_seed.json` and keep each candidate bound to seed atom ids.
- row 11 `script_reference_review.json` must verify the final script inherits the early story seed and does not bypass it.

For multiple independent videos, each video gets its own evidence pack section, initial story seed entry, story atoms, script, TTS estimate, real TTS timing, and delivery artifacts. Do not reuse a hook, story claim, or phrasing from one video as proof for another video.
