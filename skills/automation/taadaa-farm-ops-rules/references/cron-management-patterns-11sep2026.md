# Cron Management Patterns for MobiProxy & TikTok Farm (11/09/2026)

## Cron Jobs Updated in This Session

### Active Cron Jobs (18/18 enabled)
1. **`mobiproxy-auto-healer-watchdog`** (Job ID: `7e5e3980dde1`) — **PAUSED**. Lý do: firmware mới có Scan Guard (firewall iptables kernel), cron cũ dùng logic "tắt NAT → update IP → bật NAT" gây spike RAM → sập 502. Khi Scan Guard active thì PAUSE cron này.
2. **`phase9-runner-tiktok-feed`** — Chu kỳ 15 phút, feed runner nuôi acc. Test đã chạy thành công trên máy S7 thật.
3. **`phase9-staging-picker-455f8e989c6c4cde9b4028ac01e682c3`** — Picker lúc 06:00 hàng ngày.
4. **`tiktok-feed-session-watchdog`** — Báo cáo tổng kết ca/phiên nuôi acc (5 phút/lần).
5. **`kibe-phone-online-autoproxy-watchdog`** — Tự phát hiện máy S7 online, gán proxy LAN MikroTik (2 phút/lần). **Chỉ gán 1 lần duy nhất** cho mỗi máy khi lên nguồn (file state `farm_kibe_online_assigned.txt`).
6. **`device-locks-watchdog`** & **`reap-dead-owner-locks`** — Quản lý khóa máy (15 phút/lần).
7. **`night-chain-reg-pipeline`** — Chuỗi reg ban đêm 01:00.
8. **`end-of-day-clear-tiktok-cache`** — Xóa cache 40 worker (04:00).
9. **`daily-manual-stock-checklive`** — Check live kho acc (07:00).
10. **Avatar watchdogs** — `avatar-post-feed-watchdog` (22-23h) & `avatar-tik4-idle-trigger`.
11. **System sync/watchdogs** — `sync-hermes-skills-to-git`, `taikhoan-run-safe-sync`, `sync-gmail-clean-v2-to-tong`, `onedrive-multicloud-sync-watchdog`, `auto-trim-startup-files`, `hermes-stale-watchdog`.

## MobiProxy Scan Guard Cron Pattern
Khi firmware MobiProxy có **Scan Guard (3.0.67+)**:
- **PAUSE cron `mobiproxy-auto-healer-watchdog`** — cron này dùng logic cũ gây sập box
- Update IP WAN MikroTik đổi: gọi API `proxy.scan_guard.save` (JSON + CSRF token) → ghi iptables kernel, **không restart proxy**, không sập 502
- Chỉ cần 2 IP whitelist: IP WAN MikroTik + IP PC Kibe

## TikTok Runner State
- State file: `D:/Taadaa/runtime/kibe/cron-state/runner_simple_state.json`
- Last run: 11/09/2026 06:00 (Row 1, Ca sáng, ngày lẻ)
- Test feed session (1 máy S7): **THÀNH CÔNG** — wake, unlock, launch TikTok, verify focus, profile switch, nav tab Profile — tất cả OK.