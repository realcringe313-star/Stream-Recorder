"""
Telegram Session String Generator (Supports both User Account and Bot)
Requirements: pip install pyrogram tgcrypto

Usage:
  python generate_session.py
"""
import sys

try:
    from pyrogram import Client
except ImportError:
    print("Pyrogram is not installed. Run: pip install pyrogram tgcrypto")
    sys.exit(1)

print("=" * 60)
print("     Telegram Session String Generator")
print("=" * 60)
print("1. Log in with your Telegram User Account (phone number)")
print("2. Log in with a Telegram Bot Token (from @BotFather)")
choice = input("\nChoose (1 or 2): ").strip()

api_id = input("Enter your API_ID (from my.telegram.org): ").strip()
api_hash = input("Enter your API_HASH (from my.telegram.org): ").strip()

if choice == "2":
    bot_token = input("Enter your Bot Token (from @BotFather): ").strip()
    with Client(":memory:", api_id=int(api_id), api_hash=api_hash, bot_token=bot_token) as app:
        session = app.export_session_string()
else:
    with Client(":memory:", api_id=int(api_id), api_hash=api_hash) as app:
        session = app.export_session_string()

print("\n" + "=" * 60)
print("YOUR TELEGRAM_SESSION_STRING IS:")
print("=" * 60)
print(session)
print("=" * 60)
print("\nSave this string and add it as TELEGRAM_SESSION_STRING in GitHub Secrets.")
