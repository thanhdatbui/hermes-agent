# Strict 3-Way Parallel Execution & Dual-Vault Media Isolation on Admin-PC

## 1. Kiến Trúc 3 Luồng Song Song Độc Lập (Decoupled Pipelines)
Hệ thống Admin-PC (192.168.110.119) vận hành đồng thời 3 chu trình ngầm:
1. **Downloader (Scraper):** 40 luồng tải video gốc từ niche pool vào `D:\video goc may 2\{f_src}`. Tự động kiểm tra cờ `downloader_pause.flag` để unpause/pause an toàn.
2. **Renderer (ffmpeg):** 2 luồng render song song chuyển đổi video thô thành clip thành phẩm nuôi nick tại `D:\TIKTOK-videonuoinick-admin\{f_vid}`. Tích hợp Game Guard tự động kill ffmpeg khi phát hiện `War3.exe`, `w3l.exe`, `TFTClient.exe` và tự động resume ngay sau khi thoát game.
3. **Cloud Synchronizer & Tiering (Google Drive 5TB):** Giải phóng đĩa tự động theo 2 kho lưu trữ riêng biệt để giữ mức trống của ổ D: luôn `> 200 GB`.

---

## 2. Kỷ Luật Phân Tách Kho Lưu Trữ Google Drive (Dual-Vault Media Isolation)
TUYỆT ĐỐI KHÔNG trộn lẫn video gốc và video render thành phẩm trong cùng một cây thư mục Google Drive:
- **Kho Video Gốc:** `G:\My Drive\video_goc_backup\{f_src}\`
  - Chỉ copy video thô tải về lên đây.
  - File trên local `D:\video goc may 2\{f_src}` chỉ được phép xóa khi và chỉ khi folder render tương ứng đã đạt `>= 45` clip thành phẩm.
- **Kho Video Render Thành Phẩm:** `G:\My Drive\video_render_backup\{f_vid}\`
  - Chỉ copy các clip render số lớn từ `21.mp4` trở lên lên đây.
  - Local `D:\TIKTOK-videonuoinick-admin\{f_vid}` bắt buộc giữ lại trọn vẹn từ `1.mp4` đến `20.mp4` (đủ gối đầu cho farm đăng bài thoải mái trong 3 tuần mà không cần truy cập mạng).
  - Đối soát byte-for-byte chuẩn 100% trước khi xóa file local.

---

## 3. Công Thức Ánh Xạ Slot và Khôi Phục Nguồn (Restore Mapping)
- **Từ `f_src` sang `f_vid`:**
  ```python
  slot = (f_src - 1) // 80 + 1
  m_idx = (f_src - 1) % 80 + 1
  f_vid = (m_idx - 1) * 8 + slot
  ```
- **Từ `f_vid` sang `f_src`:**
  ```python
  slot = (f_vid - 1) % 8 + 1
  m_idx = (f_vid - 1) // 8 + 1
  f_src = (slot - 1) * 80 + m_idx
  ```
- **Điều kiện tải bù nguồn (Dual-layer Deficit Check):**
  Khi kiểm tra folder có thiếu video render không, BẮT BUỘC tính:
  `total_rendered = local_rendered_count + gdrive_rendered_count`
  Chỉ tải bù video gốc từ `video_goc_backup\{f_src}` về `D:\video goc may 2\{f_src}` khi `total_rendered < 45`.

---

## 4. Tự Động Hóa Qua Windows Task Scheduler
- Task: `Taadaa_Sync_GDrive_Backup` (chu kỳ 2 tiếng/lần).
- Launcher: `D:\Taadaa\tools\start_sync_gdrive_hidden.vbs` chạy ngầm tuần tự:
  1. `sync_and_clean_gdrive.py 640`: Dọn video gốc đã render đủ `>= 45` clip lên `video_goc_backup`.
  2. `manage_admin_media_gdrive.py offload 640`: Đẩy clip render `>= 21` lên `video_render_backup`.
