# Farm Alert Delivery & Telegram Constraints Reference

## 1. Telegram API Photo Caption Limit (1024 chars)
- **Constraint**: Telegram `sendPhoto` accepts at most **1,024 characters** for the `caption` parameter.
- **Symptom**: Exceeding 1,024 characters causes Telegram to reject the request with `HTTP 400 Bad Request: MEDIA_CAPTION_TOO_LONG`.
- **Anti-pattern**: Falling back directly to text-only `sendMessage`. This drops the photo showing the red machine banner and timestamp (`[MAY <N>] - HH:MM:SS DD/MM`), breaking user monitoring.
- **Correct Architecture**:
  1. **Message 1 (Photo)**: Send photo with `summary_caption` (Machine, Serial, Nick, Error reason, Status) guaranteed $\le 1024$ chars.
  2. **Message 2 (Text)**: Immediately send the full 5-step recovery instructions + canary command as a follow-up text message.
  3. **HTML Tag Safety**: Use `_safe_truncate_html()` so truncated text always closes open tags (`<b>`, `<code>`, `<pre>`), preventing Telegram HTML parse errors.

## 2. Alert Claim Deduplication vs. Network Failures
- **Constraint**: `_claim_machine_alert_once` prevents duplicate spam by writing a claim file (`machine_<N>.claimed`).
- **Symptom**: If `send_farm_machine_alert` returns `True` unconditionally despite network failure (DNS error, timeout), the claim file is committed with `status=delivered`. This permanently suppresses retries on all future cron ticks for that shift.
- **Rule**:
  - `send_farm_machine_alert()` MUST return `False` when HTTP request fails or times out.
  - On delivery failure, the caller MUST unlink the pending/claimed file (`claimed.unlink(missing_ok=True)`) so the next tick can retry delivery when network recovers.

## 3. Pipeline / Script-Level vs Machine-Level Alerts
- **Machine-level (`send_farm_machine_alert`)**: For UI, ADB, and flow errors tied to specific devices (Machine N, Serial).
- **Script-level (`send_farm_script_alert`)**: For batch/pipeline crashes not bound to a single device (e.g. night-chain reg pipeline, clear-cache timeout waves, checklive scripts).
  - Bắn trực tiếp về Farm Alerts (`-5373649734`).
  - Phải ghi rõ: Quy trình / Script, Chi tiết lỗi, File thực thi (`flow_file`), File log (`log_path`), Lệnh chạy kiểm chứng (`canary_cmd`).
