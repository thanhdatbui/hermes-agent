# Quy Trình Chuẩn Hoá 3 Món (Pin Top - Niche/Hashtag - Avatar) & Bẫy Báo Ảo Haar Cascade (2026-10-17)

## 1. Bản Chất Tác Vụ: "Chuẩn Hoá Acc Này" (Chuẩn Hoá 3 Món)
Khi User gửi ảnh chụp màn hình trang cá nhân TikTok và phát lệnh *"Chuẩn hoá acc này"* hoặc *"Chuẩn hoá kênh này"*, Coordinator cần thực hiện quy trình chuẩn hoá 3 món:
1. **Ghim Video (Pin Top)**: Video đạt $\ge 1.000$ views bắt buộc ghim lên đầu profile (tối đa 3 video).
2. **Niche & Hashtags**: Đối soát nội dung video thực tế với dữ liệu Excel, khắc phục Niche Drift và khóa marker `.manual_hashtag_locked`.
3. **Avatar Mới**: Trích xuất nhân vật/creator đúng chủ đề từ kho video, crop $512 \times 512$, tạo 2 phương án có viền tròn xanh preview, soi mắt qua `browser_vision`, trình User duyệt và nạp ngay lập tức.

---

## 2. Quy Trình Đối Soát Tọa Độ Phone Farm $O(1)$
1. **Nhận diện từ ảnh chụp màn hình (What I See)**:
   - Handle / Username (`@username`), Display Name (`Hoàng Phước Nghĩa`).
   - Chỉ số kênh: Đã follow, Follower, Tổng lượt thích.
   - Nhận diện avatar cũ (thường là avatar rác, đĩa ăn, rêu đá, cây cỏ hoặc sai giới tính/ngách).
   - Đọc nội dung và lượt xem của $\ge 6$ video hiển thị trên lưới profile.
2. **Truy vấn tọa độ Farm trong `tiktok_tracker.db`**:
   ```python
   # Truy vấn account_mapping hoặc avatar_replace_queue
   cur.execute("SELECT may, tik FROM account_mapping WHERE username = ?", (username,))
   may, slot = cur.fetchone()
   ```
3. **Xác định đường dẫn dữ liệu**:
   - Workbook: `D:/OneDrive/TaadaaData/kibe/Tik<slot>.xlsx` (hoặc `admin` nếu $M \ge 201$).
   - Dòng dữ liệu: Row $M + 1$ (Sheet `TaiKhoan`).
   - Kho gốc $F_{src} = (\text{Slot} - 1) \times 80 + \text{Máy}$.
   - Kho render $F_{out}$: Đọc từ cột `Folder Video (Render Dich)` trong Excel.

---

## 3. Cạm Bẫy Báo Ảo Của Haar Cascade & Bộ Lọc Vision Bắt Buộc
- **Hiện tượng**: `haarcascade_frontalface_default.xml` và `haarcascade_eye.xml` liên tục bắt nhầm các cấu trúc ngẫu nhiên trong video thành khuôn mặt:
  * Tán lá cây ở mép trên video (`y < 50`).
  * Mặt đường bê tông, vệt nước, vết nứt đá.
  * Đĩa thức ăn, bàn ăn, dao nĩa.
  * Bàn tay, cổ chân, giày dép.
- **Quy tắc an toàn**:
  * **CẤM TUYỆT ĐỐI** tự động lấy frame trúng Haar Cascade làm avatar mà không soi mắt.
  * **BẮT BUỘC** gọi `browser_vision` (hoặc OCR) mở từng ảnh ứng viên ra xem trước khi crop và trước khi tạo ảnh preview.
  * **Ưu tiên nhân vật trên lưới profile**: Nếu trong $\ge 6$ video đã đăng có video cận cảnh creator/nhân vật (ví dụ: Video 5 là chàng trai chơi đàn), hãy ưu tiên trích xuất avatar từ chính video đó để tạo độ đồng nhất tuyệt đối giữa Avatar và Lưới video của kênh.

---

## 4. Kỹ Thuật Tạo Ảnh Preview Viền Tròn Xanh Lá ($512 \times 512$)
TikTok cắt avatar thành hình tròn, do đó các avatar vuông thông thường rất dễ bị cắt lẹm đỉnh nón, cằm hoặc phụ đề.
- **Công thức crop an toàn**:
  * Khung vuông $512 \times 512$.
  * Headroom: Đỉnh đầu/nón cách mép trên 20–30px.
  * Căn tâm ngũ quan ở chính giữa khung hình $(cx \approx 256, cy \approx 256)$.
  * Vẽ viền tròn xanh lá mô phỏng khung cắt tròn của TikTok:
    ```python
    preview = crop_512.copy()
    cv2.circle(preview, (256, 256), 250, (0, 255, 0), 3)
    cv2.imwrite("D:/Taadaa/reports/avatar_<username>_opt1_preview.jpg", preview)
    cv2.imwrite("D:/Taadaa/reports/avatar_<username>_opt1_clean.jpg", crop_512)
    ```
- Lưu cả bản `preview` (để gửi User duyệt) và bản `clean` (để nạp lên app khi User chốt).

---

## 5. Pitfall Kỹ Thuật Terminal Trên Windows MSYS Bash
- Khi gọi `python -c "..."` qua `terminal` trên Windows MSYS bash: nếu command chứa chuỗi nhiều dòng (`\n`), hook/lifecycle guard của hệ thống có thể báo lỗi:
  `ValueError: open: embedded null character in path`
- **Khắc phục**: Luôn viết code inline trên 1 dòng đơn (dùng dấu chấm phẩy `;` hoặc list comprehension), hoặc ghi ra file `.py` tạm thời trong `D:/Taadaa/tmp/` rồi chạy.
