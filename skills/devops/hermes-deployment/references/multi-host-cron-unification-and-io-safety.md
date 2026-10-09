# Nguyên Tắc Thiết Kế & Đồng Bộ Cron Toàn Farm (Multi-Host Architecture)

## 1. Nguyên Tắc Cốt Lõi: Cấu hình dùng chung, Data tách biệt
- **Cấu hình Cron dùng chung 100%**:
  - Không tạo cronjob riêng lẻ với tên mang tính cục bộ (như `farm-admin-render-download-watchdog` vs `farm-kibe-render-download-watchdog`).
  - Thống nhất 1 tên cron duy nhất (ví dụ: `farm-render-download-watchdog`).
  - Toàn bộ logic kiểm tra, watchdog, runner phải được viết **Host-Aware** (tự động nhận diện host qua file nhận diện hoặc biến môi trường `TAADAA_HOST_CONFIG` / `TAADAA_HOST`).
- **Data & Thiết bị tách biệt theo máy**:
  - Máy Kibe: Quản lý cụm S7 M1..M80, dữ liệu tại `D:\OneDrive\TaadaaData\kibe\`, video gốc `D:\video goc`, render `D:\TIKTOK-videonuoinick`.
  - Máy Admin: Quản lý cụm S7 M201..M280, dữ liệu tại `D:\OneDrive\TaadaaData\admin\`, video gốc `D:\video goc may 2`, render `D:\TIKTOK-videonuoinick-admin`.

## 2. Quy Trình Tự Động Đồng Bộ 2 Chiều (Sync Pipeline)
Để tránh tình trạng mỗi máy tạo cron riêng lẻ, phân mảnh:
1. **Master Script Danh Mục Cron (`setup_admin_cron.py`)**:
   - Nằm tại `D:\OneDrive\Taadaa_Sync_Shared\tools\setup_admin_cron.py` và được mirror sang `D:\Taadaa\Hermes\deploy\hermes-home\scripts\setup_admin_cron.py`.
   - Chứa danh sách đầy đủ 16 Cron Jobs chuẩn toàn farm.
   - Hỗ trợ `--dry-run` để kiểm tra trước khi apply.
2. **Kích hoạt tự động trong `sync-from-kibe.ps1`**:
   - Trong Section 3 (đồng bộ config và scripts) của `deploy/sync-from-kibe.ps1`, tích hợp lệnh tự động thực thi `python setup_admin_cron.py`.
   - Khi máy Admin chạy lệnh:
     `git -C D:\Taadaa\Hermes pull --rebase fork main && powershell -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Hermes\deploy\sync-from-kibe.ps1`
     thì toàn bộ danh sách cronjob dùng chung sẽ tự động được cập nhật trên Admin mà không cần bất kỳ thao tác tay nào.

## 3. Pitfall Tránh Nghẽn I/O HDD Trong Watchdog Giám Sát Video
- Khi viết script đếm số lượng video gốc (hàng chục nghìn file MP4):
  - **CẤM** dùng `os.walk` hoặc đếm đệ quy toàn bộ đĩa HDD, vì sẽ gây treo script > 180s (timeout).
  - **BẮT BUỘC** ưu tiên đọc metadata nhanh từ `state.db` SQLite (`SELECT video_count FROM folders WHERE video_count IS NOT NULL`), tốc độ < 10ms.
  - Khi duyệt thư mục render Tik1..Tik8: chỉ scan thư mục cấp 1 bằng `os.scandir` cho 80 folder tương ứng với 80 máy, không duyệt sâu.
