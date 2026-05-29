#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


AI_TTS_SCRIPT = Path("/Users/gxator.alli/.codex/skills/AI-tts/scripts/generate_ai_tts.py")
TRAILING_PUNCTUATION = "，。！？、；：,.!?;:"
SCHEMA_VERSION = "anime-noref-clip.ai_tts_adapter.v1.4.18"
BOUNDARY_TABLE_SCHEMA_VERSION = "anime-noref-clip.tts_boundary_table.v1.4.9"
DEFAULT_TTS_SPEED = 1.2


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_project_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def display_project_path(root: Path, value: str | Path) -> str:
    path = Path(value)
    if path.is_absolute():
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return path.as_posix()
    return path.as_posix()


def strip_display(text: str) -> str:
    return text.strip().rstrip(TRAILING_PUNCTUATION).strip()


def normalize_text(text: str) -> str:
    return re.sub(r"[\s，。！？、；：,.!?;:：]+", "", text or "")


def split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[。！？!?.])\s*", text) if part.strip()]
    return parts or [text.strip()]


def route_language(language: str) -> str:
    value = (language or "auto").lower()
    if value.startswith("th"):
        return "th"
    if value.startswith("zh"):
        return "zh"
    if value.startswith("en"):
        return "en"
    return "auto"


def raw_slice_for_normalized_span(text: str, start_norm: int, end_norm: int) -> str:
    if start_norm >= end_norm:
        return ""
    cursor = 0
    raw_start: int | None = None
    raw_end: int | None = None
    for index, char in enumerate(text):
        normalized = normalize_text(char)
        if normalized:
            if raw_start is None and cursor >= start_norm:
                raw_start = index
            cursor += len(normalized)
            if cursor >= end_norm and raw_end is None:
                raw_end = index + 1
                break
    if raw_start is None:
        raw_start = 0
    if raw_end is None:
        raw_end = len(text)
    return strip_display(text[raw_start:raw_end])


def source_boundary_spans(boundaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    cursor = 0
    for boundary in boundaries:
        text = str(boundary.get("source_text") or boundary.get("text") or boundary.get("provider_text") or "")
        normalized = normalize_text(text)
        length = len(normalized)
        if length <= 0:
            continue
        start = float(boundary["start"])
        end = float(boundary["end"])
        spans.append(
            {
                "source_text": text,
                "norm_start": cursor,
                "norm_end": cursor + length,
                "start": start,
                "end": end,
                "duration": max(0.001, end - start),
            }
        )
        cursor += length
    return spans


def boundary_duration(boundary: dict[str, Any]) -> float:
    start = float(boundary["start"])
    end = float(boundary.get("end", start + float(boundary.get("duration", 0.001))))
    return max(0.001, end - start)


def assemblyai_word_boundaries_from_raw(raw: dict[str, Any]) -> list[dict[str, Any]]:
    boundaries: list[dict[str, Any]] = []
    for index, word in enumerate(raw.get("words") or [], start=1):
        if not isinstance(word, dict):
            continue
        text = str(word.get("text") or "").strip()
        if not text:
            continue
        start = round(float(word.get("start", 0) or 0) / 1000, 6)
        end = round(float(word.get("end", word.get("start", 0)) or 0) / 1000, 6)
        if end <= start:
            end = round(start + 0.001, 6)
        boundary: dict[str, Any] = {
            "index": index,
            "text": text,
            "start": start,
            "end": end,
            "duration": round(end - start, 6),
            "source": "assemblyai_word_boundary",
        }
        if word.get("confidence") is not None:
            boundary["confidence"] = round(float(word.get("confidence", 0.0)), 4)
        boundaries.append(boundary)
    return boundaries


def normalized_word_boundaries(segments_payload: dict[str, Any], raw_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    boundaries = segments_payload.get("word_boundaries") or []
    if boundaries:
        normalized: list[dict[str, Any]] = []
        for index, boundary in enumerate(boundaries, start=1):
            start = float(boundary["start"])
            end = float(boundary.get("end", start + float(boundary.get("duration", 0.001))))
            item = dict(boundary)
            item["index"] = int(item.get("index", index))
            item["start"] = round(start, 6)
            item["end"] = round(max(start + 0.001, end), 6)
            item["duration"] = round(item["end"] - item["start"], 6)
            item["source"] = "assemblyai_word_boundary"
            normalized.append(item)
        return normalized
    if raw_payload:
        return assemblyai_word_boundaries_from_raw(raw_payload)
    return []


def build_units(
    units: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    duration: float,
    audio_rel: str,
    *,
    boundary_field: str,
    boundary_source: str,
) -> list[dict[str, Any]]:
    spans = source_boundary_spans(boundaries)
    unit_results: list[dict[str, Any]] = []
    unit_cursor = 0
    total_unit_norm = sum(len(normalize_text(str(unit["text"]))) for unit in units)

    for unit in units:
        unit_id = int(unit["unit_id"])
        text = str(unit["text"])
        unit_norm = normalize_text(text)
        unit_start_norm = unit_cursor
        unit_end_norm = unit_cursor + len(unit_norm)
        unit_cursor = unit_end_norm
        boundaries: list[dict[str, Any]] = []

        for span in spans:
            overlap_start = max(unit_start_norm, int(span["norm_start"]))
            overlap_end = min(unit_end_norm, int(span["norm_end"]))
            if overlap_end <= overlap_start:
                continue
            span_len = max(1, int(span["norm_end"]) - int(span["norm_start"]))
            rel_start = (overlap_start - int(span["norm_start"])) / span_len
            rel_end = (overlap_end - int(span["norm_start"])) / span_len
            start = float(span["start"]) + float(span["duration"]) * rel_start
            end = float(span["start"]) + float(span["duration"]) * rel_end
            unit_text_start = overlap_start - unit_start_norm
            unit_text_end = overlap_end - unit_start_norm
            boundary_text = raw_slice_for_normalized_span(text, unit_text_start, unit_text_end)
            if not boundary_text:
                boundary_text = unit_norm[unit_text_start:unit_text_end]
            boundaries.append(
                {
                    "offset": round(start, 6),
                    "start": round(start, 6),
                    "end": round(max(start + 0.001, end), 6),
                    "duration": round(max(0.001, end - start), 6),
                    "text": boundary_text,
                    "normalized_text": normalize_text(boundary_text),
                    "source": boundary_source,
                }
            )

        if not boundaries:
            if total_unit_norm:
                start = duration * unit_start_norm / total_unit_norm
                end = duration * unit_end_norm / total_unit_norm
            else:
                start = unit_results[-1]["timeline_end"] if unit_results else 0.0
                end = duration
            boundaries.append(
                {
                    "offset": round(start, 6),
                    "start": round(start, 6),
                    "end": round(max(start + 0.001, end), 6),
                    "duration": round(max(0.001, end - start), 6),
                    "text": strip_display(text),
                    "normalized_text": unit_norm,
                    "source": "unit_duration_fallback",
                }
            )

        timeline_start = float(boundaries[0]["start"])
        timeline_end = float(boundaries[-1]["end"])
        unit_results.append(
            {
                "unit_id": unit_id,
                "text": text,
                "audio_path": audio_rel,
                "duration": round(max(0.001, timeline_end - timeline_start), 6),
                "timeline_start": round(timeline_start, 6),
                "timeline_end": round(timeline_end, 6),
                "speech_start": round(timeline_start, 6),
                "speech_end": round(timeline_end, 6),
                "sentences": split_sentences(text),
                "sentence_boundaries": [],
                "word_boundaries": boundaries if boundary_field == "word_boundaries" else [],
                "segment_boundaries": boundaries if boundary_field == "segment_boundaries" else [],
            }
        )

    if unit_results:
        unit_results[0]["timeline_start"] = min(0.0, unit_results[0]["timeline_start"])
        unit_results[0]["duration"] = round(unit_results[0]["timeline_end"] - unit_results[0]["timeline_start"], 6)
        unit_results[-1]["timeline_end"] = round(max(unit_results[-1]["timeline_end"], duration), 6)
        unit_results[-1]["duration"] = round(unit_results[-1]["timeline_end"] - unit_results[-1]["timeline_start"], 6)
    return unit_results


def build_boundary_table(tts_units: list[dict[str, Any]], language: str) -> dict[str, Any]:
    units = []
    total_boundaries = 0
    word_boundary_count = 0
    segment_boundary_count = 0
    mismatch_units = 0
    timing_sources: set[str] = set()
    for unit in tts_units:
        entries = []
        normalized_cursor = 0
        unit_boundaries = unit.get("word_boundaries") or unit.get("segment_boundaries", [])
        for bid, boundary in enumerate(unit_boundaries):
            text = strip_display(str(boundary.get("text", "")))
            normalized = normalize_text(text)
            start = float(boundary.get("start", boundary.get("offset", unit["timeline_start"])))
            end = float(boundary.get("end", start + float(boundary.get("duration", 0.001))))
            entries.append(
                {
                    "bid": bid,
                    "text": text,
                    "normalized_text": normalized,
                    "start": round(start, 6),
                    "end": round(max(start + 0.001, end), 6),
                    "duration": round(max(0.001, end - start), 6),
                    "normalized_char_start": normalized_cursor,
                    "normalized_char_end": normalized_cursor + len(normalized),
                }
            )
            normalized_cursor += len(normalized)
            timing_sources.add(str(boundary.get("source", "real_tts_boundary")))
            if boundary.get("source") == "assemblyai_word_boundary":
                word_boundary_count += 1
            else:
                segment_boundary_count += 1
        normalized_boundary_text = "".join(item["normalized_text"] for item in entries)
        normalized_source_text = normalize_text(str(unit["text"]))
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
        "schema_version": BOUNDARY_TABLE_SCHEMA_VERSION,
        "language": language,
        "timing_source": timing_source,
        "boundary_type": "assemblyai_word" if word_boundary_count else "assemblyai_segment",
        "unit_count": len(units),
        "word_boundary_count": total_boundaries,
        "assemblyai_word_boundary_count": word_boundary_count,
        "assemblyai_segment_boundary_count": segment_boundary_count,
        "real_boundary_count": total_boundaries,
        "boundary_text_mismatch_units": mismatch_units,
        "units": units,
        "passes": total_boundaries > 0 and all(unit["boundary_count"] > 0 for unit in units),
    }


def build_config(args: argparse.Namespace, script: dict[str, Any]) -> dict[str, Any]:
    root = args.project_root.resolve()
    out_dir = resolve_project_path(root, args.out_dir)
    subtitles_dir = resolve_project_path(root, args.subtitles_dir)
    language = route_language(args.language or script.get("language", "auto"))
    return {
        "provider": "ai_tts",
        "script": args.script,
        "script_unit_count": len(script["script_units"]),
        "language": language,
        "speed": args.speed,
        "output_audio": display_project_path(root, out_dir / "narration_full.wav"),
        "text_output": display_project_path(root, out_dir / "narration_full.txt"),
        "srt_output": display_project_path(root, subtitles_dir / "ai_tts_timing.srt"),
        "segments_json_output": display_project_path(root, out_dir / "ai_tts_segments.json"),
        "raw_transcript_json_output": display_project_path(root, out_dir / "ai_tts_assemblyai_raw.json"),
        "tts_durations": display_project_path(root, out_dir / "tts_durations.json"),
        "tts_boundaries": display_project_path(root, out_dir / "narration_boundaries.json"),
        "tts_generation_manifest": display_project_path(root, out_dir / "tts_generation_manifest.json"),
        "boundary_table": display_project_path(root, subtitles_dir / "tts_boundary_table.json"),
        "ai_tts_script": str(args.ai_tts_script),
    }


def run_ai_tts(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, text=True, capture_output=True, check=True)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"AI-tts did not return JSON stdout: {proc.stdout}\nstderr: {proc.stderr}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate anime-noref-clip narration through local AI-tts.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--script", default="script/script.json")
    parser.add_argument("--out-dir", default="tts")
    parser.add_argument("--subtitles-dir", default="subtitles")
    parser.add_argument("--language", default="")
    parser.add_argument("--speed", type=float, default=DEFAULT_TTS_SPEED)
    parser.add_argument("--ai-tts-script", type=Path, default=AI_TTS_SCRIPT)
    parser.add_argument("--summary-json", type=Path, help="Use an existing AI-tts JSON summary instead of generating.")
    parser.add_argument("--dry-run-config", action="store_true")
    args = parser.parse_args()

    root = args.project_root.resolve()
    script = load_json(resolve_project_path(root, args.script))
    units = script["script_units"]
    full_text = "\n".join(str(unit["text"]) for unit in units)
    config = build_config(args, script)
    if args.dry_run_config:
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return 0

    out_dir = resolve_project_path(root, args.out_dir)
    subtitles_dir = resolve_project_path(root, args.subtitles_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / "narration_full.wav"
    text_path = out_dir / "narration_full.txt"
    srt_path = subtitles_dir / "ai_tts_timing.srt"
    segments_path = out_dir / "ai_tts_segments.json"
    raw_transcript_path = out_dir / "ai_tts_assemblyai_raw.json"

    if args.summary_json:
        summary = load_json(args.summary_json.expanduser().resolve())
    else:
        command = [
            sys.executable,
            str(args.ai_tts_script.expanduser().resolve()),
            "--language",
            config["language"],
            "--speed",
            str(config["speed"]),
            "--text",
            full_text,
            "--output",
            str(wav_path),
            "--srt-output",
            str(srt_path),
            "--segments-json-output",
            str(segments_path),
            "--raw-transcript-json-output",
            str(raw_transcript_path),
        ]
        summary = run_ai_tts(command)

    text_path.write_text(full_text + "\n", encoding="utf-8")
    if not segments_path.exists() and summary.get("segments_json_output"):
        summary_segments = Path(str(summary["segments_json_output"]))
        if summary_segments.exists():
            segments_path.write_text(summary_segments.read_text(encoding="utf-8"), encoding="utf-8")
    if not raw_transcript_path.exists() and summary.get("raw_transcript_json_output"):
        summary_raw = Path(str(summary["raw_transcript_json_output"]))
        if summary_raw.exists():
            raw_transcript_path.write_text(summary_raw.read_text(encoding="utf-8"), encoding="utf-8")
    segments_payload = load_json(segments_path)
    raw_payload = load_json(raw_transcript_path) if raw_transcript_path.exists() else None
    word_boundaries = normalized_word_boundaries(segments_payload, raw_payload)
    duration = float(summary.get("duration_seconds") or summary.get("duration") or 0.0)
    if duration <= 0:
        candidate_boundaries = word_boundaries or segments_payload.get("segments", [])
        duration = max(float(boundary.get("end", 0.0)) for boundary in candidate_boundaries)
    audio_rel = display_project_path(root, wav_path)
    if word_boundaries:
        boundary_source = "assemblyai_word_boundary"
        boundary_field = "word_boundaries"
        source_boundaries = word_boundaries
    else:
        boundary_source = "assemblyai_segment_boundary"
        boundary_field = "segment_boundaries"
        source_boundaries = segments_payload.get("segments", [])
    units_with_timing = build_units(
        units,
        source_boundaries,
        duration,
        audio_rel,
        boundary_field=boundary_field,
        boundary_source=boundary_source,
    )
    boundary_table = build_boundary_table(units_with_timing, config["language"])

    residue = list(out_dir.glob("unit_*.mp3")) + list(out_dir.glob("unit_*.wav"))
    concat_manifest = out_dir / "concat_units.txt"
    if concat_manifest.exists():
        residue.append(concat_manifest)

    tts_payload = {
        "schema_version": SCHEMA_VERSION,
        "provider": "ai_tts",
        "synthesis_mode": "full_script",
        "script_path": args.script,
        "language": script.get("language", config["language"]),
        "ai_tts_language": config["language"],
        "speed": config["speed"],
        "line_count": len(units_with_timing),
        "total_audio_duration": round(duration, 6),
        "audio_path": audio_rel,
        "text_path": display_project_path(root, text_path),
        "srt_output": display_project_path(root, srt_path),
        "segments_json_output": display_project_path(root, segments_path),
        "raw_transcript_json_output": display_project_path(root, raw_transcript_path) if raw_transcript_path.exists() else None,
        "timing_source": boundary_table["timing_source"],
        "word_boundary_count": len(word_boundaries),
        "segment_boundary_count": boundary_table["real_boundary_count"] - len(word_boundaries),
        "units": units_with_timing,
    }
    boundaries_payload = {
        "schema_version": SCHEMA_VERSION,
        "provider": "ai_tts",
        "timing_source": boundary_table["timing_source"],
        "speed": config["speed"],
        "audio_path": audio_rel,
        "duration": round(duration, 6),
        "segments_json_output": display_project_path(root, segments_path),
        "raw_transcript_json_output": display_project_path(root, raw_transcript_path) if raw_transcript_path.exists() else None,
        "word_boundaries": word_boundaries,
        "segment_boundaries": segments_payload.get("segments", []),
        "units": units_with_timing,
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "mode": "full_script",
        "provider": "ai_tts",
        "language": script.get("language", config["language"]),
        "ai_tts_language": config["language"],
        "speed": config["speed"],
        "text_source": args.script,
        "output_audio": audio_rel,
        "srt_output": display_project_path(root, srt_path),
        "segments_json_output": display_project_path(root, segments_path),
        "raw_transcript_json_output": display_project_path(root, raw_transcript_path) if raw_transcript_path.exists() else None,
        "boundary_source": boundary_table["timing_source"],
        "word_boundary_source": "assemblyai_word_boundary" if word_boundaries else None,
        "unit_audio_glob_checked": [f"{args.out_dir}/unit_*.mp3", f"{args.out_dir}/unit_*.wav"],
        "concat_units_checked": f"{args.out_dir}/concat_units.txt",
        "unit_audio_residue_count": len(residue),
        "single_generation": True,
    }

    write_json(out_dir / "tts_durations.json", tts_payload)
    write_json(out_dir / "narration_boundaries.json", boundaries_payload)
    write_json(out_dir / "tts_generation_manifest.json", manifest)
    write_json(subtitles_dir / "tts_boundary_table.json", boundary_table)
    print(
        json.dumps(
            {
                "duration": round(duration, 6),
                "speed": config["speed"],
                "units": len(units_with_timing),
                "word_boundaries": len(word_boundaries),
                "segment_boundaries": boundary_table["real_boundary_count"] - len(word_boundaries),
                "unit_audio_residue_count": len(residue),
                "audio": audio_rel,
                "boundary_table": display_project_path(root, subtitles_dir / "tts_boundary_table.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not residue and boundary_table["passes"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
