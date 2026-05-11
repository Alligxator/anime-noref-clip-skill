#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


ASS_TAG_RE = re.compile(r"\{[^}]*\}")
DRAWING_RE = re.compile(r"\\p\d+")


def ass_time_to_seconds(value: str) -> float:
    hours, minutes, rest = value.strip().split(":")
    seconds, centis = rest.split(".")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(centis) / 100


def clean_text(text: str) -> str:
    text = text.replace("\\N", "\n").replace("\\n", "\n").replace("\\h", " ")
    text = ASS_TAG_RE.sub("", text)
    text = DRAWING_RE.sub("", text)
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def parse_ass(path: Path):
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    in_events = False
    format_fields = []
    events = []

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped == "[Events]":
            in_events = True
            continue
        if not in_events:
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            break
        if stripped.startswith("Format:"):
            format_fields = [part.strip() for part in stripped[len("Format:") :].split(",")]
            continue
        if not stripped.startswith("Dialogue:"):
            continue
        if not format_fields:
            continue

        payload = stripped[len("Dialogue:") :].lstrip()
        parts = payload.split(",", len(format_fields) - 1)
        if len(parts) != len(format_fields):
            continue
        row = dict(zip(format_fields, parts))
        text = clean_text(row.get("Text", ""))
        if not text:
            continue
        style = row.get("Style", "")
        style_upper = style.upper()
        effect_lower = row.get("Effect", "").lower()
        event = {
            "index": len(events),
            "start": round(ass_time_to_seconds(row["Start"]), 3),
            "end": round(ass_time_to_seconds(row["End"]), 3),
            "duration": round(ass_time_to_seconds(row["End"]) - ass_time_to_seconds(row["Start"]), 3),
            "style": style,
            "name": row.get("Name", ""),
            "effect": row.get("Effect", ""),
            "text": text,
            "is_song": style_upper.startswith("OP") or style_upper.startswith("ED") or effect_lower == "karaoke",
        }
        events.append(event)
    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ass", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--md", type=Path, required=True)
    args = parser.parse_args()

    events = parse_ass(args.ass)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps({"source": str(args.ass), "events": events}, ensure_ascii=False, indent=2), encoding="utf-8")

    dialogue = [e for e in events if not e["is_song"]]
    songs = [e for e in events if e["is_song"]]
    lines = [
        f"# Subtitle Timeline",
        "",
        f"- Source: `{args.ass}`",
        f"- Dialogue events: {len(dialogue)}",
        f"- Song/karaoke events: {len(songs)}",
        "",
        "## Dialogue",
        "",
    ]
    for e in dialogue:
        lines.append(f"- `{e['start']:07.2f}-{e['end']:07.2f}` {e['text'].replace(chr(10), ' / ')}")
    if songs:
        lines.extend(["", "## Song/Karaoke", ""])
        for e in songs:
            lines.append(f"- `{e['start']:07.2f}-{e['end']:07.2f}` {e['text'].replace(chr(10), ' / ')}")
    args.md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "events": len(events),
        "dialogue_events": len(dialogue),
        "song_events": len(songs),
        "first_dialogue": dialogue[0] if dialogue else None,
        "last_dialogue": dialogue[-1] if dialogue else None,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
