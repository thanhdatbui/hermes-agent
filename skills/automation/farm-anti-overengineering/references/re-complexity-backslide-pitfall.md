# Re-Complexity Backslide Pitfall (2026-09-10)

## Incident
User đã simplify hệ thống cron runner (03/09/2026, commit `7824154`): tiktok_runner.py đọc thẳng từ taikhoan_run_safe.xlsx, không cần picker/cohort/manifest.

6 ngày sau (09/09/2026), worker subagent (`9r-free`) tự ý thêm picker/cohort/manifest layers khi user chỉ yêu cầu thêm Ca 4. Commit `4891fec` tạo ra:
- `picker.py` — phân bổ máy theo block/session
- `cohort.py` — validate block/session ranges
- `manifest.json` — assignment plan

Hệ quả: `cohort.py` line 108 hardcode `block not in (1, 2, 3)` → block 4 bị reject → **toàn bộ farm chết** (09/10/2026). User rất frustration.

## Root Cause
Worker subagent coi "thêm Ca 4" = "phải viết hệ thống scheduler phức tạp". Không nhận ra user muốn giải pháp đơn giản nhất.

## Pitfall Rule
**Khi user yêu cầu "thêm/sửa X", CẤM tự ý tạo thêm abstraction layers mới.**

Luôn hỏi: "Cách đơn giản nhất để đạt yêu cầu user là gì?" — thường là sửa 1 dòng code, không phải viết hệ thống mới.

Dấu hiệu nhận biết over-engineering:
- Tạo file/module mới khi chưa được yêu cầu
- Thêm validation layers khi logic hiện tại đã đủ
- Viết picker/scheduler/manifest khi chỉ cần if-else đơn giản
- Worker tự ý expand scope beyond user request

## Recovery (10/09/2026)
1. Fix `cohort.py`: `block not in (1, 2, 3)` → `block not in (1, 2, 3, 4)` (commit `8155776`)
2. Simplify `tiktok_runner.py`: bỏ picker/cohort/manifest, dùng `_SCHEDULE` dict đơn giản
3. Giữ runner architecture: giờ → Row → PS1 → chạy (xem `tiktok-feed-session/references/simplified-cron-runner-architecture.md`)