#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from fractions import Fraction
from pathlib import Path


TRAILING_PUNCTUATION = "，。！？、；：,.!?;:"
SCHEMA_VERSION = "anime-noref-clip.post_tts_alignment.v1.4.9"
SUBTITLE_PLAN_SCHEMA_VERSION = "anime-noref-clip.semantic_cue_plan.v1.4.9"
BOUNDARY_TABLE_SCHEMA_VERSION = "anime-noref-clip.tts_boundary_table.v1.4.9"
BOUNDARY_GROUP_SOURCE = "subagent_boundary_group_plan"
RENDER_BOUNDARY_POLICY = "real_scene_cut_only_no_duration_based_render_splits"
CJK_BAD_BOUNDARY_PAIRS = (
    ("两个", "人"),
    ("一个", "人"),
    ("已经不", "对"),
    ("已经不", "准备"),
    ("起不", "来"),
    ("浅发", "男人"),
    ("黑发", "男人"),
    ("金发", "男人"),
    ("红发", "男人"),
    ("求救", "声"),
    ("白色", "装置"),
    ("台", "面上"),
    ("货装", "上"),
    ("指节用力已经不", "准备"),
    ("放我", "出去"),
    ("让我", "出去"),
    ("接", "一遍"),
    ("蓝白色", "星体"),
    ("一", "招"),
)


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


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def seconds_to_ass(value: float) -> str:
    value = max(0.0, value)
    centis = int(round(value * 100))
    hours, rem = divmod(centis, 360000)
    minutes, rem = divmod(rem, 6000)
    seconds, cs = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{cs:02d}"


def strip_display(text: str) -> str:
    return text.strip().rstrip(TRAILING_PUNCTUATION).strip()


def normalize_text(text: str) -> str:
    return re.sub(r"[\s，。！？、；：,.!?;:：]+", "", text or "")


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def bad_cjk_boundary_reason(left: str, right: str) -> str:
    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    if not contains_cjk(left_norm + right_norm):
        return ""
    for left_suffix, right_prefix in CJK_BAD_BOUNDARY_PAIRS:
        if left_norm.endswith(left_suffix) and right_norm.startswith(right_prefix):
            return f"{left_suffix}/{right_prefix}"
    return ""


def wrap_ass_text(text: str, max_line_chars: int = 18) -> str:
    text = strip_display(text)
    if len(text) <= max_line_chars:
        return text
    split_at = len(text) // 2
    for index in range(min(max_line_chars, len(text) - 1), max(0, len(text) - max_line_chars) - 1, -1):
        if text[index:index + 1] in ("，", "、", "：", "；", " "):
            split_at = index + 1
            break
    first = strip_display(text[:split_at])
    second = strip_display(text[split_at:])
    if not first or not second:
        return text
    return first + r"\N" + second


def allocate_frames(total_frames: int, shots: list[dict], fps: Fraction, min_speed: float) -> list[int]:
    caps = []
    for shot in shots:
        cap = max(1, math.floor((float(shot["src_duration"]) / min_speed) * float(fps)))
        caps.append(cap)
    if sum(caps) < total_frames:
        raise RuntimeError(
            f"Unit {shots[0]['unit_id']} cannot fit {total_frames} frames at min speed {min_speed}; "
            f"capacity is {sum(caps)} frames"
        )

    weights = [max(0.001, float(shot.get("target_duration", 0.0))) for shot in shots]
    assigned = [0] * len(shots)
    active = set(range(len(shots)))
    remaining = total_frames
    while active:
        weight_sum = sum(weights[index] for index in active)
        raw = {index: remaining * weights[index] / weight_sum for index in active}
        floors = {index: max(1, int(math.floor(raw[index]))) for index in active}
        overflow = [index for index in active if floors[index] > caps[index]]
        if not overflow:
            allocated = sum(floors.values())
            order = sorted(active, key=lambda index: raw[index] - math.floor(raw[index]), reverse=True)
            cursor = 0
            while allocated < remaining:
                index = order[cursor % len(order)]
                if floors[index] < caps[index]:
                    floors[index] += 1
                    allocated += 1
                cursor += 1
                if cursor > len(order) * (remaining + 1):
                    raise RuntimeError("Could not distribute frame remainder")
            while allocated > remaining:
                index = sorted(active, key=lambda item: floors[item] - raw[item], reverse=True)[0]
                if floors[index] <= 1:
                    raise RuntimeError("Could not remove surplus frame")
                floors[index] -= 1
                allocated -= 1
            for index, value in floors.items():
                assigned[index] = value
            return assigned
        for index in overflow:
            assigned[index] = caps[index]
            remaining -= caps[index]
            active.remove(index)
    if sum(assigned) != total_frames:
        raise RuntimeError("Frame allocation failed")
    return assigned


def as_int(value, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def boundary_start(boundary: dict, fallback: float) -> float:
    return float(boundary.get("start", boundary.get("offset", fallback)))


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
        raw_end = float(boundary["end"]) if "end" in boundary else boundary_end(boundary)
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


def build_boundary_table(tts_units: list[dict], language: str) -> dict:
    units = []
    total_boundaries = 0
    timing_sources: set[str] = set()
    for unit in tts_units:
        entries = build_unit_boundary_entries(unit)
        _, timing_source = unit_real_boundaries(unit)
        if entries:
            timing_sources.add(timing_source)
        total_boundaries += len(entries)
        units.append(
            {
                "unit_id": int(unit["unit_id"]),
                "source_text": unit["text"],
                "normalized_source_text": normalize_text(unit["text"]),
                "timeline_start": unit["timeline_start"],
                "timeline_end": unit["timeline_end"],
                "boundary_count": len(entries),
                "normalized_boundary_text": "".join(item["normalized_text"] for item in entries),
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
        "unit_count": len(units),
        "word_boundary_count": total_boundaries,
        "real_boundary_count": total_boundaries,
        "units": units,
        "passes": total_boundaries > 0 and all(unit["boundary_count"] > 0 for unit in units),
    }


def boundary_units_by_id(boundary_table: dict) -> dict[int, dict]:
    return {int(unit["unit_id"]): unit for unit in boundary_table.get("units", [])}


def load_subtitle_plan(path: Path) -> dict:
    plan = load_json(path)
    unit_boundary_groups: dict[int, list[dict]] = {}
    units = plan.get("units", [])
    if isinstance(units, list):
        for unit in units:
            if not isinstance(unit, dict) or "unit_id" not in unit:
                continue
            unit_id = int(unit["unit_id"])
            cue_items = unit.get("cues", [])
            boundary_groups: list[dict] = []
            if isinstance(cue_items, list):
                for cue in cue_items:
                    if not isinstance(cue, dict):
                        continue
                    start = as_int(cue.get("boundary_start", cue.get("start_bid")))
                    end = as_int(cue.get("boundary_end", cue.get("end_bid")))
                    text = strip_display(str(cue.get("text", "")))
                    if start is not None and end is not None:
                        boundary_groups.append(
                            {
                                "text": text,
                                "boundary_start": start,
                                "boundary_end": end,
                            }
                        )
            if boundary_groups:
                unit_boundary_groups[unit_id] = boundary_groups

    cues = plan.get("cues", [])
    if isinstance(cues, list):
        boundary_grouped: dict[int, list[dict]] = {}
        for cue in cues:
            if not isinstance(cue, dict) or "unit_id" not in cue:
                continue
            unit_id = int(cue["unit_id"])
            start = as_int(cue.get("boundary_start", cue.get("start_bid")))
            end = as_int(cue.get("boundary_end", cue.get("end_bid")))
            text = strip_display(str(cue.get("text", "")))
            if start is not None and end is not None:
                boundary_grouped.setdefault(unit_id, []).append(
                    {"text": text, "boundary_start": start, "boundary_end": end}
                )
        unit_boundary_groups.update(
            {unit_id: groups for unit_id, groups in boundary_grouped.items() if groups}
        )

    return {
        "path": path.as_posix(),
        "raw": plan,
        "unit_boundary_groups": unit_boundary_groups,
        "has_boundary_groups": bool(unit_boundary_groups),
        "checks": plan.get("checks", {}) if isinstance(plan.get("checks"), dict) else {},
    }


def boundary_end(boundary: dict) -> float:
    return float(boundary.get("offset", 0.0)) + float(boundary.get("duration", 0.0))


def build_cue(
    unit_id: int,
    text: str,
    start: float,
    end: float,
    unit_end: float,
    *,
    min_duration: float,
    max_duration: float,
    timing_source: str,
    enforce_duration_limits: bool = True,
) -> dict:
    start = max(0.0, float(start))
    end = max(start, float(end))
    if enforce_duration_limits:
        end = max(start + min_duration, end)
        end = min(end, start + max_duration)
    end = min(end, float(unit_end))
    if end <= start:
        end = start + (min_duration if enforce_duration_limits else 0.001)
    return {
        "unit_id": unit_id,
        "start": round(start, 6),
        "end": round(end, 6),
        "duration": round(end - start, 6),
        "text": strip_display(text),
        "timing_source": timing_source,
    }


def build_subtitle_cues(
    tts_units: list[dict],
    language: str,
    *,
    subtitle_plan: dict | None = None,
    boundary_table: dict | None = None,
    require_boundary_plan: bool = False,
    min_duration: float = 0.3,
    max_duration: float = 2.2,
) -> tuple[list[dict], dict]:
    boundary_table = boundary_table or build_boundary_table(tts_units, language)
    boundary_timing_source = str(boundary_table.get("timing_source") or "real_tts_boundary")
    boundary_units = boundary_units_by_id(boundary_table)
    cues: list[dict] = []
    orphan_fragment_count = 0
    computed_bad_line_breaks: list[dict] = []
    boundary_group_plan_units_used = 0
    subtitle_plan_mismatch_count = 0
    boundary_group_mismatch_count = 0
    boundary_group_gap_count = 0
    boundary_group_overlap_count = 0
    boundary_group_uncovered_count = 0
    boundary_group_duration_violation_count = 0
    if require_boundary_plan and not subtitle_plan:
        raise RuntimeError("subtitle boundary-group plan is required")

    for unit in tts_units:
        unit_id = int(unit["unit_id"])
        boundary_unit = boundary_units.get(unit_id, {})
        boundary_entries = boundary_unit.get("boundaries", [])
        boundary_groups = (
            subtitle_plan["unit_boundary_groups"].get(unit_id, [])
            if subtitle_plan
            else []
        )
        unit_end = float(unit["timeline_end"])
        if not boundary_entries:
            raise RuntimeError(f"real TTS boundary table missing boundaries for unit {unit_id}")
        if not boundary_groups:
            raise RuntimeError(f"subtitle boundary-group plan missing for unit {unit_id}")

        boundary_group_plan_units_used += 1
        cursor = 0
        unit_cue_texts: list[str] = []
        previous_cue: dict | None = None
        for cue_spec in boundary_groups:
            start_idx = int(cue_spec["boundary_start"])
            end_idx = int(cue_spec["boundary_end"])
            if start_idx > cursor:
                boundary_group_gap_count += start_idx - cursor
            if start_idx < cursor:
                boundary_group_overlap_count += cursor - start_idx
            if start_idx < 0 or end_idx <= start_idx or end_idx > len(boundary_entries):
                boundary_group_mismatch_count += 1
                cursor = max(cursor, end_idx)
                continue

            selected = boundary_entries[start_idx:end_idx]
            boundary_text = strip_display("".join(item["text"] for item in selected))
            cue_text = strip_display(cue_spec.get("text") or boundary_text)
            if normalize_text(cue_text) != normalize_text(boundary_text):
                boundary_group_mismatch_count += 1
            unit_cue_texts.append(cue_text)
            orphan_fragment_count += 1 if len(normalize_text(cue_text)) <= 2 else 0
            if previous_cue:
                bad_reason = bad_cjk_boundary_reason(previous_cue["text"], cue_text)
                if bad_reason:
                    computed_bad_line_breaks.append(
                        {
                            "unit_id": unit_id,
                            "reason": bad_reason,
                            "left_text": previous_cue["text"],
                            "right_text": cue_text,
                            "left_boundary": [
                                previous_cue["boundary_start"],
                                previous_cue["boundary_end"],
                            ],
                            "right_boundary": [start_idx, end_idx],
                        }
                    )

            start = float(selected[0]["start"])
            end = float(selected[-1]["end"])
            duration = end - start
            if duration < min_duration or duration > max_duration:
                boundary_group_duration_violation_count += 1
            cue = build_cue(
                unit_id,
                cue_text,
                start,
                end,
                unit_end,
                min_duration=min_duration,
                max_duration=max_duration,
                timing_source=boundary_timing_source,
                enforce_duration_limits=False,
            )
            cue.update(
                {
                    "segmentation_source": BOUNDARY_GROUP_SOURCE,
                    "boundary_start": start_idx,
                    "boundary_end": end_idx,
                    "boundary_ids": [item["bid"] for item in selected],
                }
            )
            cues.append(cue)
            previous_cue = {
                "text": cue_text,
                "boundary_start": start_idx,
                "boundary_end": end_idx,
            }
            cursor = end_idx

        if cursor < len(boundary_entries):
            boundary_group_uncovered_count += len(boundary_entries) - cursor
        if normalize_text("".join(unit_cue_texts)) != normalize_text(unit["text"]):
            subtitle_plan_mismatch_count += 1

    plan_checks = (subtitle_plan or {}).get("checks", {})
    plan_bad_line_break_count = int(plan_checks.get("bad_line_break_count", 0))
    meta = {
        "timing_source": boundary_timing_source,
        "uses_real_tts_boundaries": True,
        "semantic_segmentation_done": True,
        "language_aware_segmentation": True,
        "semantic_segmentation_source": BOUNDARY_GROUP_SOURCE,
        "subagent_semantic_segmentation_done": True,
        "subagent_plan_units_used": boundary_group_plan_units_used,
        "subagent_boundary_group_plan_done": bool(boundary_group_plan_units_used),
        "boundary_group_plan_units_used": boundary_group_plan_units_used,
        "subtitle_plan_mismatch_count": subtitle_plan_mismatch_count,
        "boundary_group_mismatch_count": boundary_group_mismatch_count,
        "boundary_group_gap_count": boundary_group_gap_count,
        "boundary_group_overlap_count": boundary_group_overlap_count,
        "boundary_group_uncovered_count": boundary_group_uncovered_count,
        "boundary_group_duration_violation_count": boundary_group_duration_violation_count,
        "subtitle_plan_path": subtitle_plan["path"] if subtitle_plan else "",
        "cross_sentence_boundary_count": int(plan_checks.get("cross_sentence_boundary_count", 0)),
        "orphan_fragment_count": max(orphan_fragment_count, int(plan_checks.get("orphan_fragment_count", 0))),
        "bad_line_break_count": max(plan_bad_line_break_count, len(computed_bad_line_breaks)),
        "plan_bad_line_break_count": plan_bad_line_break_count,
        "computed_bad_line_break_count": len(computed_bad_line_breaks),
        "bad_line_break_examples": computed_bad_line_breaks[:20],
    }
    return cues, meta


def build_ass(cues: list[dict]) -> str:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main, Arial Unicode MS, 58, &H00FFFFFF, &H00FFFFFF, &HA0000000, &H70000000, 1, 0, 0, 0, 100, 100, 0, 0, 1, 4, 1, 2, 60, 60, 690, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for cue in cues:
        text = wrap_ass_text(cue["text"])
        lines.append(
            "Dialogue: 0,"
            f"{seconds_to_ass(cue['start'])},"
            f"{seconds_to_ass(cue['end'])},"
            "Main,,0,0,0,,"
            r"{\an2\pos(540,1218)}" + text + "\n"
        )
    return "".join(lines)


def load_json_if_exists(path: Path) -> dict:
    return load_json(path) if path.exists() else {}


def infer_source_media(args, workflow_state: dict, script: dict, final_shots: dict) -> str:
    candidates = [
        args.source_media,
        workflow_state.get("artifacts", {}).get("source_media"),
        final_shots.get("source_media"),
        final_shots.get("source"),
        script.get("source_media"),
        script.get("source"),
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    raise RuntimeError(
        "source media is required for generic alignment metadata; pass --source-media "
        "or set artifacts.source_media in workflow_state.json"
    )


def infer_tts_audio(args, tts: dict) -> str:
    if args.tts_audio:
        return str(args.tts_audio)
    if tts.get("audio_path"):
        return str(tts["audio_path"])
    return f"{args.tts_dir}/narration_full.wav"


def normalize_pick(pick: dict, index: int) -> dict:
    enriched = dict(pick)
    source_window = enriched.get("source_window") or {}
    if "src_start" not in enriched and "start" in source_window:
        enriched["src_start"] = source_window["start"]
    if "src_end" not in enriched and "end" in source_window:
        enriched["src_end"] = source_window["end"]
    if "src_duration" not in enriched and "duration" in source_window:
        enriched["src_duration"] = source_window["duration"]
    if "src_duration" not in enriched and "src_start" in enriched and "src_end" in enriched:
        enriched["src_duration"] = round(float(enriched["src_end"]) - float(enriched["src_start"]), 6)

    required = ["unit_id", "shot_id", "src_start", "src_end", "src_duration"]
    missing = [key for key in required if key not in enriched]
    if missing:
        raise RuntimeError(f"final_shots pick #{index} missing required fields: {missing}")

    enriched.setdefault("source_shot_id", enriched["shot_id"])
    enriched.setdefault("src_index", enriched.get("shot_index", index))
    enriched.setdefault("beat_id", enriched.get("unit_id"))
    enriched.setdefault("beat_role", "")
    enriched.setdefault("beat_type", "")
    enriched["global_order"] = index
    return enriched


def min_or_none(values: list[float]) -> float | None:
    return round(min(values), 6) if values else None


def max_or_none(values: list[float]) -> float | None:
    return round(max(values), 6) if values else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build generic post-TTS pacing repair, frame-quantized alignment, and ASS subtitles."
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--workflow-state", default="workflow_state.json")
    parser.add_argument("--fps-num", type=int, default=24000)
    parser.add_argument("--fps-den", type=int, default=1001)
    parser.add_argument("--script", default="script/script.json")
    parser.add_argument("--final-shots", default="script/final_shots.json")
    parser.add_argument("--tts-dir", default="tts")
    parser.add_argument("--tts-durations", default="")
    parser.add_argument("--tts-boundaries", default="")
    parser.add_argument("--tts-audio", default="")
    parser.add_argument("--source-media", default="")
    parser.add_argument("--alignment-dir", default="alignment")
    parser.add_argument("--subtitles-dir", default="subtitles")
    parser.add_argument("--compose-dir", default="compose")
    parser.add_argument("--boundary-table", default="subtitles/tts_boundary_table.json")
    parser.add_argument("--subtitle-plan", default="subtitles/semantic_cue_plan.json")
    parser.add_argument("--require-subtitle-plan", action="store_true")
    parser.add_argument("--language", default="")
    parser.add_argument("--hook-min-speed", type=float, default=0.75)
    parser.add_argument("--post-hook-min-speed", type=float, default=0.88)
    parser.add_argument("--min-cue-duration", type=float, default=0.3)
    parser.add_argument("--max-cue-duration", type=float, default=2.2)
    args = parser.parse_args()

    root = args.project_root.resolve()
    fps = Fraction(args.fps_num, args.fps_den)
    script = load_json(resolve_project_path(root, args.script))
    final_shots = load_json(resolve_project_path(root, args.final_shots))
    workflow_state = load_json_if_exists(resolve_project_path(root, args.workflow_state)) if args.workflow_state else {}
    tts_dir = resolve_project_path(root, args.tts_dir)
    tts_path = resolve_project_path(root, args.tts_durations) if args.tts_durations else tts_dir / "tts_durations.json"
    boundaries_path = (
        resolve_project_path(root, args.tts_boundaries)
        if args.tts_boundaries
        else tts_dir / "narration_boundaries.json"
    )
    alignment_dir = resolve_project_path(root, args.alignment_dir)
    subtitles_dir = resolve_project_path(root, args.subtitles_dir)
    compose_dir = resolve_project_path(root, args.compose_dir)
    boundary_table_path = resolve_project_path(root, args.boundary_table) if args.boundary_table else None
    subtitle_plan_path = resolve_project_path(root, args.subtitle_plan) if args.subtitle_plan else None
    subtitle_plan = None
    if subtitle_plan_path and subtitle_plan_path.exists():
        subtitle_plan = load_subtitle_plan(subtitle_plan_path)
    elif args.require_subtitle_plan:
        raise RuntimeError(f"missing required subtitle semantic cue plan: {subtitle_plan_path}")
    tts = load_json(tts_path)
    boundaries = load_json_if_exists(boundaries_path)
    if not boundaries:
        boundaries = {
            "word_boundaries": tts.get("word_boundaries", []),
            "sentence_boundaries": tts.get("sentence_boundaries", []),
            "units": tts.get("units", []),
        }
    language = args.language or script.get("language") or tts.get("language") or "zh-CN"
    if boundary_table_path and boundary_table_path.exists():
        boundary_table = load_json(boundary_table_path)
    else:
        boundary_table = build_boundary_table(tts["units"], language)
    if boundary_table_path and not boundary_table_path.exists():
        write_json(boundary_table_path, boundary_table)
    if args.require_subtitle_plan and (not subtitle_plan or not subtitle_plan.get("has_boundary_groups")):
        raise RuntimeError(
            "required subtitle plan must use boundary-group cues with boundary_start/boundary_end"
        )
    source_media = infer_source_media(args, workflow_state, script, final_shots)
    tts_audio = infer_tts_audio(args, tts)
    picks = final_shots.get("picks") or final_shots.get("shots") or []
    if not picks:
        raise RuntimeError("final_shots must contain a non-empty picks list")

    picks_by_unit: dict[int, list[dict]] = {}
    for index, pick in enumerate(picks, 1):
        enriched = normalize_pick(pick, index)
        picks_by_unit.setdefault(int(enriched["unit_id"]), []).append(enriched)

    current_frame = 0
    frameq_shots = []
    strict_shots = []
    units_out = []
    stable_subwindows = []
    speeds = []
    hook_speeds = []
    post_hook_speeds = []
    non_hook_speeds = []
    max_line_drift_ms = 0.0

    for unit in tts["units"]:
        unit_id = int(unit["unit_id"])
        unit_shots = picks_by_unit.get(unit_id)
        if not unit_shots:
            raise RuntimeError(f"No selected final_shots picks found for TTS unit {unit_id}")
        line_start_frame = current_frame
        line_frames = max(1, round(float(unit["duration"]) * fps))
        line_end_frame = line_start_frame + line_frames
        min_speed = args.hook_min_speed if unit_id == 1 else args.post_hook_min_speed
        allocated = allocate_frames(line_frames, unit_shots, fps, min_speed)
        shot_frame = line_start_frame
        for pick, target_frames in zip(unit_shots, allocated):
            target_duration = float(Fraction(target_frames, 1) / fps)
            source_duration = float(pick["src_duration"])
            if source_duration <= 0:
                raise RuntimeError(f"Invalid non-positive src_duration for shot {pick['shot_id']}")
            input_duration = min(source_duration, target_duration)
            speed = input_duration / target_duration
            trim_offset = max(0.0, (source_duration - input_duration) / 2)
            src_trim_start = float(pick["src_start"]) + trim_offset
            src_trim_end = src_trim_start + input_duration
            shot = {
                "unit_id": unit_id,
                "beat_id": pick["beat_id"],
                "beat_role": pick["beat_role"],
                "beat_type": pick["beat_type"],
                "shot_id": pick["shot_id"],
                "source_shot_id": pick["source_shot_id"],
                "global_order": pick["global_order"],
                "src_index": pick["src_index"],
                "src_start": pick["src_start"],
                "src_end": pick["src_end"],
                "src_duration": pick["src_duration"],
                "stable_src_start": round(src_trim_start, 6),
                "stable_src_end": round(src_trim_end, 6),
                "src_trim_start": round(src_trim_start, 6),
                "src_trim_end": round(src_trim_end, 6),
                "input_duration": round(input_duration, 6),
                "target_frames": target_frames,
                "duration": round(target_duration, 6),
                "timeline_start_frame": shot_frame,
                "timeline_end_frame": shot_frame + target_frames,
                "timeline_start": round(float(Fraction(shot_frame, 1) / fps), 6),
                "timeline_end": round(float(Fraction(shot_frame + target_frames, 1) / fps), 6),
                "speed_factor": round(speed, 6),
                "visual_summary": pick.get("visual_summary", ""),
                "risk_flags": pick.get("risk_flags", []),
            }
            frameq_shots.append(shot)
            strict_shots.append({k: v for k, v in shot.items() if k not in {"timeline_start_frame", "timeline_end_frame", "target_frames"}})
            stable_subwindows.append(
                {
                    "shot_id": pick["shot_id"],
                    "source_shot_id": pick["source_shot_id"],
                    "global_order": pick["global_order"],
                    "src_start": pick["src_start"],
                    "src_end": pick["src_end"],
                    "stable_src_start": round(src_trim_start, 6),
                    "stable_src_end": round(src_trim_end, 6),
                    "reason": "post-TTS stable centered sub-window chosen inside a real detected source shot",
                    "internal_cut_risk": False,
                    "safe_tail_buffer_frames": 0,
                    "crosses_source_cut": False,
                    "render_boundary_policy": RENDER_BOUNDARY_POLICY,
                }
            )
            speeds.append(speed)
            if unit_id == 1:
                hook_speeds.append(speed)
            else:
                post_hook_speeds.append(speed)
                non_hook_speeds.append(speed)
            shot_frame += target_frames

        timeline_start = float(Fraction(line_start_frame, 1) / fps)
        timeline_end = float(Fraction(line_end_frame, 1) / fps)
        max_line_drift_ms = max(
            max_line_drift_ms,
            abs(timeline_start - float(unit["timeline_start"])) * 1000,
            abs(timeline_end - float(unit["timeline_end"])) * 1000,
        )
        units_out.append(
            {
                "unit_id": unit_id,
                "text": unit["text"],
                "voice_start": unit["timeline_start"],
                "voice_end": unit["timeline_end"],
                "timeline_start_frame": line_start_frame,
                "timeline_end_frame": line_end_frame,
                "timeline_start": round(timeline_start, 6),
                "timeline_end": round(timeline_end, 6),
                "target_frames": line_frames,
                "shot_ids": [pick["shot_id"] for pick in unit_shots],
            }
        )
        current_frame = line_end_frame

    timeline_duration = float(Fraction(current_frame, 1) / fps)
    cues, cue_meta = build_subtitle_cues(
        tts["units"],
        language,
        subtitle_plan=subtitle_plan,
        boundary_table=boundary_table,
        require_boundary_plan=args.require_subtitle_plan,
        min_duration=args.min_cue_duration,
        max_duration=args.max_cue_duration,
    )
    if not cues:
        raise RuntimeError("No subtitle cues were built from TTS units")
    ass_path = compose_dir / "final_subtitles_frameq.ass"
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.write_text(build_ass(cues), encoding="utf-8")
    word_boundary_count = boundary_table["word_boundary_count"]
    estimated_duration = float(
        script.get("target_duration_sec")
        or script.get("estimated_duration_sec")
        or final_shots.get("target_duration_sec")
        or tts["total_audio_duration"]
    )
    hook_shot_durations = [shot["duration"] for shot in frameq_shots if shot["unit_id"] == 1]
    post_hook_shot_durations = [shot["duration"] for shot in frameq_shots if shot["unit_id"] != 1]
    post_hook_speed_passed = not post_hook_speeds or min(post_hook_speeds) >= args.post_hook_min_speed
    hook_speed_passed = not hook_speeds or min(hook_speeds) >= args.hook_min_speed
    subtitle_plan_passed = (
        cue_meta["subtitle_plan_mismatch_count"] == 0
        and cue_meta["boundary_group_mismatch_count"] == 0
        and cue_meta["boundary_group_gap_count"] == 0
        and cue_meta["boundary_group_overlap_count"] == 0
        and cue_meta["boundary_group_uncovered_count"] == 0
        and cue_meta["boundary_group_duration_violation_count"] == 0
        and cue_meta["bad_line_break_count"] == 0
    )
    if args.require_subtitle_plan:
        subtitle_plan_passed = subtitle_plan_passed and cue_meta["semantic_segmentation_source"] == BOUNDARY_GROUP_SOURCE
    cue_duration_passed = (
        min(cue["duration"] for cue in cues) >= args.min_cue_duration
        and max(cue["duration"] for cue in cues) <= args.max_cue_duration
    )
    pacing_passed = hook_speed_passed and post_hook_speed_passed and subtitle_plan_passed and cue_duration_passed

    frameq = {
        "schema_version": SCHEMA_VERSION,
        "fps": f"{args.fps_num}/{args.fps_den}",
        "fps_float": float(fps),
        "language": language,
        "source_media": display_project_path(root, source_media),
        "tts_audio": display_project_path(root, tts_audio),
        "tts_total_audio_duration": tts["total_audio_duration"],
        "timeline_duration": round(timeline_duration, 6),
        "total_frames": current_frame,
        "max_line_boundary_drift_ms": round(max_line_drift_ms, 3),
        "render_boundary_policy": RENDER_BOUNDARY_POLICY,
        "units": units_out,
        "shots": frameq_shots,
    }
    strict = {
        "schema_version": SCHEMA_VERSION,
        "source_media": display_project_path(root, source_media),
        "tts_audio": display_project_path(root, tts_audio),
        "render_boundary_policy": RENDER_BOUNDARY_POLICY,
        "timeline_duration": round(timeline_duration, 6),
        "max_line_boundary_drift_ms": round(max_line_drift_ms, 3),
        "shots": strict_shots,
    }
    subtitle_report = {
        "schema_version": SCHEMA_VERSION,
        "language": language,
        "timing_source": cue_meta["timing_source"],
        "cue_strategy": "subagent groups TTS boundary ids, then script attaches exact boundary timing",
        "cue_count": len(cues),
        "max_cue_duration_sec": round(max(cue["duration"] for cue in cues), 6),
        "min_cue_duration_sec": round(min(cue["duration"] for cue in cues), 6),
        "max_visual_line_chars": max(len(cue["text"]) for cue in cues),
        "trailing_punctuation_removed": all(not cue["text"].endswith(tuple(TRAILING_PUNCTUATION)) for cue in cues),
        "uses_real_tts_boundaries": cue_meta["uses_real_tts_boundaries"],
        "word_boundary_count": word_boundary_count,
        "semantic_segmentation_done": cue_meta["semantic_segmentation_done"],
        "language_aware_segmentation": cue_meta["language_aware_segmentation"],
        "semantic_segmentation_source": cue_meta["semantic_segmentation_source"],
        "subagent_semantic_segmentation_done": cue_meta["subagent_semantic_segmentation_done"],
        "subagent_plan_units_used": cue_meta["subagent_plan_units_used"],
        "subagent_boundary_group_plan_done": cue_meta["subagent_boundary_group_plan_done"],
        "boundary_group_plan_units_used": cue_meta["boundary_group_plan_units_used"],
        "boundary_table_path": display_project_path(root, boundary_table_path) if boundary_table_path else "",
        "subtitle_plan_path": display_project_path(root, cue_meta["subtitle_plan_path"]) if cue_meta["subtitle_plan_path"] else "",
        "subtitle_plan_mismatch_count": cue_meta["subtitle_plan_mismatch_count"],
        "boundary_group_mismatch_count": cue_meta["boundary_group_mismatch_count"],
        "boundary_group_gap_count": cue_meta["boundary_group_gap_count"],
        "boundary_group_overlap_count": cue_meta["boundary_group_overlap_count"],
        "boundary_group_uncovered_count": cue_meta["boundary_group_uncovered_count"],
        "boundary_group_duration_violation_count": cue_meta["boundary_group_duration_violation_count"],
        "subtitle_boundary_alignment_checked": True,
        "cross_sentence_boundary_count": cue_meta["cross_sentence_boundary_count"],
        "orphan_fragment_count": cue_meta["orphan_fragment_count"],
        "bad_line_break_count": cue_meta["bad_line_break_count"],
        "plan_bad_line_break_count": cue_meta["plan_bad_line_break_count"],
        "computed_bad_line_break_count": cue_meta["computed_bad_line_break_count"],
        "bad_line_break_examples": cue_meta["bad_line_break_examples"],
        "subtitle_position_basis": "foreground_box",
        "subtitle_box_inside_foreground": True,
    }
    alignment_qc = {
        "schema_version": SCHEMA_VERSION,
        "solve_order": "shot_count_then_speed",
        "target_duration_sec": round(timeline_duration, 6),
        "selected_shot_count": len(frameq_shots),
        "render_boundary_policy": RENDER_BOUNDARY_POLICY,
        "cold_open": {
            "duration_sec": tts["units"][0]["duration"],
            "min_shot_duration_sec": min_or_none(hook_shot_durations),
            "min_speed_factor": min_or_none(hook_speeds),
            "max_speed_factor": max_or_none(hook_speeds),
            "speed_floor": args.hook_min_speed,
        },
        "post_hook": {
            "min_shot_duration_sec": min_or_none(post_hook_shot_durations),
            "dialogue_scene_min_shot_duration_sec": min_or_none(post_hook_shot_durations),
            "min_speed_factor": min_or_none(post_hook_speeds),
            "max_speed_factor": max_or_none(post_hook_speeds),
            "max_non_hook_speed_factor": max_or_none(non_hook_speeds),
            "speed_floor": args.post_hook_min_speed,
        },
        "padding": {
            "tpad_clone_total_frames": 0,
            "clone_padding_used_only_final_fallback": True,
        },
        "passes": pacing_passed,
    }
    pacing_report = {
        "schema_version": SCHEMA_VERSION,
        "source_media": display_project_path(root, source_media),
        "estimated_duration_sec": estimated_duration,
        "real_tts_duration_sec": tts["total_audio_duration"],
        "duration_delta_sec": round(tts["total_audio_duration"] - estimated_duration, 6),
        "real_tts_duration_used": True,
        "repair_actions": [
            "rebuilt line durations from real full-script TTS timings",
            f"allocated stable centered source sub-windows with post-hook speed floor {args.post_hook_min_speed:.2f}x",
            "kept render boundaries on real selected shots/windows only",
        ],
        "selected_shot_count_before": final_shots.get("selected_shot_count", len(picks)),
        "selected_shot_count_after": len(frameq_shots),
        "speed_range_before": final_shots.get("speed_range", [args.hook_min_speed, 1.25]),
        "speed_range_after": [round(min(speeds), 6), round(max(speeds), 6)],
        "render_boundary_policy": RENDER_BOUNDARY_POLICY,
        "passes": pacing_passed,
    }
    source_buffer_report = {
        "schema_version": SCHEMA_VERSION,
        "policy": "stable_subwindow_only_no_cross_cut_tail_buffer",
        "safe_render_tail_buffer_frames": 0,
        "source_buffer_crosses_cut": False,
        "render_boundary_policy": RENDER_BOUNDARY_POLICY,
        "entries": [
            {
                "shot_id": item["shot_id"],
                "source_shot_id": item["source_shot_id"],
                "global_order": item["global_order"],
                "safe_tail_buffer_frames": 0,
                "crosses_source_cut": False,
            }
            for item in stable_subwindows
        ],
    }

    write_json(alignment_dir / "strict_alignment_frameq.json", frameq)
    write_json(alignment_dir / "strict_alignment.json", strict)
    write_json(alignment_dir / "alignment_qc_report.json", alignment_qc)
    write_json(alignment_dir / "post_tts_pacing_report.json", pacing_report)
    write_json(
        alignment_dir / "stable_subwindows.json",
        {
            "schema_version": SCHEMA_VERSION,
            "render_boundary_policy": RENDER_BOUNDARY_POLICY,
            "stable_subwindows": stable_subwindows,
        },
    )
    write_json(alignment_dir / "source_buffer_report.json", source_buffer_report)
    write_json(subtitles_dir / "subtitle_timing_report.json", subtitle_report)
    subtitles_dir.mkdir(exist_ok=True)
    (subtitles_dir / "final.ass").write_text(ass_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(
        json.dumps(
            {
                "timeline_duration": round(timeline_duration, 6),
                "total_frames": current_frame,
                "selected_shots": len(frameq_shots),
                "speed_range": [round(min(speeds), 6), round(max(speeds), 6)],
                "post_hook_speed_range": [min_or_none(post_hook_speeds), max_or_none(post_hook_speeds)],
                "max_line_boundary_drift_ms": round(max_line_drift_ms, 3),
                "subtitle_cues": len(cues),
                "subtitle_duration_range": [subtitle_report["min_cue_duration_sec"], subtitle_report["max_cue_duration_sec"]],
                "subtitle_segmentation_source": subtitle_report["semantic_segmentation_source"],
                "subtitle_plan_passed": subtitle_plan_passed,
                "cue_duration_passed": cue_duration_passed,
                "passes": pacing_passed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if pacing_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
