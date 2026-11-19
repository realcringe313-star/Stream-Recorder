"""
Local Stream Guard & Emergency Recorder for The Muslim Lantern (@TheMuslimLantern)
Continuously monitors for live streams and records them locally to prevent missing streams
when GitHub Actions is disabled or down.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
import subprocess
from datetime import datetime

CHANNEL_HANDLE = "@TheMuslimLantern"
LIVE_URL = f"https://www.youtube.com/{CHANNEL_HANDLE}/live"
POLL_INTERVAL_SECONDS = 30
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recordings")

os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "CONSENT=YES+cb.20230101-00-p0.en+FX+414; SOCS=CAI"
}

def log(msg, level="INFO"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] [{level}] {msg}", flush=True)

def check_live_status():
    """
    Checks if @TheMuslimLantern is actively live streaming.
    Returns (is_live: bool, video_id: str or None, title: str or None)
    """
    req = urllib.request.Request(LIVE_URL, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            eff_url = resp.geturl()
            html = resp.read().decode("utf-8", errors="ignore")
            
            # Check redirect to watch?v=
            import re
            m = re.search(r"watch\?v=([a-zA-Z0-9_-]{11})", eff_url)
            if not m:
                m = re.search(r"/live/([a-zA-Z0-9_-]{11})", eff_url)
            
            vid = m.group(1) if m else None
            is_live_now = '"isLiveNow":true' in html or '"isLive":true' in html
            
            if vid and is_live_now:
                m_title = re.search(r"<title>(.*?)</title>", html)
                raw_title = m_title.group(1) if m_title else "The Muslim Lantern Live Stream"
                clean_title = raw_title.replace(" - YouTube", "").strip()
                return True, vid, clean_title
            
            return False, vid, None
    except Exception as e:
        log(f"Connection check warning: {e}", level="WARN")
        return False, None, None

def record_stream(video_id, title):
    """
    Spawns yt-dlp to record the stream from start to finish.
    """
    stream_url = f"https://www.youtube.com/watch?v={video_id}"
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip()[:50]
    out_template = os.path.join(OUTPUT_DIR, f"{date_str}_{video_id}_{safe_title}.%(ext)s")
    
    log("=" * 60, level="STREAM")
    log(f"🔴 LIVE STREAM DETECTED: {title}", level="STREAM")
    log(f"🔗 URL: {stream_url}", level="STREAM")
    log(f"📁 Saving to: {out_template}", level="STREAM")
    log("=" * 60, level="STREAM")
    
    cmd = [
        "yt-dlp",
        "--live-from-start",
        "--no-part",
        "--retries", "infinite",
        "--fragment-retries", "infinite",
        "--output", out_template,
        stream_url
    ]
    
    try:
        proc = subprocess.run(cmd)
        if proc.returncode == 0:
            log(f"✅ Stream successfully recorded and saved to {OUTPUT_DIR}", level="SUCCESS")
        else:
            log(f"⚠️ yt-dlp exited with code {proc.returncode}", level="WARN")
    except Exception as e:
        log(f"❌ Recording error: {e}", level="ERROR")

def main():
    log("=" * 60)
    log(f"🚀 Local Stream Guard started for {CHANNEL_HANDLE}")
    log(f"👀 Monitoring URL: {LIVE_URL}")
    log(f"⏱️ Check interval: {POLL_INTERVAL_SECONDS} seconds")
    log(f"📂 Output directory: {OUTPUT_DIR}")
    log("=" * 60)
    
    last_recorded_id = None
    
    # Read existing last_video_id if present
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    last_id_path = os.path.join(repo_root, "last_video_id.txt")
    if os.path.exists(last_id_path):
        with open(last_id_path, "r", encoding="utf-8") as f:
            last_recorded_id = f.read().strip()
            log(f"Loaded previous recorded ID: {last_recorded_id}")
            
    while True:
        try:
            is_live, video_id, title = check_live_status()
            
            if is_live and video_id:
                if video_id == last_recorded_id:
                    log(f"Stream {video_id} is live but was already recorded. Skipping duplicate.", level="INFO")
                else:
                    log(f"New stream found: {video_id} - '{title}'", level="ALERT")
                    record_stream(video_id, title)
                    last_recorded_id = video_id
                    with open(last_id_path, "w", encoding="utf-8") as f:
                        f.write(video_id)
            else:
                log(f"Channel is currently offline. Polling again in {POLL_INTERVAL_SECONDS}s...", level="INFO")
                
        except KeyboardInterrupt:
            log("Stopped by user.")
            break
        except Exception as e:
            log(f"Unexpected error in guard loop: {e}", level="ERROR")
            
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
