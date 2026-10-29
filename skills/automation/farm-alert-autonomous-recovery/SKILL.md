---
name: farm-alert-autonomous-recovery
description: Taadaa Farm Alert recovery to closeout.
---
# Farm Alert Autonomous Recovery

> Core Refs: `dynamic-feed-row0-starvation-and-contiguous-video-triage-20261029.md`, `dynamic-feed-row0-starvation-and-ssh-stderr-masking-20261029.md`, `upload-hook-auto-login-recovery-and-canary-gate-wiring.md`, `canary-receipt-expiry-and-safe-push-pre-commit.md`, `recovery-proof-and-operator-closeout.md`, `anti-performative-alert-handling-and-immediate-code-fix.md`, `missing-account-switcher-vs-auto-login-fail-closed.md`, `admin-cluster-remote-adb-socket-injection-and-welcome-back-switcher.md`, `run-artifacts-extraction-and-session-dedup.md`, `upload-batch-alert-triage-and-flop-reporting-separation.md`, `blank-workbook-id-cross-file-recovery-and-create-button-tokens.md`, `feed-batch-alert-triage-and-cold-start-transient-20261029.md`.

## UI evidence: target screen only

> Ref: `references/report-routing-and-workbook-shape-20261011.md`.
- Duyệt hiện trường qua `MEDIA:<path>`. CẤM gửi ảnh Home/Launcher sau teardown/lỗi.
- Bắt buộc chụp in-app (Profile/Settings/Popup/Switcher) TRƯỚC KHI teardown.

## 🛑 FEED TAB FALLBACK & IMMEDIATE RECOVERY
- Khi tab Friends/Following gặp lỗi mạng (`manual-needed:network`) hoặc trống (`manual-needed:empty`): Cơ chế `_tab_fallback_reason` phải lập tức kích hoạt chuyển về For You feed (Graceful Fallback), không được chờ đợi consecutive manual guard >= 2 khiến phiên dừng sớm. BẮT BUỘC bảo vệ bằng GuardGate rule `case_invariant_prohibit_guarded_friends_feed_fallback` trong `rules.json` và test kiểm chứng ALLOW/DENY để chống agent sau phá. Chi tiết xem: `references/feed-tab-fallback-and-immediate-network-recovery-20261029.md`.

## 🛑 TRIAGE LỖI CÁP VẬT LÝ ADB (CM_PROB_PHANTOM)
- Khi nhận alert máy offline / `[01_open]` mà ADB báo `device not found` hoặc `offline`:
  Chạy lệnh PowerShell:
  `Get-PnpDevice | Where-Object { $_.InstanceId -like "*<serial>*" } | Select-Object FriendlyName, Status, Present, Problem`
- Nếu `Present: False` hoặc `Problem: CM_PROB_PHANTOM`: Lỗi cáp USB/nguồn. DỪNG NGAY, chuyển L3 BLOCKED.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
