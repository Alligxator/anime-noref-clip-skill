#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
from pathlib import Path

import edge_tts


SENTENCE_RE = re.compile(r"[^。！？!?.\n]+[。！？!?\.]?")
TICKS_PER_SECOND = 10_000_000


def seconds_from_ticks(value: int | float) -> float:
    return round(float(value) / TICKS_PER_SECOND, 6)


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return round(float(result.stdout.strip()), 6)


def split_sentences(text: str) -> list[str]:
    parts = [match.group(0).strip() for match in SENTENCE_RE.finditer(text) if match.group(0).strip()]
    return parts or [text.strip()]


def normalize_text(text: str) -> str:
    return re.sub(r"[\s，。！？、；：,.!?;:：]+", "", text)


def convert_mp3_to_wav(mp3: Path, wav: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(mp3),
            "-ac",
            "2",
            "-ar",
            "48000",
            str(wav),
        ],
        check=True,
    )


async def synthesize(text: str, voice: str, rate: str, pitch: str, mp3_path: Path) -> tuple[list[dict], list[dict]]:
    last_error: Exception | None = None
    for attempt in range(3):
        sentence_boundaries: list[dict] = []
        word_boundaries: list[dict] = []
        communicate = edge_tts.Communicate(
            text,
            voice=voice,
            rate=rate,
            pitch=pitch,
            boundary="WordBoundary",
        )
        try:
            with mp3_path.open("wb") as audio:
                async for chunk in communicate.stream():
                    ctype = chunk.get("type")
                    if ctype == "audio":
                        audio.write(chunk["data"])
                    elif ctype == "SentenceBoundary":
                        sentence_boundaries.append(
                            {
                                "offset": seconds_from_ticks(chunk["offset"]),
                                "duration": seconds_from_ticks(chunk["duration"]),
                                "text": chunk.get("text", ""),
                            }
                        )
                    elif ctype == "WordBoundary":
                        word_boundaries.append(
                            {
                                "offset": seconds_from_ticks(chunk["offset"]),
                                "duration": seconds_from_ticks(chunk["duration"]),
                                "text": chunk.get("text", ""),
                            }
                        )
            return sentence_boundaries, word_boundaries
        except Exception as exc:  # pragma: no cover - network/provider retry
            last_error = exc
            if mp3_path.exists():
                mp3_path.unlink()
            await asyncio.sleep(2 + attempt * 3)
    raise RuntimeError(f"Edge TTS failed after retries: {last_error}")


def group_sentence_boundaries(
    units: list[dict],
    boundaries: list[dict],
    duration: float,
    *,
    audio_path: str,
) -> list[dict]:
    expected_counts = [len(split_sentences(unit["text"])) for unit in units]
    total_expected = sum(expected_counts)
    if len(boundaries) < len(units):
        raise RuntimeError(f"Too few sentence boundaries: {len(boundaries)} for {len(units)} units")

    groups: list[list[dict]] = []
    cursor = 0
    if len(boundaries) == total_expected:
        for count in expected_counts:
            groups.append(boundaries[cursor : cursor + count])
            cursor += count
    else:
        for index, unit in enumerate(units):
            remaining_units = len(units) - index
            remaining_boundaries = len(boundaries) - cursor
            if remaining_units == 1:
                take = remaining_boundaries
            else:
                target = normalize_text(unit["text"])
                max_take = remaining_boundaries - (remaining_units - 1)
                take = 1
                while take < max_take:
                    candidate = normalize_text("".join(item["text"] for item in boundaries[cursor : cursor + take]))
                    if target in candidate or candidate in target or len(candidate) >= len(target) * 0.9:
                        break
                    take += 1
            groups.append(boundaries[cursor : cursor + take])
            cursor += take

    unit_results = []
    for index, (unit, group) in enumerate(zip(units, groups)):
        speech_start = group[0]["offset"]
        speech_end = group[-1]["offset"] + group[-1]["duration"]
        timeline_start = 0.0 if index == 0 else unit_results[-1]["timeline_end"]
        next_speech_start = groups[index + 1][0]["offset"] if index + 1 < len(groups) else duration
        timeline_end = min(duration, max(timeline_start + 0.3, next_speech_start))
        unit_results.append(
            {
                "unit_id": unit["unit_id"],
                "text": unit["text"],
                "audio_path": audio_path,
                "duration": round(timeline_end - timeline_start, 6),
                "timeline_start": round(timeline_start, 6),
                "timeline_end": round(timeline_end, 6),
                "speech_start": round(speech_start, 6),
                "speech_end": round(min(speech_end, timeline_end), 6),
                "sentences": [item["text"] for item in group],
                "sentence_boundaries": group,
            }
        )
    if unit_results:
        unit_results[-1]["timeline_end"] = duration
        unit_results[-1]["duration"] = round(duration - unit_results[-1]["timeline_start"], 6)
    return unit_results


def group_word_boundaries(
    units: list[dict],
    boundaries: list[dict],
    duration: float,
    *,
    audio_path: str,
) -> list[dict]:
    if len(boundaries) < len(units):
        raise RuntimeError(f"Too few word boundaries: {len(boundaries)} for {len(units)} units")

    groups: list[list[dict]] = []
    target_lengths = [len(normalize_text(unit["text"])) for unit in units]
    boundary_lengths = [len(normalize_text(item.get("text", ""))) for item in boundaries]
    total_target_length = sum(target_lengths)
    total_boundary_length = sum(boundary_lengths)
    if total_target_length and total_boundary_length:
        scale = total_boundary_length / total_target_length
        cumulative_target = 0
        cumulative_boundary = 0
        cursor = 0
        for index, target_length in enumerate(target_lengths):
            remaining_units = len(units) - index
            if remaining_units == 1:
                groups.append(boundaries[cursor:])
                break
            cumulative_target += target_length
            target_limit = cumulative_target * scale
            start_cursor = cursor
            max_cursor = len(boundaries) - (remaining_units - 1)
            while cursor < max_cursor and cumulative_boundary < target_limit:
                cumulative_boundary += boundary_lengths[cursor]
                cursor += 1
            if cursor == start_cursor:
                cumulative_boundary += boundary_lengths[cursor]
                cursor += 1
            groups.append(boundaries[start_cursor:cursor])
        return build_unit_results(units, groups, duration, audio_path=audio_path)

    cursor = 0
    for index, unit in enumerate(units):
        remaining_units = len(units) - index
        remaining_boundaries = len(boundaries) - cursor
        if remaining_units == 1:
            take = remaining_boundaries
        else:
            target = normalize_text(unit["text"])
            max_take = remaining_boundaries - (remaining_units - 1)
            take = 1
            while take < max_take:
                candidate = normalize_text("".join(item["text"] for item in boundaries[cursor : cursor + take]))
                if target in candidate or len(candidate) >= len(target) * 0.9:
                    break
                take += 1
        groups.append(boundaries[cursor : cursor + take])
        cursor += take

    return build_unit_results(units, groups, duration, audio_path=audio_path)


def build_unit_results(
    units: list[dict],
    groups: list[list[dict]],
    duration: float,
    *,
    audio_path: str,
) -> list[dict]:
    unit_results = []
    for index, (unit, group) in enumerate(zip(units, groups)):
        speech_start = group[0]["offset"]
        speech_end = group[-1]["offset"] + group[-1]["duration"]
        timeline_start = 0.0 if index == 0 else unit_results[-1]["timeline_end"]
        next_speech_start = groups[index + 1][0]["offset"] if index + 1 < len(groups) else duration
        timeline_end = min(duration, max(timeline_start + 0.3, next_speech_start))
        unit_results.append(
            {
                "unit_id": unit["unit_id"],
                "text": unit["text"],
                "audio_path": audio_path,
                "duration": round(timeline_end - timeline_start, 6),
                "timeline_start": round(timeline_start, 6),
                "timeline_end": round(timeline_end, 6),
                "speech_start": round(speech_start, 6),
                "speech_end": round(min(speech_end, timeline_end), 6),
                "sentences": split_sentences(unit["text"]),
                "sentence_boundaries": [],
                "word_boundaries": group,
            }
        )
    if unit_results:
        unit_results[-1]["timeline_end"] = duration
        unit_results[-1]["duration"] = round(duration - unit_results[-1]["timeline_start"], 6)
    return unit_results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--script", default="script/script.json")
    parser.add_argument("--out-dir", default="tts")
    parser.add_argument("--voice", default="zh-CN-YunxiNeural")
    parser.add_argument("--rate", default="+20%")
    parser.add_argument("--pitch", default="+0Hz")
    args = parser.parse_args()

    root = args.project_root
    script_path = root / args.script
    script = json.loads(script_path.read_text(encoding="utf-8"))
    units = script["script_units"]
    full_text = "\n".join(unit["text"] for unit in units)
    out_dir = root / args.out_dir
    out_rel = out_dir.relative_to(root).as_posix()
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3_path = out_dir / "narration_full.mp3"
    wav_path = out_dir / "narration.wav"
    text_path = out_dir / "narration_full.txt"

    sentence_boundaries, word_boundaries = asyncio.run(
        synthesize(full_text, args.voice, args.rate, args.pitch, mp3_path)
    )
    text_path.write_text(full_text + "\n", encoding="utf-8")
    convert_mp3_to_wav(mp3_path, wav_path)
    duration = probe_duration(wav_path)
    audio_rel = f"{out_rel}/narration.wav"
    if word_boundaries:
        units_with_timing = group_word_boundaries(
            units, word_boundaries, duration, audio_path=audio_rel
        )
    else:
        units_with_timing = group_sentence_boundaries(
            units, sentence_boundaries, duration, audio_path=audio_rel
        )

    residue = list(out_dir.glob("unit_*.mp3")) + list(out_dir.glob("unit_*.wav"))
    concat_manifest = out_dir / "concat_units.txt"
    if concat_manifest.exists():
        residue.append(concat_manifest)

    tts_payload = {
        "provider": "edge_tts",
        "synthesis_mode": "full_script",
        "script_path": args.script,
        "voice": args.voice,
        "language": script.get("language", "zh-CN"),
        "rate": args.rate,
        "pitch": args.pitch,
        "line_count": len(units_with_timing),
        "total_audio_duration": duration,
        "audio_path": audio_rel,
        "source_audio_path": f"{out_rel}/narration_full.mp3",
        "text_path": f"{out_rel}/narration_full.txt",
        "sentence_boundary_count": len(sentence_boundaries),
        "word_boundary_count": len(word_boundaries),
        "sentence_boundaries": sentence_boundaries,
        "word_boundaries": word_boundaries,
        "units": units_with_timing,
    }
    boundaries_payload = {
        "provider": "edge_tts",
        "timing_source": "edge_tts_word_boundary",
        "audio_path": audio_rel,
        "duration": duration,
        "sentence_boundaries": sentence_boundaries,
        "word_boundaries": word_boundaries,
        "units": units_with_timing,
    }
    manifest = {
        "mode": "full_script",
        "provider": "edge_tts",
        "voice": args.voice,
        "language": script.get("language", "zh-CN"),
        "rate": args.rate,
        "pitch": args.pitch,
        "text_source": args.script,
        "output_audio": audio_rel,
        "source_audio": f"{out_rel}/narration_full.mp3",
        "word_boundary_source": "edge_tts_word_boundary",
        "unit_audio_glob_checked": [f"{out_rel}/unit_*.mp3", f"{out_rel}/unit_*.wav"],
        "concat_units_checked": f"{out_rel}/concat_units.txt",
        "unit_audio_residue_count": len(residue),
        "single_generation": True,
    }

    (out_dir / "tts_durations.json").write_text(json.dumps(tts_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "narration_boundaries.json").write_text(json.dumps(boundaries_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "tts_generation_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "duration": duration,
                "units": len(units_with_timing),
                "sentence_boundaries": len(sentence_boundaries),
                "word_boundaries": len(word_boundaries),
                "unit_audio_residue_count": len(residue),
                "audio": audio_rel,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not residue and word_boundaries else 2


if __name__ == "__main__":
    raise SystemExit(main())
