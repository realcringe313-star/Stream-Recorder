#!/usr/bin/env python3
"""
YouTube Ghost-Host: automated multi-stream download, optional morph/faststart,
resumable YouTube unlisted upload, verification, and live sync to Pastebin/Rentry/Git.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error


def resolve_archive_mp4(rec):
    """Resolve direct Archive.org download URL."""
    for key in ("archive_node", "archive_direct"):
        u = rec.get(key)
        if u and u.endswith(".mp4"):
            return u

    link = rec.get("archive_link", "")
    m = link.rstrip("/").rsplit("/", 1)[-1] if "/details/" in link else None
    if not m:
        return ""

    try:
        with urllib.request.urlopen(f"https://archive.org/metadata/{m}", timeout=30) as r:
            meta = json.loads(r.read())
    except Exception as e:
        print(f"   Archive metadata API failed: {e}", flush=True)
        return ""

    files = meta.get("files", [])
    mp4s = [f for f in files if f.get("name", "").lower().endswith(".mp4")]
    if not mp4s:
        return ""
    mp4s.sort(key=lambda f: int(f.get("size", 0) or 0), reverse=True)
    return f"https://archive.org/download/{m}/{mp4s[0]['name']}"


def verify_oembed(yt_id: str) -> bool:
    """Verify video is reachable on YouTube."""
    for attempt in range(6):
        time.sleep(10)
        try:
            r = subprocess.run(
                [
                    "curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
                    f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={yt_id}&format=json"
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if (r.stdout or "").strip() == "200":
                return True
        except Exception:
            pass
    return False


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    recs_path = os.path.join(root, "data", "recordings.json")

    with open(recs_path, "r", encoding="utf-8") as f:
        recs = json.load(f)

    # ── Duration gating ─────────────────────────────────────────────
    verified = os.environ.get("YOUTUBE_VERIFIED", "false").lower() in ("true", "1", "yes")
    force = os.environ.get("FORCE_UPLOAD_LONG", "false").lower() in ("true", "1", "yes")
    max_sec_unverified = 15 * 60
    max_sec_verified = 12 * 3600
    duration_cap = max_sec_verified if verified else max_sec_unverified

    try:
        max_uploads = int(os.environ.get("MAX_UPLOADS") or 5)
    except Exception:
        max_uploads = 5

    print(f"YOUTUBE_VERIFIED={verified}   duration_cap={duration_cap // 60}min   max_uploads={max_uploads}", flush=True)

    eligible = []
    skipped_too_long = []
    for r in recs:
        if r.get("youtube_unlisted") or r.get("youtube_id"):
            continue
        if not (r.get("archive_node") or r.get("archive_direct") or r.get("archive_link")):
            continue
        dur = int(r.get("duration_sec", 0) or 0)
        if dur > duration_cap and not force:
            skipped_too_long.append((r.get("video_id", ""), r.get("title", "")[:60], dur // 60))
            continue
        eligible.append(r)

    if skipped_too_long:
        print(f"\n⚠️  Skipping {len(skipped_too_long)} recording(s), too long for current account verification:", flush=True)
        for vid, t, m in skipped_too_long[:10]:
            print(f"    • {vid}  ({m} min)  {t}", flush=True)

    if not eligible:
        print("Nothing eligible to ghost-host this run.", flush=True)
        sys.exit(0)

    todo = eligible[:max_uploads]
    print(f"\nTotal eligible recordings: {len(eligible)}. Processing batch of {len(todo)} (limit: {max_uploads})...", flush=True)
    skip = os.environ.get("SKIP_MORPH", "true").lower() in ("true", "1", "yes")

    uploaded_count = 0
    for i, rec in enumerate(todo):
        title = rec.get("title", "Recording")
        vid = rec.get("video_id", "")
        url = resolve_archive_mp4(rec)

        print("\n" + "=" * 60, flush=True)
        print(f"[{i + 1}/{len(todo)}] {title}", flush=True)
        if not url:
            print("   Could not resolve a direct mp4 URL, skipping", flush=True)
            continue
        print(f"   URL: {url[:120]}", flush=True)

        input_file = "/tmp/input.mp4" if os.name != "nt" else os.path.join(root, "temp_input.mp4")
        morphed_file = "/tmp/morphed.mp4" if os.name != "nt" else os.path.join(root, "temp_morphed.mp4")

        # Cleanup existing temp files
        for tf in (input_file, morphed_file):
            if os.path.exists(tf):
                try:
                    os.remove(tf)
                except Exception:
                    pass

        # 1. Download
        print("   Downloading with aria2c multi-stream...", flush=True)
        dl_dir = os.path.dirname(input_file) or "."
        dl_name = os.path.basename(input_file)
        dl = subprocess.run(
            [
                "aria2c", "-x", "8", "-s", "8", "-k", "1M", "-j", "8",
                "--allow-overwrite=true", "--connect-timeout=30", "--timeout=60",
                "-o", dl_name, "-d", dl_dir, url
            ]
        )
        if dl.returncode != 0 or not os.path.exists(input_file) or os.path.getsize(input_file) < 10_000_000:
            print("   aria2c failed or incomplete, falling back to curl...", flush=True)
            dl = subprocess.run(
                ["curl", "-L", "--fail", "--retry", "3", "--retry-delay", "5", "--max-time", "1800", "-o", input_file, url]
            )
            if dl.returncode != 0 or not os.path.exists(input_file):
                print(f"   Download failed (exit {dl.returncode})", flush=True)
                continue

        if os.path.getsize(input_file) < 10_000_000:
            print("   Download too small (<10MB), skipping", flush=True)
            continue

        with open(input_file, "rb") as f:
            head = f.read(16)
        if b"ftyp" not in head:
            print(f"   Not a valid mp4 header, skipping", flush=True)
            continue

        print(f"   Downloaded: {os.path.getsize(input_file) / 1024 / 1024:.0f} MB", flush=True)

        # 2. Process / morph video
        env = os.environ.copy()
        if skip:
            env["SKIP_MORPH"] = "true"
        print("   Processing video (morph/copy)...", flush=True)
        subprocess.run(["python3", os.path.join(root, "scripts", "morph_video.py"), input_file, morphed_file], env=env)

        if not os.path.exists(morphed_file):
            print("   Morph/copy failed", flush=True)
            if os.path.exists(input_file):
                os.remove(input_file)
            continue

        # 3. Upload to YouTube
        print("   Uploading to YouTube (streaming progress)...", flush=True)
        env["YOUTUBE_UPLOAD_TITLE"] = f"Archive Backup - {title}"
        p = subprocess.Popen(
            ["python3", "-u", os.path.join(root, "scripts", "upload_to_youtube.py"), morphed_file],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        yt_id = ""
        quota_hit = False
        for line in p.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            line_str = line.strip()
            if line_str.startswith("VIDEO_ID="):
                yt_id = line_str.split("=", 1)[1].strip()
            if "QUOTA_EXCEEDED" in line_str or "quotaExceeded" in line_str:
                quota_hit = True
        p.wait()

        # 4. Verify upload
        if yt_id:
            print(f"   Verifying {yt_id} via YouTube oembed...", flush=True)
            if not verify_oembed(yt_id):
                print(f"   ⚠️  Upload {yt_id} did not become reachable within 60s, discarding", flush=True)
                yt_id = ""

        # 5. Commit & sync immediately
        if yt_id:
            # Re-read to guard against external modifications
            try:
                with open(recs_path, "r", encoding="utf-8") as f:
                    recs = json.load(f)
            except Exception:
                pass

            for r in recs:
                if r.get("video_id") == vid:
                    r["youtube_id"] = yt_id
                    r["youtube_unlisted"] = f"https://youtu.be/{yt_id}"

            with open(recs_path, "w", encoding="utf-8") as f:
                json.dump(recs, f, indent=2)

            print(f"   ✅ Successfully mirrored: https://youtu.be/{yt_id}", flush=True)
            uploaded_count += 1

            # Sync Pastebin & Rentry
            print("   📡 Syncing updated links to Pastebin & Rentry...", flush=True)
            subprocess.run(["python3", os.path.join(root, "scripts", "format_and_upload_pastes.py")], env=env)

            # Push immediately to GitHub
            print("   💾 Committing and pushing progress to GitHub...", flush=True)
            subprocess.run(["git", "config", "user.name", "Stream Recorder Bot"], cwd=root)
            subprocess.run(["git", "config", "user.email", "bot@stream-recorder.local"], cwd=root)
            subprocess.run(["git", "add", "data/recordings.json"], cwd=root)
            subprocess.run(["git", "commit", "-m", f"YouTube Ghost-Host: mirror {vid} ({title[:40]})"], cwd=root)
            subprocess.run(["bash", os.path.join(root, "scripts", "safe-push.sh")], cwd=root)
        else:
            print("   Upload failed or discarded for this item.", flush=True)

        for tf in (input_file, morphed_file):
            if os.path.exists(tf):
                try:
                    os.remove(tf)
                except Exception:
                    pass

        if quota_hit:
            print("\n⚠️  Daily YouTube upload quota reached (6/day max for standard accounts).", flush=True)
            print("   Stopping batch early. All successful uploads were already committed and pushed.", flush=True)
            break

    print(f"\nFinished batch: {uploaded_count}/{len(todo)} uploaded and pushed successfully.", flush=True)


if __name__ == "__main__":
    main()
