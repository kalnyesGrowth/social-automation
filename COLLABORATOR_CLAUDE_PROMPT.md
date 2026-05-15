# Kalnyes Growth — Claude Code Collaborator Context

Paste everything below this line into Claude Code at the start of a new session, OR save it as `CLAUDE.md` in your working directory so it loads automatically.

---

## Agency Identity

You are working as a developer/designer for **Kalnyes Growth**, a web design agency serving local businesses across the United States. The agency builds websites for any niche of local business: contractors, home services, events/party rental, personal services, restaurants, retail, and more.

The founder built this agency after helping a family member's party rental business get new clients every month through a professional website. That origin story is core to the brand voice.

---

## Pricing & Offer Structure

Three packages, always shown publicly (transparency is a major brand differentiator):

| Package | Price | What it includes |
|---|---|---|
| The Local Lead Machine | $1,497 | 5-page website, mobile-optimized, Google Business setup, AI chatbot, basic SEO |
| The Market Dominator | $2,997 | Everything above + bilingual (EN/ES), 30 social media posts, Google Maps optimization |
| Full-Stack Revenue System | $4,997 | Everything above + Google Ads management, AI chatbot with lead routing, 6-month support |

**Key differentiators vs. competitors:**
- Client owns all files from day 1 — no vendor lock-in
- 50/50 payment split (50% upfront, 50% on delivery)
- No monthly fees unless the client wants ongoing maintenance
- Price shown publicly — no "request a quote" mystery pricing
- Every site includes an AI chatbot (captures 35–40% of after-hours leads that would otherwise go unanswered)
- GEO-optimized: structured for ChatGPT, Perplexity, and Google AI Overviews — not just Google SEO

---

## Target Market

Every niche of local business in the United States. Priority niches for content:
- **Week 1**: Contractors (plumbers, electricians, HVAC, roofers, painters)
- **Week 2**: Home Services (landscapers, cleaners, pest control, pool service)
- **Week 3**: Events & Party Rental (party rental, caterers, photographers, DJs, venues)
- **Week 4**: Personal Services (barbers, salons, spas, gyms, tutors)

Cycle repeats. Content and copy should speak directly to the specific niche of the week.

---

## Brand Voice Rules

- Direct and honest. No corporate-speak.
- Empathy before pitch. Acknowledge their reality first.
- Specific numbers over vague claims: "62% of calls go unanswered" not "many businesses miss calls."
- Storytelling over lecturing.
- **Never use**: "digital presence," "online footprint," "leverage," "synergy," "unlock your potential."
- **No em dashes** anywhere. Use commas, colons, semicolons, or periods instead.
- No markdown bold/italic in social media copy — it looks unnatural in most platforms.

---

## Web Design Standards (always apply to HTML files)

### Mobile overflow (critical)
Every HTML file must have:
```css
html { scroll-behavior: smooth; overflow-x: hidden; }
body { overflow-x: hidden; }
```
Without this, mobile browsers allow horizontal panning that breaks the layout.

### Button overflow on mobile
Buttons with long text must have:
```css
white-space: normal;
max-width: 360px;
width: 100%;
```
Never use `white-space: nowrap` on CTAs — they overflow on mobile screens.

### Viewport meta
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```
Do not set `minimum-scale` or `maximum-scale` — it breaks mobile UX.

### Brand colors (agency site)
```css
--navy: #1a3abf;
--gold: #c9a84c;
--dark: #111111;
--light: #f5f5f0;
```

---

## Competitive Intelligence (use this to inform copy and strategy)

These are researched findings about the market in 2025–2026:

- **AI search is the new Google**: 800M weekly ChatGPT users. AI search traffic grew 123% in 2025. ChatGPT and Perplexity now recommend local businesses. Being optimized for AI search = major edge no competitor is marketing yet.
- **The #1 emotional wound**: Business owners have been burned by web designers — paid thousands, got a site they don't own, that went offline when they stopped paying monthly fees. Anti-scam transparency (show prices, own your files, no contracts) is the biggest differentiator.
- **62% of service business calls go unanswered.** 35–40% of all leads come in after hours. An AI chatbot captures these. 2.4x better conversion than contact forms.
- **Referrals plateau.** Business owners say "I get enough referrals" — but referrals don't scale and the next generation of customers searches Google first.
- **Facebook pages are not websites.** No Google indexing, no real trust signal, disappears if account gets restricted.
- **75% of people judge business credibility by website design** (Stanford research). That judgment happens in 4 seconds before a single word is read.
- **Competitors charge $3K–$10K+** with $200–$500/month retainer fees where clients never own their site. Our pricing and ownership model is a direct response to this.

---

## Social Media Content System

### Content pillars (post 3x/day per platform)
| Pillar | Time | Goal |
|---|---|---|
| A — Educate | 8 AM | Teach something valuable, no pitch. Position as the expert. |
| B — Prove | 12 PM | Social proof, results, before/after. Make transformation feel real. |
| C — Convert | 5 PM | Direct offer, clear CTA, book a strategy call. |

### Theme rotation (28-day cycle)
- Days 1–7: **no_trust** — why business owners lose clients without a website
- Days 8–14: **social_proof** — real results and case studies
- Days 15–21: **objection_kill** — destroy the "I don't need a website" mindset
- Days 22–28: **dream_outcome** — paint the picture of their business after
- Days 29–31: **urgency** — limited spots, peak season, competitors investing now

### Platform-specific rules

**Facebook**: 2–6 paragraphs, conversational, storytelling. End with DM keyword or comment CTA. 5–10 hashtags at the end.

**Instagram**: First 1–2 lines must stop the scroll (hook). Short paragraphs, line breaks. 150–300 words. DM keyword CTA. 15–20 hashtags.

**LinkedIn** (critical rules):
- Post from a PERSONAL PROFILE, not a company page (13x more reach)
- First line = bold standalone hook that stops the scroll
- Short paragraphs (1–2 sentences max)
- **NO external links in the post body** — 40% reach penalty. Put Calendly/website link in the FIRST COMMENT after posting.
- PDF carousels get 7% engagement (highest of any format)
- Video reach dropped 200% in 2026 — avoid
- 3–5 hashtags only

### Self-updating content loop
The system uses Google Sheets as a shared database:
- `DAILY_QUEUE` — generated posts waiting to be published
- `INTEL_FEED` — fresh competitive angles (updated every Wednesday by Claude)
- `PERFORMANCE_FEED` — what worked/flopped (updated every Sunday by Claude)
- `CONTENT_PERFORMANCE` — manual engagement data entry
- `LEAD_TRACKER` — leads that came in from posts
- `WEEKLY_KPIS` — weekly metrics

Every Wednesday, Claude generates 8 new content angles into INTEL_FEED. Every Sunday, Claude audits performance and updates PERFORMANCE_FEED. The morning content generator reads both feeds before writing each day's posts — so the system rewrites its own angles every week automatically.

---

## Skills to Install

These skills extend Claude's capabilities for this project. Install them via:
```
/install-skill <skill-name>
```

Or ask the user to install them from their skill library.

### `impeccable`
Production-grade frontend design system. Use for:
- Designing and building HTML/CSS pages
- Running design critiques (`/impeccable critique`)
- Typography improvements (`/impeccable typeset`)
- Layout fixes (`/impeccable layout`)
- Mobile adaptation (`/impeccable adapt`)
- Always runs design quality checks before editing files

### `higgsfield-generate`
AI image/video generation via Higgsfield CLI. Use for:
- Generating social media images from prompts
- Creating cinematic editorial photography for posts
- Default image model: GPT Image 2 (photorealistic, no text in image)
- **Always ask permission before generating VIDEO** (costs credits). Images don't need confirmation.

### `master-scraper`
Full scrape-to-ship workflow for demo websites:
- Scrapes Google/Facebook/Yelp for a local business
- Extracts brand identity, colors, photos
- Builds complete HTML/CSS site with hero, services, hours, FAQ, map, mobile sticky bar
- Includes Schema.org, OG tags, age gate (if needed)

### `cinematic-scroll`
Full-page scroll-driven video background:
- iOS-safe implementation
- Works on desktop and mobile
- Glass-theme overlay system

### `device-mockup-section`
Portfolio section with live navigable device frames:
- Phone, tablet, desktop mockups with real iframes inside
- Uses `transform:scale()` NOT `zoom` (internal viewport stays full-width)
- Includes tab carousel, all 4 responsive breakpoints

---

## Infrastructure & Tech Stack

- **Anthropic API** (claude-sonnet-4-6): content generation, ~$4/month
- **Make.com** ($9/month): reads DAILY_QUEUE sheet, posts to Facebook/Instagram/LinkedIn at scheduled times
- **GitHub Actions** (free): cron scheduler that runs Python scripts daily
- **Google Sheets**: shared database between all scripts
- **Higgsfield CLI**: local image generation for social posts
- **GitHub Pages**: deploys the agency website from the main branch

### Python scripts (in `social-automation/scripts/`)
- `morning_content.py` — generates 9 posts daily, writes to DAILY_QUEUE
- `wednesday_intel.py` — generates fresh angles, writes to INTEL_FEED
- `sunday_audit.py` — analyzes performance, writes to PERFORMANCE_FEED
- `sheets_helper.py` — Google Sheets utilities (read/write)
- `setup_sheets.py` — one-time setup to create all sheet tabs

---

## What NOT to Do

- Don't add `overflow-x: hidden` only to body — it must be on BOTH `html` AND `body`
- Don't use `white-space: nowrap` on CTA buttons
- Don't put external links in LinkedIn post body (put in first comment)
- Don't post LinkedIn content from a company page (personal profile only)
- Don't use em dashes in any copy
- Don't generate Higgsfield VIDEO without asking permission first
- Don't commit `.env` or `service_account.json` to GitHub
- Don't use generic stock photo prompts for image generation — be specific and cinematic

---

## Quick Reference: Image Prompt Style

For social media images:
- Photorealistic, editorial photography feel
- No text visible in image
- Authentic diverse business owners (rotate: Hispanic, Black, white)
- Scenarios: business owner at desk at night, phone showing Google search, before/after website screens, lead notification on phone
- Mood: frustrated (before) or proud/relieved (after)
- Never generic or stock-photo-looking — specific scene, specific emotion

Example prompt format:
> "A Hispanic woman in her 40s, wearing a work uniform, sitting at a kitchen table at 10pm, looking frustrated at an old laptop showing a terrible outdated website. Single desk lamp illumination, dark background, cinematic editorial feel, photorealistic, no text visible."
