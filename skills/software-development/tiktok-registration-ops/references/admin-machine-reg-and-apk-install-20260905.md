# Admin Machine Setup, APK Deployment, and Dynamic STT Resolution (2026-09-05)

## 1. Dynamic Device Resolution cho dải máy Admin (STT 201+) - Case REG-05
- **Nguyên nhân gốc rễ (Anti-Pattern):**
  Trong `social_reg_v1.py`, mảng `ACCOUNTS` bị hardcode danh sách 80 máy cũ (STT 1..80) của máy Kibe. Khi chạy trên host Admin (dải 201..280) bằng lệnh `social_reg_v1.py 201 --ss`, script tìm STT trong `ACCOUNTS` không thấy nên in `Không có STT 201` và thoát ngay (`sys.exit(1)`).
- **Giải pháp chuẩn hóa (Case Fix commit `3fd3f51`):**
  Tích hợp hàm `resolve_account_for_stt(stt, target_device=None, preferred_email=None, inventory_workbook=None)`:
  1. Tra cứu danh sách `ACCOUNTS` legacy trước.
  2. Nếu không có: sử dụng `target_device` (nếu truyền từ CLI) hoặc gọi `scripts.target_inventory.resolve_machine_device(stt, TARGET_INVENTORY_WORKBOOK)` từ workbook inventory của host (`D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx`).
  3. Trả về đối tượng `acc = {"stt": stt, "device": resolved_device, "email": preferred_email or "", "pass": ""}`.
  4. Bổ sung tra cứu inventory trong `_process_mentions_known_target` để regex process nhận diện đúng dải STT 201+.

## 2. Tool Cài Đặt APK Tự Động Farm (`install_farm_apks.py`)
- **Vị trí tool:** `D:\Taadaa\tools\install_farm_apks.py` (đồng bộ vào `AI-Tools/tools/` và thư mục chia sẻ OneDrive).
- **Thư mục APK nguồn trên OneDrive:** `D:\OneDrive\apk-bank`
  - TikTok Split APK (50 file): `D:\OneDrive\apk-bank\com_ss_android_ugc_trill\` -> cài đặt qua `adb -s <serial> install-multiple -r <files>`.
  - Outlook: `D:\OneDrive\apk-bank\com_microsoft_office_outlook\com.microsoft.office.outlook_...apk` -> cài đặt qua `adb -s <serial> install -r <apk>`.
  - ViChanger: `D:\OneDrive\apk-bank\vn_vichanger_app\base.apk` -> cài đặt qua `adb -s <serial> install -r <apk>`.
- **Cơ chế thông minh:**
  - Tự động kiểm tra `pm path` trước khi cài; nếu ứng dụng đã tồn tại thì skip (`[SKIP_INSTALLED]`), trừ khi truyền `--force`.
  - CLI commands:
    ```bash
    # Cài cho 1 máy cụ thể theo STT
    python D:/Taadaa/tools/install_farm_apks.py --stt 201

    # Cài song song cho toàn bộ máy đang kết nối ADB
    python D:/Taadaa/tools/install_farm_apks.py --all
    ```

## 3. Tool Mua & Nạp Hotmail OAuth2 Tự Động Cho Admin (`buy_hotmail.py`)
- **Vị trí tool:** `D:\Taadaa\tools\buy_hotmail.py` (đồng bộ vào `AI-Tools/tools/` và `Hotmail/tools/`).
- **Endpoint BoxTaiKhoan:**
  - `POST https://boxtaikhoan.com/ajaxs/client/product.php` (Product 60 - Hotmail OAuth2).
  - Mua lẻ từng acc `amount=1` để nhận trực tiếp data JSON token đầy đủ 450-525 ký tự.
- **Preflight Live Token Check:**
  - Gọi `POST https://login.microsoftonline.com/consumers/oauth2/v2.0/token` lấy `access_token` live (HTTP 200) trước khi nạp vào sheet.
- **Nạp trực tiếp vào kho Admin:**
  ```bash
  python D:/Taadaa/tools/buy_hotmail.py --append-admin <SO_LUONG>
  ```
  Tự động nạp vào `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx` đúng chuẩn 11 cột bắt đầu từ máy 201+.

## 4. Setup Host Môi Trường Admin & Tránh Lỗi Ký Tự Escape
- Trong batch script Windows (`link_shared_to_admin.bat`):
  - Dấu `\a` trong `\admin.yaml` dễ bị nuốt thành `dmin.yaml` (ký tự chuông ASCII \a).
  - Dấu `\t` trong `\tools` dễ bị chuyển thành Tab `\t`.
  - Cần bọc string hoặc viết rõ ràng: `setx TAADAA_HOST_CONFIG "D:\Taadaa\machine-config\admin.yaml"`.
- Bắt buộc tạo thư mục runtime cục bộ ngoài OneDrive: `mkdir "D:\Taadaa\runtime\admin"`.
