# Bẫy Cắt Cụt Cằm Video Dọc & Kỷ Luật Kích Hoạt Watchdog Đổi Avatar (Cập nhật 2026-10-15)

## 1. Bẫy Cắt Cụt Cằm & Thấy Mỗi Tóc Khi Crop Avatar Từ Video Dọc 1080x1920 (Vertical Video Haircut & Text-Anchor Trap)

### Bối cảnh sự cố (15/10/2026 — @nhathasz4vw Folder 396)
- Coordinator gửi ảnh preview viền tròn xanh cho User.
- User phản hồi gay gắt: *"Ava loz gì k thấy ng hoặc thấy mỗi cái tóc v"* kèm ảnh chụp bằng chứng.
- Thực tế ảnh gửi đi: Vòng tròn chỉ thấy đỉnh trán, tóc mái và dòng chữ slogan subtitle trên cao (*"...xua đuổi mấy tên dê trong 1 nốt nhạc"*), toàn bộ mắt, mũi, miệng và cằm bị cắt cụt ra ngoài mép dưới.

### Nguyên nhân cốt lõi
1. **Bẫy text/sticker vùng trên**: Video dọc 1080×1920 trên TikTok hầu hết có caption, tiêu đề hoặc sticker ở 10%–25% phía trên (`fy < 0.25 * h`). Bộ nhận diện Haar Cascade thường bắt nhầm các chi tiết đồ họa này làm khuôn mặt, hoặc box bị neo quá cao.
2. **Lệch tâm crop vuông**: Khi tính `y0 = head_center_y - side / 2`, nếu `head_center_y` bị neo ở trán hoặc dòng chữ, cửa sổ crop 512×512 bị trôi lên trần video. Ngũ quan thật của nhân vật bị đẩy tụt xuống đáy hoặc rơi ra ngoài vòng tròn viền xanh.
3. **Bẫy góc cúi / đội mũ ngược (Folder 325 - Chi Dâu)**: Khi nhân vật cúi đầu hoặc đội mũ ngược, nếu lấy `y_center = 420` (vùng trần) thì vòng tròn chỉ chụp được đỉnh mũ và sau gáy; tâm mặt thực tế nằm ở `y_center ≈ 800 - 850`.

### Quy chuẩn trích xuất & lọc tọa độ video dọc bắt buộc
1. **Lọc vùng hợp lệ**:
   - Loại bỏ mọi box có `fy < 0.20 * h` (vùng chữ / sticker / trần video).
   - Khuôn mặt người thật trong video dọc chuẩn TikTok luôn nằm trong dải: `0.25 * h <= fy <= 0.65 * h`.
2. **Căn tâm sống mũi chuẩn**:
   ```python
   fx, fy, fw, fh = box
   head_center_x = fx + fw * 0.5
   # Tâm khuôn mặt thực tế nằm ở sống mũi (khoảng 55-60% chiều cao box)
   head_center_y = fy + fh * 0.60
   # Side không vượt quá 90% chiều rộng video dọc (1080px)
   side = int(min(fw * 2.6, w * 0.9, h * 0.55))
   x0 = int(head_center_x - side / 2)
   y0 = int(head_center_y - side * 0.50)
   # Bắt buộc clamp an toàn trong khung hình
   x0 = max(0, min(x0, w - side))
   y0 = max(0, min(y0, h - side))
   ```
3. **Kiểm chứng thị giác độc lập bắt buộc (Semantic Vision Grounding)**:
   Trước khi gửi bất kỳ ảnh nào cho User, BẮT BUỘC chạy `ag_cli.py ask` hoặc `browser_vision` với câu hỏi cụ thể:
   - *"Có thấy rõ đầy đủ cả mắt, mũi, miệng, cằm, trán không? Mặt có nằm ở trung tâm vòng tròn không?"*
   - Nếu kết quả trả về: "chỉ thấy trán", "thấy mỗi tóc", "mặt bị cắt mép", "không thấy cằm" $\rightarrow$ **CẤM GỬI CHO USER**, bắt buộc điều chỉnh lại tọa độ crop ngay lập tức.

---

## 2. Kỷ Luật Chống Hứa Suông Về Watchdog (Anti-"Nói Mõm" Watchdog Queue Discipline)

### Bối cảnh sự cố (15/10/2026)
- Coordinator thông báo với User: *"Ngay khi ca nuôi 12h nhả lock, hệ thống sẽ tự động kích hoạt ghim 3 bài pin và nạp avatar mới lên tài khoản"*.
- User chất vấn: *"Có watchdog canh k hay nói mõm cho vui?"*.
- Kiểm tra thực tế: Trên hệ thống cron ĐÃ CÓ watchdog `post-evening-avatar-watchdog` (Job ID: `25d6f8ab0264`, chạy `*/5 * * * *`), NHƯNG trong workbook `Tik<N>.xlsx`, cột `Avatar` của các kênh vẫn đang ghi `OK`. Do đó, script `resolve_avatar_pending_machines.py` bỏ qua các máy này, dẫn tới hoàn toàn KHÔNG CÓ tiến trình nào tự động bốc máy để chạy. Lời hứa của Coordinator bị coi là hứa suông ("nói mõm").

### Nguyên tắc vận hành chống hứa suông
1. **CẤM TUYỆT ĐỐI hứa "hệ thống sẽ tự động làm" khi chưa ghi nhận vào trigger state.**
2. **Quy trình nạp hàng đợi Watchdog chuẩn hóa cho Avatar**:
   - Khi cần đổi avatar cho một tài khoản đã từng có avatar (`Avatar = OK` trong Excel):
     1. Mở file `Tik<N>.xlsx` tương ứng.
     2. Cập nhật ô `Avatar` của tài khoản mục tiêu từ `OK` sang **`FORCE_UPLOAD`** (hoặc `PENDING`).
     3. Lưu workbook an toàn.
   - **Lệnh verify bắt buộc trước khi báo cáo**:
     ```bash
     python D:/Taadaa/Tiktok-video/scripts/resolve_avatar_pending_machines.py <Tik>
     ```
     Chỉ khi stdout in ra danh sách chứa đúng ID máy mục tiêu (ví dụ: máy 50, máy 41), Coordinator mới được phép báo cáo với User là máy đã nằm trong hàng đợi tự động.
3. **Minh bạch thông tin Watchdog trong báo cáo**:
   Khi thông báo máy đang chờ chạy tự động, BẮT BUỘC nêu rõ 4 yếu tố:
   - **Tên Job Watchdog:** `post-evening-avatar-watchdog`
   - **Lịch chạy cron:** `*/5 * * * *` (mỗi 5 phút)
   - **Điều kiện kích hoạt:** Máy rảnh (nhả `Device Lock` sau ca nuôi, không xung đột với `run_tiktok.py`)
   - **Bằng chứng hàng đợi:** Kết quả lệnh `resolve_avatar_pending_machines.py` hiển thị ID máy.
