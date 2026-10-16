# Architectural Blocker, Score Plateau Breaker & User Force-Push Protocol

## 1. Bệnh Thành Tích & Vòng Lặp Micro-Fix Chasing (Pathological Failure Mode)
- **Triệu chứng:** Coordinator bị kẹt trong vòng lặp đóng phiên (Closeout Gate) kéo dài hàng giờ với Sol Reviewer (:20129), điểm số trồi sụt quanh ngưỡng trượt (72 -> 52 -> 62 -> 72 -> 82).
- **Nguyên nhân gốc:** Sol Reviewer trừ điểm ở tiêu chí **Kiến trúc (Code Architecture < 7/10)** do vi phạm DRY (duplicate code giữa các file monolith runner), nhưng Coordinator lại đi "sửa ngọn":
  - Sửa microsecond (`999999 -> 0`).
  - Viết thêm hàng chục test case vụn vặt quanh 1 hàm utility.
  - Nhồi nhét comment "chúng tôi đã sync".
  - Chạy theo điểm số biên (nhiễu LLM judge) thay vì xử lý tận gốc.

## 2. Quy Tắc Nhận Diện Sớm & Tự Động Giải Quyết Dứt Điểm (Auto-Resolve)
- **Nhận diện Architectural Blocker:**
  - Nếu `code_architecture < 7/10` HOẶC feedback của Reviewer nhắc đến `DRY`, `duplication`, `copy-paste`, `monolith`:
  - **CẤM TUYỆT ĐỐI sửa ngọn T1.** Mọi nỗ lực sửa microsecond/comment/test lẻ đều vô ích và lãng phí thời gian.
- **Circuit Breaker chống kẹt (Score Plateau):**
  - Nếu sau 2 lần chấm liên tiếp mà điểm số $\Delta < 3$ điểm (ví dụ 82 -> 82) hoặc lặp lại cùng một lý do kiến trúc:
  - **Ngắt ngay Coordinator.**
  - **CẤM dừng lại khóc lóc / xin ý kiến User:** User không muốn nghe agent dừng lại than vãn hay báo cáo bế tắc.
  - **Auto-Handoff sang Claude CLI:** Giao toàn quyền cho Claude CLI nhảy vào xử lý tận gốc:
    1. Tách hàm trùng lặp ra shared module (ví dụ `scripts/watchdog/<module>.py`).
    2. Cập nhật các file monolith import từ shared module, xóa sạch đoạn code nhân bản.
    3. Chạy test xác nhận pass 100%.
    4. Chạy lại Closeout Gate lấy `APPROVED >= 85` (điểm Architecture sẽ nhảy lên 10/10).

## 3. Quyền Tối Cao Của User (User Force-Push Override)
- **Quy tắc bất biến:** `USER PROFILE` có hiệu lực tối cao đối với các lệnh cưỡng chế:
  - Khi User ra lệnh rõ ràng: *"push luôn"*, *"ép push"*, *"khỏi qua sol"*, *"bỏ qua gate"*:
  - Coordinator BẮT BUỘC thực thi ngay lập tức qua lệnh:
    ```bash
    python D:/Taadaa/tools/safe_push.py <repo> origin master -- --no-verify
    ```
  - **CẤM cãi, CẤM rên rỉ về invariant, CẤM dừng lại chất vấn.** Thực thi dứt điểm và báo cáo xác nhận SHA commit đã lên remote.
