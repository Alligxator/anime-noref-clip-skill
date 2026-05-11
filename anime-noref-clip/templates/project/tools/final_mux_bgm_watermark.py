#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path


FONTS_DIR = "/System/Library/Fonts/Supplemental"
FONT_FILE = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


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
    return float(result.stdout.strip())


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_video_filter(subtitles: Path, watermark_text: str) -> str:
    font_file = escape_filter_path(Path(FONT_FILE))
    ass_file = escape_filter_path(subtitles)
    watermark = escape_drawtext(watermark_text)
    return (
        f"ass={ass_file}:fontsdir={FONTS_DIR},"
        "drawtext="
        f"fontfile={font_file}:"
        f"text='{watermark}':"
        "fontsize=42:"
        "fontcolor=white:"
        "alpha='0.10+0.05*sin(2*PI*t/19)':"
        "x='(w-text_w)*(0.05+0.88*(0.5+0.5*sin(t/43)))':"
        "y='(h-text_h)*(0.30+0.25*(0.5+0.5*cos(t/37)))':"
        "shadowcolor=black@0.12:shadowx=1:shadowy=1,"
        "format=yuv420p"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--narration", type=Path, required=True)
    parser.add_argument("--subtitles", type=Path, required=True)
    parser.add_argument("--bgm", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--watermark-text", default="@YourHandle")
    parser.add_argument("--narration-volume", type=float, default=1.0)
    parser.add_argument("--bgm-volume", type=float, default=0.15)
    parser.add_argument("--bgm-atempo", type=float, default=1.0)
    args = parser.parse_args()

    duration = args.duration or probe_duration(args.video)
    fade_duration = min(2.0, max(0.0, duration / 4))
    fade_start = max(0.0, duration - fade_duration)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    bgm_tempo_filter = ""
    if abs(args.bgm_atempo - 1.0) > 1e-6:
        bgm_tempo_filter = f"atempo={args.bgm_atempo:.6f},"
    filter_complex = (
        f"[0:v]{build_video_filter(args.subtitles, args.watermark_text)}[v];"
        f"[1:a]aresample=48000,apad=pad_dur=1,atrim=0:{duration:.6f},"
        f"asetpts=N/SR/TB,volume={args.narration_volume:.4f}[narr];"
        f"[2:a]aresample=48000,{bgm_tempo_filter}atrim=0:{duration:.6f},asetpts=N/SR/TB,"
        f"afade=t=out:st={fade_start:.3f}:d={fade_duration:.3f},"
        f"volume={args.bgm_volume:.4f}[bgm];"
        "[narr][bgm]amix=inputs=2:duration=first:dropout_transition=0,"
        "alimiter=limit=0.95[a]"
    )

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(args.video),
        "-i",
        str(args.narration),
        "-stream_loop",
        "-1",
        "-i",
        str(args.bgm),
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-t",
        f"{duration:.6f}",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        str(args.output),
    ]
    subprocess.run(cmd, check=True)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "duration": round(duration, 6),
                "watermark_text": args.watermark_text,
                "watermark_strategy": "slow dynamic motion, opacity cycles 5%-15%",
                "bgm": str(args.bgm),
                "bgm_volume": args.bgm_volume,
                "bgm_atempo": args.bgm_atempo,
                "narration_volume": args.narration_volume,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
