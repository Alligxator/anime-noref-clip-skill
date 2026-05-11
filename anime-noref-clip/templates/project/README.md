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
- `tools/generate_tts_edge_v145.py`: single full-script Edge TTS with word-boundary timing.
- `tools/build_tts_boundary_table.py`: convert real TTS WordBoundary metadata into the boundary table used by the subtitle subagent.
- `tools/build_post_tts_alignment_v145.py`: post-TTS pacing repair, stable source sub-windows, frame-quantized alignment, and boundary-group ASS subtitles.
- `tools/render_frameq_segments.py`: frame-quantized vertical segment render and drift report.
- `tools/internal_jump_scan.py`: rendered-output internal jump scanner.
- `tools/final_mux_bgm_watermark.py`: final subtitle/BGM/narration/watermark mux.

The skill bootstrap script also copies the current validator into the project:

```bash
python3 ~/.codex/skills/anime-noref-clip/scripts/init_project_scripts.py --project-root .
```

After full-script TTS and before segment rendering, build the boundary table, create `subtitles/semantic_cue_plan.json` with a Codex subagent using the skill reference `references/subtitle_semantic_cue_plan.md`, then run the post-TTS alignment builder from the project copy:

```bash
python3 tools/build_tts_boundary_table.py --project-root . --language zh-CN
python3 tools/build_post_tts_alignment_v145.py --project-root . --source-media <source-mkv> --language zh-CN --require-subtitle-plan
```

Use the target language's own TTS directory and workflow state for localized versions; do not reuse another language's alignment or subtitle timing.
