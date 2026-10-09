# Log-first registration alert triage

Use this after a registration Farm Alert reports failed machines.

## Evidence order

1. Read the configured canonical run log around the alert timestamp. For this farm, the observed source was `D:/Taadaa/Tiktok_Reg/social_reg_log.txt`.
2. Filter by machine ID, timestamp, and exact error token; do not treat the newest unrelated batch directory as the matching run.
3. Follow artifact paths emitted by the log and open the exact matching XML and screenshot for the same attempt.
4. Use `inspect_machine.py <N>` only as a current live-state cross-check. It cannot replace historical evidence.

## Error partition observed in a Row 2 alert

- `[07] Khong the xac dinh trang thai email` was preceded by `detect timeout: unknown`, `unknown_fallback`, and `no_new_email`. The matching XML showed TikTok's `Xác minh email` screen and the email/link text. This supports a post-submit state-detector timeout/classification failure, not proof that the source email is invalid.
- `adb-timeout` at `shell ime set ...`, `shell am force-stop ...`, or `device offline/not found` is a device/ADB transport fault.
- `[01_open] TikTok not foreground after clean launch` must be correlated with preceding `adb warn ... device not found/offline`; when present, the foreground error is downstream of lost device transport.
- `[03_dropdown] Khong mo duoc account dropdown` is confirmed only after opening the final XML and checking that expected anchors (`Chuyển đổi tài khoản`, `Thêm tài khoản`) are absent or the screen is a fallback Settings/profile state.

## Required report shape

- Machine and exact timestamp
- Verbatim log line(s)
- Exact XML/screenshot paths
- `Confirmed / Excluded / Unproven`
- Error class: detector, UI-flow, or ADB transport
- No live retry or code patch until the historical evidence pass is complete

## Pitfall

A huge append-only log may contain many historical runs. A live inspection that says Launcher/sleep/offline is not enough to explain a past alert; always correlate the failure line with the attempt artifacts created at that same timestamp.
