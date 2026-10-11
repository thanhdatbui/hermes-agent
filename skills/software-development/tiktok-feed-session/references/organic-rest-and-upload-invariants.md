# Quy Tắc Dưỡng Sinh Tự Nhiên & Invariant Đăng Video (Chốt 11/10/2026)

## 1. Nguyên Tắc Cốt Lõi Về Đăng Video & Dưỡng Sinh
- **BỎ HOÀN TOÀN TỶ LỆ DƯỠNG SINH NGẪU NHIÊN (~33% md5 hash % 3):**
  - Trước đây: Mỗi ngày khoảng 1/3 nick bị hash modulo 3 rơi vào ngày dưỡng sinh ngẫu nhiên, dẫn đến bị bỏ qua follow (`organic-rest-day-pure-feed`) và bỏ qua upload (`organic-rest-day-upload-disabled`).
  - Hiện tại: `_is_account_organic_rest_day` trong `multi_machine_feed_session.py` mặc định trả về `False`.
  - Ngoại lệ duy nhất: Chỉ trả về `True` khi nick được chỉ định đích danh trong sổ cái can thiệp khẩn cấp `force_rest_ledger` (ví dụ `{"1:1": True}`).
- **CỜ UPLOAD MỞ Ở CẢ 2 PHIÊN (`-AllowUploadHook`):**
  - Trong `tiktok_runner.py`: Cờ `-AllowUploadHook` được truyền ở cả Phiên 1 (06:00, 12:00, 18:00) và Phiên 2 (08:00, 14:00, 20:00).
  - Cơ chế tự cân bằng: Hệ thống có sổ cái `shift_upload_history.json` tự động kiểm tra và khóa trùng. Nếu Phiên 1 đã đăng video thành công cho nick đó thì Phiên 2 tự động skip; nếu Phiên 1 chưa kịp đăng (do mạng, do preflight) thì Phiên 2 tiếp tục thử đăng.
  - Invariant vận hành: **CẤM chặn upload ngày nghỉ / ngày dưỡng sinh**, bảo đảm mục tiêu tối thiểu 1 video/ngày cho mọi nick đủ điều kiện.

## 2. Telemetry & Observability Bắt Buộc
- Khi hàm `_run_upload_hook` trong `multi_machine_feed_session.py` đánh giá trạng thái organic rest, bắt buộc phát sự kiện telemetry có cấu trúc:
  ```python
  _safe_fenced_log(
      child_ctx,
      device_id=getattr(account, "serial", ""),
      account=getattr(account, "expected_username", ""),
      step="upload-hook",
      action="organic_rest_ratio_evaluated",
      result="rest" if is_organic else "active",
      machine=getattr(account, "machine", 0),
      row=upload_row,
      extra={"random_organic_rest_ratio_disabled": True, "is_organic_rest_day": is_organic},
  )
  ```
  giúp dashboard và audit log phân biệt rõ nick chạy bình thường hay bị cưỡng chế nghỉ bởi `force_rest_ledger`.

## 3. Pitfalls & Mocking Khi Viết Test Cho Upload Preflight
- `DummyAccount` trong unit test bắt buộc phải có đầy đủ các thuộc tính:
  - `machine`: số máy (int)
  - `account_row_index`: số row (int)
  - `expected_username`: username dự kiến (str) — nếu thiếu sẽ văng `AttributeError` tại Gate 4c
  - `serial`: device serial (str)
- `check_upload_cooldown_eligibility(...)` trả về 3-tuple `(is_eligible: bool, cool_reason: str, min_post_date: date | None)`. Mock phải trả về đúng 3-tuple, không dùng mock object đơn lẻ làm crash unpacking `ValueError: not enough values to unpack`.
- Để test đi sâu vào preflight Gate 4c:
  - `ctx.config["_allow_upload_hook"] = True`
  - `child_ctx.config["_session_index"] = 2`
  - `child_result = MagicMock(stop_reason="")` (không truyền `None` để tránh lỗi `child_result.stop_reason`)
