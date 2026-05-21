#!/usr/bin/env python3
"""
Push the corrected Make.com blueprint using live session cookies from Chrome.
Requires Keychain access (macOS prompt may appear — click Allow).
"""
import json, sys, urllib.request, urllib.error, os

sys.path.insert(0, os.path.dirname(__file__))

try:
    import browser_cookie3
except ImportError:
    print("Install: pip3 install browser-cookie3")
    sys.exit(1)

SCENARIO_ID = 5071326
BLUEPRINT_FILE = os.path.join(os.path.dirname(__file__), '..', 'make_fixed_blueprint.json')

print("Extracting Chrome session cookies for us2.make.com...")
try:
    cj = browser_cookie3.chrome(domain_name='us2.make.com')
    cookies = {c.name: c.value for c in cj}
except Exception as e:
    print(f"Keychain access failed: {e}")
    print("Make sure Chrome is not running and try again, or click Allow on the Keychain popup.")
    sys.exit(1)

xsrf = cookies.get('XSRF-TOKEN', '')
if not xsrf:
    print("No XSRF-TOKEN found — are you logged into us2.make.com in Chrome?")
    sys.exit(1)

print(f"Got {len(cookies)} cookies, XSRF: {xsrf[:20]}...")
cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())

headers = {
    'Accept': 'application/json',
    'X-XSRF-TOKEN': xsrf,
    'x-imt-apps-version': '2',
    'Content-Type': 'application/json',
    'Cookie': cookie_str,
}

def call(method, path, body=None):
    url = f"https://us2.make.com/api/v2{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()[:400]
        return e.code, {'error': body_text}

# Load the fixed blueprint
with open(BLUEPRINT_FILE) as f:
    fixed = json.load(f)
new_bp = fixed['blueprint']

print(f"Blueprint flow to push: {[m['id'] for m in new_bp['flow']]}")

# PUT blueprint
print("\nPushing blueprint...")
status, resp = call('PUT', f'/scenarios/{SCENARIO_ID}/blueprint', {'blueprint': new_bp})
print(f"  → {status} | {resp.get('code', resp)}")
if status not in (200, 201) or resp.get('code') != 'OK':
    print("  Full response:", json.dumps(resp, indent=2)[:600])
    sys.exit(1)

# Verify
print("\nVerifying...")
status, data = call('GET', f'/scenarios/{SCENARIO_ID}/blueprint')
updated = data['response']['blueprint']
flow_ids = [m['id'] for m in updated['flow']]
orphan_ids = [[m['id'] for m in c] for c in updated['metadata']['designer']['orphans']]
print(f"  Flow:    {flow_ids}")
print(f"  Orphans: {orphan_ids}")
print(f"  Instant: {updated['metadata']['instant']}")

if flow_ids == [2, 3, 4] and updated['metadata']['instant']:
    print("\n✅ Make.com scenario is fixed!")
    print("   Go to Make.com → open the scenario → click Run once to test.")
else:
    print(f"\n⚠️  Unexpected flow IDs: {flow_ids} — check Make.com editor")
