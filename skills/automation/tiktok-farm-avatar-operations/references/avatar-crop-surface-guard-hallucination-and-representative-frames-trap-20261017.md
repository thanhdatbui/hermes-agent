# Bẫy Representative Frames Giả Mạo, Haar Cascade False Positive & Kỷ Luật WinRT OCR / Vision (2026-10-17)

## 1. Bản Chất Sự Cố (Root Cause Analysis - Case @yobi1965 M34 Tik 6)
- **Hiện tượng**:
  - Khi nạp avatar cho tài khoản Yoga `@yobi1965`, tool chụp màn hình `avatar-save-surface-guard.png`.
  - Trên màn hình app TikTok, vòng tròn crop thực tế hiển thị một mảng màu đỏ/hồng nhòe nhoẹt (góc rào chắn/mũ bảo hiểm ngoài trời), hoàn toàn KHÔNG có người.
  - Tuy nhiên, Coordinator lại báo cáo tự tin: *"Người phụ nữ trong tư thế ngồi Yoga thẳng đứng, mắt nhìn thẳng, gương mặt sáng sủa..."*.
  - User phát hiện và nổi giận: *"Ảnh đéo thấy clg cả mỗi 1 khoảng đỏ mà mày dám chọn đc, mày có dùng WinRT OCR đọc ảnh không vậy?"*.

- **Gốc rễ kỹ thuật**:
  1. **Bẫy `representative_frames` rác**:
     - Thư mục `D:/video goc/<folder>/.avatar_work/representative_frames/` được sinh ra tự động từ crawler, chứa nhiều frame tĩnh không có người (sàn nhà, thảm tập, góc tường, background nhòe).
     - Thuật toán dò mặt cổ điển `Haar Cascade` (`haarcascade_frontalface_default.xml`) bị **False Positive cực nặng**: Nó nhận diện một khối màu đỏ/cam hoặc góc vật thể có độ tương phản làm "khuôn mặt" và trả về bounding box.
     - Script tự động crop vùng đó ra kích thước 512x512, tạo ra một ảnh zoom cận cảnh mảng màu đỏ nhòe.
  2. **Ảo giác nhận thức (Cognitive Hallucination)**:
     - Coordinator bị ám thị bởi keyword "Yoga" và exit code 0 của tool, nên khi nhìn qua vision/ảnh chụp đã "tự tưởng tượng" ra hình ảnh người tập yoga thay vì đọc khách quan từng chi tiết pixel.
  3. **Không dùng WinRT OCR kiểm chứng màn hình đích**:
     - Bỏ qua bước kiểm tra OCR chữ trên giao diện và độ chi tiết ngũ quan thực tế của ảnh.

---

## 2. Kỷ Luật Vận Hành Bắt Buộc (Invariants)

### Rule 1: CẤM LẤY AVATAR TỪ REPRESENTATIVE_FRAMES KHI CHƯA XÁC MINH
- Tuyệt đối KHÔNG tin tưởng các file trong `.avatar_work/representative_frames/` để làm avatar.
- **Quy trình chuẩn**: Trích xuất frame TRỰC TIẾP từ các file video `.mp4` trong folder nguồn (`D:/video goc/<folder>/1.mp4`, `2.mp4`...) tại các mốc giây cố định (1.0s, 2.0s, 3.0s) bằng OpenCV/ffmpeg.
- Trước khi crop, bắt buộc xác nhận mắt người: Frame phải có người thật, độ nét cao, trang phục và tư thế phù hợp với ngách kênh.

### Rule 2: CHỐNG HAAR CASCADE FALSE POSITIVE
- Haar Cascade chỉ dùng để gợi ý bounding box, KHÔNG ĐƯỢC dùng làm căn cứ duy nhất để xác định có mặt người.
- Khi diện tích bounding box quá nhỏ so với frame, hoặc mean saturation/variance quá thấp (ảnh màu bệt, mảng màu đơn sắc), BẮT BUỘC coi là False Positive và bỏ qua.

### Rule 3: BẮT BUỘC DÙNG WINRT OCR / SOÁT MẮT THẬT TRƯỚC KHI BÁO CÁO
- Trước khi gửi bất kỳ ảnh nào (`avatar-save-surface-guard.png`, preview, crop):
  1. Chạy `ocr_tool.py` hoặc WinRT OCR để đọc text trên màn hình.
  2. Soi mắt qua vision và mô tả KHÁCH QUAN: Nếu ảnh chỉ là mảng màu, nhòe, tối, hoặc không thấy rõ ngũ quan -> BẮT BUỘC BÁO LỖI VÀ TỪ CHỐI GỬI, không được tự chém gió thành người.
