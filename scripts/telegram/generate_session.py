import os
import sys

try:
    from pyrogram import Client
except ImportError:
    print("Pyrogram is not installed. Run: pip install pyrogram")
    sys.exit(1)

API_ID = 30156787
API_HASH = "b4c75044ad3b41306bd03d367b37fbb1"

print("=" * 60)
print("     Telegram Session Generator")
print("=" * 60)
print(f"Using App ID:   {API_ID}")
print(f"Using App Hash: {API_HASH[:6]}...{API_HASH[-4:]}")
print("=" * 60)
print("Enter your phone number with country code (e.g. +923001234567)")
print("Telegram will send the verification code to your Telegram Desktop App.")
print("=" * 60)

with Client(":memory:", api_id=API_ID, api_hash=API_HASH) as app:
    session = app.export_session_string()

# Save to file
out_path = os.path.join(os.path.dirname(__file__), "..", "..", "telegram_session.txt")
out_path = os.path.abspath(out_path)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(session)

print("\n" + "=" * 60)
print("SUCCESS! Session string generated and saved to:")
print(f"  {out_path}")
print("=" * 60)
print("\nSession string (first 30 chars):", session[:30] + "...")
print("You can now return to the chat!")
