# Admin Farm Inventory Resolution & One-Tap Login Reactivation

> **Date:** 2026-10-09  
> **Repo:** `D:/Taadaa/Tiktok_Reg`  
> **Script:** `tiktok_login_v1.py`  
> **Context:** Vận hành login phục hồi tài khoản cũ trên cụm Admin (Máy 201-280) khi văng phiên.

---

## 1. Multi-Host Inventory Resolution Trong `tiktok_login_v1.py`

### Vấn đề gốc rễ:
- Script `tiktok_login_v1.py` ban đầu sử dụng hàm `resolve_device(stt)` chỉ quét danh sách cứng `ACCOUNTS` trong `social_reg_v1.py`.
- Danh sách `ACCOUNTS` này chỉ chứa ánh xạ máy STT 1–80 (thuộc cụm Kibe farm).
- Khi gọi lệnh login cho các máy thuộc cụm Admin (STT 201–280), ví dụ Máy 266:
  ```text
  STOPPED: Khong co STT 266 trong ACCOUNTS (RuntimeError)
  ```

### Bản vá chuẩn hóa O(1):
Hàm `resolve_device(stt)` được bổ sung fallback động:
```python
def resolve_device(stt):
    acc = next((item for item in ACCOUNTS if item["stt"] == stt), None)
    if acc and acc.get("device"):
        return acc["device"]
    from project_paths import TARGET_INVENTORY_WORKBOOK
    from scripts.target_inventory import load_machine_devices
    dev = load_machine_devices(TARGET_INVENTORY_WORKBOOK).get(stt)
    if dev:
        return dev
    raise RuntimeError(f"Khong co STT {stt} trong ACCOUNTS")
```
Khi chạy trên cụm Admin (`TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml"`), `TARGET_INVENTORY_WORKBOOK` tự động trỏ về `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx` và giải quyết chính xác serial máy thực tế.

---

## 2. Remote ADB Socket Requirement Cho Cụm Admin

### Cạm bẫy VPN Gate Blocked:
- Dàn Admin vận hành qua ADB server từ xa tại `192.168.110.119:5037`.
- Nếu chỉ truyền `TAADAA_HOST_CONFIG` mà thiếu biến môi trường `ADB_SERVER_SOCKET`, tiến trình `adb.exe` con sẽ kết nối mặc định vào `localhost:5037`:
  ```text
  [device-lock] VPN GATE BLOCKED: device is offline or ADB/USB disconnected for <serial>: adb.exe: device '<serial>' not found
  ```

### Lệnh chạy chuẩn:
BẮT BUỘC kẹp biến `ADB_SERVER_SOCKET`:
```bash
ADB_SERVER_SOCKET="tcp:192.168.110.119:5037" \
TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml" \
python -u D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <stt> --email <target_id_or_email> --ss
```

---

## 3. Khôi Phục Phiên Siêu Tốc Qua One-Tap Login ("Chào Mừng Bạn Trở Lại")

### Cơ chế giao diện TikTok v46.x:
1. Khi máy có <= 2 tài khoản hoặc toàn bộ tài khoản bị hết hạn token/văng phiên:
   - Header trang Profile không hiển thị nút mũi tên dropdown (▼).
   - Tên hiển thị chỉ là text tĩnh (`sv6` / `pmf`), bấm vào không bung Account Switcher.
   - Menu Cài đặt không có mục "Chuyển đổi tài khoản".
2. Toàn bộ các phiên cũ thực chất được TikTok lưu đệm trong bottom sheet **"Chào mừng bạn trở lại" (One-tap login)**.

### Thao tác kích hoạt nhanh O(1) (Bypass OTP):
- Thay vì chạy luồng login OTP tốn 2–3 phút:
  1. Vào tab Hồ sơ -> Màn hình "Chào mừng bạn trở lại" xuất hiện liệt kê các nick (ví dụ `@bongbong02892`, `@letam2502`).
  2. Tap trực tiếp vào hàng tài khoản mong muốn (hoặc node `ptp`).
  3. App TikTok sử dụng token đệm nội bộ để kích hoạt lại phiên đăng nhập ngay lập tức (2–3 giây).
- Khi có ít nhất 1 nick đăng nhập active:
  - Context phiên app được nạp đầy đủ.
  - Phá vỡ trạng thái deadlock để tiếp tục các tác vụ chuyển nick hoặc đăng ký tài khoản mới (Row N).
