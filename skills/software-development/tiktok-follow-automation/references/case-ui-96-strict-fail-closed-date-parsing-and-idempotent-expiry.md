# Case UI 96: Strict Fail-Closed Legacy Date Parsing & Idempotent Cooldown Expiry

## Context & Problem
Trong cơ chế migration legacy cooldown state (`follow_state.py`):
1. **Lỗ hổng cắt chuỗi mù (`[:10]`):**
   - Trước đây dùng `str(legacy_failed_date).strip()[:10]` để parse ngày legacy dạng `%Y-%m-%d`.
   - Các chuỗi dữ liệu hỏng mang đuôi rác như `"2026-08-27-corrupt"` hoặc `"2020-01-01junk"` bị cắt gọt thành chuỗi ngày hợp lệ, né tránh nhánh `except` (fail-closed).
   - Với các ngày lỗi trong quá khứ, việc parse thành công khiến trạng thái bị coi là **hết hạn cooldown** (`expired`), dẫn đến **fail-open** — tài khoản tiếp tục đi follow dù đang gặp lỗi state hỏng.
2. **Lặp migration & Write Churn sau khi hết hạn cooldown:**
   - Trong nhánh hết hạn cooldown (`expired`), code chỉ pop `cooldown_until_at` và `cooldown_until_date` nhưng vẫn giữ lại `follow_failed_date` / `last_failed_date`.
   - Ở các lần đọc sau, điều kiện `"cooldown_until_at" not in self._data and "follow_failed_date" in self._data` lại thỏa mãn, khiến migration chạy lại trên mỗi lần đọc `follow_failed`, liên tục save disk và spam log `[COOLDOWN_EXPIRED]`.

## Triệt để giải quyết (Rules)
1. **Parse toàn vẹn chuỗi ngày (Strict Exact Match):**
   - Tuyệt đối không dùng slicing `[:10]` khi parse chuỗi ngày từ state.
   - Yêu cầu `isinstance(legacy_failed_date, str)` và parse toàn bộ chuỗi với `datetime.strptime(legacy_failed_date, "%Y-%m-%d")`.
   - Bất kỳ chuỗi nào thừa ký tự, có suffix, hoặc sai định dạng đều phải throw exception và rơi thẳng vào nhánh fail-closed:
     ```python
     logger.warning("[COOLDOWN_MIGRATION_ERROR] machine=%s row=%s malformed date=%r, failing closed", ...)
     return True  # Lock account safely
     ```
2. **Dọn sạch marker legacy khi hết hạn (Idempotent Expiry):**
   - Khi legacy cooldown đã hết hạn, bắt buộc pop toàn bộ marker liên quan:
     ```python
     self._data["follow_failed"] = False
     self._data.pop("follow_failed_date", None)
     self._data.pop("last_failed_date", None)
     self._data.pop("cooldown_until_at", None)
     self._data.pop("cooldown_until_date", None)
     self._save()
     ```
   - Đảm bảo các lần đọc tiếp theo không bao giờ kích hoạt lại migration hay ghi lại file state khi không có thay đổi.
