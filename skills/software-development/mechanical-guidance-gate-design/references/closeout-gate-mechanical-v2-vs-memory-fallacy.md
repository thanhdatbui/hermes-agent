# Closeout Gate Mechanical V2 vs Memory Fallacy

## 1. Bản Chất Quán Tính Lưu Memory Của Hermes Agent
- Framework Hermes Agent có system prompt liên tục nhắc nhở Agent: *"Save durable facts using the memory tool: user preferences, environment details..."*.
- Điều này tạo ra một phản xạ quán tính vô điều kiện ở các mô hình: hễ có quy tắc mới hoặc User chỉnh đốn là Agent nhảy vào gọi tool `memory`.

## 2. Tử Huyệt Của Memory vs Định Luật Cơ Giới Hóa Taadaa Farm
- **User chấn chỉnh gay gắt:**
  - *"đéo dùng memory nhé, dùng memory mày đéo bh tuân thủ"*
  - *"k thiết kế trong script ddc à, có gate canary k?"*
  - *"Bỏ khỏi memory sửa tầng cơ học"*
  - *"Sao mày cứ quán tính đòi lưu memory v nhỉ. Do hermes nó thiết kế v ad"*
- **Bản chất:**
  - Memory là cam kết mềm (soft belief): rất dễ bị trôi sau các lượt nén context (compaction), model khác vào phiên mới có thể bỏ qua hoặc hiểu sai, không có tính ràng buộc thực thi.
  - Cơ giới hóa (Mechanical Layer): Định hình logic trực tiếp bằng code trong script/gate. Bất kể Agent nào, model nào hay cron nào chạy cũng bắt buộc phải đi qua đúng luồng cơ học đó.

## 3. Khai Tử Bureaucratic Theater Trong Chốt Phiên (Closeout Gate V2)
- Script `closeout_v2.py` đã được thiết kế để loại bỏ 100% hình thức chấm điểm cảm tính:
  1. KHÔNG gọi LLM Reviewer chấm điểm (81 vs 86 điểm).
  2. KHÔNG gọi Sol Repair sửa code ma trong các phiên vận hành.
  3. KHÔNG kiểm tra các commit cũ ngoài phiên.
- Quy chuẩn O(1) của `closeout_v2.py`:
  - Phiên Vận Hành (không chạm code hoặc có cờ `--operational`): Cấp APPROVED ngay lập tức trong 0.05s.
  - Phiên Code: Kiểm tra biên dịch cú pháp (`py_compile`) và chạy focused pytest. Test PASS -> Cấp APPROVED.
- **Quy tắc tuyệt đối:** CẤM dùng `memory` để ghi nhớ cách chốt phiên. Mọi quy trình chốt phiên phải được thực thi cơ học qua `closeout_v2.py`.
