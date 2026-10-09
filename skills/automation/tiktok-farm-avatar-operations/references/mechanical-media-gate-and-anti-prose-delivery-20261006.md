# Mechanical MEDIA Evidence Gate, Visual Verification Discipline & Architecture Consultation (06/10/2026)

## 1. Sự cố thực tế ngày 06/10/2026 (Máy 15 & Máy 16)
1. **Hiện tượng:**
   - Hoàn thành đổi avatar trên Máy 16 (`@verdhsclf6f` / Tik 5) và Máy 15 (`@ngobaoquynh29` / Tik 7). Runner trả về `AVATAR_SMOKE_SUCCESS` và `FORCED_REPLACED_VERIFIED`.
   - Tuy nhiên, Coordinator lại nộp kết quả bằng cách dán đường dẫn thư mục và file ảnh vào code block markdown thay vì xuất thẻ `MEDIA:<path>` ở dòng riêng để Telegram client tự động hiển thị ảnh cho Operator.
   - User phản ánh gay gắt:
     * *"hình đâu gửi link folder ăn l à"*
     * *"lí do tại sao k gửi ảnh mà đi gửi link, rule k ép chặt mày à?"*
     * *"tao đang yêu cầu hỏi lí do mày làm sai, rule thiết kế k chặt r, gọi claude sonnet tư vấn thiết kế r mày thi công lại"*
     * *"làm đi, và yêu cầu LLM phải đọc ảnh trc khi gửi tao, tránh việc gửi ảnh cho có lệ"*
     * *"gọi advisor kiểm tra"*

2. **Căn nguyên kỹ thuật (Root Cause):**
   - **Rule dạng lời dặn (Advisory Prose) vs Chốt chặn cơ học (Mechanical Gate):** Trước đó, Gate 6 và các quy định trong skill chỉ tồn tại dưới dạng văn bản nhắc nhở model trong prompt. Hệ thống thiếu một chốt chặn vật lý quét literal text trước khi đưa ra kênh truyền tin (Telegram delivery).
   - Mô hình dễ bị trôi ngữ cảnh khi xử lý nhiều lượt, ngộ nhận việc in đường dẫn file trong code block là đã hoàn thành nghĩa vụ báo cáo.

---

## 2. Quy trình 4 bước chuẩn hóa kiến trúc (Sonnet Design $\to$ Build $\to$ SOUL Hardening $\to$ Advisor Review)

### Bước 1: Tư vấn thiết kế Read-Only từ Claude Sonnet
- Khi rule thiết kế lỏng lẻo, không tự vá chắp vá: Gọi Claude Sonnet (`claude -p`) ở chế độ Read-Only để phân tích ranh giới và lên bản vẽ thiết kế `media_evidence_gate.py` fail-closed.
- Sonnet chỉ rõ: Chặn ngay trước `_deliver_to_platform` trong `gateway/delivery.py`. Mọi tin nhắn mang cờ báo hoàn tất bắt buộc phải có thẻ `MEDIA:<absolute_path>`. Cấm đường dẫn thô, cấm bọc trong code fence markdown, kiểm tra file tồn tại, độ tươi (freshness), kích thước tối thiểu và độ lệch chuẩn hình ảnh.

### Bước 2: Thi công Mechanical Gate trong Core Hermes
- Module: `gateway/media_evidence_gate.py`
  * Nhận diện cờ hoàn tất (`DONE`, `VERIFIED_SUCCESS`, `FIXED`, `HOÀN TẤT`, `ĐÃ XONG`, `THÀNH CÔNG`...) và biểu thức chính quy tiếng Việt (`đã ... xong/rồi/thành công`).
  * Trích xuất token `MEDIA:`, đối soát containment trong `run_dir` / `evidence_roots`.
  * Kiểm tra độ sáng và độ lệch chuẩn ảnh: Chặn ảnh đen kịt (`mean <= 2.0`), ảnh trắng xóa (`mean >= 253.0`), và ảnh màu phẳng không chi tiết (`stddev < 3.0`).
- Tích hợp vào `DeliveryRouter._deliver_to_platform()`: Chặn đứng tin nhắn trước khi chạm vào adapter Telegram nếu vi phạm evidence gate.
- Unit test: `tests/gateway/test_media_evidence_gate.py` đạt 7/7 tests pass.

### Bước 3: Đưa Kỷ luật Soi Mắt Đọc Ảnh vào SOUL.md và Skill
- Cập nhật trực tiếp vào `SOUL.md` (System Prompt gốc) và các skill vận hành:
  * **CẤM gửi ảnh mù / gửi đối phó:** Trước khi xuất thẻ `MEDIA:<path>`, LLM BẮT BUỘC phải dùng `browser_vision` hoặc OCR mở ảnh ra soi mắt kiểm tra trước.
  * Xác nhận đúng màn hình đích (Profile/Switcher), đúng nhân vật/avatar mới, không bị lỗi hiển thị.
  * Trong tin nhắn, bắt buộc tóm tắt ngắn gọn những gì đã thấy tận mắt qua vision thay vì ném link ảnh vô cảm.

### Bước 4: Thẩm định độc lập từ Advisor (Hermes Advisory Board)
- Gọi model `plan-review` qua 9Router (`invoke-plan-review.py`) thẩm định giải pháp:
  * Advisor đánh giá 7.5/10 (`MINOR_FIXES`), khen ngợi kiến trúc Mechanical Gate biến rule thành barrier vật lý.
  * Chỉ ra 2 điểm cần vá:
    1. **Semantic Bypass:** LLM paraphrase né keyword cứng $\to$ Đã vá bằng regex `_COMPLETION_REGEX` bắt trọn các câu hoàn tất tiếng Việt.
    2. **Ảnh đơn sắc:** Chống trường hợp gửi ảnh trắng hoặc màu solid $\to$ Đã vá bằng kiểm tra độ lệch chuẩn độ xám `stddev < 3.0`.

---

## 3. Kỷ luật khi phát hiện Avatar lệch Niche ("Đổi đi hỏi lại chi v")
- Khi Operator gửi ảnh hỏi kiểm tra và Coordinator đã chẩn đoán chính xác avatar bị lệch niche / dính rủi ro chính sách:
  * **CẤM hỏi lại:** Tuyệt đối không hỏi *"Có muốn đổi không?"* hay dừng lại xin ý kiến vô ích.
  * **Thực thi dứt điểm:** Tự động cắt frame chuẩn nhất từ video kênh, đồng bộ 2 đầu kho (`D:\video goc` và `D:\TIKTOK-videonuoinick`), cập nhật `avatar_replace_queue` về `status = 'PENDING'`, và kích hoạt canonical runner (`run_tiktok_upload_avatar.ps1`) chạy nền có event-driven wakeup.
