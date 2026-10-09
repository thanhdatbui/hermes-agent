# Gender / Demographic Mismatch Triage: Folder Video vs Video Gốc (2026-10-09)

## 1. Hiện tượng & Vấn đề thực tế
Operator phản ánh: *"nick này thấy video gái mà sao để ava nam v"* kèm ảnh chụp màn hình máy farm (ví dụ Máy 62 Tik 3 `@tyrusbwiqiw`, tên "Dương Chi"):
- Video trên Profile lưới hiển thị bạn nữ (đeo kính, áo thể thao đỏ).
- Tên hiển thị là con gái ("Dương Chi").
- Nhưng Avatar tròn ngoài Profile lại là thanh niên gồng cơ bắp, đeo kính râm đen.

## 2. Quy trình chẩn đoán O(1) 3 chiều
1. **Đối soát Workbook (`Tik1..8.xlsx`) dòng máy mục tiêu:**
   - Tra cứu cột `Folder Video` (folder render đăng bài) vs cột `video gốc` (nguồn media ban đầu).
   - Kiểm tra `Keyword Video` và `Video Đã Đăng`.
   - *Nguyên nhân cốt lõi:* `Folder Video` (ví dụ 491) đã được đổi sang kênh nữ sinh/gái xinh thể thao, nhưng cột `video gốc` vẫn giữ ID cũ (ví dụ 222 - kênh gym/thể thao nam).

2. **Xác minh nội dung video thực tế (Ground Truth):**
   - Trích xuất frame các video mới nhất tương ứng với số `Video Đã Đăng` (ví dụ `491/8.mp4`, `491/9.mp4`).
   - Dùng Vision API xác nhận nhân vật chính trong video đăng tải (bạn nữ áo jersey đỏ).
   - Trích xuất frame `video goc/<video_goc>/2.mp4` và xem `avatar.jpg` của video gốc để thấy sự khác biệt (nam đeo kính râm gồng bắp tay).

3. **Cơ chế bốc nhầm Avatar:**
   - Khi chạy avatar batch / watchdog, script hoặc pipeline ưu tiên đọc hoặc sinh file theo `video gốc` (222), sinh ra avatar nam và đẩy lên tài khoản.

## 3. Tạo ảnh đối chiếu 3 Panel (Composite Proof) cho Operator
Trước khi thay đổi, bắt buộc tạo composite 3 panel gửi qua `MEDIA:`:
- **Panel 1 (Trái):** `AVA HIEN TAI (video goc <ID>)` — ảnh avatar nam đang set trên tài khoản.
- **Panel 2 (Giữa):** `VIDEO TREN KENH (folder <ID>)` — frame video thực tế đang phát trên kênh (chứng minh là con gái).
- **Panel 3 (Phải):** `DE XUAT AVA MOI (chuan kenh)` — chân dung cận cảnh cắt từ video của chính `Folder Video`, chuẩn headroom 512x512.
- **Quy tắc soi mắt:** BẮT BUỘC dùng Vision API kiểm tra toàn bộ 3 panel không có viền đen, lỗi text, hoặc ảnh rỗng trước khi gắn `MEDIA:`.

## 4. Các bước Remediation dứt điểm
1. **Đồng bộ 2 đầu kho:**
   - Lưu avatar mới vào `D:\video goc\<Folder Video>\avatar.jpg`.
   - Lưu avatar mới vào `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`.
2. **Khóa nguồn trong Excel (`Tik<N>.xlsx`):**
   - Sửa cột `video gốc` trùng với `Folder Video` để runner không bao giờ bốc nhầm nguồn cũ.
3. **Reset Database Queue:**
   - `UPDATE avatar_replace_queue SET status='PENDING', last_error=NULL, updated_at=datetime('now','localtime') WHERE username='<username>';`
4. **Dispatch Runner đơn lẻ:**
   - Chạy lệnh upload avatar với cờ `-ForceAvatarMachineList "<May>"`.
