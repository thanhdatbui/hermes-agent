# Chuẩn Hoá Kênh Admin Remote (M >= 200) & Khắc Phục Lệch Video Gốc / Niche (17/10/2026)

## 1. Cấu Trúc File & Workbook Của Cụm Admin Farm (M >= 200)
- **Vị trí Workbook SSOT**:
  - Không nằm rải rác ở thư mục gốc mà nằm tại `D:/OneDrive/TaadaaData/admin/Tik<Slot>.xlsx` (ví dụ Slot 5 -> `Tik5.xlsx`).
  - Đường dẫn cấu hình host: `D:/Taadaa/machine-config/admin.yaml` (`workbook_root: D:/OneDrive/TaadaaData/admin`).
- **Công thức ánh xạ Machine/Slot ↔ Folder**:
  - Kibe (1 - 80) & Admin (201 - 280):
    - $F_{src} = (\text{Slot} - 1) \times 80 + (M - 200)$
    - $F_{vid} = ((M - 200) - 1) \times 8 + \text{Slot}$
  - Ví dụ: Máy 243, Slot 5 -> $F_{vid} = (43 - 1) \times 8 + 5 = 341$.

---

## 2. Cạm Bẫy Niche Drift & Lệch Video Gốc (Kho Render vs Kho Gốc)
- **Hiện tượng**:
  - Kênh đang nuôi video về bản tin truyền hình / phóng sự thời sự (folder render `341`), nhưng trong `Tik5.xlsx` cột `Video Goc` lại bị trôi sang `363` (Gym), và avatar cũ của folder 341 lại là ảnh chữ `"CHÓ"` + xe máy đi đường (lệch hoàn toàn).
- **Quy trình chuẩn hóa 3 món bắt buộc**:
  1. **Khám nghiệm lưới video thật (Grid Audit)**: Đọc video trên profile và trích xuất frame từ video đầu tiên trong kho render (`D:/TIKTOK-videonuoinick-admin/341/` hoặc `D:/video goc may 2/341/`).
  2. **Trích xuất 2 phương án Avatar (Option 1 & 2)**:
     - Tạo ảnh vuông $512 \times 512$, headroom ~12-15%, mắt ~38% chiều cao, ngũ quan rõ nét nhìn thẳng.
     - Dựng ảnh so sánh $1024 \times 512$ có viền tròn màu xanh lá (`comparison_preview.jpg`), soi mắt qua `browser_vision` trước khi gửi user.
  3. **Khóa 3 đầu kho & đồng bộ Workbook**:
     - Đồng bộ avatar mới vào cả `TIKTOK-videonuoinick-admin/341/avatar.jpg`, `video goc may 2/341/avatar.jpg` và `video goc may 2/363/avatar.jpg` (nếu có liên đới).
     - Cắm marker `.manual_avatar_locked` và `.manual_hashtag_locked`.
     - Cập nhật đúng dòng của máy trong `D:/OneDrive/TaadaaData/admin/Tik<Slot>.xlsx` (lưu ý tìm đúng dòng theo `Máy == <M>`, tránh nhầm index 0-based vs 1-based header):
       * `Video Goc`: 341
       * `Keyword Video`: Thời sự pháp luật
       * `Hashtag Pool`: `#thoisu #tintuc #phapluat #tintuc24h #anninhtrattu #xuhuong #fyp #videohay`
       * `Avatar`: `PENDING`
     - Cập nhật SQLite `D:/Taadaa/data/tiktok_tracker.db` bảng `avatar_replace_queue`: `status = 'PENDING'`.

---

## 3. Khởi Chạy Runner Avatar Trên Admin Remote Bằng Launcher Phù Hợp
- **Vấn đề**: Runner `run_avatar_batch_3accs.py` cần có trên Admin-PC tại `D:/Taadaa/tools/run_avatar_batch_3accs.py`.
- **Cách dispatch an toàn**:
  1. Đồng bộ runner sang Admin-PC qua `sync_to_admin.py`.
  2. Kích hoạt runner background với timeout đủ lớn ($\ge 360$s):
     ```bash
     python D:/Taadaa/tools/admin_ssh.py --timeout 360 "python -u D:\Taadaa\tools\run_avatar_batch_3accs.py --tik 5 --machine 243"
     ```
  3. Không block session chờ đợi mà dùng `background=True, notify_on_complete=True`.
