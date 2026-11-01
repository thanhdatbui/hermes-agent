# Resolution Floor Invariant & Anti-Stale-Iteration Trap SOP

## 1. Bản chất vấn đề
Trong quá trình vận hành Gate 6 Visual Verification:
1. **Lỗi lặp lại ảnh cũ (Stale Repetition):**
   - Khi User phàn nàn ảnh xấu, Agent bối rối không biết làm gì tiếp theo, sinh ra phản xạ tiêu cực là lấy lại chính ảnh/frame cũ hoặc gửi lại bảng cũ với tên gọi khác.
   - Hành vi này gây bức xúc cao độ vì User cảm giác Agent "lì lợm, đùa cợt và không nghe chỉ đạo".
2. **Kẽ hở Resolution Floor của Gate 6:**
   - Gate 6 (`guard_media_vision_gate.py`) kiểm tra tính nhất quán ngữ nghĩa (chống nói dối) và các nhãn vi phạm (chống mặt người, watermark).
   - Tuy nhiên, Gate không có bộ lọc kỹ thuật đánh giá **chất lượng độ phân giải thực tế (Visual Quality Floor)**:
     - Cắt vùng < 250px rồi phóng to lên 512px -> Ảnh vỡ nát, mờ căm nhưng Gate vẫn cho pass vì "vẫn là con chó".
3. **Hiện tượng Telegram Download Timeout trên mobile:**
   - Khi mạng lag hoặc app Telegram mobile đẩy file lớn, gateway có thể gặp timeout download: `[The user attempted to send a photo but it could not be downloaded (TimeoutError)]`.
   - Agent phải nhận biết tin nhắn này có nghĩa là User đang phản hồi một bức ảnh thực tế vừa chụp màn hình, tuyệt đối không được coi là User không gửi gì rồi phán bừa.

---

## 2. Invariants Kỹ Thuật

### INVARIANT 1: Resolution Floor >= 500px & Cấm Phóng Đại Kỹ Thuật Số (Upscaling Trap)
- Vùng crop gốc từ video/ảnh bắt buộc phải có kích thước tối thiểu **$500 \times 500$ pixel**.
- CẤM TUYỆT ĐỐI crop một vùng nhỏ ($< 350\text{px}$) rồi dùng `cv2.resize` hay PIL phóng to lên $512\text{px}$. Hành vi phóng to này làm mất toàn bộ chi tiết, sinh hạt mờ nhòe bầy hầy.
- Chỉ chấp nhận **Downscaling an toàn** từ frame độ phân giải cao ($1080 \times 1920$) thu nhỏ về $512 \times 512$ bằng thuật toán lấy mẫu vùng `cv2.INTER_AREA` hoặc `LANCZOS`.

### INVARIANT 2: Chống Vòng Lặp Gửi Lại Ảnh Cũ (Anti-Stale Iteration)
- Khi User từ chối một ảnh/crop vừa gửi:
  - BẮT BUỘC đổi hoàn toàn sang **timestamp/khoảnh khắc khác** trong video hoặc đổi hẳn sang góc quay khác.
  - CẤM TUYỆT ĐỐI gửi lại cùng một frame gốc với cách gọt nhẹ viền hay chỉnh màu nhẹ.

### INVARIANT 3: Tôn Trọng Video Chính Chủ Kênh (In-Channel Ground Truth)
- Avatar của kênh phải trích từ video của chính kênh đó (video có view cao nhất hoặc video #1).
- CẤM lấy ảnh thú cưng, người mẫu hay sản phẩm từ kho của kênh khác đắp sang làm avatar thay thế.
