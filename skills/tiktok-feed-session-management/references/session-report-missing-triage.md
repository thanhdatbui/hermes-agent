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

## Reporting standard

Tell the operator: cron health, manual-run exit/stdout, exact state keys found, artifact discovery result, and the most likely blocker. Keep the answer short and evidence-led. Distinguish `no reportable artifact`, `wrong session key claimed`, `runner busy`, and `Telegram delivery failure` as separate causes.
