# Tik7 & Tik8 Mapping, Render Pipeline and Source Inventory Specifications

## 1. Overview & Context (8 Nick/Máy Expansion)

Farm quy chuẩn mở rộng 80 máy x 8 slot (tổng cộng 640 accounts).
Các slot 1..6 (Tik1..Tik6) đã hoàn thiện render và vận hành ổn định.
Slot 7 & Slot 8 được kích hoạt bổ sung nhằm phục vụ kho nuôi nick và ươm phôi trắng.

## 2. Quy chuẩn Mapping Slot & Folders (Tik7 & Tik8)

### Output Render Folders (`D:\TIKTOK-videonuoinick`)
Theo công thức định danh toàn farm: `Folder Video = (m - 1) * 8 + k` (máy $m = 1..80$, slot $k = 1..8$):
- **Tik7 (Slot 7)**:
  - Công thức: `(m - 1) * 8 + 7`
  - Dải folder: `7, 15, 23, 31, 39, ..., 631, 639` (đúng 80 folders).
  - Tên file trong folder: bắt buộc tuần tự `1.mp4..N.mp4` ($\ge 30$ mp4, target 45 mp4) + `avatar.jpg`.
- **Tik8 (Slot 8)**:
  - Công thức: `(m - 1) * 8 + 8`
  - Dải folder: `8, 16, 24, 32, 40, ..., 632, 640` (đúng 80 folders).
  - Tên file trong folder: bắt buộc tuần tự `1.mp4..N.mp4` ($\ge 30$ mp4, target 45 mp4) + `avatar.jpg`.

### Nguồn Video Gốc (`D:\video goc`)
Theo công thức nguồn video gốc toàn farm: `video goc = (k - 1) * 80 + m`:
- **Tik7 (Slot 7)**: `480 + m` -> dải `481..560` (80 folders).
- **Tik8 (Slot 8)**: `560 + m` -> dải `561..640` (80 folders).

### CẢNH BÁO BẪY TƯ DUY TRÙNG LẶP SỐ DẢI
- **Bẫy nhầm lẫn giữa Output Folder và Source Folder**:
  - Dải số `481..560` trong `D:\TIKTOK-videonuoinick` là output của Máy 61..70 (Slot 1..8).
  - Dải số `481..560` trong `D:\video goc` là folder NGUỒN của Tik7 (Máy 1..80).
  - Hai namespace này hoàn toàn tách biệt. Tuyệt đối không nhầm lẫn số folder output của cụm máy 61..70 với số folder nguồn của Tik7.

## 3. Quy trình Triển khai Kéo Nguồn & Render

1. **Kiểm tra State & Global Ledger**:
   - Khi kéo video cho `D:\video goc\481..640`, sử dụng SQLite `D:\CodexRuntime\tiktok-video\state.db` và ledger `D:\OneDrive\SharedData\tiktok-video\global-ledger\Kibe.jsonl` để tránh tải trùng URL/video đã dùng cho các máy hoặc slot khác.
2. **Workbook Khởi tạo**:
   - Tạo `Tik7.xlsx` và `Tik8.xlsx` tại `D:\OneDrive\TaadaaData\kibe\` theo schema chuẩn 12 cột: `Máy`, `device ID`, `ID`, `Folder Video`, `video gốc`, `Keyword Video`, `Hashtag Pool`, `Video Đã Đăng`, `Kiểm Tra Dữ Liệu`, `Render Status`, `Render MP4`, `Render Updated`.
3. **Render Launcher**:
   - Nhân bản từ launcher chuẩn `run_tik6_random_render.ps1` thành `run_tik7_random_render.ps1` (`$Slot = 6`) và `run_tik8_random_render.ps1` (`$Slot = 7`).
   - Cấu hình `--slot` tương ứng để phân phối Voice Profile và filter ngẫu nhiên chống trùng lặp vân tay A/V.
   - Luôn chạy `--parallel 1` để bảo toàn CPU host Kibe.
