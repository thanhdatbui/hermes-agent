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

---

## 4. Bẫy Môi Trường Scheduler Gây Lỗi `No module named 'automation_core.alerts'`
- **Vấn đề:**
  - Khi script watchdog chạy qua Hermes cron runner (`no_agent: true`), tiến trình được thực thi độc lập bằng Python của hệ điều hành hoặc venv scheduler, không tự động kế thừa `PYTHONPATH` của repo.
  - Khi watchdog gọi `from automation_core.alerts import _load_bot_token`, nếu `sys.path` chưa chèn đường dẫn tuyệt đối chuẩn hoặc module con phát sinh lỗi import thư viện bên thứ 3 (như `PIL`), Python sẽ ném `ModuleNotFoundError: No module named 'automation_core.alerts'`.
  - Khi không đọc được token, hàm gửi tin thường log warning và âm thầm bỏ qua (`Không có Telegram bot token, bỏ qua báo cáo`), khiến watchdog đêm hoặc ca trưa tưởng như chạy xong nhưng hoàn toàn mất hút báo cáo trên Telegram.
- **Khắc phục:**
  - BẮT BUỘC chèn đường dẫn tuyệt đối `sys.path.insert(0, r"D:/Taadaa/automation-core/src")` ở ngay đầu file hoặc trong bootstrap block trước mọi import nghiệp vụ.
  - Bổ sung cơ chế fallback đọc bot token trực tiếp từ file cấu hình / secrets nếu `automation_core.alerts` không thể tải.

---

## 5. Quy Trình Rà Soát Hệ Thống Báo Cáo Cron Bị Nuốt Chửng (Systemic Audit Protocol)
- **Phương pháp rà soát nhanh O(1) trên toàn bộ farm:**
  - Quét danh sách cronjob trong `jobs.json` lọc các job thỏa mãn 2 điều kiện:
    1. Cấu hình `deliver: "local"`.
    2. Tên job hoặc prompt mang ý nghĩa báo cáo/theo dõi (`report`, `watchdog`, `báo cáo`, `tracker`).
  - Kiểm tra mã nguồn script tương ứng: Nếu script chỉ `print(summary)` mà không có các hàm gọi Telegram (`_send_telegram_text`, `dispatch_report`, HTTP sendMessage), thì job đó CHẮC CHẮN đang bị nuốt chửng báo cáo cục bộ (như `daily-tiktok-farm-tracker`, `post-morning-gmail-2fa-watchdog`).
  - Đối với các job này, phải chủ động: hoặc bổ sung in-process `dispatch_report()`, hoặc cấu hình `deliver: telegram:<chat_id>` kèm silent skip khi không có nội dung.
