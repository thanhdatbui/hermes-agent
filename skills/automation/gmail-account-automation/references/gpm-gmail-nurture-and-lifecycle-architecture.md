# GPM Gmail Nurture, Aging & Lifecycle Architecture

## 1. Core End-to-End Account Lifecycle
```
[Phase 1: S7 Hardware Genesis]
Reg Gmail on S7 (4G proxy) 
  -> Direct Email Signup ChatGPT on S7 Chrome (get OpenAI OTP to establish 1st non-Google activity)
  -> Enable 2FA TOTP on S7 via ADB 10-digit security code (Save 32-char secret to Excel as escape hatch)
  -> Soak >= 7 days on physical S7 with Auto-sync ON.

[Phase 2: Transition to GPM (PC) & ChatGPT-Web Harvest]
After 7 days on S7 -> Login to GPM Chromium profile via dedicated 4G mobile proxy port
  -> Fill Password + TOTP from Excel (completely bypasses phone SMS verification challenge)
  -> Immediately login & extract ChatGPT-Web session token (__Secure-next-auth.session-token) for OmniRoute pool
  -> Run noise injection (YouTube / Search) before closing profile.

[Phase 3: Automated Periodic Nurturing on GPM (cron_gpm_gmail_nurture.py)]
Runs purely on PC across scheduled hours (09:00, 11:00, 13:00, 15:00, 17:00, 19:00, 21:00).
  - Staggered Launch (45-60s jitter between profiles) + Proxy Exclusivity (1 profile per 4G port).
  - Frequency: 5-7 days per account rotation.
  - Task distribution (probabilistic, non-uniform):
    * 50% sessions: ONLY YouTube watch (90-120s real video playback, ad skip handling).
    * 30% sessions: ONLY Google News (45-60s human scroll) + Google Search (15-20s).
    * 20% sessions: Mixed (YouTube + News sequentially).

[Phase 4: GPM 7-Day Aging Gate Before Antigravity OAuth]
NEVER authorize Antigravity (Google Cloud Developer API) on session 1 of a new GPM profile.
Google Cloud Developer scopes are high-risk privilege escalation. Calling them on a new device triggers instant scrutiny.
Gate rule: `is_profile_aged_7_days(profile)` -> Only after profile has aged >= 7 days on PC and has established local browsing history/cookies is Antigravity OAuth permitted.
OAuth timeout: Configured to 120s (never 35s) to tolerate 4G mobile proxy resolution latency.
```

## 2. YouTube Nurture Mechanics & Pitfalls
- **Empty Feed Trap ("Thử tìm kiếm để bắt đầu")**:
  - Accounts with blank watch history show an empty home feed with 0 videos. F5/reload DOES NOT work.
  - **Fix**: Click `Shorts` tab (watch 5-8s) -> Click YouTube logo/Home. This immediately forces YouTube to populate the home feed with ~30 recommended videos. If still empty, use search input with lifestyle keywords.
- **Sponsored Card Trap ("Được tài trợ" / "Sponsored")**:
  - Never click cards containing "Được tài trợ", "Sponsored", or "Ad".
  - Filter `ytd-rich-item-renderer` ancestors for ad markers; select genuine organic `/watch?v=...` videos.
- **Smart Ad Skip vs Watch**:
  - 100% watching ads is a botnet signature (real users hate ads).
  - 70% probability: Wait 5s countdown + random 2.0-5.5s delay (reaction time at seconds 7-10) -> click `.ytp-skip-ad-button` or `.ytp-ad-skip-button-modern`.
  - 30% probability: Allow ad to run naturally (simulating passive background listening).
- **Player Playback & Verification**:
  - Wait for URL to reach `**/watch*`. Press 'k' or Space to unpause. Watch for 90-120s.
  - Screenshot verification: Take screenshot via CDP `Page.captureScreenshot` (avoids font-loading timeouts) while `/watch` is active.

## 3. Google News & Search Interaction
- **Google News Reading Time**:
  - Open `news.google.com`, click an organic article into a dedicated tab.
  - Read for 45-60s using `human_scroll` (chunked scrolling in 5-7 steps with 0.3-0.7s delays).
  - English vs Vietnamese news: Both are completely natural in Google's behavioral analysis; English news from tier-1 publishers actually improves global trust scores.
- **Google Search**:
  - Search random Vietnamese lifestyle queries (weather, gold prices, football, travel, technology).
  - Dwell on results page for 10-15s with light scrolling.

## 4. Single-Tab Sequential Discipline & Hard Cleanup
- **No Concurrent Multi-Tabs within a Profile**:
  - Never open 3 tabs simultaneously. Use a single active tab: YouTube -> close tab -> News -> close tab -> Search -> close tab. Prevents memory bloat and bot detection.
- **GPM Profile Hard Close**:
  - GPM Local API (v3 port 19995) standard termination endpoint is `GET /api/v3/profiles/close/{id}` (fallback to `/profiles/stop/{id}`).
  - In Playwright `finally` block: `browser.close()` -> `context.close()` -> `profiles/close/{id}`.
  - Ensure all Chrome instances terminate so taskbar remains clean and free of orphaned profile windows.
