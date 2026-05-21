#!/usr/bin/env python3
"""
Reads Gmail drafts via IMAP → fires each to Make.com webhook → Make.com sends via Gmail OAuth.

One-time setup:
  1. Go to myaccount.google.com/apppasswords
  2. Create an App Password (name it anything) → copy the 16 chars
  3. Run: python3 scripts/send_drafts.py
     Paste the App Password when prompted (saved to .env, never committed)

Usage:
  python3 scripts/send_drafts.py            # preview + confirm
  python3 scripts/send_drafts.py --all      # send all instantly
  python3 scripts/send_drafts.py --list     # list only, don't send
  python3 scripts/send_drafts.py --limit 50 # only first 50 drafts
"""
import os, sys, imaplib, email, json, time, argparse, urllib.request
from pathlib import Path
from email.header import decode_header
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

GMAIL_USER   = "kalnyesgrowth@gmail.com"
IMAP_HOST    = "imap.gmail.com"
MAKE_WEBHOOK = "https://hook.us2.make.com/mrlfie2pjkwo8t5y1mx6wcr59lququbg"


def get_app_password():
    pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if pw:
        return pw

    print("\nGmail App Password needed (one-time setup):")
    print("  1. Open: myaccount.google.com/apppasswords")
    print("  2. Click Create → name anything → copy 16-char password\n")
    pw = input("  Paste App Password: ").replace(" ", "").strip()
    if not pw:
        sys.exit(1)

    env_path = BASE_DIR / ".env"
    content  = env_path.read_text()
    if "GMAIL_APP_PASSWORD=" in content:
        lines = [
            f"GMAIL_APP_PASSWORD={pw}" if l.startswith("GMAIL_APP_PASSWORD=") else l
            for l in content.splitlines()
        ]
        env_path.write_text("\n".join(lines) + "\n")
    else:
        with open(env_path, "a") as f:
            f.write(f"\nGMAIL_APP_PASSWORD={pw}\n")
    print("  Saved.\n")
    return pw


def decode_str(s):
    if not s:
        return ""
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def get_body(msg):
    if msg.is_multipart():
        # Prefer HTML, fall back to plain
        html_part = plain_part = None
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html" and not html_part:
                html_part = part
            elif ct == "text/plain" and not plain_part:
                plain_part = part
        chosen = html_part or plain_part
        if chosen:
            payload = chosen.get_payload(decode=True)
            return payload.decode("utf-8", errors="replace") if payload else ""
    else:
        payload = msg.get_payload(decode=True)
        return payload.decode("utf-8", errors="replace") if payload else ""
    return ""


def fetch_drafts(imap):
    imap.select('"[Gmail]/Drafts"')
    _, data = imap.search(None, "ALL")
    ids = data[0].split()
    drafts = []
    for mid in ids:
        _, msg_data = imap.fetch(mid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        to      = decode_str(msg.get("To", ""))
        subject = decode_str(msg.get("Subject", "(no subject)"))
        if not to:
            continue
        body = get_body(msg)
        drafts.append({"imap_id": mid, "to": to, "subject": subject, "body": body})
    return drafts


def fire_to_make(draft):
    payload = json.dumps({
        "to":      draft["to"],
        "subject": draft["subject"],
        "body":    draft["body"],
    }).encode()
    req = urllib.request.Request(
        MAKE_WEBHOOK,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status


def delete_draft(imap, msg_id):
    imap.store(msg_id, "+FLAGS", "\\Deleted")
    imap.expunge()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all",   action="store_true")
    parser.add_argument("--list",  action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    app_password = get_app_password()

    print(f"Connecting to Gmail ({GMAIL_USER})...")
    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST)
        imap.login(GMAIL_USER, app_password)
    except imaplib.IMAP4.error as e:
        print(f"\nLogin failed: {e}")
        print("Make sure IMAP is enabled: Gmail Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP")
        print("And use an App Password, not your regular password.")
        sys.exit(1)

    print("Fetching drafts...")
    drafts = fetch_drafts(imap)

    if not drafts:
        print("No drafts found.")
        imap.logout()
        return

    if args.limit:
        drafts = drafts[:args.limit]

    print(f"\nFound {len(drafts)} draft(s):\n")
    for i, d in enumerate(drafts, 1):
        print(f"  [{i:3d}] {d['to'][:50]:<50}  {d['subject'][:45]}")

    if args.list:
        imap.logout()
        return

    print()
    if args.all:
        confirm = "y"
    else:
        confirm = input(f"Send all {len(drafts)} via Make.com? [y/N] ").strip().lower()

    if confirm != "y":
        imap.logout()
        return

    print(f"\nFiring to Make.com...\n")
    sent = failed = 0
    for i, d in enumerate(drafts, 1):
        try:
            status = fire_to_make(d)
            if status == 200:
                delete_draft(imap, d["imap_id"])
                print(f"  [{i:3d}/{len(drafts)}] ✓  {d['to'][:50]}")
                sent += 1
            else:
                print(f"  [{i:3d}/{len(drafts)}] ✗  HTTP {status}  {d['to'][:40]}")
                failed += 1
        except Exception as e:
            print(f"  [{i:3d}/{len(drafts)}] ✗  {d['to'][:40]} | {e}")
            failed += 1
        time.sleep(0.3)  # avoid rate limits

    imap.logout()
    print(f"\nDone. {sent} sent via Make.com, {failed} failed.")

    # Remind to restore Calendly if needed
    if sent > 0:
        print("\nReminder: run  python3 scripts/restore_make.py  to re-enable the Calendly auto-reply.")


if __name__ == "__main__":
    main()
