#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


BASE_URL = "https://api.assemblyai.com/v2"


def request_json(url: str, api_key: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"authorization": api_key}
    if payload is not None:
        headers["content-type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="GET" if payload is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"AssemblyAI HTTP {exc.code}: {body}") from exc


def upload(path: Path, api_key: str) -> str:
    headers = {"authorization": api_key, "transfer-encoding": "chunked"}
    req = urllib.request.Request(f"{BASE_URL}/upload", headers=headers, method="POST")
    with path.open("rb") as handle:
        req.data = handle.read()
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"AssemblyAI upload HTTP {exc.code}: {body}") from exc
    return payload["upload_url"]


def normalize(raw: dict, source_audio: str) -> dict:
    utterances = []
    for item in raw.get("utterances") or []:
        utterances.append(
            {
                "speaker": f"Speaker {item.get('speaker')}",
                "start": round((item.get("start") or 0) / 1000, 3),
                "end": round((item.get("end") or 0) / 1000, 3),
                "text": item.get("text", ""),
            }
        )
    return {
        "provider": "assemblyai",
        "source_audio": source_audio,
        "language": raw.get("language_code"),
        "utterances": utterances,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--raw-out", type=Path, required=True)
    parser.add_argument("--normalized-out", type=Path, required=True)
    parser.add_argument("--language-code", default="ja")
    parser.add_argument("--speech-model", default="universal-2")
    parser.add_argument("--poll-interval", type=float, default=6.0)
    args = parser.parse_args()

    api_key = os.environ.get("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("ASSEMBLYAI_API_KEY is required in the environment")

    upload_url = upload(args.audio, api_key)
    submit_payload = {
        "audio_url": upload_url,
        "speaker_labels": True,
        "language_code": args.language_code,
        "speech_models": [args.speech_model],
    }
    submitted = request_json(f"{BASE_URL}/transcript", api_key, submit_payload)
    transcript_id = submitted["id"]

    while True:
        raw = request_json(f"{BASE_URL}/transcript/{transcript_id}", api_key)
        status = raw.get("status")
        if status == "completed":
            break
        if status == "error":
            raise RuntimeError(raw.get("error") or "AssemblyAI transcription failed")
        print(json.dumps({"id": transcript_id, "status": status}, ensure_ascii=False), flush=True)
        time.sleep(args.poll_interval)

    args.raw_out.parent.mkdir(parents=True, exist_ok=True)
    args.normalized_out.parent.mkdir(parents=True, exist_ok=True)
    args.raw_out.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    normalized = normalize(raw, str(args.audio))
    args.normalized_out.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "id": transcript_id,
                "status": raw.get("status"),
                "language": raw.get("language_code"),
                "utterances": len(normalized["utterances"]),
                "raw_out": str(args.raw_out),
                "normalized_out": str(args.normalized_out),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
