#!/bin/bash
# Wrapper for launchd — sets up PATH so higgsfield (nvm node) is found
export PATH="/Users/jessyt_sw/.nvm/versions/node/v24.15.0/bin:/usr/local/bin:/usr/bin:/bin"
export HOME="/Users/jessyt_sw"

cd /Users/jessyt_sw/web-design-clients/social-automation

# Activate venv if present, otherwise use system python3
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

python3 scripts/generate_ig_images.py
