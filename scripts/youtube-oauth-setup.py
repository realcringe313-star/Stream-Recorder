#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  YOUTUBE GHOST-HOST, OAuth Token Setup Helper                                ║
# ║                                                                              ║
# ║  Run this ONCE locally to get your refresh token:                            ║
# ║    python youtube-oauth-setup.py                                             ║
# ║                                                                              ║
# ║  It will open a browser for you to authorize. After you grant access,        ║
# ║  it saves youtube_token.json and prints the values for GitHub secrets.       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

import json
import os
import sys

# These are installed by the user: pip install google-auth-oauthlib
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

import glob
import json
import os
import sys

# These are installed by the user: pip install google-auth-oauthlib
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def find_client_secrets():
    # 1. Command-line argument
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return sys.argv[1]

    # 2. Check current dir and scripts dir
    candidates = [
        "client_secrets.json",
        "client_secret.json",
        os.path.join(os.path.dirname(__file__), "client_secrets.json"),
        os.path.join(os.path.dirname(__file__), "client_secret.json"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    # 3. Check Downloads folder
    user_home = os.path.expanduser("~")
    downloads_patterns = [
        os.path.join(user_home, "Downloads", "client_secret*.json"),
        os.path.join(user_home, "Downloads", "New folder", "client_secret*.json"),
        os.path.join(user_home, "Downloads", "*client_secret*.json"),
    ]
    for pat in downloads_patterns:
        matches = glob.glob(pat)
        if matches:
            # Sort by newest
            matches.sort(key=os.path.getmtime, reverse=True)
            return matches[0]

    return None

CLIENT_SECRETS_FILE = find_client_secrets()


def main():
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║  YouTube OAuth Setup Helper                              ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()

    if not CLIENT_SECRETS_FILE:
        print("❌ Client secrets file not found!")
        print()
        print("Make sure one of these files exists in the SAME folder as this script:")
        print("  - client_secrets.json")
        print("  - client_secret.json")
        print()
        print("To get one:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create OAuth 2.0 Client ID → 'Desktop application'")
        print("  3. Download the JSON and save it here")
        print("  4. Ensure YouTube Data API v3 is enabled for your project")
        print()
        input("Press Enter to exit...")
        sys.exit(1)

    print(f"Loading {CLIENT_SECRETS_FILE}...")
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES
    )

    print("Opening browser for authorization...")
    print("   A browser tab will open.")
    print("   Sign in with the YouTube account you want to upload to.")
    print("   Click 'Advanced' → 'Go to Stream Recorder (unsafe)' → Allow all.")
    print()

    credentials = flow.run_local_server(
        port=8080,
        prompt="consent",
    )

    # Save token to file
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
    with open("youtube_token.json", "w") as f:
        json.dump(token_data, f, indent=2)

    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║  ✅ SUCCESS! Token saved to youtube_token.json              ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    print("Now add these as GitHub Secrets:")
    print()
    print("1. Open client_secrets.json with Notepad → copy ALL text")
    print("   Secret name: YOUTUBE_CLIENT_SECRETS")
    print()
    print("2. Open youtube_token.json with Notepad → copy ALL text")
    print("   Secret name: YOUTUBE_TOKEN")
    print()
    print(f"  Refresh Token: {credentials.refresh_token}")
    print()
    print("⚠️  The refresh token does NOT expire unless you revoke access.")
    print()
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
