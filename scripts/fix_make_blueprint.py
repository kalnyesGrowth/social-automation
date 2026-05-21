#!/usr/bin/env python3
"""
Fix Make.com scenario 5071326.

The scenario has gateway:CustomWebHook (module 2) stuck in orphans.
This moves it back into the flow as the trigger:
  Webhook (mod2) → Google Sheets filterRows (mod3) → Router (mod4) → FB/IG/LI

The Google Sheets filter already uses {{2.pillar}} and {{2.date}} correctly.
Only fix needed beyond reconnecting: Instagram image_url → column 15 (image_url_1).

Usage:
  MAKE_API_TOKEN=<token> python3 scripts/fix_make_blueprint.py

Get your token: make.com → avatar (top right) → Profile → API → New API Token
"""
import os
import sys
import json
import urllib.request
import urllib.error

SCENARIO_ID = 5071326
BASE_URL = "https://us2.make.com/api/v2"

API_TOKEN = os.environ.get("MAKE_API_TOKEN", "")
if not API_TOKEN:
    print("ERROR: MAKE_API_TOKEN not set.")
    print("Get it: make.com → avatar → Profile → API → New API Token")
    sys.exit(1)


def api(method, path, body=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Token {API_TOKEN}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code}: {body[:400]}")
        return e.code, {}


def main():
    # 1. Fetch current blueprint
    print("Fetching blueprint...")
    status, data = api("GET", f"/scenarios/{SCENARIO_ID}/blueprint")
    if status != 200:
        print(f"Failed: {status}")
        sys.exit(1)

    bp = data["response"]["blueprint"]
    print(f"  Current flow:   {[m['id'] for m in bp['flow']]}")
    orphan_chain = bp["metadata"]["designer"]["orphans"][0]
    print(f"  Orphaned mods:  {[m['id'] for m in orphan_chain]}")

    # 2. Pull modules from orphans
    by_id = {m["id"]: m for m in orphan_chain}
    mod2 = by_id[2]   # gateway:CustomWebHook — becomes the trigger
    mod3 = by_id[3]   # google-sheets:filterRows — already uses {{2.pillar}}/{{2.date}}
    mod4 = by_id[4]   # builtin:BasicRouter with routes for FB/IG/LI

    # 3. Fix Instagram (mod 6): use image_url_1 (col P, index 15) not image_prompt (index 10)
    for route in mod4["routes"]:
        for flow_mod in route["flow"]:
            if flow_mod["id"] == 6:
                old = flow_mod["mapper"]["image_url"]
                flow_mod["mapper"]["image_url"] = "{{3.`15`}}"
                print(f"  Instagram image_url: {old} → {{{{3.`15`}}}}")

    # 4. Position on canvas
    mod2["metadata"]["designer"].update({"x": 0,   "y": 0})
    mod3["metadata"]["designer"].update({"x": 300, "y": 0})
    mod4["metadata"]["designer"].update({"x": 600, "y": 0})

    # 5. New flow: webhook trigger → sheets filter → router
    new_bp = {
        "flow": [mod2, mod3, mod4],
        "name": bp["name"],
        "metadata": {
            "instant": True,      # webhook-triggered = instant
            "version": 1,
            "designer": {"orphans": []},
        },
    }

    print(f"\n  New flow: {[f\"{m['id']}:{m['module']}\" for m in new_bp['flow']]}")
    print(f"  mod3 filter: {json.dumps(mod3['mapper']['filter'])}")

    # 6. PUT blueprint
    print("\nPushing blueprint...")
    status, resp = api("PUT", f"/scenarios/{SCENARIO_ID}/blueprint", {"blueprint": new_bp})
    print(f"  → {status} | code: {resp.get('code')}")
    if resp.get("code") != "OK":
        print("  Full response:", json.dumps(resp, indent=2)[:600])
        sys.exit(1)

    # 7. Verify
    print("\nVerifying...")
    status, data = api("GET", f"/scenarios/{SCENARIO_ID}/blueprint")
    updated = data["response"]["blueprint"]
    print(f"  Flow:    {[m['id'] for m in updated['flow']]}")
    print(f"  Orphans: {[[m['id'] for m in c] for c in updated['metadata']['designer']['orphans']]}")
    print(f"  Instant: {updated['metadata']['instant']}")

    if [m["id"] for m in updated["flow"]] == [2, 3, 4]:
        print("\n✅ Fixed. GitHub Actions webhook will now trigger Make.com correctly.")
        print("   Test: Go to Make.com editor → Run once (or fire a manual workflow dispatch)")
    else:
        print("\n⚠️  Flow IDs unexpected — check manually in Make.com editor")


if __name__ == "__main__":
    main()
