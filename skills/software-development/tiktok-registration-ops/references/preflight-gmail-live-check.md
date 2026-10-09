# Preflight Check Live Gmail via checkmail.live (Anti-OTP Timeout)

## Bối cảnh & Vấn đề:
Khi chạy batch reg TikTok (`_run_all_targets.py` / `social_reg_v1.py`), nếu danh sách mục tiêu chứa Gmail đã bị khóa/DIE bởi Google (vô hiệu hóa, captcha checkpoint, đổi pass), TikTok không thể phát thư OTP về inbox. Máy S7 bị kẹt chờ trong app Gmail suốt timeout 150s (`GMAIL_OTP_ATTEMPT_TIMEOUT`) dẫn đến lỗi hàng loạt:
`[7c][BLOCKED_GMAIL_OTP_TIMEOUT] <email>`

## Giải pháp Preflight Check Live:
1. **Công cụ nền tảng**:
   - File: `D:/Taadaa/tools/check_gmail_live_fast.py`
   - Chạy Playwright kết nối web `https://checkmail.live/` qua proxy Mobi1 (`http://test.taadaa.click:5101`).
   - Hàm `check_gmail_live_batch(emails: list[str]) -> dict[str, bool]` kiểm tra đồng loạt danh sách email và parse nhãn `[LIVE]` / `[DIE]`.
   - Cơ chế fail-open an toàn: nếu gặp sự cố mạng hoặc timeout, fallback giữ `True` (không tự ý coi là DIE nếu chưa có kết quả khẳng định).

2. **Quy trình tích hợp trong `_run_all_targets.py`**:
   - Hàm chuẩn hóa module-level: `filter_live_gmail_targets(targets: list[dict[str, object]]) -> list[dict[str, object]]`.
   - Trước khi chia worker batch và dispatch máy S7: tự động gom toàn bộ Gmail trong danh sách mục tiêu.
   - Gọi `check_gmail_live_batch` để rà soát.
   - Mail nào được web khẳng định **DIE** (`live_map.get(em) is False`):
     + Loại khỏi danh sách chạy ngay lập tức, tiết kiệm 150s chờ vô ích trên thiết bị thật.
     + Gọi `remove_captcha_dead_email_from_source(email)` để xóa dứt điểm khỏi file nguồn `gmail_clean_v2.xlsx`, tránh việc các batch sau lại bốc trúng.
     + Gọi `remove_device_account_fast(device, email)` từ `tools/remove_device_google_account.py` để dọn sạch account DIE đang gán trên thiết bị Samsung.
   - Cờ `--skip-live-check`:
     ```python
     if not getattr(args, "skip_live_check", False):
         targets = filter_live_gmail_targets(targets)
     ```

## Lưu ý Test & Refactoring (Pitfalls):
- **Top-level execution trap**: `_run_all_targets.py` có mã chạy detector / subprocess ở top-level nếu không được bọc dưới `if __name__ == "__main__":`. Khi viết unit test cho `filter_live_gmail_targets`, cần đảm bảo script không tự động kích hoạt detector khi import hoặc bọc entrypoint runner sạch sẽ.
- **Fail-open contract**: CHỈ dọn dẹp và skip khi `live_map.get(em) is False`. Nếu email không có trong kết quả hoặc gặp sự cố mạng, giữ nguyên target để không làm gián đoạn batch reg.
- **Dependency load failure**: Khi không import được các tools phụ trợ, ném `RuntimeError(f"PREFLIGHT_LIVE_DEPENDENCY_ERROR: {exc}")` để fail-closed rõ ràng thay vì nuốt lỗi âm thầm.

