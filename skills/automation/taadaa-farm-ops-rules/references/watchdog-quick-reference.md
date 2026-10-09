# Quick Pointer: Event-Driven Machine Idle Watchdog Policy
See full implementation guide at:
`references/event-driven-idle-machine-watchdog-policy.md`

## 5 Invariant Rules do Claude CLI tư vấn:
1. RULE #0 (Zero Hardcoded Time): Cấm tuyệt đối Coordinator đặt giờ cố định (13h, 21h, 23h30...).
2. RULE #1 (No Touch Without Lock): Bắt buộc kiểm tra `machine_N.lock.json`. Đang bận ca chính cấm đụng vào máy.
3. RULE #2 (Source of Truth): Chỉ tin dữ liệu live lock thực tế.
4. RULE #3 (Session Exclusivity): Ca chính (Feed, 2FA, Reg Gmail) là bất khả xâm phạm.
5. RULE #4 (Event-Driven Watchdog): Dùng watchdog polling 1-2m check lock riêng của máy mục tiêu. Máy vừa rảnh là vào việc ngay lập tức, xong tự tắt.
