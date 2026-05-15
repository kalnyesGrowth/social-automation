"""Google Sheets helper — read/write DAILY_QUEUE and feed sheets."""
import os
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_ID = os.environ["GOOGLE_SHEETS_ID"]
SA_PATH = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "./service_account.json")


def get_client():
    creds = Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def get_sheet(tab_name: str):
    gc = get_client()
    return gc.open_by_key(SHEET_ID).worksheet(tab_name)


# ── DAILY_QUEUE ──────────────────────────────────────────────────────────────

QUEUE_HEADERS = [
    "id", "date", "week_num", "day_num", "niche", "theme",
    "pillar", "platform", "copy", "hashtags",
    "image_prompt", "post_time", "status", "post_id", "posted_at",
]


def write_daily_queue(posts: list[dict]):
    ws = get_sheet("DAILY_QUEUE")
    today = datetime.now().strftime("%Y-%m-%d")

    rows_to_append = []
    for p in posts:
        row = [p.get(h, "") for h in QUEUE_HEADERS]
        rows_to_append.append(row)

    ws.append_rows(rows_to_append, value_input_option="RAW")
    print(f"  ✅ Wrote {len(rows_to_append)} posts to DAILY_QUEUE")


def update_post_status(row_index: int, status: str, post_id: str = ""):
    """Called by Make.com webhook or manually after posting."""
    ws = get_sheet("DAILY_QUEUE")
    status_col = QUEUE_HEADERS.index("status") + 1
    post_id_col = QUEUE_HEADERS.index("post_id") + 1
    posted_at_col = QUEUE_HEADERS.index("posted_at") + 1

    ws.update_cell(row_index, status_col, status)
    ws.update_cell(row_index, post_id_col, post_id)
    ws.update_cell(row_index, posted_at_col, datetime.now().isoformat())


# ── INTEL_FEED ───────────────────────────────────────────────────────────────

def read_intel_feed(last_n: int = 10) -> str:
    try:
        ws = get_sheet("INTEL_FEED")
        rows = ws.get_all_records()
        recent = rows[-last_n:] if len(rows) >= last_n else rows
        if not recent:
            return "No intel yet."
        lines = [f"- [{r.get('date','')}] {r.get('insight','')}" for r in recent]
        return "\n".join(lines)
    except Exception as e:
        return f"Intel unavailable: {e}"


def write_intel_feed(insights: list[dict]):
    ws = get_sheet("INTEL_FEED")
    for item in insights:
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d"),
            item.get("insight", ""),
            item.get("source", ""),
            item.get("angle", ""),
        ], value_input_option="RAW")
    print(f"  ✅ Wrote {len(insights)} intel items")


# ── PERFORMANCE_FEED ─────────────────────────────────────────────────────────

def read_performance_feed() -> str:
    try:
        ws = get_sheet("PERFORMANCE_FEED")
        rows = ws.get_all_records()
        if not rows:
            return "No performance data yet."
        last = rows[-1]
        return (
            f"Week of {last.get('week','?')}: "
            f"Top post type={last.get('top_post_type','?')}, "
            f"What worked={last.get('what_worked','?')}, "
            f"What flopped={last.get('what_flopped','?')}, "
            f"Angle update={last.get('angle_update','?')}"
        )
    except Exception as e:
        return f"Performance data unavailable: {e}"


def write_performance_feed(data: dict):
    ws = get_sheet("PERFORMANCE_FEED")
    ws.append_row([
        data.get("week", ""),
        data.get("top_post_type", ""),
        data.get("what_worked", ""),
        data.get("what_flopped", ""),
        data.get("angle_update", ""),
        data.get("notes", ""),
    ], value_input_option="RAW")
    print("  ✅ Wrote performance data")
