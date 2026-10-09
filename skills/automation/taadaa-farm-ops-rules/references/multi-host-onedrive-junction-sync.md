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
2. Chạy file `link_shared_to_admin.bat` với quyền Administrator:
   - Tạo junction link 2 chiều từ OneDrive vào `D:\Taadaa\machine-config` và `D:\Taadaa\tools`.
   - Copy các file rules vào `D:\Taadaa\`.
   - Set biến môi trường hệ thống: `TAADAA_HOST_CONFIG="D:\Taadaa\machine-config\admin.yaml"`.
3. Chạy file `clone_all_repos.bat`:
   - Tự động clone 15 repo chuẩn vào `D:\Taadaa`.
4. Tạo venv tại `D:\Taadaa\python-envs\automation` và cài đặt `automation-core`.

Từ lúc này:
- Bất kỳ khi nào máy `kibe` sửa `machine-config` hoặc `tools`, máy `admin` sẽ tự động có ngay lập tức qua OneDrive.

---

## 4. Quy tắc Single Source of Truth cho Tools Dùng Chung Toàn Farm

Nhằm tránh tình trạng phân mảnh mã nguồn, lệch phiên bản (out-of-sync) và xung đột file đồng bộ trên OneDrive, toàn bộ hệ thống tuân thủ nghiêm ngặt các quy chuẩn sau:

### A. Phân tách Runtime vs Quản lý Mã nguồn (Git)
1. **Runtime duy nhất (Single Execution Path):**
   - Toàn bộ công cụ vận hành chung (`buy_hotmail.py`, `inspect_machine.py`, `install_farm_apks.py`...) BẮT BUỘC đặt tại `D:\Taadaa\tools\`.
   - Cả 2 máy Kibe và Admin đều dùng chung thư mục này qua OneDrive NTFS Junction.
   - Mọi script, pipeline, runner ở mọi repo (`Tiktok_Reg`, `Hotmail`...) đều gọi trực tiếp qua `python D:/Taadaa/tools/<tool_name>.py` hoặc import từ `D:\Taadaa\tools\`.
2. **Quản lý mã nguồn tập trung (Git Version Control):**
   - Mã nguồn các tools dùng chung được commit và quản lý tập trung DUY NHẤT tại repo `AI-Tools` (`D:\Taadaa\AI-Tools\tools\`).
   - **CẤM TUYỆT ĐỐI nhân bản (duplicate):** Cấm sao chép các file tool chung vào thư mục `tools/` của các repo con (`Hotmail/tools/`, `Tiktok_Reg/tools/`...). Mọi hành vi nhân bản làm rác git repo và gây rủi ro sửa ở repo này nhưng chạy code cũ ở repo khác.

### B. Phân quyền Master / Client (Chống OneDrive Conflicted Copy)
- **Kibe là Master:** Toàn bộ việc code, sửa đổi, nâng cấp, kiểm thử tool thực hiện trên máy Kibe tại `D:\Taadaa\tools\`.
- **Admin là Client (Read-Only Execution):** Máy Admin CHỈ thực thi chạy các file tool trong `D:\Taadaa\tools\`, tuyệt đối KHÔNG chỉnh sửa code tool từ máy Admin.
- **Mục đích:** Ngăn chặn OneDrive tạo các file conflict nguy hiểm như `buy_hotmail (Kibe's conflicted copy).py` khi hai máy cùng chạm vào file.

### C. Kiến trúc Phân lớp Rule (Layered Rules Placement)
- **Root Workspace Rules (`D:\Taadaa\AGENTS.md`):**
  - Đồng bộ tự động 2 chiều qua `D:\OneDrive\Taadaa_Sync_Shared\AGENTS.md`.
  - Giúp mọi AI Agent (Hermes, Claude, Codex) khi mở session trên cả Kibe và Admin đều lập tức nạp quy tắc toàn cục này mà không cần chờ `git pull`.
- **Repo-level Rules (`AGENTS.md` từng repo):**
  - Lưu trong các repo Git (`AI-Tools`, `Hotmail`, `Tiktok_Reg`...).
  - Ép các worker subagent tuân thủ ranh giới single-repo, không được tự ý tạo/sao chép tool sang repo con.

### D. Vệ sinh Python Bytecode & OneDrive Sync
- Tránh để OneDrive sync các file bytecode `__pycache__/` và `*.pyc` giữa 2 máy (có thể gây lệch cache bytecode khi phiên bản Python giữa 2 máy khác nhau).
- Đảm bảo các thư mục tools có `.gitignore` bao gồm `__pycache__/`, `*.pyc`. Khi cần thiết thiết lập `PYTHONDONTWRITEBYTECODE=1` trong môi trường runtime của farm.
