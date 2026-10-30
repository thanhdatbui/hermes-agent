---
name: farm-watchdog-fidelity-engineering
description: "Use when designing or fixing watchdogs and cron reports."
---
# Farm Watchdog & Reporting Fidelity Engineering

## 1. When to Use
Use when creating, auditing, modifying, or troubleshooting background watchdogs, scheduled cron reports, and alert aggregators on automation farms.
Applies whenever reports fail to reflect actual fleet health, mask dropped machines, report false aggregate metrics, or omit actionable failure details.
Also applies when compliance reports trigger high failure counts and agents enter a block death spiral due to misaligned guidance or false-positive subfolder blocks.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.

## 2. Core Invariants Summary & Deep References
- **4-Way Multi-Tier Cron Sync Parity (Anti-Ghost Revert / Stale Runtime):** Khi sửa bất kỳ cron script hoặc wrapper runner nào, bắt buộc đồng bộ đồng nhất và đối soát SHA-256 trên cả 4 tầng (Repo, Runtime `%LOCALAPPDATA%`, Deploy `Hermes/deploy`, và OneDrive Sync Shared) kèm chạy `cron_sync_watchdog.py --force`. Cấm tuyệt đối đặt script tại `~/.hermes/scripts` vì Windows Scheduler chỉ đọc `%LOCALAPPDATA%\hermes\scripts`. Tạo/sửa cronjob bắt buộc `cronjob(action='run')` test ngay tại chỗ. Chi tiết: [`references/four-way-cron-sync-parity-and-runtime-drift.md`](references/four-way-cron-sync-parity-and-runtime-drift.md).
- **Watchdog Session 1 Baseline Buffer Parity (Anti-Zero-Buffer T0 Trap):** Trong watchdog đối soát delta (như follow/upload), cửa sổ truy vấn baseline T0 cho Phiên 1 (`is_p1_or_unknown`) bắt buộc phải có buffer tối thiểu 15 phút (`buffer_reconcile_iso(session_start_iso, 15)`). Cấm tuyệt đối gán 0 buffer vì tiến trình cào T0 đầu phiên chạy mất 1–2 phút sau mốc bắt đầu ca, khiến SQL query `timestamp <= session_start_iso` loại bỏ snapshot T0 tươi mới và rơi vào bẫy stale baseline > 4h dán nhãn `UNPROVEN`. Chi tiết: [`references/watchdog-p1-zero-buffer-t0-exclusion-trap.md`](references/watchdog-p1-zero-buffer-t0-exclusion-trap.md).
- **Cronjob Guard Guidance, Auto-Rewire & Farm Contract Templates (Anti-Block Death Spiral):** Khi nhận báo cáo Gate G8/G7 nổ vi phạm hàng loạt, phân định dứt khoát: Tầng Auto-Rewire tự động tiêm ngầm 0-turn `no_agent=True` khi lệnh đã có `script` (thỏa 3 Tiêu Chí Vàng: tất định, thu hẹp quyền hạn, minh bạch); Tầng Active Pivot (Fail-Fast) bắt buộc trả về pre-filled `farm_contract` template chuẩn (touches_device=false vs rolling 1..50) và context-aware guidance tra cứu file O(1), triệt tiêu bão thử sai mò mẫm. Chi tiết: [`references/cronjob-guard-guidance-auto-rewire-and-contract-templates.md`](references/cronjob-guard-guidance-auto-rewire-and-contract-templates.md).
- **Cron Guard Single-Pass Active Pivot & Pipeline Execution Invariant:** Khi cron watchdog báo vi phạm hàng loạt ở G8, hook `guard_cronjob_safety.py` bắt buộc tiêm metadata `auto_rewire` với `strategy: "single_pass_active_pivot"` + `stop_retrying_original_payload: True`. Đặc biệt: khi User ra lệnh nắn/sửa, Coordinator BẮT BUỘC kích hoạt NGAY TRỌN GÓI Gate A-Z (`unified_patch_pipeline.py run`), cấm đứng im giải trình phương án xin duyệt gây bại liệt flow. Chi tiết: [`references/cron-guard-single-pass-active-pivot-and-prefilled-contract-invariants.md`](references/cron-guard-single-pass-active-pivot-and-prefilled-contract-invariants.md).
