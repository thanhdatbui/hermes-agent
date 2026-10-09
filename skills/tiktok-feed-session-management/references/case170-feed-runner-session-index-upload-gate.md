# Case 170: Gating -AllowUploadHook trong Cron Runner Theo Session Index

## Bối cảnh & Hiện tượng
- Tại Ca 3 - Phiên 1 (18:00), wrapper cron `tiktok_runner.py` gọi PowerShell `run-feed-session.ps1` nhưng lại truyền cứng cờ `-AllowUploadHook`.
- Hậu quả: Toàn bộ 45 máy đủ điều kiện đã tự động kích hoạt hook Đăng Video (Upload) ngay tại Phiên 1, vi phạm quy tắc nuôi tài khoản của Farm: **chỉ đăng video ở Phiên 2 mỗi ca** (Phiên 1 chỉ lướt feed thuần túy để nuôi trust).

## Nguyên nhân gốc rễ (Root Cause)
- Trong hàm `_spawn_feed_session(row, session_index, now)` của `tiktok_runner.py`, mảng tham số khởi tạo `argv` bị hardcode cố định dòng `"-AllowUploadHook"` mà không phụ thuộc vào giá trị `session_index`.
- Mặc dù hàm `_determine_row()` vẫn phân biệt chính xác `session_index = 1` hay `session_index = 2`, việc hardcode tham số đã vô hiệu hóa logic phân tầng phiên.

## Giải pháp (Patch Contract)
Cập nhật mảng tham số `argv` trong `_spawn_feed_session()`:
```python
# Cũ:
"-Row", str(row),
"-SessionIndex", str(session_index),
"-AllowUploadHook",
"-Preset", "full",

# Mới:
"-Row", str(row),
"-SessionIndex", str(session_index),
# Quy định farm: chỉ kích hoạt hook upload video ở Phiên 2 (session_index == 2); Phiên 1 chỉ lướt feed thuần
*( ["-AllowUploadHook"] if session_index == 2 else [] ),
"-Preset", "full",
```

## Các vị trí áp dụng & Đồng bộ (3 điểm)
1. Runtime cục bộ: `C:/Users/Kibe/AppData/Local/hermes/scripts/tiktok_runner.py`
2. Git Deploy: `D:/Taadaa/Hermes/deploy/hermes-home/scripts/tiktok_runner.py`
3. OneDrive Shared: `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/tiktok_runner.py`
(Đồng bộ qua lệnh: `python C:/Users/Kibe/AppData/Local/hermes/scripts/cron_sync_watchdog.py --force`).

## Bài học Gate 1 (Reviewer OmniRoute)
- Khi review diff của file wrapper cron, Reviewer sẽ reject nếu diff kèm theo các thay đổi ngoài lề làm thay đổi logic state/retry (ví dụ: vô tình làm mất file lock marker hoặc thay đổi cách lưu `_save_state`).
- Phải giữ scoped diff cực kỳ tối giản (Clean Scoped Diff) chỉ đúng 1 dòng logic thay đổi của `-AllowUploadHook` để OmniRoute :20129 phê duyệt `VERDICT: APPROVED` ngay vòng 1.
