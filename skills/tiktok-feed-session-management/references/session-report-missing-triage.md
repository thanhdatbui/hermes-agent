# Missing Session Report Triage

Use when a scheduled feed-session watchdog exits 0 but Telegram has no report.

## Evidence-first sequence

1. Inspect the cron job definition: script, schedule, delivery target, `last_run_at`, `last_status`, and `last_delivery_error`.
2. Run the watchdog once manually and capture both stdout and exit code. Exit 0 plus empty stdout means the script intentionally found nothing reportable; it is not proof that Telegram failed.
3. Read the session claim state file (`feed_session_reported.json`) and filter keys for the current date. Verify the exact expected key format (`YYYY-MM-DD_caN_phienM`).
4. Inspect current-day live artifacts/manifests and correlate their session timestamp, row, ca, and phien with the expected 06:00 window. Do not infer a report from a different session key.
5. Check whether the watchdog parser is discovering the artifact root and whether `runner_busy`/completion guards suppress reporting.
6. Only after artifact evidence exists, re-run the watchdog or repair the parser/state. Never fabricate a missing report from prior-session data.

## Important anomaly & Mid-Window Deferral Logic

1. **Mid-Window Locked-Machine Deferral (`can_report_session`):**
   - In `feed_session_watchdog.py`, each session has a defined time window in `SESSION_WINDOWS` (e.g., Ca 1 Phiên 2: `08:00 - 12:00`).
   - If `now_hm < window_end_hm` (e.g., asking at 10:15) AND any expected machine was skipped due to lock (`has_unattempted_locked = True`, e.g., `skipped-device-locked` like M20) or `completed_expected_count < expected_count`:
   - The watchdog intentionally holds back the automated Telegram delivery until either (a) all machines complete cleanly, or (b) the window ends (`now_hm >= window_end_hm`).
   - When the user asks for the report mid-window ("Report chạy fl chéo ca sáng row 1 phiên 2 đâu"), inspect the live artifact folder directly using `parse_run_all(r_path)`, explain the mid-window deferral reason, and deliver the on-demand report immediately.

2. **Session Key Anomaly:**
   If the current date has `ca4_phien*` claimed while the expected morning `ca1_phien1` key is absent, treat it as a session-window/parser/state mapping anomaly. Report the exact keys and missing key; do not claim the morning session completed.

3. **Telegram 4096-Character Limit Silent Rejection (`HTTP 400: message is too long`):**
   - When a session has many events (e.g., 20+ IP Circuit Breaker proxy locks + detailed released machine lists across 2 clusters Kibe & Admin), the formatted message easily exceeds 4,096 characters.
   - If `dispatch_split_reports` catches HTTP errors silently without chunking, the Feed report is saved to cron output while the Follow report to `-5127276494` silently drops!
   - Triage step: Inspect length of `full_msg = hdr + "\n\n" + "\n\n".join(parts)`. If > 4,000 characters, Telegram API returns `HTTP 400 Bad Request: message is too long`.
   - Mandatory Fix:
     * Line-aware auto-chunking: Divide `full_msg` by line boundaries into chunks of $\le 3,900$ characters and dispatch each chunk sequentially.
     * Deduplicate cluster-level blocks: Ensure reports like `format_ip_circuit_breaker_report` only attach to the owning cluster (Kibe), preventing payload duplication.

4. **Split-Report Channel Blindness & Forum Topic Blackhole (`message_thread_id` Omission):**
   - **Tri-Channel Split Architecture:** `dispatch_split_reports()` distributes session sections into 3 dedicated Telegram chats:
     * Feed ➔ `Tiktok Luot Nuoi Acc` (`-5377611430`) via cronjob stdout.
     * Follow ➔ `Tiktok Follow` (`-5127276494`) via direct Telegram API `sendMessage`.
     * Video Upload ➔ `Tiktok video` (`-5435853713`) via direct Telegram API `sendMessage`.
   - **Channel Blindness Trap:** The Feed report strips `• Follow chéo` and `• Đăng Video`. An operator monitoring only `Tiktok Luot Nuoi Acc` will see zero mention of follow execution, misinterpreting it as "follow was never run or watchdog forgot to report".
   - **Forum Topic Blackhole:** Groups with Forum Topics enabled (`has_topics_enabled: true`, such as `Tiktok Follow` `-5127276494`):
     * Calling `sendMessage` with only `chat_id` and omitting `message_thread_id` sends messages to the **General Topic** instead of the active operational thread.
     * The API returns HTTP 200 (`WATCHDOG_TELEGRAM_DISPATCH_SUCCESS`), but operators inside dedicated topic threads never see notification alerts.
     * Fix: When configuring Telegram targets for forum supergroups, `message_thread_id` must be provided, or maintain a high-level 1-line cross-reference block in the main feed report.

5. **Follow-Fail vs Follow-Skip Semantics in Rookies (Row 4) Under Rolling 48h IP Breaker:**
   - In sessions where follow count = 0 across the entire fleet despite active runs:
     * **Organic Rest (1/3):** ~33% fleet skips follow/upload by daily hash for organic rest.
     * **Rolling 48h IP Breaker:** Proxies tripped in earlier shifts (e.g. Ca 1) automatically skip subsequent rows (`CIRCUIT_BREAKER_SKIPPED`) to protect rookie accounts from shared IP taint.
     * **Fail-Closed Immediate Release (Lượt 0):** Non-rested rookie accounts encountering TikTok server action drop get reverted instantly (`FOLLOW_FAILED` after swipe) ➔ Script aborts at 0 count to prevent ban, tripping breaker for the proxy.
     * **Zero-following Anchor:** Anchor target has 0 following ➔ cleanly skipped (`zero-following-skip-v2`).
   - Triage rule: Do not declare follow broken or unrun when follow count = 0; verify the breakdown across rest, breaker skips, and fail-closed terminations.

## Reporting standard

Tell the operator: cron health, manual-run exit/stdout, exact state keys found, artifact discovery result, and the most likely blocker. Keep the answer short and evidence-led. Distinguish `no reportable artifact`, `wrong session key claimed`, `runner busy`, and `Telegram delivery failure` as separate causes.
