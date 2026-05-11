#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


RENDER_BOUNDARY_POLICY = "real_scene_cut_only_no_duration_based_render_splits"


def read_scene_times(path: Path) -> tuple[list[float], dict[float, float]]:
    times: list[float] = []
    scores: dict[float, float] = {}
    last_time: float | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(r"pts_time:([0-9.]+)", line)
        if match:
            last_time = float(match.group(1))
            times.append(last_time)
            continue
        match = re.search(r"lavfi\.scene_score=([0-9.]+)", line)
        if match and last_time is not None:
            scores[last_time] = float(match.group(1))
    return times, scores


def filtered_cuts(times: list[float], min_gap: float, duration: float) -> list[float]:
    cuts: list[float] = []
    for time in sorted(times):
        if time <= 0 or time >= duration:
            continue
        if cuts and time - cuts[-1] < min_gap:
            continue
        cuts.append(time)
    return cuts


def representative_times(start: float, end: float) -> dict[str, float]:
    mid = (start + end) / 2
    return {
        "first": round(min(end - 0.05, start + 0.12), 3),
        "mid": round(mid, 3),
        "last": round(max(start + 0.05, end - 0.12), 3),
    }


def sample_times(
    start: float,
    end: float,
    *,
    threshold: float,
    interval: float,
    max_total_frames: int,
) -> list[float]:
    duration = end - start
    if duration <= threshold:
        return []
    extra_count = max(1, int(math.floor(duration / interval)))
    extra_count = min(max(0, max_total_frames - 3), extra_count)
    if extra_count <= 0:
        return []
    step = duration / (extra_count + 1)
    base_times = set(round(value, 3) for value in representative_times(start, end).values())
    samples: list[float] = []
    for index in range(1, extra_count + 1):
        time = round(start + step * index, 3)
        if time in base_times:
            continue
        time = round(min(end - 0.08, max(start + 0.08, time)), 3)
        samples.append(time)
    return samples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-file", type=Path, required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-gap", type=float, default=0.45)
    parser.add_argument("--min-duration", type=float, default=0.25)
    parser.add_argument("--long-shot-threshold", type=float, default=8.0)
    parser.add_argument("--sample-interval", type=float, default=3.5)
    parser.add_argument("--max-total-frames-per-shot", type=int, default=12)
    args = parser.parse_args()

    times, scores = read_scene_times(args.scene_file)
    cuts = filtered_cuts(times, args.min_gap, args.duration)
    boundaries = [0.0] + cuts + [args.duration]

    shots = []
    long_shot_count = 0
    sample_frame_count = 0
    for start, end in zip(boundaries, boundaries[1:]):
        if end - start < args.min_duration:
            continue
        shot_id = f"shot_{len(shots):04d}"
        duration = round(end - start, 3)
        frame_times = representative_times(start, end)
        frames = {
            key: f"shots/frames/{shot_id}_{key}.jpg"
            for key in ("first", "mid", "last")
        }
        samples = sample_times(
            start,
            end,
            threshold=args.long_shot_threshold,
            interval=args.sample_interval,
            max_total_frames=args.max_total_frames_per_shot,
        )
        if samples:
            long_shot_count += 1
        sample_frames = [
            {
                "role": f"sample_{index:02d}",
                "time": time,
                "path": f"shots/frames/{shot_id}_sample_{index:02d}.jpg",
                "analysis_only": True,
            }
            for index, time in enumerate(samples, start=1)
        ]
        sample_frame_count += len(sample_frames)
        frame_manifest = [
            {"role": key, "time": frame_times[key], "path": frames[key], "analysis_only": False}
            for key in ("first", "mid", "last")
        ] + sample_frames
        shots.append(
            {
                "shot_id": shot_id,
                "src_index": len(shots),
                "cut_source": "scene",
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": duration,
                "scene_score": scores.get(start),
                "render_boundary_policy": RENDER_BOUNDARY_POLICY,
                "frame_times": frame_times,
                "frames": frames,
                "sample_frames": sample_frames,
                "frame_manifest": frame_manifest,
            }
        )

    payload = {
        "schema_version": "anime-noref-clip.shots.v1.4.7",
        "source_scene_file": str(args.scene_file),
        "duration": args.duration,
        "min_gap": args.min_gap,
        "min_duration": args.min_duration,
        "long_shot_threshold": args.long_shot_threshold,
        "sample_interval": args.sample_interval,
        "max_total_frames_per_shot": args.max_total_frames_per_shot,
        "render_boundary_policy": RENDER_BOUNDARY_POLICY,
        "raw_cut_count": len(times),
        "filtered_cut_count": len(cuts),
        "shot_count": len(shots),
        "long_shot_count": long_shot_count,
        "sample_frame_count": sample_frame_count,
        "render_level_duration_splits_absent": True,
        "shots": shots,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    durations = [shot["duration"] for shot in shots]
    print(
        json.dumps(
            {
                "raw_cuts": len(times),
                "filtered_cuts": len(cuts),
                "shots": len(shots),
                "long_shots": long_shot_count,
                "sample_frames": sample_frame_count,
                "min_duration": round(min(durations), 3) if durations else 0,
                "median_duration": round(sorted(durations)[len(durations) // 2], 3) if durations else 0,
                "max_duration": round(max(durations), 3) if durations else 0,
                "render_level_duration_splits_absent": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
