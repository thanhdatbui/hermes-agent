# Google Drive Virtual Mirror Deadlock & Host Game Preservation

## 1. Google Drive Desktop Virtual Mirror Deadlock (Con Gà - Quả Trứng)
- **Cơ chế:** Google Drive Desktop (ổ ảo `G:`) trên Windows khi cấu hình `ContentCachePath` trên ổ `D:\GoogleDriveCache`, Windows API `shutil.disk_usage("G:")` phản chiếu trực tiếp dung lượng còn trống của ổ vật lý chứa Cache (`D:`).
- **Deadlock Loop:**
  1. Khi ổ `D:` đầy cứng `0 bytes free`, ổ `G:` cũng lập tức báo `0 bytes free` (dù tài khoản Google Drive cloud còn nhiều TB).
  2. Các script backup cuốn chiếu (như `sync_and_clean_gdrive.py`) copy file từ `D:` sang `G:` trước khi xóa `D:`.
  3. Thao tác copy sang `G:` quăng lỗi `OSError: [Errno 28] No space left on device` vì Google Drive không còn bộ đệm ghi đĩa.
  4. Script không thể copy $\rightarrow$ không dám xóa file trên `D:` $\rightarrow$ ổ `D:` kẹt vĩnh viễn ở 0 bytes, làm toàn bộ downloader (`download_by_niche.py`) crash hàng loạt.
- **Cách tháo gỡ an toàn:**
  - BẮT BUỘC "mồi" giải phóng 20–30 GB dung lượng trống trên ổ vật lý chứa cache trước để Google Drive mở khóa bộ đệm ghi đĩa ảo `G:`.
  - Không xóa bừa bãi dữ liệu của farm hay user để lấy dung lượng.

## 2. Bảo Tồn Game Host (CẤM XÓA NHẦM LEAGUE OF LEGENDS / TFT)
- **Vị trí Game trên Farm:**
  - **Máy chính (Kibe):** Cài tại `C:\Riot Games\` (Live + PBE). Ổ D: máy Kibe KHÔNG chứa game.
  - **Máy phụ (Admin - 192.168.110.119):** Được cài tại `D:\x\Riot Games\` hoặc phân bổ Live tại `C:\Riot Games\` và PBE tại `D:\Riot Games\`.
- **CẤM TUYỆT ĐỐI:** Phán đoán thư mục `D:\x` hay thư mục game là "bộ cài cũ/file rác" để tự ý xóa khi dọn đĩa.
- **Quy trình kiểm tra trước khi dọn đĩa:**
  1. Kiểm tra cấu hình cài đặt tại `C:\ProgramData\Riot Games\RiotClientInstalls.json`.
  2. Kiểm tra tiến trình hoạt động (`is_gaming_active()`: `league of legends.exe`, `tftclient.exe`, `war3.exe`).
  3. Nếu cần giải phóng dung lượng cho máy Admin: Hỏi rõ User hoặc chia tách rõ ràng: Live ném vào `C:\Riot Games` (nếu ổ C còn $\ge 50$ GB), PBE ném vào `D:\Riot Games`.

## 3. Quy Tắc Xóa Cuốn Chiếu Video Gốc (`D:\video goc may 2`)
- Video gốc **CHỈ ĐƯỢC PHÉP XÓA** khi thỏa mãn đồng thời 2 điều kiện:
  1. Đã copy an toàn 100% sang `G:\My Drive\video_goc_backup\` (khớp từng byte kích thước).
  2. Thư mục render thành phẩm tương ứng trong `D:\TIKTOK-videonuoinick-admin` **ĐÃ RENDER XONG $\ge 30-45$ CLIP**.
- **CẤM XÓA SỚM:** Video gốc của các cụm Tik chưa render xong (như Tik6, Tik7, Tik8 đang mới đạt 1% – 18%) tuyệt đối không được xóa, tránh làm mất video nguồn khiến farm không thể tiếp tục render.
