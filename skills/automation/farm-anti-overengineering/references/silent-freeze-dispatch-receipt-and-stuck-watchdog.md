# Silent Freeze, Dispatch Receipt & Stuck Watchdog Pattern

## 1. Sự Cố "Treo Im Lặng 1 Tiếng" (06/09/2026)
- **Hiện tượng:** Coordinator nhận task nhưng output `[SILENT]` sau khi dispatch, trong khi 2 Worker subagent chạy ngâm lệnh liên tiếp (Worker 1 chạy 44 phút kịch trần 35 turns, Worker 2 chạy 20 phút cho hotfix 2 dòng). Khung chat Telegram hoàn toàn bất động suốt hơn 1 giờ khiến user cực kỳ bức xúc (*"Lí do treo im lặng? Địt mẹ mày"*).
- **Nguyên nhân cốt lõi:**
  1. **Áp dụng sai quy tắc `[SILENT]`:** Coordinator nhầm lẫn giữa việc "giảm loãng log/tool output" với "giao diện người dùng", tự ý emit `[SILENT]` khi gọi `delegate_task`.
  2. **Trộn lẫn Code Patch với Canary Device:** Nhét cả việc đọc/sửa file Python và chạy Canary thật qua ADB vào 1 Worker subagent khiến thời gian thực thi bị đội lên 40+ phút mà không có điểm dừng trung gian.
  3. **Thiếu ranh giới giữa "Đang chạy lâu" vs "Bị treo thực sự":** User chấp nhận tác vụ chạy lâu nếu có việc thật (Canary thiết bị), nhưng KHÔNG chấp nhận việc hệ thống im lặng khi bị đơ/treo.

---

## 2. Quy Tắc Dispatch Receipt (Cấm Tuyệt Đối `[SILENT]`)
- **BANNED:** CẤM TUYỆT ĐỐI output token `[SILENT]` tại bất kỳ turn nào Coordinator gọi `delegate_task`.
- **BẮT BUỘC gửi 1 tin thông báo ngay khi giao việc (Dispatch Receipt):**
  ```text
  🚀 Đang giao việc: [Mục tiêu ngắn gọn]. Phạm vi: [File/Module]. Dự kiến: [Thời gian/Canary].
  ```
- **Không spam tiến độ liên tục:** Không cần gửi tin nhắn định kỳ 60s gây loãng chat. User chỉ cần biết việc đã bắt đầu và khi nào hoàn thành.

---

## 3. Tách Bạch 2 Pha: Code Patch vs Device Canary (Pipeline Separation)
- **Pha 1 — Patch Code (Worker chuyên trách, Tier 1):**
  + Nhiệm vụ: Đọc đúng traceback -> Sửa đúng file (Scope Lock) -> `py_compile`.
  + Giới hạn cứng: <= 10 turns, hoàn tất trong <= 5 phút. CẤM can thiệp ADB hoặc chạy Canary trong pha này.
  + Báo cáo ngay khi xong: *"Đã sửa xong code và verify cú pháp, bắt đầu kích hoạt Canary trên máy N..."*
- **Pha 2 — Canary Test (Coordinator hoặc Worker chuyên trách):**
  + Kích hoạt sau khi Pha 1 đã xác nhận byte ghi xuống đĩa.
  + Chạy script canary trên máy thật (`run-feed-session.ps1` hoặc tương đương). Pha này chạy 5–8 phút là hợp lệ và user đã nắm rõ bối cảnh.

---

## 4. Cơ Chế Silent Watchdog ("Chỉ Hú Khi Thực Sự Treo")
- **Nguyên tắc:** Bình thường giữ yên lặng tuyệt đối để không spam chat Telegram; CHỈ bắn cảnh báo khi phát hiện tiến trình thực sự bị đơ/treo:
  1. **Ngưỡng kiểm tra (Dual-Thresholds):**
     + **Thao tác thường (Code fix, inspect, compile):** Ngưỡng treo = **> 10 phút (600s)** không có tool call mới.
     + **Live Device Canary máy thật:** Ngưỡng treo = **> 25 phút (1500s)** để cho phép điện thoại thực hiện đầy đủ chu kỳ khởi động app, nạp tài khoản và lướt feed thật.
  2. **Hạ tầng triển khai:**
     + **Hook `post_tool_call` (`farm-coordinator-guard` v2.1):** Tự động ghi nhận heartbeat sau mỗi tool call vào `watchdog_state.json` (atomic write bằng tmp file cùng thư mục + replace). Thu hẹp nhận diện `is_canary` bằng regex `r'\b(canary|recoverytestswipes)\b'` (loại trừ từ "swipe" thông thường).
     + **Script `hermes_stale_watchdog.py`:** Chạy ngầm qua cronjob `hermes-stale-watchdog` mỗi 2 phút (`no_agent=True`, `deliver=origin`). Toàn bộ `main()` được bọc `try...except` để đảm bảo khi bình thường hoặc idle thì stdout hoàn toàn trắng, không bao giờ in traceback gây nhiễu Telegram.
  3. **Cơ chế chống spam (One-shot Alert):**
     + Dùng `stale_alert_sent.json` ghi nhận timestamp đã cảnh báo. Mỗi sự cố treo chỉ phát đúng 1 thông báo duy nhất về Telegram cho đến khi có beat mới hoặc session được giải phóng.
