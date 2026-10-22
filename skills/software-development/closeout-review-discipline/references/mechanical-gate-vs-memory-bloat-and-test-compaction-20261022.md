# Mechanical Gate vs Memory Administrative Bloat & Remediation Test Compaction (2026-10-22)

## 1. Bẫy Ghi Chép Hành Chính Vào Memory Khi Đã Có Gate Cơ Học
- **Hiện tượng:** Khi hoàn thành việc cấu hình hoặc hardcode logic vào file công cụ cơ học (ví dụ: đổi `dispatch_worker.py` sang `default="agy"`, hay triển khai `plan_exec_gate.py` với chữ ký HMAC canonical), Coordinator tự ý gọi `memory(action='replace', ...)` để ghi lại các thiết lập này vào `MEMORY` / `USER PROFILE`.
- **Hậu quả & Phản ứng của User:** User lập tức chấn chỉnh: *"Có gate cơ học r mà cập nhật memory chi v"*. Việc này là "bệnh ghi chép hành chính vô ích" (administrative bloat), vừa gây lãng phí ngân sách ký tự hữu hạn của memory (2200 chars), vừa tạo context rác vì runtime tự động ép luồng bằng code thật chứ không dựa vào memory để nhớ.
- **Quy tắc cốt lõi:**
  1. Những gì đã được khóa cứng bằng code, config, hoặc gate cơ học: ĐỂ TOOL TỰ CHẠY, CẤM ghi chép thủ tục vào `memory`.
  2. `memory` CHỈ lưu giữ sở thích cá nhân, phong cách làm việc của User, và các sự thật lâu dài về môi trường phần cứng/hạ tầng mà code không thể tự động hóa hoặc enforce được.

## 2. Bẫy Phình To Test Suite Khi Remediation Gây Truncation Diff
- **Hiện tượng:** Trong các vòng Closeout Remediation (Strike 1..4), khi cố gắng thỏa mãn mọi finding của Reviewer Sol High bằng cách append thêm hàng chục hàm test mới (đẩy file test lên 540 dòng, diff vượt 31KB), `sol_payload_guard.py` tự động cắt tỉa hunks và chèn `[TRUNCATION_MANIFEST]`.
- **Hậu quả:** Sol High thấy diff bị cắt sẽ lập tức trừ nặng điểm (từ 78 xuống 65–72) với lý do: *"Phần test bị lược chưa được review, chưa đủ cơ sở để đánh giá an toàn"*.
- **Quy tắc khắc phục:**
  1. CẤM viết test tràn lan mô phỏng lại mock logic.
  2. Giữ nguyên tắc O(1): cô đọng bộ test bằng parameterized tests hoặc helper tập trung, chỉ test các nhánh biên quan trọng nhất (`success`, `fallback_ladder`, `short_circuit`).
  3. Giữ tổng diff dưới 12KB–15KB để payload review được gửi trọn vẹn 100% không bị elide.

## 3. Chống Dừng Lại Phân Trần / Khóc Lóc Khi Gate Chưa Đạt
- **Hiện tượng:** Khi Closeout Gate trả về REJECTED hoặc kích hoạt Reviewer Hand-off, Coordinator dừng lại giải thích dông dài lý do tại sao chưa closeout được và hỏi User "bạn muốn tôi làm gì".
- **Phản ứng của User:** *"Là sao lại dừng lại khóc lóc r?"*.
- **Quy tắc ứng xử:**
  1. Không xin phép lòng vòng, không kể lể lý do.
  2. Báo cáo thẳng 3 dữ kiện cơ học: (a) Điểm số và verdict thực tế, (b) Rào cản kỹ thuật cụ thể (quota guard, pool cooldown, diff truncation), (c) 1–2 phương án hành động rõ ràng kèm khuyến nghị.
