# Bẫy Thiếu File Manifest Trong sync_2fa_to_admin.py & Code Drift run_capture_phase_a.py (29/10/2026)

## 1. Hiện Tượng Thực Tế
- Báo cáo 2FA ban đêm toàn farm:
  - Farm Kibe (Máy 1-80): Hoàn tất 23 | Bỏ qua 8 | Lỗi 38
  - Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 22 | Lỗi 69
- Toàn bộ 69 máy mục tiêu của Farm Admin đều thất bại (tỷ lệ lỗi 100%), trong khi ADB daemon 192.168.110.119:5037 nhận đủ 78 thiết bị và Preflight VPN/Proxy đều đạt.

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)
1. **Thiếu file trong manifest đồng bộ `D:/Taadaa/tools/sync_2fa_to_admin.py`:**
   - Script đồng bộ `sync_2fa_to_admin.py` chỉ khai báo đẩy 2 file:
     * `python_runner/run_capture_phase_b.py`
     * `python_runner/run_batch_live_2fa.py`
   - File `python_runner/run_capture_phase_a.py` bị bỏ sót hoàn toàn khỏi danh sách `files`.
2. **Hệ quả Code Drift trên Admin-PC:**
   - Logic `resolve_adb_path()` (nằm trong `run_capture_phase_a.py`) được vá trên Kibe để bổ sung fallback XiaoWei `C:\Program Files (x86)\xiaowei\tools\adb.exe` và user `Admin`.
   - Do không được đồng bộ, file `run_capture_phase_a.py` trên Admin-PC vẫn mang code cũ với `DEFAULT_BUNDLED_ADB` trỏ cứng vào `C:\Users\Kibe\...`.
   - Khi runner trên Admin-PC gọi `resolve_adb_path("adb")`, hàm trả về bare string `"adb"`. Vì user `Admin` không có `adb` trong `PATH`, subprocess ném `FileNotFoundError: [WinError 2] The system cannot find the file specified: 'adb'` trên toàn bộ worker con, làm liệt 100% mục tiêu.

## 3. Quy Tắc & Giải Pháp Chuẩn Hóa
1. **Bắt buộc đồng bộ bộ ba runner:**
   - Trong `D:/Taadaa/tools/sync_2fa_to_admin.py`, danh sách `files` bắt buộc phải bao gồm đủ cả 3 file:
     * `python_runner/run_capture_phase_a.py` (chứa `resolve_adb_path`)
     * `python_runner/run_capture_phase_b.py` (chứa core Phase B worker)
     * `python_runner/run_batch_live_2fa.py` (chứa batch runner & freeze logic)
2. **Quy trình Verify sau khi Sync:**
   - Sau khi chạy `sync_2fa_to_admin.py`, bắt buộc chạy lệnh kiểm tra nhanh qua SSH:
     ```powershell
     & 'D:\Taadaa\python-envs\automation\Scripts\python.exe' -c "from run_capture_phase_a import resolve_adb_path; print(resolve_adb_path('adb'))"
     ```
   - Xác nhận output trả về đúng đường dẫn XiaoWei `C:\Program Files (x86)\xiaowei\tools\adb.exe` thay vì bare string `"adb"`.
