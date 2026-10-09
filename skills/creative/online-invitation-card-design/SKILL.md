---
name: online-invitation-card-design
description: Design and render high-resolution digital invitation cards, announcements, and posters optimized for mobile social chat sharing (Zalo, Messenger, Telegram) using HTML/CSS + Playwright.
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [invitation, card, poster, mobile-design, playwright, html2image, creative, graphic-design]
    related_skills: [claude-design, popular-web-designs]
---

# Online Digital Invitation & Event Card Design

Workflow and typography standards for creating digital invitation cards, milestone posters, and event announcements optimized specifically for sharing over mobile messaging platforms (Zalo, Telegram, Messenger, Instagram/Facebook Stories).

## Support Files & Templates
- `templates/mobile_hero_card.html` — Starter full-bleed mobile template (huge photo + giant bold text).
- `templates/magazine_cover_card.html` — Editorial magazine cover template (Baby Vogue / Lookbook style).
- `references/omniroute_image_generation.md` — OmniRoute (:20129) image provider behaviors (`antigravity` vs `codex` vs `chatgpt-web`).

## Core Requirements & Mobile-First Invariants

Unlike print documents (which rely on delicate 10pt–14pt text and balanced margins), digital cards viewed inside mobile messaging bubbles MUST be readable immediately without zooming:

1. **Standard Resolution**: 1080×1920 px (9:16 vertical story / full-screen mobile aspect ratio).
2. **Hero Subject Proportions (Anti-Small-Photo)**:
   - The primary subject/photo MUST occupy **45% to 60%** of the canvas (or top-half full bleed) to ensure faces and outfits are striking and recognizable at a glance.
3. **Typography Scale (Anti-Pinch-to-Zoom)**:
   - **Main Event Title / Greeting**: `90px – 120px` bold/script font (e.g., *Dancing Script*, *Alex Brush*).
   - **Main Highlight / Name / Badge**: `44px – 54px` ultra-bold (900 weight) with high-contrast background pill/badge.
   - **Time & Venue (Critical Info)**: `40px – 48px` extra-bold (e.g., `17:00 | 11.10.2026`, `168 XUÂN HỒNG`).
   - **Secondary Details / Lunar Dates**: `24px – 28px` italic/medium.
   - **Footer Invitation Message**: `24px – 28px` bold.

## Technical Execution (HTML + Playwright)

### 1. Self-Contained Template Structure
- Embed the user's photo using base64 data URI (`data:image/jpeg;base64,...`) to avoid local asset path resolution issues.
- Import web fonts (Google Fonts) with Vietnamese character support (`Montserrat`, `Playfair Display`, `Dancing Script`).

### 2. Playwright Headless Rendering Pattern (Windows)
When rendering HTML to PNG on Windows environments:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Use system installed Chrome or Edge channels to avoid missing standalone headless binaries
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1080, "height": 1920})
    page.goto(f"file:///{html_file_path}")
    page.wait_for_timeout(2000)  # Ensure Google web fonts load completely
    page.screenshot(path=output_png_path, full_page=True)
    browser.close()
```

## AI Image Generation & OmniRoute Behaviors

When generating backgrounds or AI illustrations for cards:
- **Primary Generator**: Route via OmniRoute (`http://127.0.0.1:20129/v1/images/generations`) with model `antigravity/gemini-3.1-flash-image`. It runs in < 5 seconds and returns base64 images directly.
- **Prompt Formulation**: Always request empty/clean center space (`no text, no words, empty background`) when generating backdrops to composite HTML text on top, avoiding AI text distortion.

### Common Pitfalls & Traps
1. **The Print vs Online Trap**: When the user mentions "gửi online / chia sẻ Zalo/Facebook", NEVER design with traditional subtle typography. Users will immediately reject it as unreadable on mobile screens. Jump directly to high-contrast large fonts (40px+) and 50%+ hero photo area.
2. **Pure Generative AI Art vs Programmatic HTML Compositing (Critical Intent Distinction)**:
   - When a user asks to "gen ảnh / làm vài kiểu để coi" referencing previous AI-generated art (e.g., 3D Pixar, watercolor paintings), they want **pure AI image generation (Gemini/Imagen/DALL-E)** without any programmatic HTML/CSS text compositing or photo cutting. Do NOT substitute programmatic cards when they explicitly ask for AI artwork ("T cần gemini làm, hermes đừng can thiệp").
   - Conversely, use HTML/CSS + Playwright ONLY when the user needs exact Vietnamese text (time, venue, baby full name) composited with a real photograph.
3. **The "Reskinning" Repetition Trap (Structural vs Cosmetic Diversity)**:
   - Changing background gradients, borders, or font colors on the identical vertical layout (Title -> Photo Box -> Info Box) will be immediately called out as *"y 1 kiểu na ná đổi mỗi màu nền"*.
   - When presenting multiple card concepts, differentiate the core **visual metaphor and structural layout**:
     * **Magazine Cover (Baby Vogue / Lookbook)**: Photo full bleed (100% canvas), top masthead typography, floating headline callouts, article-style info grid with barcode.
     * **Boarding Pass / VIP Ticket**: Airline ticket form factor with perforated tear-off stub, passenger name, route (0T -> 1T), gate (venue), departure time, barcode.
     * **Milestone Chalkboard / Storybook**: Infographic grid with badges, illustrated doodles, circular photo vignettes.
4. **Codex Luna Image Generation Trap**: Do NOT attempt image generation via `codex/gpt-5.6-luna` or `codex/gpt-5.6-sol`. The upstream Codex CLI endpoint (`/backend-api/codex/responses`) strips image generation tools (`tools: []`), returning empty text and causing OmniRoute HTTP 502 errors.
5. **ChatGPT Web Image Generation Trap**: `chatgpt-web` requests for images frequently hang or time out (> 180s) due to Cloudflare Sentinel / Turnstile bot protection on proxy IPs.
6. **Antigravity / Gemini Quota Limits**: `antigravity/gemini-3.1-flash-image` on Google Cloud Code shares daily per-project quota. When hitting `HTTP 429: You have exhausted your capacity on this model`, cooldown is typically ~2.5 to 3 hours. Do not repeatedly hammer the endpoint once a 429 quota exhaustion is returned.
