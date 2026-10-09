# Tik7 & Tik8 Creation and Keyword/Hashtag Auto-Sync Architecture (2026-09-13)

## 1. Bối cảnh & Hiện trạng Mở Rộng 8 Slot Toàn Farm
- Farm Kibe đã nâng quy mô lên **80 máy x 8 slot = 640 accounts**.
- **Master Workbook (`taikhoan_dat_v2_updated .xlsx`)**:
  - Đã mở rộng đủ 640 dòng vật lý (80 máy x 8 hàng).
  - Slot 7 đã có 36 nick, Slot 8 đã có 4 nick.
- **Vấn đề Downloader & Hashtag Pool**:
  - Dải nguồn của Tik7 là `481..560`, Tik8 là `561..640`.
  - Downloader chưa hoàn tất 100% việc tải và phân bổ niche trong SQLite `state.db` bảng `folders` (mới đạt 20/80 folder Tik7 và 12/80 folder Tik8).
  - Nếu chờ tải xong 100% video nguồn mới tạo workbook Tik7/Tik8 thì sẽ làm gián đoạn việc quản lý nick, không up được avatar sớm và không đưa vào pipeline upload được.

## 2. Kiến trúc Decoupled Creation & Auto-Sync Keyword/Hashtag
Để vừa phục vụ vận hành sớm (quản lý nick, up avatar sau ca tối), vừa đảm bảo 100% hashtag chuẩn theo niche:

### Bước 1: Khởi tạo trước khung Workbook Tik7.xlsx và Tik8.xlsx
- Đầy đủ 12 cột chuẩn: `Máy`, `device ID`, `ID`, `Folder Video`, `video gốc`, `Keyword Video`, `Hashtag Pool`, `Video Đã Đăng`, `Kiểm Tra Dữ Liệu`, `Render Status`, `Render MP4`, `Render Updated`.
- Cột ID đồng bộ ngay nick từ `taikhoan_dat_v2_updated .xlsx` (Slot 7/8).
- `Video Đã Đăng = 0`.
- Với các folder đã có niche trong `state.db`: map thẳng Keyword & Hashtag chuẩn.
- Với các folder chưa tải xong: để trống `Keyword Video` và `Hashtag Pool` (chờ sync).

### Bước 2: Cron Tự Động Đồng Bộ Keyword & Hashtag (`sync-tik-keywords-cron`)
- **Tần suất**: Chạy định kỳ mỗi 15-30 phút (hoặc trigger sau mỗi batch download nguồn).
- **Cơ chế**:
  1. Quét `D:\CodexRuntime\tiktok-video\state.db` (bảng `folders`) cho dải `481..640`.
  2. Phát hiện các folder mới chuyển sang trạng thái có `niche` hợp lệ.
  3. Tra cứu `data/niches_pool.txt` để lấy label tiếng Việt chuẩn (`bepviet` -> "Bếp Việt").
  4. Sinh bộ Hashtag Pool chuẩn 9-13 tags:
     `#<slug> #<slug>vietnam #<slug>moingay #tiktokvietnam #xuhuong #fyp #videohay`.
  5. Cập nhật trực tiếp vào 2 cột `Keyword Video` và `Hashtag Pool` của dòng tương ứng trong `Tik7.xlsx` / `Tik8.xlsx` (kèm cập nhật sheet `Hashtag theo Folder`).
  6. Tuyệt đối không ghi đè hay làm thay đổi cột `ID`, `Video Đã Đăng`, `Avatar`.

### Bước 3: Đồng bộ vào chuỗi Sync Master
- Bổ sung `Tik7.xlsx: 7` và `Tik8.xlsx: 8` vào:
  + `D:\Taadaa\tiktok-luot nuoi acc\scripts\sync-tik-workbooks.py` (`TIK_SLOT_MAP`).
  + `D:\Taadaa\tiktok-luot nuoi acc\scripts\sync-safe-workbook.py` (`TIK_FILE_NAMES`).
  + Watchdog avatar sau ca tối `post_evening_avatar_watchdog.py` (`TARGET_TIKS = [5, 6, 7, 8, 3, 4]`).
