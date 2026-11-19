import os
import sys
import traceback

try:
    from pyrogram import Client
except ImportError:
    print("Pyrogram is not installed. Run: pip install pyrogram")
    input("\nPress Enter to exit...")
    sys.exit(1)

API_ID = 30156787
API_HASH = "b4c75044ad3b41306bd03d367b37fbb1"

print("=" * 60)
print("     Telegram Session Generator")
print("=" * 60)
print(f"App ID:   {API_ID}")
print(f"App Hash: {API_HASH[:6]}...{API_HASH[-4:]}")
print("=" * 60)
print("Choose login method:")
print("  [1] Personal Telegram Account (phone number + code in Desktop App)")
print("  [2] Telegram Bot (paste Bot Token from @BotFather)")
print("=" * 60)

choice = input("Enter 1 or 2 (default is 1): ").strip()
if choice not in ("1", "2"):
    choice = "1"

try:
    if choice == "2":
        bot_token = input("\nEnter your Bot Token: ").strip()
        print("\nConnecting as Bot...")
        app = Client(
            name="session_gen",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=bot_token,
            in_memory=True
        )
    else:
        print("\nConnecting as User Account...")
        print("Note: When prompted, enter your phone number with country code (e.g. +92...)")
        print("Then check your Telegram Desktop app for the login code.")
        app = Client(
            name="session_gen",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        )

    with app:
        session = app.export_session_string()

    out_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "telegram_session.txt"))
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(session)

    print("\n" + "=" * 60)
    print("SUCCESS! Your TELEGRAM_SESSION_STRING has been generated!")
    print(f"Saved to: {out_file}")
    print("=" * 60)
    print("\nSession string (first 35 characters):")
    print(session[:35] + "...")
    print("\nYou can now close this window and reply in the chat!")

except Exception as e:
    print("\n" + "!" * 60)
    print("An error occurred during generation:")
    print("!" * 60)
    traceback.print_exc()

input("\nPress Enter to exit...")
