# Gate 6 Auto-Rewire & Action Mandate Guidance Architecture

## 1. Nguyên Tắc Cốt Lõi: Chống Bại Liệt L3 & Cấm Đứng Im
- Trong các hệ thống Gate của Taadaa Farm (như `guard_broad_grep`, `guard_dispatch_contract`, `closeout_gate`):
  - Gate cơ học KHÔNG ĐƯỢC PHÉP chỉ dừng lại ở việc `block` thụ động rồi để Agent tự xoay sở hoặc hạ cấp xuống `L3 BLOCKED` để trốn việc.
  - Khi một thao tác thiếu bằng chứng hoặc sai quy cách, Gate BẮT BUỘC phải cung cấp một trong hai cơ chế chủ động:
    1. **Auto-Rewire:** Tự động sửa/bù đắp tham số hợp lệ (ví dụ auto-clamp timeout, auto-inject budget, auto-append thẻ ảnh).
    2. **Guidance Action Mandate:** Trả về lệnh thực thi $O(1)$ rõ ràng để Agent thực hiện ngay, đưa trạng thái về DONE thay vì BLOCKED.

## 2. Ứng Dụng Vào Gate 6 (Visual Evidence Invariant)
Khi phát hiện turn có tương tác UI mà tin nhắn claim hoàn tất thiếu thẻ `MEDIA:`:
- **Cơ chế 1 (Auto-Rewire):** Hệ thống tại `transform_llm_output` tự động lấy ảnh chụp màn hình tươi nhất trong session (`latest_evidence_image`) và găm thẻ `MEDIA:<path>` vào cuối tin nhắn trước khi phát hành ra Telegram.
- **Cơ chế 2 (Guidance Injection):** Nếu thiết bị lỗi kết nối không thể screencap, Gate trả về `action: rewrite` hoặc inject chỉ dẫn bắt buộc chạy lệnh cứu hộ:
  ```bash
  python D:/Taadaa/tools/inspect_machine.py <N>
  ```
- **Triệt tiêu hoàn toàn:** Hiện tượng LLM xin lỗi dông dài, giải thích phân trần, hoặc vội vã báo cáo `L3 BLOCKED` đùn đẩy trách nhiệm cho User.
