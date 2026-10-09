# Watchdog Follow Reconcile & Shadow Action Rules
## Session: 2026-10-06 (M80 False-Alarm Rule)

---

## 1. Problem: "Lệch -N" False Alarm for FOLLOW_FAILED Accounts

When a machine executes follows during a feed session:
- It records `followed_count` in `follow_result.json` (e.g., 1 follow on Anchor 1).
- It may also record natural follows from the feed phase (e.g., 1 follow).
- Total reported by script = natural + cross-follows = 1 + 1 = 2.
- Then on Anchor 2, the machine hits `FOLLOW_FAILED` (button bounces back after swipe).
- At session close, the watchdog reconciles script reported vs. TikTok web snapshot delta:
  `web_delta = current_web_following - baseline_web_following`
- If TikTok shadow-banned / rate-limited the account, `web_delta = 0` (server did not commit).
- Watchdog compares `0 - 2 = -2` and reports an error: `M80: Lệch -2`.

---

## 2. Root Cause Analysis

1. **Natural follows have NO verify**: During feed swiping, follow taps are fire-and-forget.
   If the account is already restricted, the natural follow was never accepted by TikTok.
2. **Anchor follows use Path B verify**: Path B checks the ANCHOR's profile button ("Đã follow"),
   NOT the runner account's own following counter.
   TikTok caches the button state locally on the device; the global backend does not commit it.
3. **The `cnt == 0` trap in watchdog**:
   ```python
   # Old logic in feed_session_watchdog.py:
   for m in fl_released:
       cnt = len(followed)
       if cnt == 0:
           # Only deduct natural follows if cross-follow count is 0
           released_machine_set.add(m)
   ```
   If `cnt > 0` (machine succeeded on first anchor, then failed on second),
   the watchdog DID NOT deduct natural follows and EXPECTED the web to increase by `cnt + natural`.
   Since the server un-committed everything, this resulted in an unavoidable false "Lệch -N" alert.

---

## 3. Operating Rule for Watchdog Reconcile

For any machine in `fl_released` (status `FOLLOW_FAILED`):
1. **Natural follows**: Deduct ALL natural follows regardless of `cnt` (even if `cnt > 0`).
   Once an account triggers `FOLLOW_FAILED` in a session, its prior actions in that session
   cannot be assumed to have been committed by TikTok server.
2. **Web Delta Expectation**: In the web-vs-script comparison table:
   - Do NOT flag `Lệch -N` as an actionable error/anomaly when the account is in `FOLLOW_FAILED`.
   - Annotate clearly: `Web +0 (Nick dính FOLLOW_FAILED ở lượt sau — TikTok server shadow-drop, không commit)`.
   - Exclude these machines from the cluster mismatch count that triggers watchdog failure alerts.
