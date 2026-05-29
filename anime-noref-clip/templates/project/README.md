# anime-noref-clip Project Template

Use this template as the source of truth for new project-local tools.

Do not copy `tools/` from an older episode project. Start from these skill-owned
templates, then make project-specific changes inside the new project only.

Baseline tools included here:

- `tools/build_shots.py`: real ffmpeg scene cuts only; no duration-based render splits; long shots get analysis-only sample frames.
- `tools/extract_frames.py`: OpenCV batch extraction with ffmpeg timestamp backfill and a zero-missing-frame report.
- `tools/analyze_shot_luma.py`: luma/black/fade risk scan for representative and long-shot sample frames.
- `tools/make_contact_sheets.py`: contact sheet generation for first/mid/last plus long-shot sample frames.
- `tools/merge_subagent_visual_tags.py`: merge and validate GPT subagent JSONL visual tags.
- `tools/parse_ass.py`: parse source ASS subtitles into structured JSON.
- `tools/transcribe_assemblyai.py`: AssemblyAI upload/transcribe/normalize helper.
- `tools/estimate_tts_duration.py`: pre-TTS script duration estimate at the anime default `speed=1.2`, using `references/tts_duration_calibration.json` when present.
- `tools/generate_tts_ai_tts_v145.py`: default single full-script local AI-tts generation with raw AssemblyAI word timing and recorded `speed=1.2`.
- `tools/build_tts_boundary_table.py`: convert real TTS boundary metadata into the boundary table used by the subtitle subagent.
- `tools/build_post_tts_alignment_v145.py`: post-TTS pacing repair, stable source sub-windows, frame-quantized alignment, and boundary-group ASS subtitles.
- `tools/render_frameq_segments.py`: frame-quantized vertical segment render and drift report.
- `tools/internal_jump_scan.py`: rendered-output internal jump scanner.
- `tools/final_mux_bgm_watermark.py`: final subtitle/BGM/narration/watermark mux.

The skill bootstrap script copies current tools plus workflow references and artifact contracts into the project:

```bash
python3 ~/.codex/skills/anime-noref-clip/scripts/init_project_scripts.py --project-root .
```

After visual tagging and dialogue/frame fusion, create `story_evidence_pack.json` with a Codex subagent using the project-local `references/initial_story_write.md`, then call `close_agent` after collecting or rejecting the subagent output. The pack is evidence only; it must not contain narration or final story copy.

Before retention brief, hook candidates, or script variants, call `content-style-system` task `anime_clip_initial_story_write` with `story_evidence_pack.json`. Save `initial_story_seed.json`, canonical `story_atoms.json`, and `initial_story_execution_log`; downstream retention and script artifacts must cite `initial_story_seed`.

When row 11 rewrites or selects final copy, every `script_units[]` item in `script.json` must include `source_time` and a `sentence_source_map` entry for every narration sentence. Each sentence map records source time, source shots, plot function, and TTS budget. The review must also reject visual-caption-only lines; final copy should explain plot causality, danger, choices, consequences, relationship shifts, questions, or payoffs instead of merely describing the frame.

Before production TTS, estimate duration and rewrite or reselect if the estimate is below 90% of target. After full-script TTS and before segment rendering, build the boundary table, create `subtitles/semantic_cue_plan.json` with a Codex subagent using the project-local `references/subtitle_semantic_cue_plan.md`, call `close_agent` after collecting that subagent result, then run the post-TTS alignment builder from the project copy:

```bash
python3 tools/estimate_tts_duration.py --project-root . --speed 1.2
python3 tools/build_tts_boundary_table.py --project-root . --language zh-CN
python3 tools/build_post_tts_alignment_v145.py --project-root . --source-media <source-mkv> --language zh-CN --require-subtitle-plan
```

Use the target language's own TTS directory and workflow state for localized versions; do not reuse another language's alignment or subtitle timing.
