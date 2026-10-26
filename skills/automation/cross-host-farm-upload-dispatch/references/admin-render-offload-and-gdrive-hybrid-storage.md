# Admin Farm Render Offload & Google Drive Hybrid Storage Architecture

## 1. Bối cảnh & Điểm Nghẽn Dung Lượng (Storage Bottleneck)
- **Cấu hình Farm Admin (`192.168.110.119`):** Ổ `D:` có dung lượng 931 GB.
  - Video gốc (`D:\video goc may 2`): 640 folders (~160–200 GB).
  - Video render thành phẩm (`D:\TIKTOK-videonuoinick-admin`): 640 folders (>625 GB).
  - Khi render đến Tik6/Tik7, ổ `D:` chạm ngưỡng `0 Byte free`, ffmpeg crash `[Errno 28] No space left on device`.
- **Lệch pha tiêu thụ:** Điện thoại farm chỉ đăng 1 clip/ngày (hiện tại các nick mới chỉ ở clip 1 đến 6). Lưu trữ toàn bộ 45 clip render trên ổ SSD là lãng phí tài nguyên cục bộ.

## 2. Cạm Bẫy Google Drive Virtual Cache Deadlock
- Google Drive Desktop (`G:`) đặt cache tại `D:\GoogleDriveCache`.
- Khi `FreeSpace(D:) == 0 Byte`, driver của Google Drive báo `FreeSpace(G:) == 0 Byte`.
- Mọi lệnh copy sang `G:` bị crash `Errno 28`, khiến các cron dọn dẹp định kỳ không thể sao lưu và không thể xóa file local (vòng lặp bế tắc).
- **Cách phá deadlock:** Mồi dung lượng khẩn cấp (xóa các file video gốc đã chắc chắn có sẵn 100% trên `G:\My Drive\video_goc_backup`), ngay khi `D:` có >20 GB trống, `G:` sẽ mở lại dung lượng ghi.

## 3. Kiến Trúc Lưu Trữ Phân Tầng (Hybrid Storage Contract)
- **Local Cache (`D:\TIKTOK-videonuoinick-admin\{f_vid}`):**
  - Giữ lại các clip từ `1.mp4` đến `20.mp4` (đủ gối đầu cho farm đăng bài 2–3 tuần độc lập, không phụ thuộc mạng).
- **Cloud Archive (`G:\My Drive\video_render_backup\{f_vid}`):**
  - Đẩy toàn bộ clip số lớn $\ge 21$ (`21.mp4` đến `45.mp4`) lên Google Drive.
  - **Kỷ luật xác thực byte-for-byte:** Chỉ xóa file local sau khi:
    ```python
    if g_dst.is_file() and g_dst.stat().st_size == sz:
        p.unlink()
    ```
  - **Hiệu quả:** Giải phóng tức thì ~350 GB đến 400 GB trên ổ `D:`, duy trì mức trống an toàn >200 GB.

## 4. Cơ Chế Phục Hồi Video Gốc Thiếu Nguồn (Selective Source Restore)
Khi video gốc bị xóa nhầm trước khi render đủ 45 clip:
- **Điều kiện lọc kép bắt buộc:**
  ```python
  total_rendered = len(local_rendered) + len(gdrive_rendered)
  if total_rendered < 45:
      # Cần kéo video gốc từ GDrive về render tiếp
  ```
  Tuyệt đối không chỉ đếm file local, tránh kéo thừa video gốc cho các folder đã offload lên Cloud.
- **Công thức ánh xạ Slot Farm Admin:**
  - Từ `f_vid` (Folder Render 1..640) sang `f_src` (Folder Gốc 1..640):
    ```python
    slot = (f_vid - 1) % 8 + 1
    m_idx = (f_vid - 1) // 8 + 1
    f_src = (slot - 1) * 80 + m_idx
    ```
  - Từ `f_src` sang `f_vid`:
    ```python
    slot = (f_src - 1) // 80 + 1
    m_idx = (f_src - 1) % 80 + 1
    f_vid = (m_idx - 1) * 8 + slot
    ```

## 5. Kỷ Luật Vận Hành & Khởi Chạy Nền Từ Xa
- **Chống bị ngắt bởi OpenSSH Job Object:** Khi kích hoạt script bảo trì dài hạn (Offload/Restore) qua `admin_ssh.py`, bắt buộc dùng cờ `0x01000008` (`CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS`).
- **Phòng thủ môi trường Python:** Tránh phụ thuộc vào thư viện bên ngoài như `psutil` trên Python hệ thống Admin; luôn có fallback `tasklist` để kiểm tra tiến trình game (`war3`, `tft`, `league of legends`).
- **Game Guard Invariant:** Tự động tạm dừng copy I/O nặng và hạ render khi phát hiện User vào trận game.
