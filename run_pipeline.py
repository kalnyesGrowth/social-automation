#!/usr/bin/env python3
"""
Kalnyes Growth — Social Media Content Pipeline
Reads posts_input.json, generates images via Higgsfield CLI, outputs final posts.
Usage: python3 run_pipeline.py --days 1 --input output/posts_input.json
"""

import argparse
import json
import subprocess
import os
import sys
from datetime import datetime

def run_higgsfield(prompt, output_path):
    """Generate image via Higgsfield CLI."""
    try:
        result = subprocess.run(
            [
                "higgsfield", "generate", "create", "gpt_image_2",
                "--prompt", prompt,
                "--aspect_ratio", "1:1",
                "--resolution", "2k",
                "--wait"
            ],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            # Extract URL from output
            for line in result.stdout.splitlines():
                if "https://" in line:
                    return line.strip()
        print(f"  Higgsfield error: {result.stderr[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Image gen failed: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--input", default="output/posts_input.json")
    args = parser.parse_args()

    input_path = os.path.join(os.path.dirname(__file__), args.input)

    with open(input_path) as f:
        posts = json.load(f)

    print(f"\n🚀 Kalnyes Growth Pipeline — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"   Posts to process: {len(posts)}\n")

    results = []
    image_posts = [p for p in posts if p.get("image_visual_prompt")]

    for i, post in enumerate(image_posts):
        print(f"[{i+1}/{len(image_posts)}] Generating image for: {post['id']}")
        url = run_higgsfield(post["image_visual_prompt"], post["id"])
        post["image_url"] = url
        status = "✅" if url else "⚠️  skipped"
        print(f"  {status} {url or 'no image'}")
        results.append(post)

    # Write enriched output
    output_enriched = input_path.replace("posts_input.json", "posts_ready.json")
    with open(output_enriched, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Pipeline complete. Ready posts saved to: {output_enriched}")
    print(f"   Posts with images: {sum(1 for p in results if p.get('image_url'))}/{len(image_posts)}")
    print(f"   Twitter: see output/tweets_today.txt for manual posting\n")

if __name__ == "__main__":
    main()
