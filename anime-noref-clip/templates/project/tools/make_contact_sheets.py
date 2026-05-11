#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_font(size: int):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def resize_cover(img: Image.Image, size):
    img = img.convert("RGB")
    img.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (18, 18, 18))
    x = (size[0] - img.width) // 2
    y = (size[1] - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def fmt_time(seconds):
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:05.2f}"


def frame_items(shot, max_frames: int):
    items = [
        {"role": key, "path": shot["frames"][key]}
        for key in ["first", "mid", "last"]
    ]
    for sample in shot.get("sample_frames", []):
        items.append(
            {
                "role": sample.get("role", "sample"),
                "path": sample["path"],
            }
        )
    return items[:max_frames]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--per-sheet", type=int, default=12)
    parser.add_argument("--thumb-width", type=int, default=220)
    parser.add_argument("--thumb-height", type=int, default=124)
    parser.add_argument("--max-frames-per-shot", type=int, default=12)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.shots.read_text(encoding="utf-8"))
    shots = data["shots"]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    font = load_font(18)
    small = load_font(15)
    label_h = 42
    pad = 12
    frame_cols = 3
    frame_rows = max(1, math.ceil(args.max_frames_per_shot / frame_cols))
    block_w = args.thumb_width * frame_cols + pad * 2
    block_h = label_h + args.thumb_height * frame_rows + pad
    cols = 2
    rows = math.ceil(args.per_sheet / cols)
    sheet_w = cols * block_w + pad
    sheet_h = rows * block_h + pad

    manifest = []
    for sheet_idx, offset in enumerate(range(0, len(shots), args.per_sheet), start=1):
        batch = shots[offset : offset + args.per_sheet]
        sheet = Image.new("RGB", (sheet_w, sheet_h), (245, 245, 242))
        draw = ImageDraw.Draw(sheet)
        for i, shot in enumerate(batch):
            col = i % cols
            row = i // cols
            x0 = pad + col * block_w
            y0 = pad + row * block_h
            draw.rectangle([x0, y0, x0 + block_w - pad, y0 + block_h - pad], fill=(255, 255, 255), outline=(190, 190, 186))
            label = f"{shot['shot_id']}  {fmt_time(shot['start'])}-{fmt_time(shot['end'])}  {shot['duration']:.1f}s"
            draw.text((x0 + 8, y0 + 5), label, fill=(20, 20, 20), font=font)
            items = frame_items(shot, args.max_frames_per_shot)
            subtitle = " / ".join(item["role"] for item in items[:6])
            if len(items) > 6:
                subtitle += f" / +{len(items) - 6}"
            draw.text((x0 + 8, y0 + 24), subtitle, fill=(90, 90, 90), font=small)
            for j, item in enumerate(items):
                img_path = args.project_root / item["path"]
                if img_path.exists():
                    img = resize_cover(Image.open(img_path), (args.thumb_width, args.thumb_height))
                else:
                    img = Image.new("RGB", (args.thumb_width, args.thumb_height), (30, 30, 30))
                frame_col = j % frame_cols
                frame_row = j // frame_cols
                x = x0 + 8 + frame_col * args.thumb_width
                y = y0 + label_h + frame_row * args.thumb_height
                sheet.paste(img, (x, y))
                draw.text((x + 4, y + 4), item["role"], fill=(255, 255, 255), font=small)
        out = args.out_dir / f"contact_sheet_{sheet_idx:03d}_shots_{batch[0]['shot_id']}_{batch[-1]['shot_id']}.jpg"
        sheet.save(out, quality=90)
        manifest.append({
            "sheet_index": sheet_idx,
            "path": str(out),
            "shot_ids": [s["shot_id"] for s in batch],
            "start": batch[0]["start"],
            "end": batch[-1]["end"],
        })

    args.manifest.write_text(json.dumps({"sheets": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"sheet_count": len(manifest), "first": manifest[0], "last": manifest[-1]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
