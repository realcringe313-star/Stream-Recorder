#!/usr/bin/env python3
"""Publish compact live-chat JSON files to Catbox and record links in the index."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

DEFAULT_ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOT = pathlib.Path(os.environ.get("REPO_ROOT", str(DEFAULT_ROOT))).resolve()
CHAT_DIR = ROOT / "data" / "chat"
RECORDINGS = ROOT / "data" / "recordings.json"
UPLOADER = ROOT / "scripts" / "catbox" / "upload_to_catbox.sh"


def log(message: str) -> None:
    print(f"ChatCatbox: {message}", flush=True)


def valid_chat(path: pathlib.Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    if data.get("demo") is True or not isinstance(data.get("messages"), list):
        return 0
    return len(data["messages"])


def upload(path: pathlib.Path) -> str | None:
    env = os.environ.copy()
    result = subprocess.run(
        ["bash", str(UPLOADER), str(path)],
        capture_output=True,
        text=True,
        timeout=360,
        env=env,
    )
    url = (result.stdout or "").strip().splitlines()[-1] if result.stdout else ""
    if result.returncode == 0 and url.startswith("https://files.catbox.moe/"):
        return url
    if result.stderr:
        log((result.stderr or "").strip()[:240])
    return None


def main() -> int:
    if not CHAT_DIR.exists():
        log("no chat directory")
        return 0

    records: list[dict] = []
    if RECORDINGS.exists():
        try:
            loaded = json.loads(RECORDINGS.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                records = loaded
        except Exception as exc:
            log(f"refusing to update recordings.json: {exc}")

    by_id = {str(r.get("video_id", "")): r for r in records if r.get("video_id")}
    uploaded = 0
    skipped = 0
    failed = 0

    for path in sorted(CHAT_DIR.glob("*.json")):
        vid = path.stem
        if len(vid) != 11:
            continue
        count = valid_chat(path)
        if count <= 0:
            continue
        rec = by_id.get(vid)
        existing = str((rec or {}).get("chat_url", ""))
        if existing.startswith("https://files.catbox.moe/"):
            skipped += 1
            continue
        url = upload(path)
        if not url:
            failed += 1
            continue
        uploaded += 1
        if rec is not None:
            rec["chat_url"] = url
            rec["catbox_chat"] = url
        log(f"{vid}: {count} messages -> Catbox")

    if uploaded and records:
        tmp = RECORDINGS.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(RECORDINGS)

    summary = f"uploaded={uploaded} skipped={skipped} failed={failed}"
    print(summary)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"uploaded={uploaded}\nskipped={skipped}\nfailed={failed}\n")
    return 1 if failed and not uploaded and not skipped else 0


if __name__ == "__main__":
    sys.exit(main())
