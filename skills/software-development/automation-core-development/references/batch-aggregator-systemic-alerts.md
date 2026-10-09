# Batch Aggregator & Systemic Failure Alerts

## Overview
`src/automation_core/batch_aggregator.py` provides multi-machine batch error aggregation and actionable Telegram alerting with dual-threshold systemic failure detection for the Taadaa farm (80–160 machines).

## Core Architecture

### 1. Error Signature Normalization (`normalize_error_signature`)
Prevents machine-specific noise from splintering identical failures:
- Replaces device serials (`m8`, `m14`, `DEV-001`, `emulator-5554`, IP addresses) with `<serial>`.
- Replaces ISO, time-of-day, date, and epoch timestamps with `<timestamp>`.
- Normalizes UI bounds (`[100,200][300,400]`) to `<bounds>` and coordinates to `<coord>`.
- Normalizes process/thread PIDs and hexadecimal memory addresses to `<pid>` and `<hex>`.

### 2. Dual-Threshold Classification (`evaluate_batch`)
A cluster of failures is classified as **systemic** if and only if:
```python
(len(machines) / total_machines >= min_rate) and (len(machines) >= min_count)
```
- Default `min_rate = 0.10` (10% of batch).
- Default `min_count = 3` (at least 3 machines).
- Failures below either threshold are classified as **sporadic** and silently skipped from Telegram spam.
- **Auth Critical Exception**: Keywords (`login`, `account screen`, `verification`, `checkpoint`, `auth`, `văng`, `identity`) flag P0 warnings even if sporadic.

### 3. Script Meta Resolution & Alert Header Standard
Alert messages sent via Telegram must immediately establish process context so operators know which pipeline failed without opening manifests.

#### Script Resolution Hierarchy:
1. Explicit CLI argument: `--script <alias_or_name>`.
2. Run directory manifest / summary JSON inspection (`mode`, `script`, `pipeline`, `script_name`).
3. Regex path heuristic on run directory name (e.g. `multi-machine-feed-session`, `row-8-`, `tiktok-reg`).
4. Display name resolution:
   ```python
   from automation_core.alerts import _resolve_script_meta
   disp_script, _, _, _ = _resolve_script_meta(script_name or "")
   ```
   If unresolved or empty, fall back cleanly to `"Chưa rõ quy trình"`.

#### Alert Header Template:
```html
🚨 <b>[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG</b>
• Quy trình / Script: <b>{html.escape(disp_script)}</b>
• Quy mô batch: <b>{total_machines} máy</b> | Thành công: {succeeded_count} | Thất bại: {failed_count}
• Tổng tỷ lệ thất bại toàn batch: <b>{overall_fail_rate:.1%}</b> ({failed_count}/{total_machines} máy)
• Số cụm lỗi hệ thống: <b>{len(systemic_signatures)}</b>

📋 <b>CHI TIẾT LỖI VƯỢT NGƯỠNG KÉP (RATE & COUNT):</b>
❌ <b>Signature:</b> <code>{sig}</code>
   - Tỷ lệ trên toàn batch: <b>{batch_rate:.1%}</b> ({len(machines)}/{total_machines} máy)
   - Tỷ lệ trong số máy lỗi: <b>{fail_share:.1%}</b> ({len(machines)}/{failed_count} máy lỗi)
   - Danh sách máy: <code>{html.escape(', '.join(serials))}</code>
```

### 4. Canary Policy & Recovery Instructions
The alert automatically generates a 4-step recovery directive:
1. Batch lock: Halt widespread interventions.
2. Canary single-machine test recommendation:
   `python D:/Taadaa/tools/inspect_machine.py <canary_machine>`
3. Representative media snapshots (up to 2 per systemic cluster attached as photo in Telegram).
4. Reopen fleet only upon successful canary verification.

## Testing Guidelines (`tests/test_batch_aggregator.py`)
- Test normalization regexes across all hardware serial variants and coordinate bounds.
- Test dual-threshold edge cases:
  - Sporadic below count or rate -> `should_alert=False`.
  - Exactly at threshold -> `should_alert=True`.
  - Overall failure rate (e.g. 80/80 = 100%) vs per-signature rate (e.g. 60/80 = 75%).
- Test script header display with:
  - Known alias (`multi-machine-feed-session` -> `Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)`).
  - Custom script path / name.
  - Missing or unknown script -> `"Chưa rõ quy trình"`.
