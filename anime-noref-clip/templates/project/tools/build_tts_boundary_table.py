#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SCHEMA_VERSION = "anime-noref-clip.tts_boundary_table.v1.4.9"
TRAILING_PUNCTUATION = "，。！？、；：,.!?;:"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_project_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def strip_display(text: str) -> str:
    return text.strip().rstrip(TRAILING_PUNCTUATION).strip()


def normalize_text(text: str) -> str:
    return re.sub(r"[\s，。！？、；：,.!?;:：]+", "", text or "")


def boundary_start(boundary: dict, fallback: float) -> float:
    return float(boundary.get("start", boundary.get("offset", fallback)))


def boundary_end(boundary: dict, fallback: float) -> float:
    if "end" in boundary:
        return float(boundary["end"])
    return boundary_start(boundary, fallback) + float(boundary.get("duration", 0.0))


def unit_real_boundaries(unit: dict) -> tuple[list[dict], str]:
    if unit.get("word_boundaries"):
        boundaries = unit.get("word_boundaries", [])
        sources = {str(boundary.get("source", "")) for boundary in boundaries}
        if sources == {"assemblyai_word_boundary"}:
            return boundaries, "assemblyai_word_boundary"
        if "assemblyai_word_boundary" in sources:
            return boundaries, "mixed_word_boundary"
        return boundaries, "provider_word_boundary"
    if unit.get("segment_boundaries"):
        return unit.get("segment_boundaries", []), "assemblyai_segment_boundary"
    return [], "no_real_boundaries"


def build_unit_boundary_entries(unit: dict) -> list[dict]:
    unit_start = float(unit["timeline_start"])
    unit_end = float(unit["timeline_end"])
    entries: list[dict] = []
    normalized_cursor = 0
    real_boundaries, _ = unit_real_boundaries(unit)
    for bid, boundary in enumerate(real_boundaries):
        raw_text = strip_display(str(boundary.get("text", "")))
        normalized = normalize_text(raw_text)
        raw_start = boundary_start(boundary, unit_start)
        raw_end = boundary_end(boundary, unit_start)
        if unit_start > 0 and raw_end <= unit_start:
            raw_start += unit_start
            raw_end += unit_start
        start = max(unit_start, raw_start)
        end = min(unit_end, raw_end)
        if end <= start:
            end = min(unit_end, start + max(0.001, float(boundary.get("duration", 0.001))))
        entries.append(
            {
                "bid": bid,
                "text": raw_text,
                "normalized_text": normalized,
                "start": round(start, 6),
                "end": round(end, 6),
                "duration": round(max(0.0, end - start), 6),
                "normalized_char_start": normalized_cursor,
                "normalized_char_end": normalized_cursor + len(normalized),
            }
        )
        normalized_cursor += len(normalized)
    return entries


def build_boundary_table(tts: dict, language: str) -> dict:
    units = []
    total_boundaries = 0
    mismatch_units = 0
    timing_sources: set[str] = set()
    for unit in tts["units"]:
        entries = build_unit_boundary_entries(unit)
        _, timing_source = unit_real_boundaries(unit)
        if entries:
            timing_sources.add(timing_source)
        normalized_boundary_text = "".join(item["normalized_text"] for item in entries)
        normalized_source_text = normalize_text(unit["text"])
        if normalized_boundary_text and normalized_boundary_text != normalized_source_text:
            mismatch_units += 1
        total_boundaries += len(entries)
        units.append(
            {
                "unit_id": int(unit["unit_id"]),
                "source_text": unit["text"],
                "normalized_source_text": normalized_source_text,
                "timeline_start": unit["timeline_start"],
                "timeline_end": unit["timeline_end"],
                "boundary_count": len(entries),
                "normalized_boundary_text": normalized_boundary_text,
                "boundaries": entries,
            }
        )
    timing_source = (
        timing_sources.pop()
        if len(timing_sources) == 1
        else "mixed_real_tts_boundaries"
        if timing_sources
        else "no_real_boundaries"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "language": language,
        "timing_source": timing_source,
        "unit_count": len(units),
        "word_boundary_count": total_boundaries,
        "real_boundary_count": total_boundaries,
        "boundary_text_mismatch_units": mismatch_units,
        "units": units,
        "passes": total_boundaries > 0
        and mismatch_units == 0
        and all(unit["boundary_count"] > 0 for unit in units),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a real TTS boundary table for subagent subtitle cue grouping."
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--tts-durations", default="tts/tts_durations.json")
    parser.add_argument("--out", default="subtitles/tts_boundary_table.json")
    parser.add_argument("--language", default="")
    args = parser.parse_args()

    root = args.project_root.resolve()
    tts = load_json(resolve_project_path(root, args.tts_durations))
    language = args.language or tts.get("language") or "zh-CN"
    table = build_boundary_table(tts, language)
    write_json(resolve_project_path(root, args.out), table)
    print(
        json.dumps(
            {
                "passes": table["passes"],
                "units": table["unit_count"],
                "word_boundaries": table["word_boundary_count"],
                "boundary_text_mismatch_units": table["boundary_text_mismatch_units"],
                "out": args.out,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if table["passes"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
