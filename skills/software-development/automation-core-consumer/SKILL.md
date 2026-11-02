---

name: automation-core-consumer

description: "Build and fix consumers of automation-core for Android/TikTok workflows. Covers startup contract, ADB config, workbook mapping, Excel pitfalls, device lock policy, and the Codex↔Claude approval loop."

version: 1.7.1

author: Hermes Agent

metadata:

  hermes:

    tags: [automation-core, android, tiktok, adb, consumer, workbook, openpyxl]

    related_skills: [consumer-scheduler-orchestration, github-code-review, automation-core-development, gemphonefarm-decrypt]

---
# automation-core-consumer

> References quan trọng:
> - `references/rolling-concurrency-vs-worker-cap-and-device-guard.md` (Rolling concurrency 15-25 workers vs worker cap, AST lock & gate guard).
> - `references/workbook-concurrency-onedrive-resilience.md` (OneDrive).
> - `references/two-way-device-lock-concurrency-contract.md` (Device Lock 2 chiều).
> - `references/asymmetric-device-lock-and-healer-collision-prevention.md` (Asymmetric Lock).
> - `references/relative-shared-tools-import-standard.md`
> - `references/bidirectional-device-lock-coordination-and-clean-skip.md` (Kiến trúc điều phối lock 2 chiều giữa script can thiệp của operator và ca nuôi/batch: Clean Skip, wait_for_device_lock, và tránh bẫy _UnlockedDeviceLockLease).
> - `references/relative-shared-tools-import-standard.md` (Chuẩn hóa import path cho shared tools và cross-repo modules qua PROJECT_ROOT.parent / 'tools' thay vì hardcode tuyệt đối).
> - `references/teardown-force-stop-and-return-home-contract.md` (Hợp đồng Teardown bắt buộc: luôn force-stop app và input keyevent 3 về HOME trong khối finally trước khi lease/device_lock.finish).
> - `references/consumer-cli-parser-contract.md` (Hợp đồng CLI Parser & tách build_parser() cho consumer entrypoints để phục vụ focused unit tests).
> - `references/batch-aggregator-consumer-hook-contract.md` (Hợp đồng Batch Aggregator: layout run_manifest/multi_machine_summary, cảnh báo P0 Auth/Login tức thì, và chuẩn hook vào PowerShell runners).
> - `references/mocking-multistep-ui-tests.md` (Pitfalls & Patterns: Mocking Multi-Step UI Automation Tests — bẫy cumulative sleeps vs timeout và quy tắc tool budget).
> - `references/s7-rolling-cleanup-preflight-contract.md` (Hợp đồng S7 Rolling Cleanup Preflight: quy tắc 3 Gates 2FA+OAuth+30d, cơ chế skip_lock tránh deadlock/self-preemption khi consumer runner đã giữ lock).
> - `references/live-proxy-ip-preflight-gate.md` (Chốt chặn xác thực proxy live IP: verify_live_ip=True, chặn proxy_ip rỗng, log STOPPED: [PREFLIGHT_PROXY], release lock handoff và exit 2).
> - `references/adb-device-proxy-preflight-probe.md` (Preflight fast probe: ưu tiên đọc `settings get global http_proxy` qua ADB trên thiết bị trước khi fallback về workbook Excel).
> - `references/protocol-v2-reservation-and-datetime-marker-pitfalls.md` (Pitfall `DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE` do thiếu `lock_protocol_version=2`/`queued_v2` trong PowerShell launcher & fix `TARGET_INVENTORY_CONFLICT` do chuỗi datetime trong cột Device ID).
> - `references/device-startup-manual-dumpsys-power-timeout.md` (Pitfall `DEVICE_STARTUP_MANUAL`: ADB timeout `dumpsys power` bị core phân loại nhầm thành `manual_needed`, và blocker B3 Soft Reboot tại `CONNECT_DEVICE` do `adapter` chưa khởi tạo).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
