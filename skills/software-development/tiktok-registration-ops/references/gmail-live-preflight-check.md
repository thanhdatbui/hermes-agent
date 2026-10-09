# Preflight Check Live Gmail trước khi chạy Batch Reg TikTok

## 1. Mục đích
Tránh lãng phí thời gian mở thiết bị, cài đặt môi trường và thao tác reg TikTok khi tài khoản Gmail đã DIE (bị khóa, xóa hoặc yêu cầu verify từ trước).

## 2. Công cụ hỗ trợ
- Module: `D:\Taadaa\tools\check_gmail_live_fast.py`
- Hàm chính:
  - `check_gmail_live_batch(emails: list[str], max_batch_size: int = 50) -> dict[str, bool]`:
    - Gom nhóm kiểm tra tối đa 50 Gmail mỗi session qua Playwright và mobile proxy (`test.taadaa.click:5101` với profile gpm browser).
    - Parse kết quả `[LIVE]` / `[DIE]` từ editor của checkmail.live.
    - Cơ chế fail-open: gặp sự cố kết nối hoặc lỗi bất ngờ mặc định trả về `True` (LIVE) để không xóa nhầm mail hợp lệ.
  - `check_gmail_is_live(email: str) -> bool`: Wrapper cho single email.

## 3. Tích hợp trong `_run_all_targets.py`
- Preflight check chạy trước khi phân bổ vào `batches`:
  - Lọc danh sách target có email đuôi `@gmail.com`.
  - Chạy `check_gmail_live_batch()` lấy status map.
  - Loại các target có email DIE, in cảnh báo `[DIE-SKIP]`.
  - Gọi `remove_captcha_dead_email_from_source(target["email"])` để dọn dẹp sạch file nguồn Excel.
- Hỗ trợ cờ `--skip-live-check` khi cần bypass preflight (ví dụ khi proxy hoặc mạng chập chờn).
