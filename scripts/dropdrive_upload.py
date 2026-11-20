#!/usr/bin/env python3
"""
DropDrive (dropdrive.rip) Uploader for Stream-Recorder.
Supports S3 direct uploads (single PUT & multipart) and storage-server chunked uploads.
Works anonymously (auto-solves sha256 PoW) or authenticated with DROPDRIVE_TOKEN.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request


API_BASE = "https://dropdrive.rip/api"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; Stream-Recorder bot; +https://github.com/realcringe313-star/Stream-Recorder)"


def log(msg: str):
    print(f"  DropDrive: {msg}", flush=True)


def fmt_size(b: int) -> str:
    if b < 1024 * 1024:
        return f"{b / 1024:.0f} KB"
    if b < 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024):.1f} MB"
    return f"{b / (1024 * 1024 * 1024):.2f} GB"


def solve_pow(challenge: str, difficulty: int = 16) -> str:
    """Solve sha256(challenge + nonce) with required leading zero bits."""
    shift = 256 - int(difficulty)
    nonce = 0
    t0 = time.time()
    while True:
        d = hashlib.sha256(f"{challenge}{nonce}".encode("utf-8")).digest()
        if int.from_bytes(d, "big") >> shift == 0:
            elapsed = time.time() - t0
            log(f"PoW solved in {elapsed:.3f}s (nonce: {nonce})")
            return str(nonce)
        nonce += 1


def make_request(url: str, data: bytes | None = None, method: str | None = None,
                 headers: dict | None = None, token: str | None = None, timeout: int = 60):
    req_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if headers:
        req_headers.update(headers)
    if token:
        req_headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, method=method, headers=req_headers)
    return urllib.request.urlopen(req, timeout=timeout)


def upload_file(file_path: str, title: str | None = None) -> str:
    if not os.path.exists(file_path):
        log(f"❌ File not found: {file_path}")
        return ""

    file_size = os.path.getsize(file_path)
    file_name = title or os.path.basename(file_path)
    if not os.path.splitext(file_name)[1]:
        file_name += ".mp4"

    token = os.environ.get("DROPDRIVE_TOKEN", "").strip() or os.environ.get("ST0807_TOKEN", "").strip()
    log(f"Uploading '{file_name}' ({fmt_size(file_size)}) | token={'yes' if token else 'anonymous'}")

    pow_challenge = None
    pow_nonce = None

    if not token:
        # Request and solve PoW challenge for anonymous uploads
        try:
            with make_request(f"{API_BASE}/upload/pow-challenge") as resp:
                chal = json.loads(resp.read().decode())
                if not chal.get("skipPow"):
                    pow_challenge = chal["challenge"]
                    pow_nonce = solve_pow(pow_challenge, chal.get("difficulty", 16))
        except Exception as e:
            log(f"⚠️ PoW challenge request failed: {e}")

    # 1. Initialize upload session
    init_payload = {
        "fileName": file_name,
        "fileSize": file_size,
        "totalChunks": max(1, (file_size + 100000000 - 1) // 100000000),
    }
    if pow_challenge and pow_nonce:
        init_payload["powChallenge"] = pow_challenge
        init_payload["powNonce"] = pow_nonce

    try:
        data = json.dumps(init_payload).encode("utf-8")
        with make_request(f"{API_BASE}/upload/init", data=data,
                          headers={"Content-Type": "application/json"}, token=token) as resp:
            init_res = json.loads(resp.read().decode())
    except urllib.error.HTTPError as he:
        log(f"❌ Init failed (HTTP {he.code}): {he.read().decode(errors='ignore')}")
        return ""
    except Exception as e:
        log(f"❌ Init error: {e}")
        return ""

    backend = init_res.get("uploadBackend", "s3")
    session_id = init_res.get("sessionId")
    upload_token = init_res.get("uploadToken")

    start_time = time.time()

    # 2. Upload according to assigned backend
    if backend == "s3":
        upload_mode = init_res.get("uploadMode", "single")
        parts = []

        if upload_mode == "single":
            upload_url = init_res["uploadUrl"]
            log("S3 single PUT upload starting...")
            with open(file_path, "rb") as fp:
                file_bytes = fp.read()
            put_req = urllib.request.Request(upload_url, data=file_bytes, method="PUT", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(put_req, timeout=3600) as put_resp:
                etag = put_resp.headers.get("ETag")
                parts.append({"PartNumber": 1, "ETag": etag})
        else:
            # S3 Multipart
            part_size = init_res.get("partSize", 16777216)
            part_count = init_res.get("partCount", 1)
            log(f"S3 multipart upload starting ({part_count} parts of {fmt_size(part_size)})...")

            last_heartbeat = time.time()
            with open(file_path, "rb") as fp:
                for part_num in range(1, part_count + 1):
                    # Request signed part URL
                    part_req_data = json.dumps({
                        "sessionId": session_id,
                        "uploadToken": upload_token,
                        "partNumber": part_num
                    }).encode("utf-8")

                    part_url = None
                    for retry in range(3):
                        try:
                            with make_request(f"{API_BASE}/upload/s3-part", data=part_req_data,
                                              headers={"Content-Type": "application/json"}, token=token) as presp:
                                p_data = json.loads(presp.read().decode())
                                part_url = p_data.get("url")
                                break
                        except Exception as pe:
                            log(f"⚠️ Part {part_num} URL fetch failed (try {retry+1}): {pe}")
                            time.sleep(2)

                    if not part_url:
                        log(f"❌ Could not obtain signed URL for part {part_num}")
                        return ""

                    # Read slice
                    slice_bytes = fp.read(part_size)

                    # Upload part with retry
                    etag = None
                    for retry in range(5):
                        try:
                            put_req = urllib.request.Request(part_url, data=slice_bytes, method="PUT",
                                                             headers={"User-Agent": USER_AGENT})
                            with urllib.request.urlopen(put_req, timeout=120) as put_resp:
                                etag = put_resp.headers.get("ETag")
                                break
                        except Exception as pue:
                            log(f"⚠️ Part {part_num} PUT failed (try {retry+1}): {pue}")
                            time.sleep(3)

                    if not etag:
                        log(f"❌ Part {part_num} PUT failed after retries")
                        return ""

                    parts.append({"PartNumber": part_num, "ETag": etag})
                    pct = (part_num * 100) // part_count
                    print(f"     Part {part_num}/{part_count} ({pct}%) uploaded", end="\r", flush=True)

                    # Send heartbeat if > 25 seconds elapsed
                    if time.time() - last_heartbeat > 25:
                        try:
                            hb_data = json.dumps({"sessionId": session_id, "uploadToken": upload_token}).encode()
                            make_request(f"{API_BASE}/upload/s3-heartbeat", data=hb_data,
                                         headers={"Content-Type": "application/json"}, token=token)
                            last_heartbeat = time.time()
                        except Exception:
                            pass

            print()

        # 3. S3 complete
        s3_comp_data = json.dumps({
            "sessionId": session_id,
            "uploadToken": upload_token,
            "parts": parts
        }).encode("utf-8")

        with make_request(f"{API_BASE}/upload/s3-complete", data=s3_comp_data,
                          headers={"Content-Type": "application/json"}, token=token) as s3_resp:
            s3_comp_res = json.loads(s3_resp.read().decode())
            if not s3_comp_res.get("success"):
                log(f"❌ S3 complete failed: {s3_comp_res}")
                return ""

        # 4. Finalize
        fin_data = json.dumps({
            "sessionId": session_id,
            "uploadToken": upload_token
        }).encode("utf-8")

        with make_request(f"{API_BASE}/upload/complete", data=fin_data,
                          headers={"Content-Type": "application/json"}, token=token) as comp_resp:
            fin_res = json.loads(comp_resp.read().decode())

    else:
        # Storage server route
        storage_url = init_res["storageServerUrl"]
        chunk_size = init_res.get("chunkSize", 100000000)
        total_parts = max(1, (file_size + chunk_size - 1) // chunk_size)
        log(f"Storage-server upload starting ({total_parts} chunks)...")

        with open(file_path, "rb") as fp:
            for part_idx in range(total_parts):
                chunk_data = fp.read(chunk_size)
                is_last = "?last=1" if part_idx == total_parts - 1 else ""
                url = f"{storage_url}/files/{session_id}/{part_idx}{is_last}"
                for retry in range(3):
                    try:
                        req = urllib.request.Request(url, data=chunk_data, method="POST",
                                                     headers={"Content-Type": "application/octet-stream", "User-Agent": USER_AGENT})
                        with urllib.request.urlopen(req, timeout=180) as resp:
                            if resp.status in (200, 201, 204):
                                break
                    except Exception as ce:
                        log(f"⚠️ Chunk {part_idx} failed (try {retry+1}): {ce}")
                        time.sleep(2)
                print(f"     Chunk {part_idx + 1}/{total_parts} uploaded", end="\r", flush=True)
        print()

        fin_data = json.dumps({"sessionId": session_id}).encode("utf-8")
        with make_request(f"{API_BASE}/upload/complete", data=fin_data,
                          headers={"Content-Type": "application/json"}, token=token) as comp_resp:
            fin_res = json.loads(comp_resp.read().decode())

    elapsed = time.time() - start_time
    speed = (file_size / elapsed) if elapsed > 0 else 0
    short_code = fin_res.get("shortCode") or fin_res.get("downloadUrl", "").replace("/d/", "")
    if not short_code:
        log(f"❌ Missing shortCode in complete response: {fin_res}")
        return ""

    share_link = f"https://dropdrive.rip/d/{short_code}"
    log(f"✅ Upload complete in {elapsed:.0f}s ({fmt_size(speed)}/s)!")
    log(f"Link → {share_link}")

    # Set GITHUB_OUTPUT
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        try:
            with open(gh_out, "a", encoding="utf-8") as f:
                f.write(f"dropdrive_link={share_link}\n")
                # Maintain st0807_link alias for seamless backward compatibility
                f.write(f"st0807_link={share_link}\n")
        except Exception:
            pass

    return share_link


def main():
    if len(sys.argv) < 2:
        print("Usage: dropdrive_upload.py <file_path> [title]")
        sys.exit(1)

    path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(path)
    link = upload_file(path, title)
    if not link:
        sys.exit(1)


if __name__ == "__main__":
    main()
