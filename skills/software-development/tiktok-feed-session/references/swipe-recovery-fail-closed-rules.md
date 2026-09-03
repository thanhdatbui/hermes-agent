# Fast-Swipe Stuck Recovery Seams & Fail-Closed Rules

## Core Rules for Swipe Recovery (`_swipe_recovery_on_stuck`)

1. **Pre-Swipe Focus Verification:**
   - Always query live `get_focused_activity(ctx)`.
   - If focus query throws an exception or returns empty/invalid data -> abort fail-closed immediately.
   - If focused package is confirmed Launcher (`com.sec.android.app.launcher`, etc.) -> trigger `_relaunch_and_poll_tiktok_focus`.
   - If focused package is external (non-TikTok, non-Launcher, e.g. `PackageInstaller`, `Settings`) -> abort fail-closed without relaunch or swipe.
   - Only execute `input swipe` if live focus is confirmed to be an allowed TikTok package (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`).

2. **Checked ADB Command Execution:**
   - For shell command invocations like `swipe = ctx.adb.shell(...)`:
   - Never default `getattr(swipe, "ok", True)`. Always use `getattr(swipe, "ok", False)` so missing or malformed execution objects fail-closed.
   - Wrap in exception handling and return `None` on error.

3. **Post-Swipe / Recapture Sensitive-Screen & Focus Verification:**
   - Before accepting a recovered feed or running `drain_known_popups`, verify both:
     1. Authoritative focus in `extra` and top-level belongs to TikTok.
     2. Neither XML nor OCR contains sensitive markers (login, password, captcha, OTP, security check).
   - Only drain popups matching strictly allowlisted benign entries; never drain generic `manual-needed` or unknown dialogs.
