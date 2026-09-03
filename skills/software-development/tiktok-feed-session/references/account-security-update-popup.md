# Account-security update popup: one-off live dismissal

## Scope

This reference covers a user-authorized one-off action on a specific live TikTok device when the popup says `Tài khoản của bạn cần được cập nhật` and offers `Liên kết số điện thoại hoặc email` plus `Để sau`.

## Evidence contract

- Resolve the machine-to-serial mapping from the authoritative workbook/config first.
- Capture a fresh screenshot for visual confirmation.
- Capture fresh ATX XML and require both the exact popup title and a clickable `Để sau` node.
- The node bounds are evidence, not a permanent coordinate. Re-capture immediately before acting and use the current bounds.

## Typed action

Click only the center of the verified `Để sau` node through the ATX session JSON-RPC `click` method. Do not choose the link action, change account security, switch accounts, use a blind coordinate, or use shell UI dump as evidence.

## Robust ATX plumbing

1. Parse `ps -A` by columns. Accept only a row whose final process-name column is exactly `com.github.uiautomator`; exclude `.test`; require one PID.
2. Read `adb forward --list` and match the exact target serial with remote `tcp:7912`.
3. Reuse that serial's local dynamic port. Never clear all forwards on a farm.
4. POST the typed click to `/session/<pid>:com.github.uiautomator/jsonrpc/0` and require HTTP 200 plus JSON-RPC `result: true`.

## Verification

Wait briefly, capture ATX XML again, and require both the popup title and `Để sau` to be absent. A successful JSON-RPC click response is not sufficient. If the marker remains or re-capture fails, preserve the live scene and report failure/uncertainty.

## Reporting

Keep the result short: machine/serial, exact action, ATX acknowledgement, and post-action marker status. Do not include credentials or unrelated farm state.

## Automation handler contract & `_row_from_attempt` pitfall

When handling `account_update_prompt` inside `feed_swipe_smoke.py` / benign popup recovery:
- `_row_from_attempt()` has a strict keyword-only signature: `step`, `action`, `expected`, `swipe_count`, `attempt`, `expected_package`, `require_feed`.
- Do NOT pass `artifact_prefix` to `_row_from_attempt()`, and always supply `expected_package=str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill"))`. Passing `artifact_prefix` triggers `TypeError: _row_from_attempt() got an unexpected keyword argument 'artifact_prefix'` at runtime, halting the batch session and causing unnecessary `GIỮ HIỆN TRƯỜNG` alerts.

