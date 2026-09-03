# Đồng bộ Cấu hình & Hạ tầng Đa máy (Kibe ↔ Admin) qua OneDrive

Tài liệu chi tiết cơ chế đồng bộ tự động hạ tầng `D:\Taadaa` giữa máy chính `kibe` và máy phụ `admin`.

## 1. Bản chất kiến trúc

- `D:\Taadaa` chứa 2 thành phần:
  1. **Các Git Repo con:** Độc lập, cập nhật qua `git pull` / `git push`.
  2. **Hạ tầng Farm dùng chung:** `machine-config/`, `tools/`, các file rules root (`AGENTS.md`, `HANDOFF.md`, `HERMES_SUBAGENT_RULES.md`).
- Để tránh việc sửa rule/config ở `kibe` mà `admin` không nhận được, toàn bộ hạ tầng dùng chung được liên kết qua OneDrive bằng **NTFS Directory Junction (`mklink /J`)**.

## 2. Thư mục đồng bộ `D:\OneDrive\Taadaa_Sync_Shared\`

Thư mục này nằm trên OneDrive gồm:
- `machine-config` (Junction trỏ thẳng vào `D:\Taadaa\machine-config`)
- `tools` (Junction trỏ thẳng vào `D:\Taadaa\tools`)
- `AGENTS.md`, `HANDOFF.md`, `HERMES_SUBAGENT_RULES.md`
- `link_shared_to_admin.bat`: Script khởi tạo liên kết trên máy admin
- `clone_all_repos.bat`: Script clone toàn bộ 15 repo cho máy admin

## 3. Quy trình Bootstrap máy Admin (Chỉ chạy 1 lần duy nhất)

Khi sang máy Admin:
1. Mở `D:\OneDrive\Taadaa_Sync_Shared\` trên máy Admin.
2. Chạy file `link_shared_to_admin.bat`:
   - Tạo junction link 2 chiều từ OneDrive vào `D:\Taadaa\machine-config` và `D:\Taadaa\tools`.
   - Copy các file rules vào `D:\Taadaa\`.
   - Set biến môi trường hệ thống: `TAADAA_HOST_CONFIG="D:\Taadaa\machine-config\admin.yaml"`.
3. Chạy file `clone_all_repos.bat`:
   - Tự động clone 15 repo chuẩn vào `D:\Taadaa`.
4. Tạo venv tại `D:\Taadaa\python-envs\automation` và cài đặt `automation-core`.

Từ lúc này:
- Bất kỳ khi nào máy `kibe` sửa `machine-config` hoặc `tools`, máy `admin` sẽ tự động có ngay lập tức qua OneDrive.
