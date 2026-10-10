# Asynchronous Stale Cron Alert Triage & Reassurance Protocol (10/10/2026)

Tài liệu đúc kết từ phiên điều phối giải đáp thắc mắc của User khi nhận cảnh báo lỗi Cronjob / Farm Alert cũ (ví dụ: `night-tiktok-2fa-watchdog` - job_id `2029d4224662`).

---

## 1. Bối cảnh & Hiện tượng (Asynchronous User Steering)
- **Hiện tượng:** User trên Telegram reply lại một tin nhắn cảnh báo cronjob thất bại (ví dụ: `⚠️ Cron 'night-tiktok-2fa-watchdog' failed: Script exited with code 1 stderr: === KÍCH HOẠT 2FA TIKTOK BAN ĐÊM LÚC 01:20:48 ...`) chỉ bằng một dấu hỏi `?` hoặc câu hỏi ngắn.
- **Đặc thù độ trễ (Latency gap):** Trên các nền tảng chat (Telegram, Discord), User thường đọc tin nhắn và phản hồi sau nhiều giờ (ví dụ: lỗi xảy ra lúc 01:20 sáng, User kiểm tra và hỏi vào chiều/tối 18:20). Trong khoảng thời gian đó, phiên làm việc trước có thể đã hoàn tất vá lỗi, vượt qua Closeout Gate và đồng bộ code lên production.

---

## 2. Bẫy phản xạ sai lầm (Anti-Patterns cần tránh)
1. **Lao vào sửa mò lại:** Nhận thông báo lỗi là lập tức sửa code, vô tình lặp lại vòng đời sửa chữa (duplicate fix) hoặc phá vỡ các commit đã được Reviewer chấm APPROVED.
2. **Báo cáo chung chung / trốn tránh:** Chỉ trả lời "đang kiểm tra" hoặc yêu cầu User giải thích thêm mà không đối soát dữ liệu hệ thống.
3. **Phỏng đoán không bằng chứng:** Khẳng định "đã fix" mà không chạy lệnh kiểm chứng thực tế tại thời điểm hiện tại.

---

## 3. Quy trình Triage 4 Bước Chuẩn (Stale Alert Triage Protocol)

### Bước 1: Trích xuất Timestamp & Định danh Cronjob
- Bóc tách chính xác thời điểm chạy trong stderr: `01:20:48 10/10/2026`.
- Bóc tách `job_id` (`2029d4224662`) và tên script liên quan (`cron_night_tiktok_2fa_watchdog.py`).

### Bước 2: Đối soát Lịch sử Phiên & Script Mtime
- Gọi `session_search(query="<tên_watchdog_hoặc_script>")` để kiểm tra xem đã có phiên nào xử lý sự cố này sau mốc timestamp chưa.
- Kiểm tra trạng thái hiện tại của cronjob qua `cronjob(action="list")`:
  - `last_status`: `ok` hay `error`?
  - `last_run_at`: Đã có lượt chạy thành công sau mốc lỗi chưa?

### Bước 3: Chạy Kiểm chứng Tức thời (Instant Sanity Check)
- Chạy thử dry-run không phá hủy:
  ```bash
  python C:/Users/Kibe/AppData/Local/hermes/scripts/<script>.py --dry-run
  ```
- Chạy focused unit test suite để xác minh 100% assertions đang pass:
  ```bash
  pytest <repo_path>/tests/test_<script>.py -v
  ```

### Bước 4: Phản hồi Bằng chứng Rõ ràng, Tường minh
- Xác nhận rõ ràng mốc thời gian xảy ra lỗi trong quá khứ so với thời điểm hiện tại.
- Trình bày ngắn gọn nguyên nhân gốc rễ (Root Cause) đã từng gây ra lỗi.
- Đưa ra bằng chứng khắc phục (Session ID, Unit test pass, Điểm Closeout Gate).
- Báo cáo trạng thái hiện tại (`last_status: ok`, `--dry-run` code 0) để User hoàn toàn an tâm.
