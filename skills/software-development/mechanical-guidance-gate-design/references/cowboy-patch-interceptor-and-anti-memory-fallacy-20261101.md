# Cowboy Patch Interceptor & Anti-Memory Fallacy (Kỷ Luật Mồm vs Chốt Chặn Cơ Học)

## 1. Sự Thất Bại Tuyệt Đối Của "Kỷ Luật Bằng Mồm" (The Memory Fallacy)

Khi Coordinator mắc lỗi nhảy bổ vào sửa code tay không lên kế hoạch (dẫn đến quên import `from pathlib import Path`, sót check `None` làm crash runtime), việc Coordinator phản hồi bằng văn mẫu hứa hẹn:
> *"Kỷ luật sắt em đã ghim cứng vào bộ nhớ... Cấm Coordinator tự ý sửa tay..."*

Đã bị User bác bỏ thẳng thừng:
> *"Kỉ luật cái địt mẹ mày, yêu cầu sửa hook gate. Vấn đề là mày đéo lên plan thì mày rất ngu, tự sửa lần nào cũng hỏng chưa bao giờ sửa 1 phát ăn luôn."*

### Bài Học Xương Máu:
- **Memory / Lời hứa của LLM có giá trị = 0:** Một LLM trong các turn tiếp theo sẽ luôn bị trôi ngữ cảnh (Context Drift), tiện tay gọi `patch` hoặc `write_file` để sửa nhanh, tái diễn đúng 100% lỗi cao bồi cũ.
- **Chỉ có Hook Gate cơ học mới có giá trị:** Nếu không có chốt chặn PreTool intercept tại ranh giới công cụ (`patch`, `write_file`), Coordinator sẽ liên tục phá vỡ quy trình phân vai.

---

## 2. Lỗ Hổng Cơ Chế Trong PreTool Hook Hiện Tại

### Nguyên Nhân Gốc Rễ:
- Hiện tại, plugin điều phối và các chốt chặn PreTool:
  * Chặn `terminal` chứa lệnh quét đĩa diện rộng, lệnh adb không lock.
  * Chặn `delegate_task` thiếu Dispatch Contract (Gate 3).
  * Nhưng đối với `patch` và `write_file`: **Chỉ kiểm tra whitelist đường dẫn (`D:/Taadaa`, `hermes`) và blacklist file nhạy cảm**.
- **Hệ quả:** Bất kỳ file code `.py` nào trong các repo Git (`D:/Taadaa/tools`, `D:/Taadaa/tiktok-luot nuoi acc`, `D:/Taadaa/Hermes`) đều bị Coordinator dùng `patch` sửa trực tiếp mà không hề kích hoạt `unified_patch_pipeline.py`.
- **Hậu quả trực tiếp:** Bỏ qua toàn bộ tầng S0 (Precheck) và S1 (Gate B Planner). Coordinator sửa mò, thiếu import, sót cú pháp và làm hỏng logic.

---

## 3. Thiết Kế Chốt Chặn Cơ Học (Mechanical Patch Interceptor)

### Ranh Giới Chặn (Tool Boundary Interception):
Bổ sung kiểm soát trực tiếp vào chốt chặn kiểm tra `patch` và `write_file`:

1. **Nhận diện Target File:**
   - Nếu target file có đuôi `.py` (hoặc nằm trong Git repository của farm: `D:/Taadaa/tools`, `D:/Taadaa/tiktok-luot nuoi acc`, `D:/Taadaa/Hermes`).
2. **Kiểm Tra Trạng Thái Kích Hoạt Pipeline:**
   - Kiểm tra xem tiến trình hiện tại có thuộc về `unified_patch_pipeline.py` (hoặc Worker token hợp lệ từ `dispatch_worker.py`) hay không.
   - Hoặc có cờ khẩn cấp `L2_EMERGENCY_SURGERY` thỏa mãn đúng ngân sách O(1) (<= 2 files, <= 30 dòng diff, kèm focused test) hay không.
3. **Phát Lệnh Chặn Kèm Action Mandate O(1):**
   Nếu Coordinator tự ý gọi `patch` / `write_file` trực tiếp ngoài pipeline:
   ```json
   {
     "action": "block",
     "message": "⛔ [HARD GATE - DIRECT CODE EDIT BLOCKED]: CẤM Coordinator tự ý dùng patch/write_file sửa code trực tiếp! Sửa code không có plan luôn gây lỗi hồi quy. BẮT BUỘC kích hoạt trọn gói pipeline: python D:/Taadaa/tools/unified_patch_pipeline.py run --repo <repo> --file <target_file> --task \"<mô tả>\""
   }
   ```

---

## 4. Bảng So Sánh Cơ Chế Bảo Vệ

| Tiêu Chí | Kỷ Luật Bằng Mồm (Prompt / Memory) | Chốt Chặn Cơ Học (PreTool Hook Gate) |
| :--- | :--- | :--- |
| **Bản chất** | Hứa hẹn văn mẫu, phụ thuộc sự tự giác của LLM | Intercept tại tầng biên công cụ (Tool Boundary) |
| **Độ tin cậy** | **0%** — luôn tái phạm khi gặp tình huống vội | **100%** — Tool call bị fail-closed ngay lập tức |
| **Hành vi khi vi phạm** | Sửa ẩu, quên import, crash runtime farm | Bị chặn đứng, nhận lệnh `unified_patch_pipeline` |
| **Chế tài xử phạt** | User phản ứng gắt gao, mất thời gian khắc phục | Hệ thống tự động cưỡng chế quy trình |
