#!/usr/bin/env python3
"""
Kalnyes Growth — Wednesday Intel Script
Runs every Wednesday at 7 AM via GitHub Actions.
Uses Claude to surface fresh competitive angles and writes to INTEL_FEED sheet.
"""
import os
import sys
import json
import re
from datetime import datetime
import anthropic
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))
from sheets_helper import write_intel_feed, read_intel_feed

INTEL_PROMPT_SYSTEM = """You are a competitive intelligence analyst for Kalnyes Growth, a web design agency serving local businesses across the United States.

Your job is to identify the freshest angles and psychological insights that will make social media content resonate with local business owners in 2026. Focus on:
- What business owners complain about online right now (scams, bad ROI, wasted money)
- New developments in AI search that affect local businesses (ChatGPT local search, Google AI Overviews)
- What the best web agencies are NOT saying that leaves a gap
- Emotional triggers: fear of being left behind, pride in their craft, distrust of technology vendors
- Seasonal angles (current month: May — peak season for contractors, events, outdoor services)"""

INTEL_PROMPT_USER = """Generate 8 fresh content angles for Kalnyes Growth social media this week.

Each angle should be a specific, surprising, or emotionally charged insight that a local business owner would react to. Not generic tips — real observations that make someone stop scrolling.

## Recent angles already used (avoid repeating):
{existing_intel}

## Output format — respond ONLY with valid JSON array:
[
  {{
    "insight": "The specific insight or angle (1–2 sentences, punchy)",
    "source": "Where this insight comes from (e.g. 'ChatGPT now shows local business recommendations to 800M weekly users')",
    "angle": "How to frame this for social media copy (e.g. 'fear angle: your competitor is showing up in AI searches and you're not')"
  }}
]"""


def main():
    print(f"\n🧠 Kalnyes Growth — Wednesday Intel | {datetime.now().strftime('%Y-%m-%d')}")

    existing = read_intel_feed(last_n=20)
    print(f"   Existing intel loaded: {len(existing.splitlines())} items")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("   Calling Claude API for fresh angles...")
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=INTEL_PROMPT_SYSTEM,
            messages=[{
                "role": "user",
                "content": INTEL_PROMPT_USER.format(existing_intel=existing)
            }],
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        insights = json.loads(raw)
    except Exception as e:
        print(f"  ❌ Failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"   Generated {len(insights)} new angles")
    write_intel_feed(insights)

    print("\n✅ Intel feed updated. Tomorrow's content will use these angles.\n")
    for i, item in enumerate(insights, 1):
        print(f"   {i}. {item['insight'][:80]}...")


if __name__ == "__main__":
    main()
