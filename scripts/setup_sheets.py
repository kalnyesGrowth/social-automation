#!/usr/bin/env python3
"""
One-time setup: creates all required sheets with headers in the Google Spreadsheet.
Run once after creating your sheet: python3 scripts/setup_sheets.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))
from sheets_helper import get_client, SHEET_ID, QUEUE_HEADERS

SHEETS = {
    "DAILY_QUEUE": QUEUE_HEADERS,
    "CONTENT_PERFORMANCE": [
        "date", "post_id", "platform", "pillar", "niche", "theme",
        "likes", "comments", "shares", "reach", "clicks", "leads_generated", "notes"
    ],
    "INTEL_FEED": ["date", "insight", "source", "angle"],
    "PERFORMANCE_FEED": ["week", "top_post_type", "what_worked", "what_flopped", "angle_update", "notes"],
    "LEAD_TRACKER": [
        "date", "source_platform", "source_post_id", "name", "business_type",
        "city", "state", "contact", "status", "booked_call", "closed", "revenue"
    ],
    "WEEKLY_KPIS": [
        "week", "total_reach", "total_engagements", "dm_leads",
        "calls_booked", "proposals_sent", "clients_closed", "revenue"
    ],
}


def main():
    print("\n🔧 Kalnyes Growth — Google Sheets Setup")
    print(f"   Sheet ID: {SHEET_ID}\n")

    gc = get_client()
    spreadsheet = gc.open_by_key(SHEET_ID)

    existing_tabs = [ws.title for ws in spreadsheet.worksheets()]
    print(f"   Existing tabs: {existing_tabs}")

    for tab_name, headers in SHEETS.items():
        if tab_name in existing_tabs:
            print(f"   ⏭  {tab_name} already exists — skipping")
            continue

        ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
        ws.append_row(headers, value_input_option="RAW")
        print(f"   ✅ Created: {tab_name} ({len(headers)} columns)")

    print("\n✅ Setup complete. All sheets ready.\n")
    print("   Next steps:")
    print("   1. Share the spreadsheet with your service account email (Editor access)")
    print("   2. Copy the Sheet ID into your .env file")
    print("   3. Run: python3 scripts/morning_content.py")


if __name__ == "__main__":
    main()
