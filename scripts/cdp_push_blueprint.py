#!/usr/bin/env python3
"""
Push Make.com blueprint via Chrome DevTools Protocol.
Relaunches Chrome with --remote-debugging-port=9222, navigates to Make.com,
executes the blueprint push JS in the authenticated session context.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

SCENARIO_ID = 5071326
MAKE_URL = f"https://us2.make.com/scenarios/{SCENARIO_ID}/edit"
BLUEPRINT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "make_fixed_blueprint.json")
CDP_HOST = "http://localhost:9222"

def cdp_request(method, params=None, session_id=None):
    import urllib.request, json, time
    payload = {"id": 1, "method": method, "params": params or {}}
    if session_id:
        payload["sessionId"] = session_id
    req = urllib.request.Request(
        f"{CDP_HOST}/json",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    # Use websocket for actual CDP commands
    return None

def get_tabs():
    try:
        with urllib.request.urlopen(f"{CDP_HOST}/json/list", timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return None

def wait_for_chrome(timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        tabs = get_tabs()
        if tabs is not None:
            return True
        time.sleep(0.5)
    return False

def run_cdp_js(ws_url, js_code, timeout=30):
    """Execute JS in a Chrome tab via CDP WebSocket."""
    import websocket as ws_lib
    import threading

    result = {"value": None, "error": None, "done": False}

    def on_message(ws, message):
        msg = json.loads(message)
        if msg.get("id") == 1:
            if "result" in msg:
                r = msg["result"].get("result", {})
                if r.get("type") == "string":
                    result["value"] = r["value"]
                elif r.get("type") == "number":
                    result["value"] = r["value"]
                elif "value" in r:
                    result["value"] = r["value"]
                else:
                    result["value"] = str(r)
                if "exceptionDetails" in msg["result"]:
                    result["error"] = msg["result"]["exceptionDetails"]
            elif "error" in msg:
                result["error"] = msg["error"]
            result["done"] = True
            ws.close()

    def on_error(ws, error):
        result["error"] = str(error)
        result["done"] = True

    def on_open(ws):
        payload = json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_code,
                "awaitPromise": True,
                "returnByValue": True,
                "timeout": timeout * 1000
            }
        })
        ws.send(payload)

    wsapp = ws_lib.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error,
        on_open=on_open
    )
    t = threading.Thread(target=wsapp.run_forever, kwargs={"ping_timeout": timeout})
    t.daemon = True
    t.start()
    t.join(timeout + 5)

    return result

def main():
    # Load blueprint
    if not os.path.exists(BLUEPRINT_PATH):
        print(f"ERROR: Blueprint not found at {BLUEPRINT_PATH}")
        sys.exit(1)

    with open(BLUEPRINT_PATH) as f:
        blueprint = json.load(f)

    print(f"Blueprint loaded: {len(json.dumps(blueprint))} bytes")
    print(f"Flow modules: {[m['id'] for m in blueprint.get('flow', [])]}")
    print(f"Orphans: {blueprint.get('metadata', {}).get('designer', {}).get('orphans', [])}")

    # Step 1: Kill Chrome and relaunch with CDP
    print("\n[1] Killing Chrome...")
    subprocess.run(["pkill", "-f", "Google Chrome"], capture_output=True)
    time.sleep(2)

    print("[2] Launching Chrome with remote debugging (Default profile)...")
    chrome_args = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
        MAKE_URL
    ]
    proc = subprocess.Popen(chrome_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"   Chrome PID: {proc.pid}")

    print("[3] Waiting for Chrome CDP to be ready...")
    if not wait_for_chrome(timeout=20):
        print("ERROR: Chrome CDP not available after 20s")
        sys.exit(1)
    print("   CDP ready!")

    # Step 2: Find Make.com tab
    print("[4] Finding Make.com tab...")
    time.sleep(4)  # Let Make.com load

    for attempt in range(12):
        tabs = get_tabs()
        if not tabs:
            time.sleep(2)
            continue

        make_tab = None
        for tab in tabs:
            url = tab.get("url", "")
            if "make.com" in url and tab.get("type") == "page":
                make_tab = tab
                print(f"   Found Make.com tab: {url[:80]}")
                break

        if make_tab:
            break

        print(f"   Waiting for Make.com tab... attempt {attempt+1}/12")
        time.sleep(3)

    if not make_tab:
        print("Available tabs:")
        for t in (tabs or []):
            print(f"  - {t.get('url','')[:80]}")
        print("ERROR: No Make.com tab found")
        sys.exit(1)

    ws_url = make_tab.get("webSocketDebuggerUrl")
    if not ws_url:
        print(f"ERROR: No WebSocket URL for tab. Tab: {make_tab}")
        sys.exit(1)

    print(f"   WS URL: {ws_url}")

    # Step 3: Check if logged in
    print("[5] Checking Make.com session...")
    check_js = """
    (async () => {
        const resp = await fetch('/api/v2/users/me', {credentials:'include'});
        const data = await resp.json();
        return JSON.stringify({status: resp.status, user: data.user?.name || data.user?.email || 'unknown'});
    })()
    """
    res = run_cdp_js(ws_url, check_js, timeout=15)
    if res["error"]:
        print(f"   Session check error: {res['error']}")
    else:
        print(f"   Session result: {res['value']}")

    # Step 4: Push blueprint
    print(f"\n[6] Pushing blueprint to scenario {SCENARIO_ID}...")

    bp_json = json.dumps(blueprint)

    push_js = f"""
    (async () => {{
        const blueprint = {bp_json};

        // Get XSRF token from cookie
        const getCookie = (name) => {{
            const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
            return match ? decodeURIComponent(match[2]) : null;
        }};

        const xsrf = getCookie('XSRF-TOKEN');
        if (!xsrf) {{
            return JSON.stringify({{error: 'No XSRF-TOKEN cookie found', cookies: document.cookie.substring(0, 200)}});
        }}

        const resp = await fetch('/api/v2/scenarios/{SCENARIO_ID}/blueprint', {{
            method: 'PUT',
            credentials: 'include',
            headers: {{
                'Content-Type': 'application/json',
                'X-XSRF-TOKEN': xsrf
            }},
            body: JSON.stringify({{blueprint: blueprint}})
        }});

        const text = await resp.text();
        let data;
        try {{ data = JSON.parse(text); }} catch(e) {{ data = text; }}

        return JSON.stringify({{
            status: resp.status,
            ok: resp.ok,
            response: typeof data === 'object' ? data : text.substring(0, 500),
            xsrf_found: true
        }});
    }})()
    """

    res = run_cdp_js(ws_url, push_js, timeout=30)

    if res["error"]:
        print(f"ERROR executing JS: {res['error']}")
        sys.exit(1)

    try:
        result = json.loads(res["value"])
        print(f"\n=== PUSH RESULT ===")
        print(f"HTTP Status: {result.get('status')}")
        print(f"Success: {result.get('ok')}")
        if "error" in result:
            print(f"Error: {result['error']}")
            if "cookies" in result:
                print(f"Cookies preview: {result['cookies']}")
        else:
            resp_data = result.get("response", {})
            if isinstance(resp_data, dict):
                scenario = resp_data.get("scenario", {})
                bp = resp_data.get("blueprint", {})
                print(f"Scenario ID: {scenario.get('id')}")
                print(f"Scenario name: {scenario.get('name')}")
                if bp:
                    flow = bp.get("flow", [])
                    orphans = bp.get("metadata", {}).get("designer", {}).get("orphans", [])
                    print(f"Flow modules: {[m.get('id') for m in flow]}")
                    print(f"Orphans: {orphans}")
                    if len(flow) >= 3 and len(orphans) == 0:
                        print("\n✓ BLUEPRINT FIXED SUCCESSFULLY!")
                        print("  Flow: webhook → sheets → router")
                        print("  Orphans: none")
                    else:
                        print(f"\nWARNING: Unexpected state. Flow={flow}, Orphans={orphans}")
            else:
                print(f"Response: {resp_data}")
    except Exception as e:
        print(f"Could not parse result: {e}")
        print(f"Raw value: {res['value']}")

if __name__ == "__main__":
    main()
