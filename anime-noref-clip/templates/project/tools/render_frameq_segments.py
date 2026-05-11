#!/usr/bin/env python3
import argparse
import json
import subprocess
from fractions import Fraction
from pathlib import Path


def run(cmd):
    subprocess.run(cmd, check=True)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def probe_segment(path: Path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate,nb_read_frames,duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["streams"][0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--alignment", default="alignment/strict_alignment_frameq.json")
    parser.add_argument("--source", required=True, help="source media path, relative to project root or absolute")
    parser.add_argument("--segments-dir", default="compose/segments_frameq")
    parser.add_argument("--concat-list", default="compose/video_concat_frameq.txt")
    parser.add_argument("--output", default="compose/video_no_subs_frameq.mp4")
    parser.add_argument("--report", default="alignment/timing_drift_report.json")
    parser.add_argument("--crf", default="18")
    parser.add_argument("--preset", default="medium")
    parser.add_argument("--canvas-width", type=int, default=1080)
    parser.add_argument("--canvas-height", type=int, default=1920)
    args = parser.parse_args()

    root = args.project_root
    alignment = load_json(root / args.alignment)
    source_arg = Path(args.source)
    source = source_arg if source_arg.is_absolute() else root / source_arg
    segments_dir = root / args.segments_dir
    segments_dir.mkdir(parents=True, exist_ok=True)
    fps = alignment["fps"]

    segment_reports = []
    concat_lines = []
    for index, shot in enumerate(alignment["shots"], start=1):
        segment_path = segments_dir / f"{index:04d}_{shot['shot_id']}.mp4"
        target_frames = int(shot["target_frames"])
        speed_factor = float(shot["speed_factor"])
        input_duration = float(shot["input_duration"])
        vf = (
            f"setpts=(PTS-STARTPTS)/{speed_factor:.8f},"
            "split=2[bg][fg];"
            f"[bg]scale={args.canvas_width}:{args.canvas_height}:force_original_aspect_ratio=increase,"
            f"crop={args.canvas_width}:{args.canvas_height},"
            "gblur=sigma=28:steps=2,"
            "eq=brightness=-0.04:saturation=0.92[bg];"
            f"[fg]scale={args.canvas_width}:-2[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
            "setsar=1,"
            f"fps={fps},"
            f"trim=end_frame={target_frames},"
            "setpts=PTS-STARTPTS,"
            "format=yuv420p"
        )
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{float(shot['src_trim_start']):.6f}",
            "-t",
            f"{input_duration:.6f}",
            "-i",
            str(source),
            "-an",
            "-vf",
            vf,
            "-frames:v",
            str(target_frames),
            "-c:v",
            "libx264",
            "-preset",
            args.preset,
            "-crf",
            args.crf,
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(segment_path),
        ]
        run(cmd)
        probe = probe_segment(segment_path)
        actual_frames = int(probe.get("nb_read_frames") or 0)
        report = {
            "index": index,
            "shot_id": shot["shot_id"],
            "path": str(segment_path),
            "target_frames": target_frames,
            "actual_frames": actual_frames,
            "frame_delta": actual_frames - target_frames,
            "duration": float(probe.get("duration", 0.0)),
            "width": int(probe["width"]),
            "height": int(probe["height"]),
            "avg_frame_rate": probe["avg_frame_rate"],
            "speed_factor": shot["speed_factor"],
        }
        segment_reports.append(report)
        concat_lines.append(f"file '{segment_path.resolve()}'\n")
        print(json.dumps({
            "segment": index,
            "shot_id": shot["shot_id"],
            "frames": f"{actual_frames}/{target_frames}",
        }, ensure_ascii=False), flush=True)

    concat_list = root / args.concat_list
    concat_list.parent.mkdir(parents=True, exist_ok=True)
    concat_list.write_text("".join(concat_lines), encoding="utf-8")

    output = root / args.output
    run([
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-c",
        "copy",
        str(output),
    ])
    output_probe = probe_segment(output)
    fps_fraction = Fraction(*map(int, alignment["fps"].split("/")))
    expected_frames = int(alignment["total_frames"])
    output_frames = int(output_probe.get("nb_read_frames") or 0)
    total_drift_ms = abs((output_frames - expected_frames) / float(fps_fraction) * 1000)
    report = {
        "pass": all(item["frame_delta"] == 0 for item in segment_reports) and output_frames == expected_frames,
        "segment_count": len(segment_reports),
        "concat_list": str(concat_list),
        "concat_paths_absolute": all(line.startswith("file '/") for line in concat_lines),
        "output": str(output),
        "expected_frames": expected_frames,
        "actual_output_frames": output_frames,
        "total_timeline_drift_ms": round(total_drift_ms, 3),
        "max_line_boundary_drift_ms": alignment["max_line_boundary_drift_ms"],
        "segments": segment_reports,
    }
    write_json(root / args.report, report)
    print(json.dumps({
        "pass": report["pass"],
        "output": str(output),
        "expected_frames": expected_frames,
        "actual_output_frames": output_frames,
        "total_timeline_drift_ms": report["total_timeline_drift_ms"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
