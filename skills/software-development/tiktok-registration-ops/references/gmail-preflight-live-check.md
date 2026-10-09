# Gmail Preflight Live Check Integration (`_detect_clean.py`)

## Context
Trong quy trình detect target email cho batch đăng ký TikTok tại `D:/Taadaa/Tiktok_Reg/_detect_clean.py`, các Gmail targets có thể đã bị vô hiệu hoá (DIE) trước khi dispatch vào máy reg. Việc lọc sớm tại khâu detect giúp tiết kiệm thời gian, tránh lỗi OTP/DOB và tránh khóa máy không cần thiết.

## Contract & Integration
1. **Module phụ trách**: `scripts/gmail_preflight_filter.py`
   - Hàm: `filter_live_gmail_targets(targets: list[dict[str, object]], project_root: Path | None = None) -> list[dict[str, object]]`
   - Dịch vụ check live: `checkmail.live` qua `tools/check_gmail_live_fast.py`.
2. **Điểm chèn trong `_detect_clean.py`**:
   - Ngay sau bước `filter_unlocked_targets()` trong hàm `detect_targets()`:
     ```python
     targets, lock_rejections = filter_unlocked_targets(
         pending_targets,
         lock_root=lock_root,
     )
     targets = filter_live_gmail_targets(targets, project_root=ROOT)
     return devices, source_rows, registered, targets, lock_rejections
     ```
3. **Cơ chế xử lý**:
   - Chỉ lọc Gmail targets (`endswith("@gmail.com")`).
   - Nếu `checkmail.live` xác nhận DIE (`False`):
     - Gọi `remove_captcha_dead_email_from_source(email)` để dọn khỏi source workbook.
     - Gọi `remove_device_account_fast(device, email)` để gỡ account rác trên thiết bị STT.
     - Loại target khỏi danh sách xuất ra `_clean_targets.json`.
   - Nếu lỗi mạng hoặc không nạp được công cụ: Log warning và fallback giữ nguyên targets để không ngắt quãng toàn bộ batch.
