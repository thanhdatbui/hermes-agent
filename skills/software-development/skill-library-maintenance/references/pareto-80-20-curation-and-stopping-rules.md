# Pareto 80/20 Discipline & Stopping Rules in Farm Operations

## Context & Core Philosophy (15/10/2026)
User directive: "Trả lời theo 80/20 đi. Từ h t muốn mọi công việc đều xử lý theo nguyên tắc 80/20".
Trong môi trường Phone Farm phức tạp, 20% nguyên nhân gốc rễ giải quyết 80% độ ổn định hệ thống. Ngược lại, 80% thời gian sau đó thường bị lãng phí vào 20% tiểu tiết vô hình hoặc bẫy over-engineering.

---

## 1. Stopping Rules (Điểm dừng dứt khoát)
- **Khi nào DỪNG?**
  1. Toàn bộ test suite liên quan (architecture gate, unit test) đều PASS 100%.
  2. Toàn bộ Cron/Watchdog runtime liên quan đang ở trạng thái `ok` và trả về báo cáo thực tế.
  3. Lỗi Invariant dữ liệu (như Excel Preflight Validator) đã sạch 0 FAIL, 0 WARN.
- **Dấu hiệu bẫy Over-Engineering (BẮT BUỘC DỪNG NGAY):**
  - Tiếp tục chẻ nhỏ file/module khi hệ thống đã xanh chỉ để "đẹp mã nguồn".
  - Refactor lại logic đang chạy ổn định của các module phụ.
  - Tự ý sinh thêm wrapper/helper không có yêu cầu nghiệp vụ thực tế.

---

## 2. Communication & Reporting Discipline (80/20)
- **Báo cáo cực ngắn gọn, đi thẳng vào kết luận:**
  - Bỏ toàn bộ lẩm bẩm debug, chi tiết dòng lệnh nội bộ, hoặc danh sách dài dòng không mang lại quyết định.
  - Trả lời theo cấu trúc 3 phần:
    1. **Kết quả cốt lõi:** Đã xong chưa? (XANH / ĐỎ / BLOCKED kèm bằng chứng).
    2. **Điểm nghẽn duy nhất (nếu có):** Nguyên nhân 20% gây ra 80% lỗi.
    3. **Hành động tiếp theo:** Bước cụ thể tiếp theo cần làm hoặc đề xuất DỪNG.

---

## 3. Autonomous Curation Constraints
- Các skills thuộc sở hữu của User (`created_by=None`) như `farm-anti-overengineering` hoặc `session-close-protocol` được bảo vệ tự động chống can thiệp autonomous ngoài ý muốn.
- Kỷ luật 80/20 cần được tích hợp vào các skill class-level được curator quản lý (`skill-library-maintenance`) và ghi nhận vào persistent memory của Agent để áp dụng nhất quán trên toàn bộ các phiên làm việc.
