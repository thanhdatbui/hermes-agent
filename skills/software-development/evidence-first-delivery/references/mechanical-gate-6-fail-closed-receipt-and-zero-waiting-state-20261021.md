# Mechanical Gate 6: HMAC Fail-Closed Vision Receipt & Zero-Waiting-State Architecture

## 1. Bản chất vấn đề & Thất bại của "Quy tắc bằng lời" (Prompt-Level Rules)
Trong quá trình vận hành, các quy định bằng lời như "Bắt buộc gửi MEDIA:", "Cấm gửi mù", "Max blind steps = 1" thường xuyên bị vi phạm do 2 cơ chế cố hữu của LLM:
1. **Thói quen trần thuật thay vì hành động:** Khi gặp lỗi hoặc thực hiện thao tác UI thành công, LLM có xu hướng sinh văn bản trần thuật ("Em đã mở trang và thấy...") thay vì thực thi lệnh chụp ảnh và gửi kèm `MEDIA:`.
2. **Cạm bẫy than thở / bại liệt (Whining & Paralysis Trap):** Khi bị chặn do thiếu bằng chứng, nếu guard cho phép LLM sinh văn xuôi hoặc tạo ra cơ chế chờ (`WAITING_OPERATOR`, xin token override), Coordinator sẽ ngay lập tức "khóc lóc", báo `BLOCKED`, hoặc quay ra xin xỏ người dùng thay vì tự động chụp ảnh hoặc tiếp tục quy trình.

---

## 2. Kiến Trúc Khóa Cơ Học (Mechanical Guard Architecture)

### A. Chứng chỉ thị giác có ký số (HMAC Vision Receipt)
- Mọi thẻ `MEDIA:<path>` xuất hiện trong output của LLM bắt buộc phải có một **Vision Receipt** hợp lệ được lưu trong runtime cache:
  - `receipt_id`: Chuỗi định danh kết hợp `rec_{sha256(image)[:8]}_{timestamp}_{uuid4()[:8]}`.
  - `signature`: Chữ ký HMAC-SHA256 tính trên `image_path + sha256 + ocr_status + timestamp + reason_code`.
  - `ocr_status`: Bắt buộc là `OK` (được xác thực qua WinRT OCR hoặc Vision API thật). Nếu trạng thái là `TIMEOUT`, `FAILED`, hoặc không đọc được chữ -> Từ chối receipt.
- **Fail-Closed:** Nếu phát hiện file ảnh bị sửa đổi sau khi tạo receipt (hash mismatch), hoặc không có receipt tương ứng -> Chặn đứng lượt gửi.

### B. Cơ chế Zero-Waiting-State (Triệt tiêu 100% khóc lóc bằng cấu trúc)
- **Tước quyền sinh văn xuôi của LLM khi lỗi:** Ở nhánh lỗi thiếu ảnh / sai receipt, guard **không ném exception để LLM tự giải thích**.
- Thay vào đó, toàn bộ output của LLM bị ghi đè hoàn toàn bằng **Machine-rendered template** cố định:
  ```text
  Trạng thái: DEGRADED | Mã: MISSING_MEDIA_EVIDENCE | Thiết bị: <device_id> | Việc tiếp theo: <next_action>
  ```
- **Hiệu quả:** LLM hoàn toàn không có không gian văn bản để giải trình, xin lỗi, hay than vãn `BLOCKED`. Hệ thống chuyển thẳng sang bước tiếp theo mà không làm gián đoạn phiên làm việc.

### C. Chống tấn công ghép ngầm thẻ (Sanitizer Loop vs Tag Reassembly)
- Kẻ tấn công hoặc prompt injection có thể cố tình lách bộ lọc bằng cách chèn thẻ lồng nhau (`MEDMEDIA:IA:`, `MEDI\nA:`) để sau khi regex thay thế một lần, chuỗi lại ghép thành `MEDIA:`.
- **Giải pháp:** Sử dụng vòng lặp `while True re.sub(r'(?i)media:', '', ...)` với giới hạn cắt độ dài input an toàn (<= 256 ký tự) để tránh bẫy suy giảm hiệu năng $O(N^2)$ (DoS regex loop).

### D. Scope-Guard phân định rõ UI vs Non-UI Tool
- Hàm `is_ui_turn` phân loại nghiêm ngặt:
  - **UI Tools:** `browser`, `computer_use`, `computer-use`, `gpm`, `adb`, `inspect_machine` (kể cả dạng nested trong `function.name`).
  - **Non-UI Tools:** `read_file`, `write_file`, `terminal`, `pytest`, thảo luận chat thường -> Bypass 100%, không đòi hỏi receipt hay thẻ `MEDIA:`.
  - **Fail-closed:** Nếu tên tool rỗng hoặc payload tool call dị dạng không parse được -> Mặc định coi là UI turn và áp dụng Gate 6 nghiêm ngặt.
