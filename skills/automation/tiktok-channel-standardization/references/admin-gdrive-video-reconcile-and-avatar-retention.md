# Điều Tra Nguồn Video & Khắc Phục Lệch Ổ Kibe vs Admin (Google Drive Backup)

## 1. Bản Chất Phân Lập Kho Video Giữa Controller (Kibe) & Remote Farm (Admin)
- **Bẫy kết luận vội vã từ đĩa local:**
  - Máy Controller (Kibe) có thư mục `D:/TIKTOK-videonuoinick/<F_vid>` và `D:/video goc/<F_src>`, nhưng đây có thể là kho video cũ hoặc chưa đồng bộ từ máy Admin (máy >= 200).
  - Khi tra cứu kênh máy Admin (ví dụ: Máy 215, `Tik7.xlsx`), Coordinator **CẤM TUYỆT ĐỐI** chỉ đọc đĩa local Kibe rồi kết luận "kho video bị lệch nguồn".
- **Kiến trúc lưu trữ 3 tầng chuẩn của Farm:**
  1. **Tầng 1 (Local Remote Admin):** `D:\TIKTOK-videonuoinick-admin\<F_vid>` (kho render) và `D:\video goc may 2\<F_src>` (kho gốc).
  2. **Tầng 2 (Cloud Backup Google Drive trên Admin):** Mount tại `G:\My Drive\`:
     * `G:\My Drive\video_render_backup\<F_vid>`: Chứa toàn bộ các clip render tiếp theo (ví dụ: clip 21 -> 54).
     * `G:\My Drive\video_goc_backup\<F_src>`: Chứa toàn bộ clip gốc ban đầu (50-60 clip).
  3. **Tầng 3 (Dịch vụ đồng bộ nền):** Script `manage_admin_media_gdrive.py` tự động kéo media từ Drive về đĩa cứng Admin khi cạn video.

## 2. Quy Trình Kéo Video & Khôi Phục Đúng Nguồn Cho Kênh Cắn Đề Xuất
Khi một kênh đang cắn đề xuất mạnh (viral view, tương tác comment cao):
1. **Kiểm tra kho Drive:**
   - Dùng lệnh PowerShell qua `admin_ssh.py` kiểm tra xem trên Google Drive đã có sẵn video render hoặc video gốc chưa:
     ```powershell
     Test-Path 'G:\My Drive\video_render_backup\<F_vid>'
     (Get-ChildItem 'G:\My Drive\video_render_backup\<F_vid>' -Filter *.mp4).Count
     ```
2. **Kéo trực tiếp từ Google Drive vào kho Admin:**
   - Chạy Python script qua SSH để sync từ `G:\My Drive\` sang `D:\`:
     ```python
     import os, shutil
     src = 'G:/My Drive/video_render_backup/119'
     dst = 'D:/TIKTOK-videonuoinick-admin/119'
     for f in os.listdir(src):
         if f.endswith('.mp4') and not os.path.exists(os.path.join(dst, f)):
             shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
     ```
3. **Cập nhật & Khóa bảo vệ chống ghi đè:**
   - Sửa `Tik<N>.xlsx`: Cập nhật đúng `Keyword Video`, `Hashtag Pool`, và số lượng `Video Đã Đăng`.
   - Cắm marker `.manual_avatar_locked` và `.manual_hashtag_locked` vào thư mục `F_vid` và `F_src` trên cả Kibe và Admin.
   - Thêm thư mục vào `D:\Taadaa\data\manual_avatar_protected_folders.json` và `manual_hashtag_protected_folders.json`.

## 3. Tư Vấn Avatar Cho Kênh Viral Dựa Trên Tương Tác Thật
- Khi người xem trong comment có dấu hiệu nhân cách hóa chủ kênh (ví dụ: *"bả chơi bản quốc tế"*):
  - **Kỷ luật:** CẤM đổi avatar sang hình bot/game vô hồn, vì sẽ làm mất kết nối cảm xúc (Human Connection) của tệp fan đang đổ về.
  - **Hành động:** Giữ nguyên avatar Nữ Creator (PA 4), đổi tên hiển thị gần gũi (ví dụ: `Bảo Loan Gaming 🎮`), thêm Bio đúng chất thân thiện và ghim ngay video Top 1 view vào Ô 1.
