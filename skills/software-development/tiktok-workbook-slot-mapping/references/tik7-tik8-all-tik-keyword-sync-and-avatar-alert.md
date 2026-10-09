# Tik7 & Tik8 Expansion, All-Tik Dynamic Keyword Sync & Post-Evening Avatar Pipeline (2026-09-13)

## 1. Mở Rộng Dải Quản Lý Farm Tik 7 & Tik 8 (8 Slot Toàn Diện)
Farm Kibe & Admin chuẩn hóa 80 máy x 8 slot (tổng 640 tài khoản).
- **Tik7.xlsx (Slot 7)**:
  - Cột `Folder Video` = `(m - 1) * 8 + 7` (dải `7, 15, 23, ..., 639`).
  - Cột `video gốc` (Source Folder) = `480 + m` (dải `481..560`).
- **Tik8.xlsx (Slot 8)**:
  - Cột `Folder Video` = `(m - 1) * 8 + 8` (dải `8, 16, 24, ..., 640`).
  - Cột `video gốc` (Source Folder) = `560 + m` (dải `561..640`).

### Quy tắc Mapping & Sync ID từ DAT (`taikhoan_dat_v2_updated .xlsx`):
1. `TIK_SLOT_MAP` trong `sync-tik-workbooks.py` và `TIK_FILE_NAMES` trong `sync-safe-workbook.py` bắt buộc khai báo đủ 8 file (`Tik1.xlsx` -> `Tik8.xlsx`).
2. Khi nick mới được reg ở Slot 7 hoặc Slot 8, cron sync 5 phút (`taikhoan_sync_cron_launcher.py`) tự động nạp ID vào đúng dòng máy của `Tik7.xlsx` / `Tik8.xlsx` và gán trạng thái `Kiểm Tra Dữ Liệu = OK`.

---

## 2. Cơ Chế Auto-Sync Niche, Keyword & Hashtag Pool Toàn Diện (All Tik)
- **Vấn đề thực tế**: Khi kho video nguồn (`D:\video goc\1..640`) chưa tải xong hết, nếu tạo trước file Excel thì các máy chưa có video sẽ bị trống `Keyword Video` và `Hashtag Pool`. Hoặc khi người dùng reset, reseed, đổi nội dung/niche cho một nick, hashtag trong Excel có thể bị lệch so với video thật trong thư mục.
- **Giải pháp: Script & Cron Dynamic Keyword Sync (`sync_all_tik_keywords.py`)**:
  - Chuỗi mapping: `D:\CodexRuntime\tiktok-video\state.db` (bảng `folders`) $\rightarrow$ `D:\Taadaa\Tiktok-video\data\niches_pool.txt` (slug $\rightarrow$ label tiếng Việt) $\rightarrow$ `Tik1..Tik8.xlsx` (`TaiKhoan` và `Hashtag theo Folder`).
  - Khi downloader gán hoặc đổi niche của bất kỳ folder nguồn nào, script tự động cập nhật lại đúng `Keyword Video` và `Hashtag Pool` tương ứng.
  - Tích hợp 2 lớp:
    1. Lớp lồng ghép trong `hermes_taikhoan_sync_cron.py` (chạy mỗi 5 phút khi có thay đổi DAT/Tik).
    2. Lớp cron độc lập (`sync-all-tik-keywords-cron`, chu kỳ `*/15 * * * *`).

---

## 3. Quy Chuẩn Báo Cáo Farm Alert Cho Batch Upload Avatar
- **Yêu cầu người dùng (User Invariant)**: **"K nhé chạy xong mới báo"**.
  - Tuyệt đối KHÔNG gửi thông báo "Bắt đầu chạy batch" làm loãng nhóm Farm Alert.
  - Chạy ngầm hoàn toàn trong suốt quá trình upload.
  - CHỈ gửi DUY NHẤT 1 tin nhắn tổng kết vào Farm Alert (`-5373649734`) khi toàn bộ batch của Row đó đã chạy xong, đối soát trực tiếp từ `summary.csv` và workbook thực tế:
    - Tổng số acc cần up
    - Danh sách máy thành công
    - Danh sách máy chưa hoàn tất (nếu có)
- **Hàng đợi tuần tự sau ca tối (21:00 - 23:30)**:
  $$\text{TARGET\_TIKS} = [\mathbf{5}, \mathbf{6}, \mathbf{7}, \mathbf{8}, \mathbf{3}, \mathbf{4}]$$
  Lọc chính xác các máy có nick hợp lệ mà cột `Avatar` khác `OK` để đưa vào `-ForceAvatarMachineList`. Không chạy lại máy đã đủ avatar.

---

## 4. Quản Lý & Đồng Bộ Script Cron Dùng Chung Trên OneDrive
- Toàn bộ script cron dùng chung giữa Kibe và Admin được lưu trữ tại:
  `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`
- Đồng thời được version control trong Git:
  `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`
- Cấu hình file hướng dẫn cho Admin: `D:\OneDrive\Taadaa_Sync_Shared\SETUP_ADMIN_CRON_CUON_CHIEU.txt`.
