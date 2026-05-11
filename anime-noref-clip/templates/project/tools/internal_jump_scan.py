#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--alignment", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.42)
    parser.add_argument("--boundary-tolerance", type=int, default=2)
    parser.add_argument("--scale-width", type=int, default=160)
    args = parser.parse_args()

    alignment = load_json(args.alignment)
    planned_boundaries = {
        int(shot["timeline_end_frame"])
        for shot in alignment["shots"][:-1]
    }
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    prev = None
    frame_index = 0
    flagged = []
    top_events = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        if args.scale_width and w > args.scale_width:
            new_h = max(1, round(h * args.scale_width / w))
            gray = cv2.resize(gray, (args.scale_width, new_h), interpolation=cv2.INTER_AREA)
        if prev is not None:
            diff = float(cv2.absdiff(prev, gray).mean()) / 255.0
            is_boundary = any(abs(frame_index - boundary) <= args.boundary_tolerance for boundary in planned_boundaries)
            event = {
                "frame": frame_index,
                "time": round(frame_index / fps, 6) if fps else None,
                "diff": round(diff, 6),
                "planned_boundary": is_boundary,
            }
            if diff >= args.threshold and not is_boundary:
                flagged.append(event)
            top_events.append(event)
        prev = gray
        frame_index += 1
    cap.release()
    top_events = sorted(top_events, key=lambda item: item["diff"], reverse=True)[:20]
    report = {
        "method": "frame_diff_scan_excluding_planned_boundaries",
        "diff_threshold": args.threshold,
        "planned_boundary_tolerance_frames": args.boundary_tolerance,
        "video": str(args.video),
        "fps": fps,
        "frames_scanned": frame_index,
        "planned_boundary_count": len(planned_boundaries),
        "internal_jump_count": len(flagged),
        "flagged_events": flagged,
        "top_diff_events": top_events,
        "passes": len(flagged) == 0,
    }
    write_json(args.out, report)
    print(json.dumps({"passes": report["passes"], "internal_jump_count": len(flagged), "frames_scanned": frame_index}, ensure_ascii=False, indent=2))
    return 0 if report["passes"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
