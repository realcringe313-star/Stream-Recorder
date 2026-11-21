# 🤖 STREAM-RECORDER AI HANDOFF & MASTER CONTEXT

> **How to use this file:** When switching to a new AI model (DeepSeek, Qwen, Llama, ChatGPT, Claude, etc.), simply copy and paste everything below the line into your first message to give the model 100% of the project context instantly.

---

## AI INSTRUCTION & PROJECT BRIEF
You are an expert AI software engineer assisting Muneeb Ahmad with the **Stream-Recorder** project (repository: `https://github.com/realcringe313-star/Stream-Recorder`).

### 1. Project Goal
An automated, 24/7 cloud recorder for "The Muslim Lantern" YouTube channel. It records live streams during Pakistani time (9:00 PM – 6:00 AM PKT), mirrors them to multiple storage providers (Telegram, Archive.org, Pixeldrain, Mega, DropDrive, and YouTube Unlisted), self-heals dead links, and publishes direct stream links to Pastebin and Rentry.co.

---

### 2. High-Level Architecture
- **Automation Engine:** GitHub Actions (`.github/workflows/*.yml`), scheduled with cron and triggered by workflow runs.
- **Recording Cascade:** Runs in `scripts/record-stream.sh`. Uses pure CDP headless browser (SeleniumBase Method K) for anonymous live stream capture without cookies + ffmpeg.
- **Database:** JSON-based master catalog at `data/recordings.json` (contains all 26+ stream entries).
- **Public Link Mirrors:**
  - **Rentry.co:** `https://rentry.co/tml-archive-index` (Edit code: `tml-archive-2026`)
  - **Pastebin:** `https://pastebin.com/eUzuhx5f` (Raw: `https://pastebin.com/raw/eUzuhx5f`)
  - Auto-synced by: `scripts/format_and_upload_pastes.py`.
- **YouTube Ghost-Host:** Uploads unlisted mirrors of recordings to YouTube for web embedding.
  - Script: `scripts/ghost_host_upload.py` (multi-stream aria2c download + 10MB chunked YouTube API uploads + live incremental git push).

---

### 3. Key Invariants & Rules
1. **`data/recordings.json` is the Single Source of Truth:** Never overwrite or write empty data; always validate reads first.
2. **Pushing to Git:** Always use `bash scripts/safe-push.sh` because the main branch moves frequently with bot snapshots.
3. **Zero Discord Spam:** Link refreshes and mirror repairs must operate silently.
4. **Recording Schedule:** 9:00 PM – 6:00 AM PKT (Asia/Karachi) only to conserve GitHub Actions minutes.
5. **No Credentials in Git:** All API keys, tokens, and credentials belong in GitHub Secrets (never commit credentials).

---

### 4. Recent Work & Current State
- **Dashboard Removal:** The web dashboard (`dashboard/`) was removed. Links were shifted to Rentry and Pastebin.
- **Runner Failures Fixed:**
  - `status.yml`: Fixed `git add` pathspec error that looked for deleted dashboard files. (Now passes 100% green).
  - `youtube-stats.yml`: Removed deleted dashboard scrape step.
  - `dependabot.yml`: Removed npm checks for deleted dashboard.
- **YouTube Ghost-Host Optimized:**
  - Previously hung for 8+ hours because of 256 KB chunk size and slow single-stream downloads.
  - Rewritten into `scripts/ghost_host_upload.py`:
    - `aria2c` multi-stream downloads from Archive.org in 10–15 seconds.
    - 10 MB upload chunks (40x faster).
    - 120s socket timeout with exponential backoff on network drops.
    - Incremental commits: saves and pushes after **every single video**.
    - Safe batching (`max_uploads: 5`) matching YouTube's daily API quota.
  - Current blocker on YouTube: Channel hit YouTube's rolling 24-hour upload limit during previous test runs (`uploadLimitExceeded: The user has exceeded the number of videos they may upload`). Awaiting 24-hour cooldown or phone verification at `https://www.youtube.com/verify`.

---

### 5. Local Environment & File Locations
- **Local Workspace:** `C:\Users\Muneeb Ahmad\.gemini\antigravity\scratch\stream-recorder`
- **Master Backup Credentials:** `C:\Users\Muneeb Ahmad\Downloads\STREAM_RECORDER_MASTER_BACKUP_CREDENTIALS.txt`
- **One-Click Disaster Recovery Script:** `restore_to_new_github_repo.py` in repo root.
- **Python on Windows:** Use `py -3` command.
