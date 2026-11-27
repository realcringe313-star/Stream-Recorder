import json
import os
import sys
import re
import urllib.request
import urllib.parse
import http.cookiejar

def generate_catalog():
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rec_path = os.path.join(repo_dir, "data", "recordings.json")
    
    with open(rec_path, "r", encoding="utf-8") as f:
        recs = json.load(f)
        
    md_lines = []
    
    md_lines.append("# The Muslim Lantern — Live Stream Archive Index")
    md_lines.append(f"**Total Recordings:** {len(recs)}  ")
    md_lines.append(f"**Archive Status:** Multi-Cloud Mirror Network (Telegram, Archive.org, Pixeldrain, Mega, DropDrive, YouTube Unlisted)  \n")
    md_lines.append("---\n")
    
    for i, r in enumerate(recs, 1):
        title = r.get("title", "Recording")
        date = r.get("date", "")
        dur = r.get("duration_fmt") or f"{r.get('duration_sec', 0)//60}m"
        size = r.get("size_human", "")
        res = r.get("resolution", "")
        vid_id = r.get("video_id", "")
        
        md_lines.append(f"### {i}. {title}")
        md_lines.append(f"- **Date:** `{date}` | **Duration:** `{dur}` | **Size:** `{size}` | **Resolution:** `{res}`")
        md_lines.append(f"- **Original YouTube:** https://www.youtube.com/watch?v={vid_id}")
        if r.get("youtube_unlisted"):
            md_lines.append(f"- **Unlisted YouTube Mirror:** {r.get('youtube_unlisted')}")
        if r.get("telegram_link"):
            md_lines.append(f"- **Telegram Direct Stream:** {r.get('telegram_link')}")
        if r.get("archive_direct"):
            md_lines.append(f"- **Archive.org Direct MP4:** {r.get('archive_direct')}")
        if r.get("archive_node"):
            md_lines.append(f"- **Archive.org CDN Node:** {r.get('archive_node')}")
        if r.get("archive_link"):
            md_lines.append(f"- **Archive.org Details:** {r.get('archive_link')}")
        if r.get("pixeldrain_link"):
            md_lines.append(f"- **Pixeldrain CDN:** {r.get('pixeldrain_link')}")
        if r.get("mega_link"):
            md_lines.append(f"- **Mega Storage:** {r.get('mega_link')}")
        if r.get("st0807_link"):
            name = "DropDrive CDN" if "dropdrive" in r.get("st0807_link") else "0807 CDN"
            md_lines.append(f"- **{name}:** {r.get('st0807_link')}")
        md_lines.append("\n---\n")

    return "\n".join(md_lines)

def update_rentry_permanent(text, url="tml-archive-index", edit_code="tml-archive-2026"):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    edit_url = f"https://rentry.co/{url}/edit"
    
    # 1. GET edit page to extract fresh CSRF
    resp = opener.open(urllib.request.Request(edit_url, headers={"User-Agent": "Mozilla/5.0"}))
    html = resp.read().decode("utf-8")
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    if not m:
        raise ValueError("Could not find CSRF token on Rentry edit page")
    csrf = m.group(1)
    
    # 2. POST updated markdown text
    post_data = urllib.parse.urlencode({
        "csrfmiddlewaretoken": csrf,
        "text": text,
        "edit_code": edit_code,
        "update_secret_metadata": "false"
    }).encode("utf-8")
    
    post_req = urllib.request.Request(
        edit_url,
        data=post_data,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": edit_url,
            "Origin": "https://rentry.co"
        }
    )
    opener.open(post_req)
    return f"https://rentry.co/{url}"

def upload_to_pastebin(api_dev_key, text, paste_name="The Muslim Lantern Archive Index"):
    data = urllib.parse.urlencode({
        "api_dev_key": api_dev_key,
        "api_option": "paste",
        "api_paste_code": text,
        "api_paste_name": paste_name,
        "api_paste_private": "1", # 1 = Unlisted
        "api_paste_expire_date": "N", # Never
        "api_paste_format": "text"
    }).encode("utf-8")
    req = urllib.request.Request("https://pastebin.com/api/api_post.php", data=data, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8").strip()

if __name__ == "__main__":
    content = generate_catalog()
    print(f"Generated catalog: {len(content)} characters.")
    
    # 1. Update Rentry permanent URL
    try:
        r_url = update_rentry_permanent(content)
        print("✅ Rentry.co (Permanent):", r_url)
    except Exception as e:
        print("❌ Rentry error:", e)

    # 2. Upload to Pastebin
    pb_key = os.environ.get("PASTEBIN_API_KEY", "")
    if len(sys.argv) > 1 and sys.argv[1]:
        pb_key = sys.argv[1]
        
    if pb_key:
        try:
            pb_url = upload_to_pastebin(pb_key, content)
            print("✅ Pastebin.com:", pb_url)
        except Exception as e:
            print("❌ Pastebin error:", e)
    else:
        print("ℹ️ Pastebin: No PASTEBIN_API_KEY supplied.")
