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
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
