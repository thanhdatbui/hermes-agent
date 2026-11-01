# Bẫy Đối Soát Lệch Kho Nhầm Giữa Controller vs Admin & Kiến Trúc Google Drive Farm

## 1. Bản Chất Bẫy Lệch Kho Nhầm (False-Positive Desync Trap)
- **Thực trạng xảy ra:**
  - Máy Admin (Machine >= 200, ví dụ Máy 215) đang chạy mượt mà, video đăng lên cắn đề xuất rất tốt (Roblox Gaming).
  - Khi tra cứu toạ độ kênh qua `lookup_channel.py`, kết quả trả về `folder_video_render: 119` và `folder_video_goc: 495`.
  - Coordinator kiểm tra nhanh trên đĩa cục bộ của Controller (Máy Kibe):
    * `D:/TIKTOK-videonuoinick/119`: Chứa video cũ từ đầu tháng 10 (ví dụ Thời trang Loewe).
    * `D:/video goc/495`: Chứa video phỏng vấn / podcast hoàn toàn khác ngách.
    * `Tik7.xlsx`: Cột Keyword bị script batch ghi đè nhầm thành `Anime`.
  - **Sai lầm nghiêm trọng:** Vội vã kết luận *"Kho render bị lệch hoàn toàn, kho gốc bị lệch hoàn toàn, nguy cơ đăng đè video hỏng kênh!"*.
  - **Sự thật thực tế trên Farm:**
    * Máy Admin có ổ cứng riêng: `D:\TIKTOK-videonuoinick-admin\119` chứa đúng 20 video Roblox đang render sẵn.
    * Hệ thống backup Google Drive tại Admin:
      + `G:\My Drive\video_goc_backup\495`: Lưu trữ đầy đủ 57 video gốc Roblox chuẩn.
      + `G:\My Drive\video_render_backup\119`: Lưu trữ 34 video render tiếp theo (từ clip 21.mp4 đến 54.mp4).
    * Dịch vụ `manage_admin_media_gdrive.py` tự động kéo media từ Google Drive xuống đĩa Admin khi farm tiêu thụ video.

## 2. Kỷ Luật Đối Soát 3 Tầng Cho Máy Admin (Machine >= 200)
Trước khi kết luận bất kỳ điều gì về "lệch kho" hay "hết video" đối với máy Admin, Coordinator **BẮT BUỘC** phải kiểm tra đủ 3 tầng:

1. **Tầng 1 (Đĩa cục bộ Admin qua `admin_ssh`):**
   * Kiểm tra trực tiếp thư mục `D:\TIKTOK-videonuoinick-admin\<F_vid>` trên host Admin (không phải `D:/TIKTOK-videonuoinick/` trên Controller).
   * Lấy số lượng file, ngày tạo và sampling frame thực tế trên Admin.

2. **Tầng 2 (Google Drive Mount `G:\My Drive\` trên Admin):**
   * Kiểm tra kho gốc backup: `G:\My Drive\video_goc_backup\<F_src>` (đếm số file `.mp4`).
   * Kiểm tra kho render backup: `G:\My Drive\video_render_backup\<F_vid>` (đếm số file `.mp4`).
   * Nếu trên đĩa Admin còn ít video nhưng Google Drive còn dồi dào, kho KHÔNG HỀ THIẾU hay LỆCH.

3. **Tầng 3 (Dịch vụ đồng bộ Drive `manage_admin_media_gdrive.py`):**
   * Xác nhận tiến trình đồng bộ hoặc kích hoạt kéo batch mới nếu máy Admin sắp cạn video đĩa cứng.

## 3. Tâm Lý Học Người Xem & Kỷ Luật Chọn Avatar Khi Video Cắn Đề Xuất
- Khi video cắn đề xuất (viral hit) và phần bình luận xuất hiện các câu hỏi như *"bản này bản nào"*, kèm câu trả lời của khán giả khác như *"bả chơi bản quốc tế"*:
  * Đại từ nhân xưng *"bả"* là bằng chứng thép cho thấy người xem **đang mặc định chủ kênh là một Nữ Gamer / Nữ Creator thật**.
  * **Cấm kỵ:** Không vội vàng thay Avatar sang icon game / linh vật vô danh vì sẽ làm biến chất kênh thành "kênh bot reup", triệt tiêu sự gắn kết con người (Human Connection) và giảm tỷ lệ follow.
  * **Quy chuẩn:** Ưu tiên giữ nguyên Avatar Nữ đời thường (PA 4) hoặc tinh chỉnh Avatar Nữ xinh xắn, gắn Bio mang sắc thái cá nhân gần gũi đúng với tệp người xem đang tương tác.
