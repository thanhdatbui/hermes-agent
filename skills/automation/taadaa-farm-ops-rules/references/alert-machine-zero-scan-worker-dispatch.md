# Quy tắc xử lý Alert [MÁY N] - Zero-Scan & Mandatory Worker Dispatch (2026-09-02)

## 1. Zero-Scan Policy
- Khi nhận thông báo `[MÁY N] DỪNG PHIÊN`:
  - **CẤM TUYỆT ĐỐI**: Không chạy các lệnh quét đệ quy (`search_files`, `find`, `glob.glob`, `os.walk`, `ls -R`) trên các thư mục `.ai-runs`, `runtime/`, `kibe/live/`.
  - **ĐÚNG**: Truy cập thẳng vào thư mục đích danh `D:\Taadaa\runtime\kibe\...\machines\machine_N` hoặc map trực tiếp serial của máy qua file `taikhoan_run_safe.xlsx` / `kibe.yaml`.

## 2. Coordinator Quarantine & Mandatory Worker Dispatch
- Session chính (Coordinator) chỉ đảm nhận vai trò:
  1. Đọc tóm tắt lỗi từ artifact `machine_N` hoặc prompt người dùng.
  2. Dispatch ngay `delegate_task(role='leaf', model='ag-worker')` mang đầy đủ thông tin máy, serial, tài khoản cho worker xử lý khép kín.
  3. Nhận kết quả từ worker và báo cáo người dùng.
- **CẤM Coordinator tự chạy**:
  - Không chạy các lệnh ADB `shell input tap`, `keyevent`, `sleep 15-30s`.
  - Không chạy các vòng lặp dump UI XML hay `reconcile_tiktok_accounts.py` timeout lớn trên context chính.
  - Việc chạy trực tiếp trên context chính làm context phình to đột ngột và dẫn đến timeout / interrupted / treo session.
