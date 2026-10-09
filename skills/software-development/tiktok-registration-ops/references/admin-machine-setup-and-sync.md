# Hướng Dẫn Thiết Lập & Đồng Bộ Máy Admin (Reg TikTok Farm Dải 200+)

Tài liệu chi tiết về cơ chế vận hành đa máy (Two-Machine Farm Architecture) và quy trình thiết lập máy Admin để chạy Reg TikTok song song và độc lập với máy chính Kibe.

---

## 1. Kiến Trúc 2 Máy (Two-Machine Farm Architecture)

Hệ thống phân định 2 máy thông qua biến môi trường `TAADAA_HOST_CONFIG` và module `taadaa_host.py`:

| Thuộc tính | Máy Kibe (Máy A) | Máy Admin (Máy B) |
|---|---|---|
| **Host ID** | `kibe` | `admin` |
| **Dải máy quản lý** | `1 - 80` | `200 - 999` |
| **Thư mục Dữ liệu** | `D:\OneDrive\TaadaaData\kibe\` | `D:\OneDrive\TaadaaData\admin\` |
| **Thư mục Runtime** | `D:\Taadaa\runtime\kibe\` | `D:\Taadaa\runtime\admin\` |
| **Host Config** | `D:\Taadaa\machine-config\kibe.yaml` | `D:\Taadaa\machine-config\admin.yaml` |

---

## 2. Quy Trình Đồng Bộ & Mua Hotmail (Pipeline Mua -> Sync Dữ Liệu)

1. **Mua Hotmail tự động qua API:**
   - Endpoint: BoxTaiKhoan `POST /ajaxs/client/product.php` (id 60 - Hotmail OAuth2) hoặc ShopClone7.
   - Luồng mua: Lặp gọi mua lẻ từng acc (`amount=1`) để nhận trực tiếp mảng JSON `data`, bảo toàn chuỗi `refresh_token` chuẩn (450–525 ký tự).
   - Test Live: Kiểm tra `exchange_refresh_token` thành công 100% trước khi nạp vào sheet.

2. **Cấu trúc Single Source of Truth (`gmail_clean_v2.xlsx`):**
   - Lưu trữ toàn bộ Gmail/Hotmail của từng cụm máy.
   - Cột 1: `Số Máy` (dải 200+ đối với Admin).
   - Cột 9–10: `Refresh Token`, `Client ID`.
   - Cột 11–12: `info_changed`, `app_logged_in`.
   - **Quy tắc chèn:** Dùng tool `D:\Taadaa\Hotmail\tools\append_mail_account.py` để chèn đúng nhóm số máy, sắp xếp tăng dần từ nhỏ đến lớn.

---

## 3. Các Bước Thiết Lập Máy Admin (Setup Checklist)

### Bước 1: Đồng bộ thư mục OneDrive
Đảm bảo OneDrive máy Admin đã tải đầy đủ:
- `D:\OneDrive\Taadaa_Sync_Shared\`
- `D:\OneDrive\TaadaaData\admin\` (chứa `gmail_clean_v2.xlsx`, `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`)

### Bước 2: Chạy script liên kết cấu hình
Mở `D:\OneDrive\Taadaa_Sync_Shared\`, chuột phải vào `link_shared_to_admin.bat` chọn **Run as Administrator**:
- Tạo `D:\Taadaa`.
- Tạo Junction `machine-config` và `tools` từ OneDrive sang `D:\Taadaa`.
- Đồng bộ file luật `AGENTS.md`, `HANDOFF.md`, `HERMES_SUBAGENT_RULES.md`.
- Gán biến môi trường hệ thống: `TAADAA_HOST_CONFIG = D:\Taadaa\machine-config\admin.yaml`.

### Bước 3: Kéo toàn bộ Repos về máy Admin
Chạy file `clone_all_repos.bat` trong `D:\OneDrive\Taadaa_Sync_Shared\`:
- Clone/pull đủ 15 repos về `D:\Taadaa\`:
  - `Tiktok_Reg` (branch `main`)
  - `Hotmail` (branch `master`)
  - `automation-core` (branch `master`)
  - `tiktok-add-bao-mat-f2a` (branch `main`)
  - Các repo nuôi acc, video, follow, login.

### Bước 4: Tạo Python Virtualenv
Mở PowerShell / Git Bash trên máy Admin:
```powershell
mkdir D:\Taadaa\python-envs -Force
python -m venv D:\Taadaa\python-envs\automation
D:\Taadaa\python-envs\automation\Scripts\python.exe -m pip install -U pip setuptools wheel
D:\Taadaa\python-envs\automation\Scripts\python.exe -m pip install -e D:\Taadaa\automation-core
D:\Taadaa\python-envs\automation\Scripts\python.exe -m pip install openpyxl requests pyyaml uiautomator2
```

---

## 4. Lệnh Vận Hành Reg TikTok Trên Máy Admin

1. **Kiểm tra phát hiện target (Dry-run):**
   ```bash
   cd D:/Taadaa/Tiktok_Reg
   D:/Taadaa/python-envs/automation/Scripts/python.exe _detect_clean.py
   ```
   *Xác nhận log nhận đúng dải máy 200+ và đọc file từ `TaadaaData\admin`.*

2. **Chạy Canary 1 máy:**
   ```bash
   D:/Taadaa/python-envs/automation/Scripts/python.exe social_reg_v1.py <STT> --email <EMAIL> --ss
   ```

3. **Chạy Batch toàn bộ target máy Admin:**
   ```bash
   D:/Taadaa/python-envs/automation/Scripts/python.exe _run_all_targets.py --full-scope-takeover
   ```
