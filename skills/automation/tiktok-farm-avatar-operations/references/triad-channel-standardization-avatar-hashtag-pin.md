# Quy Trình Chuẩn Hoá Bộ Ba Kênh TikTok (Avatar + Niche/Hashtag + Pinned Posts)

## 1. Bối Cảnh & Mục Tiêu (Triad Standardization)
Khi User gửi ảnh chụp màn hình nhiều kênh TikTok (thường từ 2–5 kênh) kèm yêu cầu:
*"Chuẩn hoá ava hashtag và bài pin các kênh này cho t"*
Coordinator cần thực thi đồng bộ 3 hạng mục:
1. **Hashtag & Niche**: Đối soát thực tế lưới video trên kênh với file Excel quản lý (`Tik{1..8}.xlsx`), sửa triệt để tình trạng lệch niche và cập nhật bộ hashtag pool chuẩn.
2. **Pinned Posts (Bài ghim)**: Phân tích view trên lưới trang cá nhân, xác định đúng top 1–3 video peak view để ghim lên đầu kênh.
3. **Avatar**: Trích xuất ứng viên từ video render thực tế (`D:/TIKTOK-videonuoinick/<F>/`), crop vuông $512 \times 512$ có headroom, tạo circle preview viền xanh lá, soi mắt nghiệm thu và gửi đề xuất chuẩn xác.

---

## 2. Quy Trình 4 Bước Chuẩn O(1)

### Bước 1: Nhận Diện Tài Khoản & Định Vị Máy/Folder Trong Farm
1. **OCR nhanh ảnh chụp màn hình User gửi**:
   - Dùng WinRT OCR đọc Display Name và `@username`.
2. **Truy vấn cơ sở dữ liệu / Excel farm**:
   - Quét `taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`) và các file `Tik1.xlsx` -> `Tik8.xlsx` (sheet `TaiKhoan` và `Hashtag theo Folder`).
   - Xác định rõ bộ 4 tham số:
     * Máy (`Machine ID`) & Serial ADB.
     * Slot / Folder Video thực tế (`F_out`).
     * Folder Video nguồn (`F_src`).
     * Vị trí hàng trong workbook (`Row Index`).

### Bước 2: Đối Soát Lệch Niche & Chuẩn Hoá Hashtag Trên Excel
- **Cạm bẫy lệch Niche (Niche Drift)**:
  - Nhiều kênh trong farm ban đầu được gán Niche theo folder nguồn cũ (ví dụ: `Game`, `Ngoại ngữ`, `Câu chuyện`), nhưng trong quá trình nuôi thực tế lại đăng tải video theo niche khác (ví dụ: `Đời sống / Vlog gái xinh & mèo`, `Clip khoảnh khắc viral`, `Marketing & AI tools`).
- **Thực thi cập nhật Write-Through**:
  - Ghi đồng thời vào cả 2 sheet trong file `Tik{N}.xlsx`:
    * Sheet `TaiKhoan`: Cột `Keyword Video` (Niche mới) và Cột `Hashtag Pool`.
    * Sheet `Hashtag theo Folder`: Cột `Keyword/Niche` và Cột `Hashtag Pool`.
  - **Bắt buộc sao lưu**: Tạo backup timestamp vào `D:/Taadaa/tmp/backups/Tik{N}_<timestamp>.xlsx` trước khi lưu file mới.

### Bước 3: Trích Xuất & Soi Mắt Avatar Chuẩn Headroom
1. **Nguồn video bắt buộc**:
   - Luôn đọc từ `D:/TIKTOK-videonuoinick/<F_out>/` (chứa các video thực tế đang đăng tải), cấm lấy mù quáng từ `video goc`.
2. **Thuật toán Face Detection & Crop**:
   - Sử dụng Haar Cascade (`haarcascade_frontalface_default.xml`) với scale 1.1, `minNeighbors=6`, lọc độ sáng ROI $50 \le \text{brightness} \le 215$ và phương sai Laplacian kiểm tra độ nét.
   - Headroom geometry:
     $$y_0 = f_y - 0.35 \times f_h - \frac{\text{margin}}{k}$$
     Đảm bảo đỉnh tóc cách mép trên ~30–40px, khuôn mặt cân đối ở giữa, không lẹm cằm.
3. **Sinh cặp file cho mỗi phương án**:
   - File raw: `D:/Taadaa/tmp/avatar_<fld>_optX_512.jpg` (512x512 JPEG quality 95).
   - File preview: `D:/Taadaa/tmp/avatar_<fld>_optX_circle.jpg` (tối 65% bên ngoài hình tròn $R=256$, viền xanh lá `(0, 255, 0)` dày 2px).
4. **Soi mắt trước khi gửi (Invariant LLM Soi Mắt)**:
   - Mở ảnh qua `browser_navigate("file:///...")` và `browser_vision` (hoặc gọi Antigravity CLI: `python D:/Taadaa/tools/ag_cli.py ask --file ...`).
   - Đọc kết quả xác nhận: đúng nhân vật chủ kênh, trang phục, biểu cảm, đỉnh đầu và cằm nằm trọn trong viền tròn xanh trước khi đính kèm `MEDIA:`.

### Bước 4: Đánh Giá & Xác Định Top Bài Pin (Ghim Clip)
1. **Phân tích số lượt xem trên lưới**:
   - Parse view count từng video trên grid ($49,7\text{K} \rightarrow 49.700$, $4.042 \rightarrow 4.042$, $3.905 \rightarrow 3.905$, $1.769 \rightarrow 1.769$).
   - Chọn top 1 đến top 3 video có view cao nhất vượt trội so với mức trung bình để ghim.
2. **Kỷ luật chạy `pin_top_videos.py` trên thiết bị thật**:
   - Lệnh: `python D:/Taadaa/tools/pin_top_videos.py --machine <M> --account <username> --min-views <V>`
   - **Pitfall**: Nếu máy đang ở Launcher hoặc TikTok bị đóng, script sẽ quăng lỗi `AccountSwitcherError: PROFILE_ROOT_NOT_CONFIRMED`.
   - **Khắc phục**: Trước khi ghim bài tự động, thiết bị phải được đánh thức, mở khóa màn hình và mở TikTok chuyển về đúng Profile Root của tài khoản mục tiêu.

---

## 3. Quy Tắc Điều Phối Khi Hết Hạn Ngạch Ghi Coordinator (T1 Exhaustion)
- Khi Coordinator đã sửa 5 files hoặc > 200 dòng cộng dồn trong session, Guard sẽ chặn mọi thao tác `write_file` / `patch` trực tiếp.
- **Giải pháp chuẩn**:
  - Dispatch script con qua Worker:
    ```bash
    python D:/Taadaa/tools/haiku_worker.py --timeout 120 --file D:/Taadaa/tmp/<script>.py "<nội dung task>"
    ```
  - Hoặc dùng `ag_cli.py fix --file ...` qua Antigravity pool.
  - Sau khi script sinh xong file hoặc cập nhật Excel, Coordinator chạy lệnh Python O(1) kiểm tra kết quả `read-back` để nghiệm thu.
