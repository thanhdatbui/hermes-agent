---
name: farm-alert-autonomous-recovery
description: Taadaa Farm Alert recovery to closeout.
---
# Farm Alert Autonomous Recovery

> Core Refs: `admin-cluster-hotmail-graph-token-resolution-and-tos-tap-trap-20261030.md`, `admin-cluster-hotmail-accounts-workbook-schema-and-otp-timeout.md`, `admin-cluster-feed-batch-alert-triage-and-one-tap-login-20261030.md`, `semantic-canary-engine-gate-b-ladder-and-log-assertion.md`, `feed-tab-fallback-canary-gap-and-target-bound-validation-20261030.md`, `gate-abc-and-6gates-canary-watchdog-monitoring-20261030.md`, `crystallize-step26-invariant-and-watchdog-12gates-20261030.md`, `dynamic-feed-row0-starvation-and-contiguous-video-triage-20261029.md`, `dynamic-feed-row0-starvation-and-ssh-stderr-masking-20261029.md`, `upload-hook-auto-login-recovery-and-canary-gate-wiring.md`, `canary-receipt-expiry-and-safe-push-pre-commit.md`, `recovery-proof-and-operator-closeout.md`, `anti-performative-alert-handling-and-immediate-code-fix.md`, `missing-account-switcher-vs-auto-login-fail-closed.md`, `admin-cluster-remote-adb-socket-injection-and-welcome-back-switcher.md`, `run-artifacts-extraction-and-session-dedup.md`, `upload-batch-alert-triage-and-flop-reporting-separation.md`, `blank-workbook-id-cross-file-recovery-and-create-button-tokens.md`, `feed-batch-alert-triage-and-cold-start-transient-20261029.md`, `one-tap-login-empty-credentials-timeout-triage-20261030.md`, `admin-cluster-hotmail-graph-token-dual-workbook-and-gpm-fallback.md`.

## UI evidence: target screen only

> Ref: `references/report-routing-and-workbook-shape-20261011.md`.
- Duyệt hiện trường qua `MEDIA:<path>`. CẤM gửi ảnh Home/Launcher sau teardown/lỗi.
- Bắt buộc chụp in-app (Profile/Settings/Popup/Switcher) TRƯỚC KHI teardown.
- **KỶ LUẬT SOI MẮT ẢNH CỤC BỘ QUA BROWSER VISION:** Khi nghiệm thu ảnh local (`D:/Taadaa/reports/*.png`), dùng `browser_navigate(url="file:///<path>")` để nạp ảnh vào trình duyệt, sau đó gọi `browser_vision` soi mắt kiểm tra (profile, username, avatar, không popup/đen màn hình) TRƯỚC KHI đính kèm `MEDIA:<path>`.
- **CANARY RUNNER TIMEOUT & BACKGROUND EXECUTION:** Quy trình chạy Canary trên thiết bị thật (Galaxy S7) thường mất 2-4 phút. Lệnh `terminal` foreground mặc định sẽ bị trần 60s kill ngang tiến trình. BẮT BUỘC chạy `canary_runner.py` với `terminal(background=True, notify_on_complete=True)` và quản lý bằng `process(action='wait', timeout=...)`.
- **SEMANTIC CANARY PLANNER (ANTI-PERFORMATIVE):** CẤM chạy Canary hình thức lướt 2 feed cho có lệ. `canary_plan.py` tích hợp thang não Gate B (`gemini-web` :20129 -> `gpt-web-sol` :20129 -> `claude-cli`) đọc `git diff` sinh `cli_args_override` và `log_assertions`. `canary_runner.py` kiểm tra log cơ học, thiếu required patterns sẽ fail-closed (exit 1). Tra cứu: `references/semantic-canary-engine-gate-b-ladder-and-log-assertion.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
