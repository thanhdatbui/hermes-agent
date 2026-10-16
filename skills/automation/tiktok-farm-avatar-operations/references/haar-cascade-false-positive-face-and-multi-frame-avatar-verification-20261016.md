# Bẫy Dương Tính Giả Haar Cascade (False Positive Face) & Kỷ Luật Soi Mắt Đa Khung Hình Trích Xuất Avatar (2026-10-16)

## 1. Bối cảnh sự cố thực tế
Khi chuẩn hoá tài khoản TikTok `@inhkhoa0211` (Máy 77, Tik 6, F_out=614, F_src=477), kênh đăng tải video của một người đàn ông trung niên chia sẻ đạo lý/thói quen sống trước phông nền hoa sen, nhưng avatar cũ lại là ảnh một cô gái trẻ chụp ngoài trời.

Khi thực hiện trích xuất avatar tự động:
1. Subagent/script dùng OpenCV Haar Cascade (`haarcascade_frontalface_default.xml`) quét frame tĩnh tại giây cố định (1.mp4 @ 5s, 4.mp4 @ 6s).
2. Haar Cascade trả về `len(faces) > 0`, script tự động crop 512x512 và báo cáo hoàn tất (exit code 0).
3. Khi Coordinator mở ảnh ra soi mắt qua vision (`browser_vision` / local vision proxy) theo đúng Invariant Gate 6:
   - **Phương án 1 (1.mp4 @ 5s):** Bị mờ nhòe, hoàn toàn không có mặt người (Haar bắt nhầm vân gỗ/kệ sách nền nhà).
   - **Phương án 2 (4.mp4 @ 6s):** Chỉ phóng to vào vành tai và thái dương do nhân vật quay nghiêng, mất hoàn toàn ngũ quan (mắt, mũi, miệng, cằm).

## 2. Bản chất kỹ thuật & Căn nguyên gốc rễ (Root Cause)
1. **Độ nhạy & False Positive của Haar Cascade trên Video Farm:**
   - Bộ phân loại Haar Cascade mặc định rất dễ kích hoạt sai (false positive) trước các họa tiết có độ tương phản cao: cánh hoa sen, vân gỗ nội thất, nếp gấp áo quần, hoặc góc chụp nghiêng chỉ thấy vành tai/tóc.
   - Nếu chỉ kiểm tra `if len(faces) > 0:` mà không kiểm tra tỷ lệ khuôn mặt, vị trí trong khung hình và độ tương phản ngũ quan, script sẽ cắt trúng rác hoặc góc tai.
2. **Ảo giác hoàn thành của Worker (Trust Artifacts, Not Summaries):**
   - Subagent thấy script chạy không văng lỗi, file `inhkhoa_opt1_512.jpg` sinh ra đủ dung lượng thì lập tức kết luận "đã tạo ảnh chuẩn xác".
   - Nếu không có bước Coordinator mở ảnh ra soi mắt (Gate 6), hệ thống sẽ nạp một ảnh nhòe đồ vật hoặc một cái tai người lên avatar TikTok của tài khoản live.
3. **Bẫy gõ phím Telex trong lệnh người dùng:**
   - Lệnh *"Chuẩn hoá acc nacy"* thực chất là gõ nhầm Telex của từ *"acc này"* (`n-a-c-y` hoặc `n-a-y-s`), không phải tên tài khoản hay username `nacy` hay `nancy`. Cần bám sát ảnh đính kèm của người dùng thay vì đi tìm kiếm chuỗi text rác trong cơ sở dữ liệu.

## 3. Quy chuẩn trích xuất khuôn mặt đa khung hình (Multi-Timestamp Multi-Video Probing)
Để tránh hoàn toàn false positive và bắt đúng khuôn mặt chính diện:
1. **Quét đa video và đa mốc thời gian:**
   - Quét tối thiểu 3–5 video khác nhau trong folder (ví dụ `1.mp4`, `2.mp4`, `3.mp4`, `5.mp4`).
   - Quét tại các mốc thời gian an toàn của video TikTok (ví dụ: `2s`, `3s`, `5s`, `8s`), né giây đầu tiên (dễ dính bìa intro/title banner) và các giây cuối (outro/kêu gọi follow).
2. **Bộ lọc tham số hình học khuôn mặt nghiêm ngặt:**
   - Kích thước khuôn mặt tối thiểu: `fw >= 150` và `fh >= 150` (trên khung hình dọc 1080x1920).
   - Tọa độ tâm mặt: $Y$ phải nằm ở nửa trên của video ($Y_{center} \in [0.15 \times H, 0.55 \times H]$), loại bỏ ngay các phát hiện giả ở vùng đáy (vùng phụ đề/caption) hoặc góc dưới.
   - Tỷ lệ khung mặt vuông vức: $0.8 \le \frac{fw}{fh} \le 1.25$.
3. **Kỷ luật Crop Center-Based & Headroom/Chin Clearance:**
   - Căn tâm: $C_x = f_x + \frac{f_w}{2}$, $C_y = f_y + 0.55 \times f_h$.
   - Kích thước khung cắt vuông: $\text{side} = \min(f_w \times 1.5, W, H)$.
   - Headroom (đỉnh đầu tới viền tròn): $30\text{px} \le \text{headroom} \le 60\text{px}$.
   - Chin clearance: Cằm phải cách đáy viền tròn $\ge 25\text{px}$, không được để cằm chạm hoặc lẹm ra ngoài viền tròn xanh.
4. **Bắt buộc kiểm tra 2 lớp bằng chứng trước khi xuất:**
   - Lớp 1: OCR check trên ảnh crop (`ocr_coords.py`) để xác nhận không có text/phụ đề che mặt (OCR text count == 0 hoặc không có cụm chữ đè lên mặt).
   - Lớp 2: Soi mắt bằng vision (`browser_vision` / local proxy) xác nhận rõ nét mặt chính diện, đủ ngũ quan và đúng nhân vật của kênh.
