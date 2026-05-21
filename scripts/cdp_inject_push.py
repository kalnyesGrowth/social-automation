#!/usr/bin/env python3
"""
1. Extract Make.com cookies from Chrome Default profile (browser_cookie3)
2. Launch Chrome with temp profile + --remote-debugging-port=9222
3. Inject cookies via CDP Network.setCookie
4. Execute blueprint push JS in the authenticated browser context
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import threading

SCENARIO_ID = 5071326
BLUEPRINT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "make_fixed_blueprint.json")
CDP_HOST = "http://localhost:9222"

# ---------- Cookie extraction ----------

def extract_make_cookies():
    print("[1] Extracting Make.com cookies from Chrome Default profile...")
    try:
        import browser_cookie3
    except ImportError:
        print("   Installing browser_cookie3...")
        subprocess.run([sys.executable, "-m", "pip", "install", "browser_cookie3", "-q"])
        import browser_cookie3

    all_cookies = []
    for domain in ['.make.com', 'us2.make.com', 'make.com']:
        try:
            jar = browser_cookie3.chrome(domain_name=domain)
            for c in jar:
                all_cookies.append({
                    "name": c.name,
                    "value": c.value,
                    "domain": c.domain,
                    "path": c.path or "/",
                    "secure": bool(c.secure),
                    "httpOnly": False,  # CDP needs this for session cookies
                    "sameSite": "None"
                })
        except Exception as e:
            print(f"   Warning extracting {domain}: {e}")

    # Deduplicate by name+domain
    seen = set()
    unique = []
    for c in all_cookies:
        key = (c["name"], c["domain"])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    xsrf = next((c for c in unique if c["name"] == "XSRF-TOKEN"), None)
    session = next((c for c in unique if "session" in c["name"].lower()), None)

    print(f"   Found {len(unique)} Make.com cookies")
    print(f"   XSRF-TOKEN: {'found (' + xsrf['value'][:20] + '...)' if xsrf else 'NOT FOUND'}")
    print(f"   Session cookie: {'found' if session else 'NOT FOUND'}")

    return unique

# ---------- CDP helpers ----------

def get_tabs(timeout=5):
    try:
        with urllib.request.urlopen(f"{CDP_HOST}/json/list", timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None

def wait_for_cdp(timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        if get_tabs(timeout=2) is not None:
            return True
        time.sleep(0.5)
    return False

def cdp_ws_send(ws_url, method, params=None, msg_id=1, await_promise=False, timeout=30):
    """Send a CDP command via WebSocket and return the result."""
    import websocket as ws_lib

    result = {"value": None, "error": None, "done": False}

    def on_message(ws, message):
        msg = json.loads(message)
        if msg.get("id") == msg_id:
            if "result" in msg:
                result["value"] = msg["result"]
            elif "error" in msg:
                result["error"] = msg["error"]
            result["done"] = True
            ws.close()

    def on_error(ws, error):
        result["error"] = str(error)
        result["done"] = True

    def on_open(ws):
        payload = {"id": msg_id, "method": method, "params": params or {}}
        ws.send(json.dumps(payload))

    wsapp = ws_lib.WebSocketApp(ws_url, on_message=on_message, on_error=on_error, on_open=on_open)
    t = threading.Thread(target=wsapp.run_forever, kwargs={"ping_timeout": timeout})
    t.daemon = True
    t.start()
    t.join(timeout + 5)
    return result

def cdp_navigate(ws_url, url, timeout=20):
    return cdp_ws_send(ws_url, "Page.navigate", {"url": url}, timeout=timeout)

def cdp_inject_cookie(ws_url, cookie, msg_id):
    params = {
        "name": cookie["name"],
        "value": cookie["value"],
        "domain": cookie["domain"],
        "path": cookie.get("path", "/"),
        "secure": cookie.get("secure", False),
        "httpOnly": cookie.get("httpOnly", False),
        "sameSite": cookie.get("sameSite", "None"),
    }
    return cdp_ws_send(ws_url, "Network.setCookie", params, msg_id=msg_id, timeout=5)

def cdp_eval_js(ws_url, js, timeout=30):
    return cdp_ws_send(ws_url, "Runtime.evaluate", {
        "expression": js,
        "awaitPromise": True,
        "returnByValue": True,
        "timeout": timeout * 1000
    }, timeout=timeout + 5)

# ---------- Main ----------

def main():
    # Load blueprint
    with open(BLUEPRINT_PATH) as f:
        blueprint = json.load(f)
    print(f"Blueprint: flow={[m['id'] for m in blueprint.get('flow',[])]} orphans={blueprint.get('metadata',{}).get('designer',{}).get('orphans',[])} size={len(json.dumps(blueprint))}b")

    # Extract cookies
    cookies = extract_make_cookies()
    if not cookies:
        print("ERROR: No Make.com cookies found — session may be expired")
        sys.exit(1)

    xsrf_cookie = next((c for c in cookies if c["name"] == "XSRF-TOKEN"), None)
    if not xsrf_cookie:
        print("ERROR: No XSRF-TOKEN cookie — cannot push blueprint")
        sys.exit(1)

    # Kill Chrome and create temp profile
    print("\n[2] Killing Chrome...")
    subprocess.run(["pkill", "-f", "Google Chrome"], capture_output=True)
    time.sleep(2)

    tmp_dir = tempfile.mkdtemp(prefix="chrome_cdp_")
    print(f"[3] Launching Chrome with temp profile: {tmp_dir}")

    chrome_args = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=http://localhost:9222",
        f"--user-data-dir={tmp_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-client-side-phishing-detection",
        "--no-sandbox",
        "about:blank"
    ]
    proc = subprocess.Popen(chrome_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"   Chrome PID: {proc.pid}")

    print("[4] Waiting for CDP...")
    if not wait_for_cdp(timeout=20):
        print("ERROR: CDP not available after 20s")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.exit(1)
    print("   CDP ready!")

    # Find blank tab
    tabs = get_tabs()
    tab = next((t for t in tabs if t.get("type") == "page"), None)
    if not tab:
        print(f"ERROR: No page tab found. Tabs: {tabs}")
        sys.exit(1)

    ws_url = tab["webSocketDebuggerUrl"]
    print(f"   Tab: {tab.get('url')}")

    # Step 5: Inject cookies via CDP
    print(f"\n[5] Injecting {len(cookies)} cookies into Chrome...")
    for i, cookie in enumerate(cookies):
        # Ensure domain is set correctly for CDP
        if not cookie["domain"].startswith("."):
            cookie["domain"] = "." + cookie["domain"].lstrip(".")

        res = cdp_inject_cookie(ws_url, cookie, msg_id=100 + i)
        if res.get("error"):
            print(f"   Warning: failed to inject {cookie['name']}: {res['error']}")

    print("   Cookies injected")

    # Step 6: Navigate to Make.com
    print(f"\n[6] Navigating to Make.com scenario {SCENARIO_ID}...")
    nav_res = cdp_navigate(ws_url, f"https://us2.make.com/scenarios/{SCENARIO_ID}/edit", timeout=20)
    print(f"   Navigate result: {nav_res}")
    time.sleep(5)  # Give page time to settle

    # Step 7: Check what we can see
    print("\n[7] Checking Make.com session state...")
    check_js = """
    (async () => {
        const resp = await fetch('/api/v2/users/me', {credentials: 'include'});
        return JSON.stringify({
            status: resp.status,
            cookie_preview: document.cookie.substring(0, 300)
        });
    })()
    """
    check = cdp_eval_js(ws_url, check_js, timeout=15)
    print(f"   Check: {check.get('value', {}).get('result', check)}")

    # Step 8: Push the blueprint
    print(f"\n[8] Pushing blueprint to scenario {SCENARIO_ID}...")
    bp_json = json.dumps(blueprint)

    push_js = f"""
    (async () => {{
        const blueprint = {bp_json};

        const getCookie = (name) => {{
            const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
            return match ? decodeURIComponent(match[2]) : null;
        }};

        const xsrf = getCookie('XSRF-TOKEN');
        const allCookies = document.cookie;

        if (!xsrf) {{
            // Try direct value from injection
            const directXsrf = "{xsrf_cookie['value']}";
            if (directXsrf) {{
                const resp2 = await fetch('/api/v2/scenarios/{SCENARIO_ID}/blueprint', {{
                    method: 'PUT',
                    credentials: 'include',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-XSRF-TOKEN': directXsrf
                    }},
                    body: JSON.stringify({{blueprint: blueprint}})
                }});
                const t2 = await resp2.text();
                return JSON.stringify({{status: resp2.status, source: 'direct_xsrf', body: t2.substring(0, 500)}});
            }}
            return JSON.stringify({{error: 'no_xsrf', cookies: allCookies.substring(0, 300)}});
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
        try {{ data = JSON.parse(text); }} catch(e) {{ data = text.substring(0, 500); }}

        return JSON.stringify({{
            status: resp.status,
            ok: resp.ok,
            xsrf_used: xsrf.substring(0, 20) + '...',
            response: data
        }});
    }})()
    """

    res = cdp_eval_js(ws_url, push_js, timeout=30)

    print("\n=== RESULT ===")
    raw = res.get("value", {})
    if isinstance(raw, dict):
        result_str = raw.get("result", {}).get("value", str(raw))
    else:
        result_str = str(raw)

    try:
        result = json.loads(result_str)
        print(f"HTTP {result.get('status')} | OK={result.get('ok')}")
        if "error" in result:
            print(f"Error: {result['error']}")
            print(f"Cookies visible: {result.get('cookies', 'none')}")
        else:
            resp_data = result.get("response", {})
            if isinstance(resp_data, dict):
                scenario = resp_data.get("scenario", {})
                bp_resp = resp_data.get("blueprint", {})
                print(f"Scenario: {scenario.get('id')} — {scenario.get('name')}")
                if bp_resp:
                    flow = bp_resp.get("flow", [])
                    orphans = bp_resp.get("metadata", {}).get("designer", {}).get("orphans", [])
                    print(f"Flow: {[m.get('id') for m in flow]}")
                    print(f"Orphans: {orphans}")
                    if flow and not orphans:
                        print("\n✓ BLUEPRINT FIXED! Webhook is now in the flow.")
                    else:
                        print(f"\nState: flow={flow} orphans={orphans}")
                if "code" in resp_data:
                    print(f"API error code: {resp_data.get('code')}")
                    print(f"Detail: {resp_data.get('detail')}")
            elif isinstance(resp_data, str):
                print(f"Response text: {resp_data[:500]}")
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Raw: {result_str[:500]}")
    finally:
        # Cleanup temp dir
        try:
            proc.terminate()
        except Exception:
            pass
        shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
