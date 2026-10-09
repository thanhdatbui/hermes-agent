# Gmail Preflight Live Check & Dual Cleanup (`_run_all_targets.py`)

## Tổng quan kiến trúc
Khi khởi chạy batch đăng ký TikTok qua `_run_all_targets.py`, runner tự động thực hiện preflight check live danh sách email đuôi `@gmail.com` qua module chuyên dụng `scripts.gmail_preflight_filter` trước khi phân chia batch workers sang các thiết bị Android S7.

## Luồng hoạt động (Workflow)
1. **Lọc mục tiêu**: Runner quét toàn bộ `targets` thu thập từ detection, tách các target có email kết thúc bằng `@gmail.com`.
2. **Batch Check Fast**:
   - Sử dụng Playwright headless kết hợp GPM Chromium (`gpm_browser_chromium_core_142`) và mobile proxy (`mobi1` tại `test.taadaa.click:5101`).
   - Gọi `check_gmail_live_batch(emails, max_batch_size=50)`.
   - Parse kết quả từ `window.liveResultEditor` dựa trên thẻ `[LIVE]` và `[DIE]`. Mọi email không có thẻ hoặc gặp lỗi parse mặc định coi là `True` (fail-open an toàn, không xóa nhầm).
   - **Lưu ý xác thực session checkmail.live**: Khi gọi checkmail.live, cần dùng persistent context có session cookie đã đăng nhập (như trong `D:/Taadaa/GPM auto/checkmail_proxy_data` qua `run_checkmail_kibe_farm.py`).
3. **Xử lý Target DIE & Dọn dẹp Song song (Dual Cleanup)**:
   - Ghi log: `[DIE-SKIP] STT={stt} Gmail {email} đã DIE -> Loại khỏi danh sách reg!`
   - **Dọn dẹp nguồn Excel**: `from social_reg_v1 import remove_captcha_dead_email_from_source; remove_captcha_dead_email_from_source(email)` để tự động khóa và xóa dòng tương ứng trong file nguồn `gmail_clean_v2.xlsx`, đồng thời append vào `gmail_die_tong.txt`.
   - **Dọn dẹp trên máy Android S7**: `from remove_device_google_account import remove_device_account_fast; remove_device_account_fast(str(t.get("device") or ""), t["email"])`.
     - `remove_device_account_fast` dùng `get_adb_exe()` (tự động phân giải từ `adb_config.resolve_adb_executable()`).
     - Kiểm tra `dumpsys account` trước: nếu máy đã sạch (không còn account) thì return `True` ngay, không trigger UI thao tác thừa.
     - **Quy trình UI gỡ tài khoản trên Samsung S7 (Android 8)**:
       1. Mở `am start -a android.settings.SYNC_SETTINGS`.
       2. Quét UI XML (`uiautomator dump`) tìm node chứa email. **CẤM gửi mù `keyevent 4` ngay sau khi mở**, vì nếu màn hình đang ở danh sách tổng "TÀI KHOẢN", ấn Back sẽ văng ra Launcher. Chỉ Back fallback khi không thấy email trong lần quét đầu tiên.
       3. Tap vào email mục tiêu -> Màn hình chi tiết xuất hiện nút **"XÓA TÀI KHOẢN"** (`bounds: [261,855][819,981]`). Chú ý normalize Unicode NFC để so sánh chuỗi tiếng Việt.
       4. Tap xác nhận trên popup (`android:id/button1`).
       5. Bấm `keyevent 3` (HOME) để đưa máy về trạng thái an toàn.
     - Bọc riêng trong `try...except` với log `[DEVICE-CLEANUP-WARN]` để không ngắt luồng reg khi máy offline/mất ADB.
   - Loại target khỏi danh sách chạy hiện tại.
4. **Vị trí gọi & Cờ bỏ qua (CLI Flag)**:
   - Gọi `filter_live_gmail_targets()` TRƯỚC khi áp dụng giới hạn `--max-targets`, đảm bảo số lượng target chạy thật không bị hao hụt khi có tài khoản DIE bị loại.
   - `--skip-live-check`: Cho phép bỏ qua hoàn toàn preflight check live khi cần (chạy test, debug offline hoặc khi proxy mobi1 gián đoạn).

## Unit Testing & Module Import Pitfall
- **Vấn đề**: `_run_all_targets.py` chứa mã thực thi ở module top-level (`args = parse_args()`, gọi subprocess `_detect_clean.py`, v.v.).
- **Nguyên tắc test**: Không `import _run_all_targets` trực tiếp trong pytest nếu không mock toàn bộ `sys.argv` và môi trường, vì nó sẽ kích hoạt detector thật.
- **Giải pháp**: Tách module logic ra `scripts/gmail_preflight_filter.py` và viết unit test cho hàm parse (`parse_checkmail_live_output`) từ `check_gmail_live_fast.py` và test logic lọc/mocking cleanup độc lập trong `tests/test_gmail_preflight_check.py`.
