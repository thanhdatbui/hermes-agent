# Decoupled Pipeline & Path B Verify Invariants

1. **Decoupled Pipelines (Feed — Follow — Upload):**
   - In `multi_machine_feed_session.py`, feed session failures (app errors, socket freezes, timeout, < 3 warm swipes) MUST NOT block the follow hook.
   - Follow hook must run independently; upload hook must run independently.

2. **Accurate Follow Release Discrimination (Anti-False-Release):**
   - When TikTok server actually un-follows/rejects, runner MUST stop immediately and lock cooldown to prevent spamming and ban.
   - In Mode 2 Path B Verify, do NOT call `pull_to_refresh_profile` when opening the profile (it causes layout jitter and loading overlays that hide the button). Read the relationship button with settle wait. Only flag `FOLLOW_FAILED` if button explicitly shows `Follow / Theo dõi`.
