#!/usr/bin/env python3
"""
Kalnyes Growth — Morning Content Generator
Runs daily at 6:30 AM via GitHub Actions.
Generates 9 posts (3 pillars × 3 platforms) and writes to Google Sheets DAILY_QUEUE.
"""
import os
import sys
import json
import re
from datetime import datetime, date
import anthropic
from dotenv import load_dotenv

load_dotenv()

# Allow running from repo root or scripts/
sys.path.insert(0, os.path.dirname(__file__))
from sheets_helper import write_daily_queue, read_intel_feed, read_performance_feed

# ── Rotation config ───────────────────────────────────────────────────────────

NICHES = [
    {
        "name": "contractors",
        "display": "Contractors",
        "examples": "plumbers, electricians, HVAC technicians, roofers, painters, general contractors",
        "pain": "jobs going to competitors who look more established online",
        "desire": "being the go-to contractor in their city, consistent job flow",
    },
    {
        "name": "home_services",
        "display": "Home Services",
        "examples": "landscapers, house cleaners, pest control, pool service, pressure washing",
        "pain": "seasonal income gaps, not being found when homeowners search",
        "desire": "fully booked schedule, recurring clients, looking professional",
    },
    {
        "name": "events_party",
        "display": "Events & Party Rental",
        "examples": "party rental companies, caterers, photographers, DJs, event venues",
        "pain": "losing bookings to bigger companies, no-shows from non-serious inquiries",
        "desire": "more deposit-first bookings, looking premium, filling the calendar",
    },
    {
        "name": "personal_services",
        "display": "Personal Services",
        "examples": "barbers, hair salons, spas, gyms, personal trainers, tutors, tax preparers",
        "pain": "clients going to chain businesses that 'look' more professional",
        "desire": "loyal client base, full appointment book, referrals that convert",
    },
]

THEMES = [
    {"days": range(1, 8), "name": "no_trust", "angle": "business owners lose customers because they don't look trustworthy online yet — no website, outdated site, or unprofessional presence loses jobs daily without the owner ever knowing"},
    {"days": range(8, 15), "name": "social_proof", "angle": "real client results and case studies — Pepe's Party Rental now gets new clients every month from their website, a cleaning company doubled inquiries, a contractor went from word-of-mouth-only to fully booked"},
    {"days": range(15, 22), "name": "objection_kill", "angle": "dismantling the most common objections: 'I get enough referrals', 'I don't need a website', 'Facebook is enough', 'websites are too expensive', 'it won't work for my type of business'"},
    {"days": range(22, 29), "name": "dream_outcome", "angle": "paint the picture of what their business looks like after — phone ringing while they sleep, professional image that commands premium prices, leads that already trust them before the first call"},
    {"days": range(29, 32), "name": "urgency", "angle": "May is peak season — competitors are investing now, only 3 spots left this month, every week without a site is revenue handed to competitors"},
]

PILLARS = {
    "A": {"name": "Educate", "post_time": "08:00", "goal": "teach something valuable, no pitch — position as the expert they trust"},
    "B": {"name": "Prove", "post_time": "12:00", "goal": "social proof, results, before/after — make the transformation feel real and achievable"},
    "C": {"name": "Convert", "post_time": "17:00", "goal": "direct offer with a clear CTA — book a strategy call, limited spots, urgency"},
}

PLATFORMS = {
    "facebook": {
        "rules": "2–6 paragraphs, conversational, storytelling works, can be longer. End with a CTA to DM or comment a keyword. No markdown bold/italic.",
        "hashtags": "5–10 max, at the very end",
    },
    "instagram": {
        "rules": "Hook line must stop the scroll (first 1–2 lines). Use line breaks for readability. 150–300 words. CTA to DM a keyword or save the post.",
        "hashtags": "15–20 relevant local business hashtags at the end",
    },
    "linkedin": {
        "rules": "CRITICAL: Write for a PERSONAL PROFILE not a company page (13x more reach). First line must be a bold standalone hook that stops the scroll. Short paragraphs, 1-2 sentences max. 150–250 words. NO external links in the post body — the Calendly link will be added in the first comment automatically. End with a question or CTA that invites comments.",
        "hashtags": "3–5 professional hashtags",
    },
}

# ── Date math ─────────────────────────────────────────────────────────────────

def get_rotation() -> dict:
    start = date(2026, 5, 13)  # day 1 of rotation
    delta = (date.today() - start).days
    week_num = (delta // 7) % 4
    day_num = (delta % 28) + 1  # 1–28 cycling

    niche = NICHES[week_num]

    theme = next(
        (t for t in THEMES if day_num in t["days"]),
        THEMES[4]  # fallback to urgency
    )

    return {
        "week_num": week_num + 1,
        "day_num": day_num,
        "niche": niche,
        "theme": theme,
    }


# ── Prompt builder ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the content strategist and copywriter for Kalnyes Growth, a web design agency serving local business owners across the United States.

## Agency context
- Founder built this after helping his father's business (Pepe's Party Rental) get new clients every month via a website
- Pricing: $1,497 / $2,997 / $4,997 — transparent, posted publicly (anti-scam positioning)
- Client owns their files from day 1. 50/50 payment split. No monthly fees unless they want maintenance
- Every site includes AI chatbot (captures 35–40% of after-hours leads), mobile-first, Google-optimized
- GEO (Generative Engine Optimization): optimized for ChatGPT, Perplexity, Google AI Overviews — a real differentiator no competitor markets yet
- CTA is always a 15-minute strategy call via Calendly
- Website: kalnyesgrowth.com

## Competitive intelligence (2025–2026 landscape)
- Main customer emotional wound: they've been burned before by web designers — paid thousands, got nothing, or site went offline when they stopped paying monthly fees
- AI search traffic grew 123% in 2025 — 800M weekly ChatGPT users search local businesses. Being in AI search results = massive edge
- 62% of service business calls go unanswered. AI chatbot captures those leads 24/7, 2.4x better than contact forms
- Business owners think "I get enough referrals" — but referrals plateau, and the next generation of customers searches Google first, not Facebook
- Facebook pages are not websites — no Google indexing, no real trust signal, disappears if account gets banned
- Competitors (web agencies) typically charge $3K–$10K+ with $200–$500/month retainers and clients never own their site
- Anti-scam transparency = biggest differentiator: show price upfront, no contracts, own files from day 1

## Brand voice
- Direct, honest, no fluff. Write like a real person, not a marketing department
- Empathy first — acknowledge their reality before pitching
- Never say "digital presence" or "online footprint" or "leverage" — sounds corporate
- Use specific numbers and specifics (62%, 4 seconds, $400, 5 days) over vague claims
- No em dashes. Use commas, periods, or colons instead
- Storytelling > lecturing. Show, don't tell
- Reference Pepe's Party Rental as a real case study when relevant (party rental, any niche)

## Image prompt style
- Photorealistic, editorial photography, no text in image, authentic real people
- Diverse business owners (Hispanic, Black, white — rotate naturally)
- Scenarios: business owners at desks at night, phones showing Google searches, before/after website comparisons, phone notifications of new leads
- Mood: frustrated (before) or relieved/proud (after)
- Never generic stock photo vibes — cinematic and specific"""


def build_user_prompt(pillar_key: str, platform: str, rotation: dict, intel: str, performance: str) -> str:
    niche = rotation["niche"]
    theme = rotation["theme"]
    pillar = PILLARS[pillar_key]
    plat = PLATFORMS[platform]

    return f"""Generate one social media post for today.

## Parameters
- Platform: {platform.upper()}
- Pillar: {pillar_key} — {pillar['name']} ({pillar['goal']})
- Niche: {niche['display']} ({niche['examples']})
- Theme: {theme['name']} — {theme['angle']}
- Post time: {pillar['post_time']}

## Platform rules
{plat['rules']}
Hashtags: {plat['hashtags']}

## Fresh intel (use if relevant)
{intel}

## Performance feedback (adjust based on this)
{performance}

## Output format — respond ONLY with valid JSON, no other text:
{{
  "copy": "full post copy here",
  "hashtags": "hashtag string here",
  "image_prompt": "detailed cinematic image generation prompt (50–80 words, photorealistic, no text in image)"
}}"""


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_post(client: anthropic.Anthropic, pillar: str, platform: str, rotation: dict, intel: str, performance: str) -> dict | None:
    prompt = build_user_prompt(pillar, platform, rotation, intel, performance)
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error for {pillar}/{platform}: {e}", file=sys.stderr)
        print(f"  Raw: {raw[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ❌ API error for {pillar}/{platform}: {e}", file=sys.stderr)
        return None


def main():
    print(f"\n🚀 Kalnyes Growth — Morning Content | {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    rotation = get_rotation()
    niche = rotation["niche"]
    theme = rotation["theme"]
    print(f"   Week {rotation['week_num']} | Day {rotation['day_num']} | Niche: {niche['display']} | Theme: {theme['name']}")

    # Read self-updating feeds
    print("\n📊 Reading feeds from Google Sheets...")
    intel = read_intel_feed(last_n=10)
    performance = read_performance_feed()

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    posts = []
    today = datetime.now().strftime("%Y-%m-%d")
    post_num = 0

    for pillar_key, pillar_data in PILLARS.items():
        for platform in ["facebook", "instagram", "linkedin"]:
            post_num += 1
            print(f"\n[{post_num}/9] Pillar {pillar_key} ({pillar_data['name']}) → {platform.upper()}")

            result = generate_post(client, pillar_key, platform, rotation, intel, performance)
            if not result:
                continue

            post_id = f"{today}_{pillar_key}_{platform}"
            posts.append({
                "id": post_id,
                "date": today,
                "week_num": rotation["week_num"],
                "day_num": rotation["day_num"],
                "niche": niche["name"],
                "theme": theme["name"],
                "pillar": pillar_key,
                "platform": platform,
                "copy": result.get("copy", ""),
                "hashtags": result.get("hashtags", ""),
                "image_prompt": result.get("image_prompt", ""),
                "post_time": pillar_data["post_time"],
                "status": "pending",
                "post_id": "",
                "posted_at": "",
            })
            print(f"  ✅ Generated ({len(result.get('copy',''))} chars)")

    print(f"\n📝 Writing {len(posts)} posts to Google Sheets DAILY_QUEUE...")
    write_daily_queue(posts)

    # Also save local backup
    backup_path = os.path.join(os.path.dirname(__file__), f"../output/posts_{today}.json")
    with open(backup_path, "w") as f:
        json.dump(posts, f, indent=2)
    print(f"   Backup saved: output/posts_{today}.json")

    print(f"\n✅ Done. {len(posts)}/9 posts queued for today.\n")


if __name__ == "__main__":
    main()
