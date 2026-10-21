# TikTok Profile Right-Side Avatar Layout Trap & Verification Discipline

## Context & Root Cause (Incident 2026-10-21)
During avatar verification on farm devices (specifically Galaxy S7 / SM-G930K, e.g., Machine 34 with TikTok account `lethanh14375`), subagents (such as Luna) fell into paralysis, falsely concluding that avatar upload had failed or hallucinating incorrect imagery.

### The Layout Trap
On certain TikTok UI variants / layouts:
- The display name (`Bảo Thịnh`) and handle (`@lethanh14375`) are aligned on the **LEFT** side (`x: 40..374, y: 289..411`).
- The circular profile **AVATAR** is rendered on the **RIGHT** side (`x: 800..1050, y: 220..460`), directly adjacent to or beneath the status bubble (e.g., "Trà hay cà phê?").
- If an agent assumes a standard left-aligned avatar layout and blindly crops `(20, 150, 320, 450)`, it crops the text area or bio header, never seeing the actual avatar. This leads to vision misclassification, confusion, and infinite retry loops.

## Canonical Verification Rules

1. **Full-Header Inspection Before Cropping**:
   - Never crop a hard-coded top-left box blindly.
   - First crop the full profile header band (`y: 200..600, width: 0..1080`) or dump the UI hierarchy via ATX (`dev.shell(["dumpsys", "window", "windows"])` / `capture_atx_session_ui`).
   - Identify whether the avatar circle is on the left or the right before performing target cropping for LLM vision verification.

2. **Multi-Account Switching on Farm Devices**:
   - Farm devices often host multiple accounts (e.g. 8 slots). When waking a device or bringing TikTok to foreground, the active account on the profile might be a different slot (e.g., `baosoc83` instead of `lethanh14375`).
   - Before taking avatar verification screenshots, ALWAYS verify the exact `@username` via WinRT OCR or UI XML.
   - If the active account does not match the target, open the account switcher (tap the dropdown arrow next to the username) and select the exact target account before judging avatar status.

3. **Byte-Exact Verification Across Directories**:
   - Compare SHA-256 hashes between raw source (`D:\video goc\<folder>\avatar.jpg`) and render target (`D:\TIKTOK-videonuoinick\<folder>\avatar.jpg`).
   - Ensure `.manual_avatar_locked` and `.manual_hashtag_locked` are present to protect the assets from automated render/crawler overwrites.
