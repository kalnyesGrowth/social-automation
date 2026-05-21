#!/usr/bin/env python3
"""
After bulk-sending drafts:
  - Deletes the bulk-send scenario
  - Re-activates the Calendly auto-reply scenario
"""
import json, urllib.request, urllib.error, os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
token = os.environ.get("MAKE_API_TOKEN", "").strip()

CALENDLY_SCENARIO = 5112412
BULK_SEND_SCENARIO = 5112576

def req(method, path, body=None):
    url = f"https://us2.make.com/api/v2{path}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

print("Restoring Make.com scenarios...")

s1, d1 = req("DELETE", f"/scenarios/{BULK_SEND_SCENARIO}")
print(f"  Deleted bulk-send scenario: HTTP {s1}")

s2, d2 = req("POST", f"/scenarios/{CALENDLY_SCENARIO}/start", {})
active = d2.get("scenario", {}).get("isActive")
print(f"  Calendly auto-reply: HTTP {s2} -> isActive={active}")

if active:
    print("\nDone. Calendly auto-reply is back online.")
else:
    print(f"\nWarning: Calendly may not be active. Check make.com/scenarios/{CALENDLY_SCENARIO}")
