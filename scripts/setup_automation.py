#!/usr/bin/env python3
"""
Full automation setup — run this once (and again whenever you need to re-push).

1. Pushes the fixed Make.com blueprint via API token (no browser, no cookie tricks)
2. Activates the Make.com scenario
3. Adds HIGGSFIELD_ACCESS_TOKEN + HIGGSFIELD_REFRESH_TOKEN to GitHub secrets

Requires MAKE_API_TOKEN in .env — get it from:
  https://us2.make.com/user/api → "Add token"
"""
import json
import os
import sys
import base64
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

SCENARIO_ID = 5071326
GITHUB_REPO  = "kalnyesGrowth/social-automation"
BLUEPRINT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "make_fixed_blueprint.json")
HIGGSFIELD_CREDS = os.path.expanduser("~/.config/higgsfield/credentials.json")
def get_github_pat():
    """Extract PAT from git remote URL (already stored there) or env."""
    pat = os.environ.get("GITHUB_PAT", "").strip()
    if pat:
        return pat
    try:
        import subprocess
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            text=True
        ).strip()
        # https://<token>@github.com/...
        if "@" in url and "://" in url:
            return url.split("://")[1].split("@")[0]
    except Exception:
        pass
    return ""


# ── Make.com API helpers ───────────────────────────────────────────────────────

def make_request(method, path, body=None, api_token=None):
    url = f"https://us2.make.com/api/v2{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        },
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            return e.code, json.loads(body_text)
        except Exception:
            return e.code, {"_raw": body_text[:400]}


def get_api_token():
    token = os.environ.get("MAKE_API_TOKEN", "").strip()
    if token:
        return token

    print("\n  Make.com API token not found in .env")
    print("  Get one in 30 seconds:")
    print("    1. Go to https://us2.make.com/user/api")
    print("    2. Click 'Add token', give it any name")
    print("    3. Copy the token and paste it below")
    print("    (It will be saved to your .env for future use)\n")
    token = input("  Paste Make.com API token: ").strip()
    if not token:
        print("  ERROR: No token provided.")
        sys.exit(1)

    # Save to .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    with open(env_path) as f:
        content = f.read()
    content = content.replace("MAKE_API_TOKEN=", f"MAKE_API_TOKEN={token}")
    with open(env_path, "w") as f:
        f.write(content)
    print("  Saved to .env\n")
    return token


# ── Step 1+2: Push blueprint + activate ───────────────────────────────────────

def push_and_activate(api_token):
    print("[1] Loading blueprint...")
    with open(BLUEPRINT_PATH) as f:
        outer = json.load(f)
    inner = outer["blueprint"]
    flow_ids = [m["id"] for m in inner.get("flow", [])]
    orphans = inner.get("metadata", {}).get("designer", {}).get("orphans", [])
    print(f"   flow={flow_ids}  orphans={orphans}  size={len(json.dumps(inner))}b")

    # Verify token works first
    print("\n[2] Verifying API token...")
    status, data = make_request("GET", f"/scenarios/{SCENARIO_ID}", api_token=api_token)
    if status == 401:
        print("   ERROR: Invalid API token — please check and update MAKE_API_TOKEN in .env")
        sys.exit(1)
    if status != 200:
        print(f"   ERROR {status}: {data}")
        sys.exit(1)
    scenario_name = data.get("scenario", {}).get("name", "?")
    is_active = data.get("scenario", {}).get("isActive")
    print(f"   Scenario: '{scenario_name}'  currently active={is_active}")

    print(f"\n[3] Pushing blueprint to scenario {SCENARIO_ID}...")
    # API token endpoint requires blueprint as a JSON string (not object)
    status, data = make_request(
        "PATCH",
        f"/scenarios/{SCENARIO_ID}",
        body={"blueprint": json.dumps(inner)},
        api_token=api_token
    )
    print(f"   HTTP {status}")
    if not (200 <= status < 300):
        print(f"   ERROR: {data}")
        sys.exit(1)
    # PATCH response returns scenario metadata only (no blueprint field); verify via GET
    is_invalid_after_patch = data.get("scenario", {}).get("isinvalid")
    print(f"   Blueprint saved  (isinvalid={is_invalid_after_patch})")

    # Confirm via GET blueprint
    status2, bp_data = make_request("GET", f"/scenarios/{SCENARIO_ID}/blueprint", api_token=api_token)
    if status2 == 200:
        bp = bp_data.get("response", bp_data).get("blueprint", {})
        saved_flow = [m.get("id") for m in bp.get("flow", [])]
        saved_orphans = bp.get("metadata", {}).get("designer", {}).get("orphans", [])
        print(f"   Verified: flow={saved_flow}  orphans={saved_orphans}")

    print(f"\n[4] Activating scenario {SCENARIO_ID}...")
    status, data = make_request("POST", f"/scenarios/{SCENARIO_ID}/start", body={}, api_token=api_token)
    print(f"   HTTP {status}")
    scenario = data.get("scenario", {})
    is_active = scenario.get("isActive")
    is_invalid = scenario.get("isinvalid")
    print(f"   isActive={is_active}  isinvalid={is_invalid}")

    already_running = "already running" in str(data)
    if is_active or already_running:
        print("   SCENARIO IS ACTIVE")
    elif is_invalid:
        print(f"   WARNING: isinvalid=True — check scenario for validation errors")
        print(f"   https://us2.make.com/scenarios/{SCENARIO_ID}/edit")
    else:
        print(f"   Response: {data}")


# ── Step 3: GitHub secrets ─────────────────────────────────────────────────────

def github_api(path, method="GET", body=None):
    pat = get_github_pat()
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            return e.code, json.loads(body_text)
        except Exception:
            return e.code, {"_raw": body_text[:400]}


def encrypt_secret(public_key_b64, secret_value):
    from nacl import public as nacl_public
    pk_bytes = base64.b64decode(public_key_b64)
    sealed = nacl_public.SealedBox(nacl_public.PublicKey(pk_bytes))
    encrypted = sealed.encrypt(secret_value.encode())
    return base64.b64encode(encrypted).decode()


def set_github_secrets():
    print("\n[5] Reading Higgsfield credentials...")
    if not os.path.exists(HIGGSFIELD_CREDS):
        print(f"   Skipped — {HIGGSFIELD_CREDS} not found (run 'higgsfield auth login' first)")
        return

    with open(HIGGSFIELD_CREDS) as f:
        creds = json.load(f)
    access_token = creds.get("access_token", "")
    refresh_token = creds.get("refresh_token", "")
    if not access_token:
        print("   Skipped — no access_token in credentials file")
        return
    print(f"   access_token: {access_token[:12]}...")

    print("\n[6] Getting GitHub repo public key...")
    status, key_data = github_api(f"/repos/{GITHUB_REPO}/actions/secrets/public-key")
    if status != 200:
        print(f"   ERROR {status}: {key_data}")
        return
    key_id = key_data["key_id"]
    pub_key = key_data["key"]

    print("\n[7] Setting GitHub secrets...")
    for name, value in [
        ("HIGGSFIELD_ACCESS_TOKEN", access_token),
        ("HIGGSFIELD_REFRESH_TOKEN", refresh_token),
    ]:
        if not value:
            print(f"   {name}: skipped (empty)")
            continue
        encrypted = encrypt_secret(pub_key, value)
        status, _ = github_api(
            f"/repos/{GITHUB_REPO}/actions/secrets/{name}",
            method="PUT",
            body={"encrypted_value": encrypted, "key_id": key_id}
        )
        print(f"   {name}: {'SET' if status in (201, 204) else f'ERROR {status}'}")


# ── Facebook re-enable ────────────────────────────────────────────────────────

def enable_facebook(api_token):
    """
    Reads the live scenario's Facebook module to get the current page_id
    (after user has fixed it in the Make.com editor), updates make_fixed_blueprint.json,
    and re-pushes.
    """
    print("[FB] Reading live blueprint to get current Facebook page_id...")
    status, d = make_request("GET", f"/scenarios/{SCENARIO_ID}/blueprint", api_token=api_token)
    if status != 200:
        print(f"   ERROR {status}: {d}")
        sys.exit(1)

    bp = d.get("response", d).get("blueprint", {})
    router = next((m for m in bp.get("flow", []) if m.get("module") == "builtin:BasicRouter"), None)
    if not router:
        print("   ERROR: Router module not found in live blueprint")
        sys.exit(1)

    fb_module = None
    for route in router.get("routes", []):
        for mod in route.get("flow", []):
            if mod.get("module") == "facebook-pages:CreatePost":
                fb_module = mod
                break

    if not fb_module:
        print("   ERROR: Facebook module not found in live blueprint")
        sys.exit(1)

    live_page_id = fb_module.get("mapper", {}).get("page_id", "")
    live_filter = fb_module.get("filter", {}).get("conditions", [[]])[0]
    current_filter_val = live_filter[0].get("b", "") if live_filter else ""

    print(f"   Live page_id: {live_page_id}")
    print(f"   Live filter value: {current_filter_val}")

    if not live_page_id or live_page_id == "1075704708966809":
        print("\n   Facebook page_id is still the old invalid value.")
        print("   Fix it first:")
        print(f"   1. Open https://us2.make.com/scenarios/{SCENARIO_ID}/edit")
        print("   2. Click the Facebook module → re-select 'Kalnyes Growth' page")
        print("   3. Save the scenario in the editor")
        print("   4. Re-run: python3 scripts/setup_automation.py --enable-facebook")
        sys.exit(1)

    # Update local blueprint file
    with open(BLUEPRINT_PATH) as f:
        outer = json.load(f)
    inner = outer["blueprint"]

    router_local = next((m for m in inner.get("flow", []) if m.get("module") == "builtin:BasicRouter"), None)
    for route in router_local.get("routes", []):
        for mod in route.get("flow", []):
            if mod.get("module") == "facebook-pages:CreatePost":
                mod["mapper"]["page_id"] = live_page_id
                mod["filter"]["conditions"] = [[{"a": "{{3.`7`}}", "b": "facebook", "o": "text:equal"}]]
                mod["filter"]["name"] = "Facebook"
                print(f"   Updated local blueprint: page_id={live_page_id}, filter='facebook'")

    with open(BLUEPRINT_PATH, "w") as f:
        json.dump(outer, f, indent=2)

    print("\n[FB] Pushing updated blueprint...")
    push_and_activate(api_token)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable-facebook", action="store_true",
                        help="Read page_id from live scenario and re-enable the Facebook route")
    args = parser.parse_args()

    print("=== Kalnyes Growth — Automation Setup ===\n")

    api_token = get_api_token()

    if args.enable_facebook:
        enable_facebook(api_token)
        print("\n=== DONE — Facebook is now enabled ===")
        return

    push_and_activate(api_token)
    set_github_secrets()

    print("\n=== DONE ===")
    print("Make.com scenario is active.")
    print("GitHub secrets updated with Higgsfield credentials.")
    print("")
    print("Daily schedule:")
    print("  6:30am ET  — Generate copy + Higgsfield images → write to Google Sheet")
    print("  8:00am ET  — Pillar A posts: LinkedIn live, Instagram (if image ready)")
    print("  12:00pm ET — Pillar B posts: LinkedIn live, Instagram (if image ready)")
    print("  5:00pm ET  — Pillar C posts: LinkedIn live, Instagram (if image ready)")
    print("")
    print("Facebook is still disabled. To enable it after fixing the page in Make.com:")
    print("  python3 scripts/setup_automation.py --enable-facebook")


if __name__ == "__main__":
    main()
