#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


REQUIRED_KEYS = {
    "shot_id",
    "src_index",
    "characters",
    "scene",
    "objects",
    "key_subject",
    "key_action",
    "emotion",
    "visual_summary",
    "story_function",
    "confidence",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalized_list(value):
    out = []
    for item in as_list(value):
        if item is None:
            continue
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out


def overlap_labels(shot, ranges):
    labels = []
    start = float(shot["start"])
    end = float(shot["end"])
    for item in ranges:
        ov = min(end, float(item["end"])) - max(start, float(item["start"]))
        if ov > 0:
            labels.append(item["label"])
    return labels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--tag-dir", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-jsonl", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    root = args.project_root
    tag_dir = args.tag_dir or root / "analysis/visual_tags_gpt55_low"
    out_json = args.out_json or root / "analysis/shot_story_tags.json"
    out_jsonl = args.out_jsonl or root / "analysis/shot_story_tags.jsonl"
    report_path = args.report or root / "analysis/visual_tag_merge_report.json"

    shots_payload = load_json(root / "shots/shots.json")
    shots = shots_payload["shots"]
    shots_by_id = {shot["shot_id"]: shot for shot in shots}
    expected_ids = [shot["shot_id"] for shot in shots]
    exclude_ranges = load_json(root / "analysis/exclude_ranges.json").get("exclude_ranges", [])
    alignment_path = root / "analysis/subtitle_shot_alignment.json"
    beats_path = root / "analysis/story_beats.json"
    alignments = {}
    beat_labels = {}
    if alignment_path.exists():
        align_payload = load_json(alignment_path)
        alignments = {item["shot_id"]: item for item in align_payload.get("shots", [])}
    if beats_path.exists():
        beat_payload = load_json(beats_path)
        beat_labels = {
            beat["beat_id"]: beat["label"]
            for beat in beat_payload.get("story_beats", [])
        }

    rows_by_id = {}
    invalid = []
    duplicates = []
    part_files = sorted(tag_dir.glob("part_*.jsonl"))

    for part in part_files:
        for line_no, line in enumerate(part.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except Exception as exc:
                invalid.append({"file": part.name, "line": line_no, "error": str(exc)})
                continue

            missing_keys = sorted(REQUIRED_KEYS - set(raw))
            shot_id = raw.get("shot_id")
            if missing_keys:
                invalid.append({"file": part.name, "line": line_no, "shot_id": shot_id, "missing_keys": missing_keys})
                continue
            if shot_id not in shots_by_id:
                invalid.append({"file": part.name, "line": line_no, "shot_id": shot_id, "error": "unknown_shot_id"})
                continue
            if shot_id in rows_by_id:
                duplicates.append({"shot_id": shot_id, "first_file": rows_by_id[shot_id]["visual_tag_source"], "duplicate_file": part.name})
                continue

            shot = shots_by_id[shot_id]
            exclude_labels = overlap_labels(shot, exclude_ranges)
            alignment = alignments.get(shot_id, {})
            dialogue = alignment.get("dialogue", [])
            beat_ids = alignment.get("beat_ids", [])
            story_function = normalized_list(raw.get("story_function"))
            for beat_id in beat_ids:
                label = beat_labels.get(beat_id)
                beat_tag = f"beat_{beat_id}:{label}" if label else f"beat_{beat_id}"
                if beat_tag not in story_function:
                    story_function.append(beat_tag)
            if exclude_labels and "op_ed" not in story_function:
                story_function.append("op_ed")
            dialogue_summary = " / ".join(item.get("text", "") for item in dialogue[:3])
            if len(dialogue) > 3:
                dialogue_summary += f" / ...(+{len(dialogue) - 3})"

            row = {
                "shot_id": shot_id,
                "src_index": int(shot["src_index"]),
                "start": shot["start"],
                "end": shot["end"],
                "duration": shot["duration"],
                "frames": shot.get("frames", {}),
                "luma": shot.get("luma", {}),
                "black_or_fade_risk": bool(shot.get("luma", {}).get("black_or_fade_risk", False)),
                "exclude_labels": exclude_labels,
                "characters": normalized_list(raw.get("characters")),
                "scene": str(raw.get("scene", "")).strip(),
                "objects": normalized_list(raw.get("objects")),
                "key_subject": str(raw.get("key_subject", "")).strip(),
                "key_action": str(raw.get("key_action", "")).strip(),
                "emotion": str(raw.get("emotion", "")).strip(),
                "visual_summary": str(raw.get("visual_summary", "")).strip(),
                "dialogue_summary": dialogue_summary,
                "dialogue": dialogue,
                "beat_ids": beat_ids,
                "story_function": story_function,
                "confidence": raw.get("confidence"),
                "visual_tag_source": part.name,
                "visual_tag_method": "gpt-5.5 subagent contact-sheet visual tagging",
                "visual_tag_gate_eligible": True,
            }
            rows_by_id[shot_id] = row

    missing = [shot_id for shot_id in expected_ids if shot_id not in rows_by_id]
    rows = [rows_by_id[shot_id] for shot_id in expected_ids if shot_id in rows_by_id]
    report = {
        "tag_dir": str(tag_dir),
        "part_files": [part.name for part in part_files],
        "expected_shots": len(expected_ids),
        "merged_rows": len(rows),
        "missing_count": len(missing),
        "duplicate_count": len(duplicates),
        "invalid_count": len(invalid),
        "missing": missing,
        "duplicates": duplicates,
        "invalid": invalid,
        "excluded_rows": sum(1 for row in rows if row["exclude_labels"]),
        "rows_with_dialogue": sum(1 for row in rows if row.get("dialogue")),
        "rows_with_beat_ids": sum(1 for row in rows if row.get("beat_ids")),
        "black_or_fade_risk_rows": sum(1 for row in rows if row["black_or_fade_risk"]),
        "gate_passed": not missing and not duplicates and not invalid and len(rows) == len(expected_ids),
        "gate_rule": "Only gpt-5.5 subagent JSONL visual tags may satisfy gpt_visual_tagging_done.",
    }

    payload = {
        "metadata": {
            "source": "gpt-5.5 subagent visual tagging",
            "shot_count": len(rows),
            "source_part_files": report["part_files"],
            "gate_rule": report["gate_rule"],
        },
        "shot_story_tags": rows,
    }

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_jsonl.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not report["gate_passed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
