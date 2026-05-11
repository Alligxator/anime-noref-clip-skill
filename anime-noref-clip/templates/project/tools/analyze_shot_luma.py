#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from PIL import Image, ImageStat


def luma(path: Path):
    img = Image.open(path).convert("L")
    stat = ImageStat.Stat(img)
    return {
        "mean": round(stat.mean[0], 3),
        "min": int(stat.extrema[0][0]),
        "max": int(stat.extrema[0][1]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--shots", default="shots/shots.json")
    parser.add_argument("--out", default="analysis/shot_luma_report.json")
    parser.add_argument("--mean-threshold", type=float, default=18.0)
    parser.add_argument("--min-threshold", type=float, default=4.0)
    args = parser.parse_args()

    root = args.project_root
    shots_path = root / args.shots
    data = json.loads(shots_path.read_text(encoding="utf-8"))
    flagged = []
    for shot in data["shots"]:
        lumas = {}
        bad = False
        frame_items = [
            {"role": key, "path": rel}
            for key, rel in shot["frames"].items()
        ]
        frame_items.extend(
            {
                "role": sample.get("role", "sample"),
                "path": sample["path"],
            }
            for sample in shot.get("sample_frames", [])
        )
        for item in frame_items:
            key = item["role"]
            rel = item["path"]
            stats = luma(root / rel)
            lumas[key] = stats
            if stats["mean"] < args.mean_threshold and stats["max"] <= args.min_threshold:
                bad = True
        means = [item["mean"] for item in lumas.values()]
        mins = [item["min"] for item in lumas.values()]
        maxes = [item["max"] for item in lumas.values()]
        shot["luma"] = {
            "frames": lumas,
            "mean_min": min(means),
            "mean_avg": round(sum(means) / len(means), 3),
            "pixel_min": min(mins),
            "pixel_max": max(maxes),
            "black_or_fade_risk": bad,
        }
        if bad:
            flagged.append({
                "shot_id": shot["shot_id"],
                "start": shot["start"],
                "end": shot["end"],
                "luma": shot["luma"],
            })

    shots_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "shot_count": len(data["shots"]),
        "flagged_count": len(flagged),
        "mean_threshold": args.mean_threshold,
        "min_threshold": args.min_threshold,
        "flagged": flagged,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "shot_count": len(data["shots"]),
        "flagged_count": len(flagged),
        "out": str(out),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
