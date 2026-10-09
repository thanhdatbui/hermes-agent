# Batch Aggregator Script & Workflow Attribution Pattern

## Context & Problem
When systemic errors occur across farm devices (e.g. 80 devices failing simultaneously during night chain, feed sessions, or mass reboots), `batch_aggregator.py` aggregates failures into clusters and generates a Telegram alert.
Without explicit workflow identification at the top of the alert, operators receiving notifications cannot immediately tell which pipeline (TikTok feed, upload, follow, 2FA, registration, cache clear) failed.

## Canonical Pattern
1. **Header Identification**:
   Always include the resolved script/workflow name at the very top of the alert header:
   ```html
   🚨 <b>[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG</b>
   • Quy trình / Script: <b>{resolved_script_name}</b>
   • Quy mô batch: <b>{total_machines} máy</b> | Thành công: {succeeded_count} | Thất bại: {failed_count}
   • Tổng tỷ lệ thất bại toàn batch: <b>{overall_fail_rate:.1%}</b> ({failed_count}/{total_machines} máy)
   ```

2. **Metadata Resolution via `_resolve_script_meta`**:
   - Reuse `_resolve_script_meta` from `automation_core.alerts` to map raw script names / aliases (e.g., `multi-machine-feed-session`, `run_night_chain_pipeline`, `clear-tiktok-cache`) to user-friendly titles:
     - `multi-machine-feed-session` -> `Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)`
     - `tiktok-video` / `run_tiktok_upload_batch` -> `Đăng Video (Tiktok-video)`
     - `Tiktok_Reg` -> `Đăng Ký TikTok (Tiktok_Reg)`
     - `tiktok-add-2fa` -> `Bật 2FA TikTok (tiktok-add-bao-mat-f2a)`
     - `clear-tiktok-cache` -> `Dọn Dẹp Cache TikTok (clear-tiktok-cache)`
   - When not matched or not provided, fallback safely to escaped raw name or `Chưa rõ quy trình`.

3. **Scope Lock & Test Lock Invariants**:
   - Only modify `src/automation_core/batch_aggregator.py`.
   - Update tests in `tests/test_batch_aggregator.py`.
   - Document in `docs/farm-automation-cases.md`.
   - **Test Isolation**: NEVER run whole-repo pytest. Always isolate to `pytest tests/test_batch_aggregator.py` inside `D:/Taadaa/automation-core`.
