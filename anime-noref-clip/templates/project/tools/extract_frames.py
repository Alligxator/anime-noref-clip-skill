#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import cv2


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def target_entries(shots_payload: dict, project_root: Path) -> list[dict]:
    entries: list[dict] = []
    for shot in shots_payload["shots"]:
        manifest = shot.get("frame_manifest")
        if not manifest:
            manifest = [
                {"role": key, "time": shot["frame_times"][key], "path": shot["frames"][key], "analysis_only": False}
                for key in ("first", "mid", "last")
            ] + shot.get("sample_frames", [])
        for item in manifest:
            entries.append(
                {
                    "shot_id": shot["shot_id"],
                    "role": item.get("role") or item.get("key"),
                    "time": float(item["time"]),
                    "path": project_root / item["path"],
                    "relative_path": item["path"],
                    "analysis_only": bool(item.get("analysis_only", False)),
                }
            )
    return entries


def verify_paths(entries: list[dict]) -> list[dict]:
    missing = []
    for entry in entries:
        path = entry["path"]
        if not path.exists() or path.stat().st_size <= 0:
            missing.append(entry)
    return missing


def ffmpeg_backfill(video: Path, entries: list[dict], width: int | None) -> int:
    saved = 0
    for entry in entries:
        output = entry["path"]
        output.parent.mkdir(parents=True, exist_ok=True)
        vf = []
        if width:
            vf = ["-vf", f"scale={width}:-2"]
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{entry['time']:.6f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            *vf,
            "-q:v",
            "3",
            str(output),
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
            saved += 1
    return saved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--shots", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--out-report", type=Path, required=True)
    parser.add_argument("--no-ffmpeg-backfill", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    shots_payload = load_json(args.shots)
    entries = target_entries(shots_payload, project_root)
    for entry in entries:
        entry["path"].parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {args.video}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count_est = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    targets_by_index: dict[int, list[dict]] = {}
    max_index = max(0, frame_count_est - 1)
    for entry in entries:
        frame_index = int(round(entry["time"] * fps)) if fps else 0
        frame_index = max(0, min(max_index, frame_index))
        targets_by_index.setdefault(frame_index, []).append(entry)

    opencv_saved = 0
    sorted_indices = sorted(targets_by_index)
    cursor = 0
    next_target = sorted_indices[cursor] if sorted_indices else None
    frame_index = 0
    while next_target is not None:
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        if frame_index == next_target:
            height, width = frame.shape[:2]
            if args.width and width > args.width:
                new_height = int(round(height * args.width / width))
                frame = cv2.resize(frame, (args.width, new_height), interpolation=cv2.INTER_AREA)
            for entry in targets_by_index[next_target]:
                cv2.imwrite(str(entry["path"]), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
                if entry["path"].exists() and entry["path"].stat().st_size > 0:
                    opencv_saved += 1
            cursor += 1
            next_target = sorted_indices[cursor] if cursor < len(sorted_indices) else None
        frame_index += 1
    cap.release()

    missing_after_opencv = verify_paths(entries)
    ffmpeg_saved = 0
    if missing_after_opencv and not args.no_ffmpeg_backfill:
        ffmpeg_saved = ffmpeg_backfill(args.video, missing_after_opencv, args.width)
    missing_after_ffmpeg = verify_paths(entries)

    expected_images = len(entries)
    saved_images = expected_images - len(missing_after_ffmpeg)
    report = {
        "schema_version": "anime-noref-clip.frame_extract.v1.4.7",
        "method": "opencv_batch_then_ffmpeg_timestamp_backfill",
        "video": str(args.video),
        "shots": str(args.shots),
        "fps": fps,
        "frame_count_est": frame_count_est,
        "shot_count": len(shots_payload["shots"]),
        "target_frame_indices": len(targets_by_index),
        "expected_images": expected_images,
        "target_images": expected_images,
        "opencv_saved_images": opencv_saved,
        "missing_after_opencv_count": len(missing_after_opencv),
        "ffmpeg_backfill_images": ffmpeg_saved,
        "saved_images": saved_images,
        "missing_images": [entry["relative_path"] for entry in missing_after_ffmpeg],
        "missing_count": len(missing_after_ffmpeg),
        "width": args.width,
        "passes": saved_images == expected_images and not missing_after_ffmpeg,
    }
    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passes"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
