# Tik7 & Tik8 Expansion, All-Tik Dynamic Keyword Sync, and Post-Evening Avatar Watchdog (2026-09-13)

## 1. Tik7 & Tik8 Expansion Architecture
- **Farm 80 máy x 8 slot**:
  - `Tik7.xlsx` (Slot 7): Folder video output `(m-1)*8 + 7` (dải `7, 15, 23... 639`), Folder nguồn `D:\video goc\481..560`.
  - `Tik8.xlsx` (Slot 8): Folder video output `(m-1)*8 + 8` (dải `8, 16, 24... 640`), Folder nguồn `D:\video goc\561..640`.
- **Đồng bộ 1-chiều (DAT -> Tik1..Tik8 -> Safe)**:
  - Cập nhật `TIK_SLOT_MAP` trong `sync-tik-workbooks.py` đủ 8 files (`Tik1.xlsx: 1` ... `Tik8.xlsx: 8`).
  - Cập nhật `TIK_FILE_NAMES` trong `sync-safe-workbook.py` để đọc số video theo ID account cho toàn bộ 8 slot.

## 2. All-Tik Dynamic Keyword & Hashtag Auto-Sync (`sync_all_tik_keywords.py`)
- **Vấn đề**: Khi tạo file Tik sớm trong khi video nguồn chưa tải xong, cột Keyword và Hashtag Pool bị trống; hoặc khi đổi niche, xóa tạo bộ video mới cho một nick, file Tik bị giữ hashtag cũ.
- **Giải pháp**:
  - Cơ chế mapping 3 bước:
    `state.db (bảng folders)` -> `niches_pool.txt (slug -> label)` -> `Tik1..Tik8 (TaiKhoan & Hashtag theo Folder)`.
  - Tự động phát hiện khi niche trong `state.db` thay đổi hoặc được nạp mới, tự động sinh lại hashtag pool chuẩn (`#<slug> #<slug>vietnam #<slug>moingay #tiktokvietnam #xuhuong #fyp #videohay` hoặc pool đã chuẩn hóa từ các Tik trước).
  - Tích hợp vào:
    1. Cron sync 5 phút (`hermes_taikhoan_sync_cron.py` gọi kèm `--silent`).
    2. Cron độc lập 15 phút (`sync-all-tik-keywords-cron`).

## 3. Pitfall: Fake "ALL_DONE" Watchdog Trap
- **Triệu chứng**: Watchdog báo cáo `[ALL_DONE]` trong khi thực tế chưa có máy nào chạy được avatar.
- **Nguyên nhân**:
  1. Script watchdog gọi `subprocess.run()` blocking một lệnh PowerShell chạy 40-80 máy -> Cron runner bị timeout hoặc văng lỗi.
  2. Code trong khối xử lý mù quáng thực hiện `state["current_index"] += 1` mà không verify kết quả thực tế trên đĩa (folder `batch-runs` hoặc workbook).
- **Quy tắc sửa đổi**:
  1. Spawner cho batch lớn BẮT BUỘC dùng `subprocess.Popen(..., creationflags=CREATE_NO_WINDOW)` chạy background không blocking cron context.
  2. State chỉ được phép advance khi verify folder `batch-runs` mới nhất xuất hiện và tiến trình hoàn thành.

## 4. User Preference: Chỉ báo cáo Farm Alert khi CHẠY XONG
- Khi cấu hình các watchdog dài hạn (như `post-evening-avatar-watchdog`):
  - **CẤM** spam thông báo "Bắt đầu chạy batch" hoặc thông báo tiến trình trung gian.
  - **CHỈ BÁO CÁO 1 LẦN DUY NHẤT KHI CHẠY XONG**: Đối soát `summary.csv` và workbook thực tế, tổng hợp số lượng máy thành công và thất bại gửi vào nhóm Farm Alert (`-5373649734`).
