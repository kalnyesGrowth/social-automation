#!/usr/bin/env python3
"""
Kalnyes Growth — Instagram Carousel Image Generator
Run locally each morning after morning_content.py has written to DAILY_QUEUE.
Reads today's pending Instagram posts, generates 3 images each via Higgsfield CLI,
and writes the public CDN URLs back to the sheet.

Usage:
    python3 scripts/generate_ig_images.py
    python3 scripts/generate_ig_images.py --date 2026-05-15   # specific date
"""
import os
import sys
import json
import subprocess
import re
import argparse
from datetime import date as date_cls

sys.path.insert(0, os.path.dirname(__file__))
from sheets_helper import get_today_instagram_rows, update_image_urls
from dotenv import load_dotenv

load_dotenv()

FALLBACK_PROMPTS = [
    "A Hispanic male contractor in his 40s, standing in front of a finished home exterior, smiling confidently while holding a phone showing a 5-star Google review. Golden hour light, cinematic editorial, photorealistic, no text visible.",
    "Close-up of a smartphone screen showing a sleek professional contractor website with a phone call button, resting on a wooden workbench with tools in background. Shallow depth of field, photorealistic, no text visible in scene.",
    "A business owner at a kitchen table late at night, opening their laptop to a notification: 3 new leads. Relief and satisfaction on their face. Single lamp illumination, dark background, cinematic, photorealistic, no text.",
]


def generate_image(prompt: str, slide_num: int) -> str:
    """Call Higgsfield CLI and return the CDN image URL."""
    cmd = [
        "higgsfield", "generate", "create", "gpt_image_2",
        "--prompt", prompt,
        "--aspect_ratio", "4:5",
        "--wait",
    ]
    print(f"      Slide {slide_num}: generating...", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise RuntimeError(f"Higgsfield exit {result.returncode}: {result.stderr.strip()[:300]}")

    output = result.stdout + result.stderr
    urls = re.findall(r'https://[^\s"\'<>]+', output)
    # Filter to likely image CDN URLs
    img_urls = [u for u in urls if any(ext in u for ext in [".jpg", ".jpeg", ".png", ".webp"]) or "cdn" in u or "media" in u]
    if img_urls:
        return img_urls[-1]
    if urls:
        return urls[-1]
    raise RuntimeError(f"No URL found in output:\n{output[:400]}")


def parse_prompts(raw: str, fallback: list[str]) -> list[str]:
    """Parse image_prompt field — JSON array or plain string."""
    if not raw or not raw.strip():
        return fallback

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list) and parsed:
            prompts = [str(p).strip() for p in parsed if p]
            while len(prompts) < 3:
                prompts.append(prompts[-1])
            return prompts[:3]
        if isinstance(parsed, str):
            return [parsed] * 3
    except (json.JSONDecodeError, TypeError):
        pass

    # Plain string
    return [raw.strip()] * 3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date_cls.today().strftime("%Y-%m-%d"))
    args = parser.parse_args()
    today = args.date

    print(f"\n🎨 Kalnyes Growth — IG Carousel Image Generator | {today}")

    rows = get_today_instagram_rows(today)
    if not rows:
        print("No pending Instagram posts found for today.\n")
        return

    print(f"Found {len(rows)} post(s) to process.\n")

    for row_idx, row in rows:
        post_id = row.get("id", f"row_{row_idx}")
        pillar = row.get("pillar", "?")
        print(f"[Row {row_idx}] {post_id} | Pillar {pillar}")

        raw_prompt = row.get("image_prompt", "")
        prompts = parse_prompts(raw_prompt, FALLBACK_PROMPTS)

        urls = ["", "", ""]
        for i, prompt in enumerate(prompts):
            try:
                url = generate_image(prompt, i + 1)
                urls[i] = url
                print(f"      ✅ {url[:70]}...")
            except Exception as e:
                print(f"      ❌ Slide {i+1} failed: {e}")

        update_image_urls(row_idx, urls[0], urls[1], urls[2])
        print(f"   ✅ URLs written to sheet.\n")

    print(f"Done. {len(rows)} post(s) processed.\n")


if __name__ == "__main__":
    main()
