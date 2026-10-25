# Deliver Local Silent Trap, In-Process Dispatching & Path Inference Routing

## 1. Bẫy Mất Tích Báo Cáo Khi Đổi Cron Sang `deliver: local`
- **Nguyên nhân cốt lõi:**
  - Quy chuẩn Hermes cron yêu cầu các watchdog kích hoạt batch dài hoặc đa phase đặt `deliver: local` trong `jobs.json` để chặn scheduler tự động tống stdout thô lên Telegram chat.
  - **Hệ quả bẫy:** Khi chuyển sang `deliver: local`, nếu bản thân script chỉ in kết quả ra stdout (`print(...)`) mà **không có logic tự dispatch trực tiếp qua Telegram bot API**, toàn bộ báo cáo sẽ bị lưu cục bộ vào file log trên máy và không bao giờ xuất hiện trên Telegram nhóm của User.
- **Quy tắc bắt buộc:**
  - Bất kỳ cronjob nào mang cờ `deliver: local` nhưng có trách nhiệm thông báo báo cáo ca/tiến độ **BẮT BUỘC phải tích hợp logic in-process dispatching**:
    - Tải bot token qua helper chuẩn (`automation_core.alerts._load_bot_token()`).
    - Gọi hàm gửi trực tiếp (`_send_telegram_text(token, chat_id, text)`) đến đúng channel ID phụ trách:
      - Reg Gmail: `GMAIL_REPORT_CHAT_ID = "-5139245637"`
      - 2FA TikTok: `TIKTOK_REPORT_CHAT_ID = "-5468653590"`
  - Tuyệt đối không chỉ đổi `deliver: local` trong `jobs.json` rồi báo cáo "đã phân tách luồng" trong khi file mã nguồn chưa thực sự nhúng hàm gửi Telegram.

---

## 2. Bẫy Thứ Tự Từ Khóa Nhận Diện Repo Trong `batch_aggregator.py`
- **Vấn đề:**
  - Khi script runner (`run_parallel.ps1`) gọi `automation_core.batch_aggregator "$summaryJson" --telegram` mà không truyền tham số tường minh `--script <name>`, hệ thống phải dựa vào `detect_script_from_source(path)` để quét chuỗi đường dẫn thư mục log (ví dụ: `.../codex_gmail_debug-register-gmail/...`).
  - Trong mảng keyword mapping:
    ```python
    ("reg", "Tiktok_Reg"),
    ("gmail", "register-gmail"),
    ```
    Từ khóa ngắn `"reg"` đứng trước `"gmail"` nên chuỗi `"register-gmail"` bị match ngay lập tức thành `"Tiktok_Reg"`, đẩy toàn bộ alert sự cố sang nhóm Reg TikTok (`-5494641602`) thay vì Reg Gmail (`-5139245637`).
- **Khắc phục:**
  1. Trong `batch_aggregator.py`: Luôn đặt các keyword dài và đặc thù (`"gmail"`) lên trước keyword ngắn (`"reg"`).
  2. Tại kịch bản gọi (`run_parallel.ps1`): BẮT BUỘC truyền rõ `--script register-gmail` thay vì để cơ chế heuristic suy đoán từ path.

---

## 3. Bẫy Kẹt Idempotency Qua Đêm (`already_ran_today`)
- **Vấn đề:**
  - Các script watchdog ca trưa thường có hàm `already_ran_today(today_str)` đọc `last_success_date` từ state file (`post_noon_chain_state.json`).
  - Nếu có đợt chạy ad-hoc, debug hoặc test lúc rạng sáng (ví dụ: `02:42 AM`) và ghi nhận `last_success_date = <today>`, thì khi đến khung giờ ca trưa thực tế (14:30 – 17:30), watchdog kiểm tra thấy `already_ran_today == True` và lập tức thoát sớm (`return 0`), bỏ qua toàn bộ ca chạy và không sinh báo cáo.
- **Khắc phục:**
  - Idempotency theo ca phải gắn liền với phiên/mốc thời gian cụ thể (ví dụ: `<date>_ca_trua` hoặc kết hợp kiểm tra giờ bắt đầu), tránh dùng chung cờ ngày thuần túy làm tê liệt các ca sau trong ngày.
