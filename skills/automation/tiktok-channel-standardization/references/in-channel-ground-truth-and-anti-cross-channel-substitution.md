# In-Channel Video Ground Truth & Anti-Cross-Channel Avatar Substitution SOP

## 1. Bối cảnh & Nguyên nhân sự cố (Incident 2026-11-01)
Khi chuẩn hóa avatar cho kênh TikTok (ví dụ: kênh `@vyvy14190` - niche Thú Cưng):
1. **Lỗi thế mạng chéo kênh (Cross-Channel Avatar Substitution):**
   - Agent gặp khó khăn khi trích xuất hoặc bị chê ảnh từ video kênh hiện tại (video dọc phòng khách, thiếu sáng).
   - Thay vì kiên trì quét sâu tìm frame đẹp trong chính video của kênh, Agent lại chạy script đi quét kho của các kênh khác (kho 385, 399, 334, 353) lấy ảnh chó Poodle, Golden, Samoyed từ các kênh khác về làm bảng lựa chọn!
   - **Hậu quả:** Vi phạm nghiêm trọng danh tính kênh. Người xem và User cần avatar đại diện cho **chính con thú cưng trong video của kênh đó**, không chấp nhận lấy ảnh con chó xa lạ ở đàn khác đắp vào.
2. **Lỗi vòng lặp gửi lại ảnh cũ (Stale / Low-effort Iteration Trap):**
   - Khi User từ chối một phương án crop ("như con cặc", "vẫn xấu"), Agent bị quán tính chạy lại logic cũ, đổi tên file hoặc gọt nhẹ rồi gửi lại chính frame đó khiến User cực kỳ ức chế vì "lặp đi lặp lại gửi ảnh cũ".
3. **Lỗi Telegram Download Timeout trên mobile:**
   - Khi mạng chập chờn hoặc Telegram desktop/mobile gửi ảnh lớn, Gateway có thể trả về `[The user attempted to send a photo but it could not be downloaded (TimeoutError)]`. Agent phải bình tĩnh nhận biết đây là sự cố download tạm thời, không được coi là User không gửi gì.

---

## 2. Invariants Bắt Buộc (Strict Invariants)

### INVARIANT 1: Ground Truth 100% Thuộc Về Video Kênh Hiện Tại
- **TUYỆT ĐỐI CẤM** lấy avatar từ thư mục video gốc/render của channel/folder khác gán sang kênh đang thi công, dù cùng chủ đề (cùng là chó, cùng là mèo, cùng là gái xinh).
- Avatar của kênh `@username` BẮT BUỘC phải trích xuất từ tập video thuộc đúng `folder_video_render` / `folder_video_goc` của chính tài khoản đó (xác định qua `lookup_channel.py`).

### INVARIANT 2: Quét Frame Dày (Dense Temporal Sampling) Trước Khi Kết Luận Video Xấu
- Không bao giờ được kết luận một video là "xấu / không dùng được" chỉ qua 1-2 frame ngẫu nhiên (ví dụ chỉ lấy ở 1s hay 2s).
- **Quy trình trích xuất chuẩn:**
  1. Dùng `cv2.VideoCapture` (bọc `safe_extract_video_frame` với timeout 10s) lấy frame mỗi 0.5s hoặc 1.0s xuyên suốt toàn bộ thời lượng video (`duration`).
  2. Đo độ sắc nét bằng Laplacian Variance:
     ```python
     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
     sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
     ```
  3. Lọc bỏ các frame bị nhòe chuyển động (motion blur, `sharpness < threshold`).
  4. Chọn ra 2-3 khoảnh khắc có biểu cảm đắt giá nhất (ví dụ: cún đang múa bụng, cún nhìn thẳng camera, cún tạo dáng tự nhiên).

### INVARIANT 3: Framing Tự Nhiên & Cấm Zoom Phóng Đại Gây Mờ Nhòe
- **Bảo toàn tỷ lệ gốc:** Khi crop chủ thể từ video 1080x1920 (dọc), lấy box kích thước tối thiểu `600x600` đến `750x750` pixel quanh trọng tâm chủ thể.
- **CẤM TUYỆT ĐỐI:** Cắt một vùng dưới `300x300` pixel rồi dùng nội suy phóng to lên 512x512 khiến ảnh bị vỡ hạt, mờ căm và mất nét.
- Downscale từ box lớn (vd: 680x680 -> 512x512 bằng `cv2.INTER_AREA`) luôn cho chất lượng ảnh sắc nét, sạch và tôn trọng độ phân giải gốc của video.

---

## 3. Checklist Thực Thi & Báo Cáo
1. [ ] Tra cứu đúng folder video gốc & render của kênh qua `lookup_channel.py`.
2. [ ] Quét frame dày (dense sampling 0.5s - 1.0s) trên video có view cao nhất hoặc video số 1 của kênh.
3. [ ] Trích xuất 2 phương án đối chiếu rõ ràng (ví dụ: Dáng đứng tự nhiên vs Khoảnh khắc hành động đắt giá).
4. [ ] Dựng preview tròn chuẩn TikTok (512x512, viền xanh lá, tỷ lệ hiển thị di động 1160x700).
5. [ ] Mở mắt soi thật 100% qua `browser_vision` xác nhận không nhòe, không vỡ hạt trước khi đăng ký receipt và gửi thẻ `MEDIA:`.
