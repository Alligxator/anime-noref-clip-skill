# Subtitle Boundary-Group Cue Plan

Use this reference after full-script TTS and after `tools/build_tts_boundary_table.py`.

Production subtitle planning uses a three-stage flow:

1. The project script builds `subtitles/tts_boundary_table.json` from real TTS `WordBoundary` metadata.
2. A Codex subagent groups contiguous boundary ids into readable subtitle cues.
3. `tools/build_post_tts_alignment_v145.py` validates the groups and uses the exact boundary times to write ASS subtitles.

The subagent does not listen to audio and must not assign timestamps. It only groups already-timed TTS boundaries.

Input to the subagent:

- target language
- `script/script.json`
- `tts/tts_durations.json`
- `subtitles/tts_boundary_table.json`
- optional style notes for the platform/language

Output path:

```text
subtitles/semantic_cue_plan.json
```

Required JSON schema:

```json
{
  "schema_version": "anime-noref-clip.semantic_cue_plan.v1.4.9",
  "language": "zh-CN",
  "generated_by": "gpt-5.5 Codex subagent",
  "strategy": "group contiguous TTS boundary ids into semantic subtitle cues; timing attached by script",
  "units": [
    {
      "unit_id": 1,
      "source_text": "戒指做好后，皇太子却先说：你没必要戴上它",
      "boundary_count": 3,
      "cues": [
        {
          "text": "戒指做好后",
          "boundary_start": 0,
          "boundary_end": 1
        },
        {
          "text": "皇太子却先说",
          "boundary_start": 1,
          "boundary_end": 2
        },
        {
          "text": "你没必要戴上它",
          "boundary_start": 2,
          "boundary_end": 3
        }
      ]
    }
  ],
  "checks": {
    "all_units_present": true,
    "boundary_groups_cover_all_boundaries": true,
    "boundary_groups_are_contiguous": true,
    "text_preserved_after_normalization": true,
    "cross_sentence_boundary_count": 0,
    "orphan_fragment_count": 0,
    "bad_line_break_count": 0,
    "trailing_punctuation_removed": true
  }
}
```

Rules:

- Use only boundary ids from `subtitles/tts_boundary_table.json`.
- `boundary_start` is inclusive and `boundary_end` is exclusive, like Python slicing.
- Within each unit, cues must cover all boundary ids from `0` to `boundary_count` with no gaps and no overlaps.
- Each cue's display text must match the concatenated boundary text for its range after normalization.
- Preserve every narration character represented in the TTS boundaries after normalization. Do not summarize, rewrite, translate, add text, or delete text.
- Strip display-only trailing punctuation from cue text, but keep `source_text` unchanged.
- Chinese: prefer complete semantic chunks around 6-14 characters, with 4-16 allowed when timing/readability requires it. Do not split particles, complements, or fixed phrases away from their head.
- Thai: group natural phrase/word boundary ranges. Do not hard-slice by character count.
- English: group natural phrase boundary ranges and avoid orphan words.
- Avoid cues that will read as flashes; merge tiny fragments with neighboring boundaries unless the source line itself is intentionally abrupt.
- Do not create a cue that crosses original sentence boundaries unless a deliberate continuation is documented.
- Return JSON only.
