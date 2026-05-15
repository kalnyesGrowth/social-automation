#!/usr/bin/env python3
"""
Kalnyes Growth — Sunday Performance Audit
Runs every Sunday at 8 PM via GitHub Actions.
Reads CONTENT_PERFORMANCE sheet, uses Claude to analyze what worked, writes to PERFORMANCE_FEED.
"""
import os
import sys
import json
import re
from datetime import datetime, timedelta
import anthropic
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))
from sheets_helper import get_sheet, write_performance_feed, read_intel_feed

AUDIT_PROMPT_SYSTEM = """You are the performance analyst for Kalnyes Growth, a web design agency. You analyze weekly social media performance data to identify what content angles drive the most engagement and lead generation from local business owners."""

AUDIT_PROMPT_USER = """Analyze this week's social media performance data and extract actionable insights for next week's content.

## Performance data (this week):
{perf_data}

## Current intel feed (angles being tested):
{intel_data}

Identify:
1. Which post type/angle got the most engagement?
2. What emotional themes resonated (trust, social proof, urgency, education)?
3. What flopped and why?
4. One specific angle adjustment for next week

## Output format — respond ONLY with valid JSON:
{{
  "week": "{week}",
  "top_post_type": "which format/angle performed best",
  "what_worked": "specific insight about what drove engagement",
  "what_flopped": "what underperformed and the likely reason",
  "angle_update": "one specific adjustment to make next week",
  "notes": "any other observations"
}}"""


def read_performance_data() -> str:
    """Read this week's CONTENT_PERFORMANCE rows."""
    try:
        ws = get_sheet("CONTENT_PERFORMANCE")
        rows = ws.get_all_records()
        week_ago = datetime.now() - timedelta(days=7)
        recent = [
            r for r in rows
            if r.get("date", "") >= week_ago.strftime("%Y-%m-%d")
        ]
        if not recent:
            return "No performance data recorded this week yet. Use default patterns: educate posts typically outperform convert posts on LinkedIn, Instagram stories drive DM keywords."
        lines = []
        for r in recent:
            lines.append(
                f"Platform={r.get('platform','')} | Pillar={r.get('pillar','')} | "
                f"Likes={r.get('likes',0)} | Comments={r.get('comments',0)} | "
                f"Shares={r.get('shares',0)} | Reach={r.get('reach',0)} | Date={r.get('date','')}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Performance sheet error: {e}"


def main():
    print(f"\n📊 Kalnyes Growth — Sunday Audit | {datetime.now().strftime('%Y-%m-%d')}")

    perf_data = read_performance_data()
    intel_data = read_intel_feed(last_n=8)
    week_label = datetime.now().strftime("%Y-W%V")

    print("   Running performance analysis with Claude...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=AUDIT_PROMPT_SYSTEM,
            messages=[{
                "role": "user",
                "content": AUDIT_PROMPT_USER.format(
                    perf_data=perf_data,
                    intel_data=intel_data,
                    week=week_label,
                )
            }],
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        result = json.loads(raw)
    except Exception as e:
        print(f"  ❌ Failed: {e}", file=sys.stderr)
        sys.exit(1)

    write_performance_feed(result)

    print("\n✅ Performance audit complete.")
    print(f"   What worked: {result.get('what_worked', '')[:80]}")
    print(f"   What flopped: {result.get('what_flopped', '')[:80]}")
    print(f"   Next week adjustment: {result.get('angle_update', '')[:80]}\n")


if __name__ == "__main__":
    main()
