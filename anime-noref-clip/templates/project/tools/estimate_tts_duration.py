#!/usr/bin/env python3
"""Estimate full-script TTS duration before synthesis."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_TTS_SPEED = 1.2
DEFAULT_MIN_RATIO = 0.9
DEFAULT_TARGET_DURATION_SEC = 60.0
CALIBRATION_SCHEMA_VERSION = "anime-noref-clip.tts_duration_calibration.v1"
LANGUAGE_PROFILES = {
    "zh": {
        "metric": "cjk_chars",
        "units_per_second_at_speed_1": 4.9,
        "description": "Chinese IndexTTS local workflow calibration",
    },
    "th": {
        "metric": "nonspace_chars",
        "units_per_second_at_speed_1": 12.5,
        "description": "Thai F5 local workflow calibration",
    },
    "en": {
        "metric": "words",
        "units_per_second_at_speed_1": 2.25,
        "description": "English narration word budget calibration",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_project_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def display_project_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def route_language(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("zh") or normalized in {"cn", "chinese"}:
        return "zh"
    if normalized.startswith("th") or normalized == "thai":
        return "th"
    if normalized.startswith("en") or normalized == "english":
        return "en"
    return "zh"


def load_calibrated_profile(
    root: Path, language: str, calibration_arg: str
) -> tuple[dict[str, Any], str, int]:
    profile = dict(LANGUAGE_PROFILES[language])
    candidates = []
    if calibration_arg:
        candidates.append(resolve_project_path(root, calibration_arg))
    candidates.append(root / "references" / "tts_duration_calibration.json")
    for path in candidates:
        if not path.exists():
            continue
        payload = load_json(path)
        profiles = payload.get("profiles", {})
        calibrated = profiles.get(language) if isinstance(profiles, dict) else None
        if not isinstance(calibrated, dict):
            continue
        profile.update(
            {
                key: calibrated[key]
                for key in ("metric", "units_per_second_at_speed_1", "description")
                if key in calibrated
            }
        )
        sample_count = int(calibrated.get("sample_count", payload.get("sample_count", 0)) or 0)
        return profile, display_project_path(root, path), sample_count
    return profile, "builtin_language_profile", 0


def script_text(script: dict[str, Any]) -> str:
    units = script.get("script_units", [])
    if isinstance(units, list) and units:
        return "\n".join(str(unit.get("text", "")) for unit in units if isinstance(unit, dict))
    return str(script.get("text", ""))


def count_units(text: str, metric: str) -> int:
    if metric == "words":
        return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", text))
    if metric == "cjk_chars":
        return len(re.findall(r"[\u3400-\u9fff]", text))
    if metric == "nonspace_chars":
        return len(re.sub(r"\s+", "", text))
    return len(text.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate anime-noref-clip TTS duration.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--script", default="script/script.json")
    parser.add_argument("--out-json", default="analysis/tts_duration_estimate.json")
    parser.add_argument("--language", default="")
    parser.add_argument("--speed", type=float, default=DEFAULT_TTS_SPEED)
    parser.add_argument("--target-duration-sec", type=float, default=None)
    parser.add_argument("--min-ratio", type=float, default=DEFAULT_MIN_RATIO)
    parser.add_argument("--calibration", default="")
    parser.add_argument("--fail-on-under-target", action="store_true")
    args = parser.parse_args()

    root = args.project_root.expanduser().resolve()
    script_path = resolve_project_path(root, args.script)
    script = load_json(script_path)
    language = route_language(args.language or str(script.get("language", "")))
    profile, calibration_source, calibration_sample_count = load_calibrated_profile(
        root, language, args.calibration
    )
    text = script_text(script)
    unit_count = count_units(text, str(profile["metric"]))
    rate = float(profile["units_per_second_at_speed_1"]) * float(args.speed)
    estimated = unit_count / rate if rate > 0 else 0.0
    target = float(
        args.target_duration_sec
        if args.target_duration_sec is not None
        else script.get("target_duration_sec", DEFAULT_TARGET_DURATION_SEC)
    )
    ratio = estimated / target if target > 0 else 0.0
    passes = ratio >= float(args.min_ratio)

    out_path = resolve_project_path(root, args.out_json)
    payload = {
        "schema_version": "anime-noref-clip.tts_duration_estimate.v1.4.18",
        "script": display_project_path(root, script_path),
        "language": language,
        "speed": float(args.speed),
        "target_duration_sec": round(target, 6),
        "estimated_duration_sec": round(estimated, 6),
        "estimated_duration_ratio": round(ratio, 6),
        "min_ratio": float(args.min_ratio),
        "passes": passes,
        "rewrite_required": not passes,
        "metric": profile["metric"],
        "unit_count": unit_count,
        "units_per_second_at_speed_1": profile["units_per_second_at_speed_1"],
        "profile": profile["description"],
        "calibration_source": calibration_source,
        "calibration_sample_count": calibration_sample_count,
        "calibration_schema_version": CALIBRATION_SCHEMA_VERSION,
        "gate_rule": "Estimated TTS duration must be at least 90% of target before final script/TTS.",
    }
    write_json(out_path, payload)
    print(
        json.dumps(
            {
                **payload,
                "estimate_output": display_project_path(root, out_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if args.fail_on_under_target and not passes else 0


if __name__ == "__main__":
    raise SystemExit(main())
