# TikTok Login Automation: Admin Remote Socket, Inventory Fallback & One-Tap vs Switcher (2026-10-09)

> **Bối cảnh:** Vận hành `tiktok_login_v1.py` trên cụm Admin (Máy 201–280) và chẩn đoán giao diện One-tap Login ("Chào mừng bạn trở lại") vs Account Switcher trên Samsung Galaxy S7 (Android 8, TikTok v46.6.3).

---

## 1. Bản Vá Khẩn Cấp: `resolve_device(stt)` Hỗ Trợ Máy Cụm Admin (STT 201–280)

### Triệu chứng:
Khi chạy lệnh login trên máy cụm Admin:
```bash
python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py 266 --email letam2502
```
Script văng lỗi:
```text
STOPPED: Khong co STT 266 trong ACCOUNTS
```

### Nguyên nhân:
Mảng `ACCOUNTS` trong `social_reg_v1.py` chỉ định nghĩa cứng danh sách serial cho các máy STT 1–39/80 (Cụm Kibe). Hàm `resolve_device` tra cứu trong `ACCOUNTS` và văng `RuntimeError` khi gặp máy Admin.

### Bản vá chuẩn hóa (O(1) Fallback):
Bổ sung fallback sang `load_machine_devices(TARGET_INVENTORY_WORKBOOK)` (`taikhoan_run_safe.xlsx`):
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

---

## 2. Invariant Môi Trường ADB Socket Cho Cụm Admin Remote

### Triệu chứng:
```text
Reconnecting remote ADB host localhost:5037 for serial=ce0516052b95322202
[device-lock] VPN GATE BLOCKED: device is offline or ADB/USB disconnected for ce0516052b95322202: device offline or ADB/USB disconnected: adb.exe: device 'ce0516052b95322202' not found
```

### Quy tắc bắt buộc:
Xiaowei ADB wrapper (`adb_config.py`) chỉ đọc `ADB_SERVER_SOCKET` từ biến môi trường. Khi gọi `tiktok_login_v1.py` trực tiếp từ terminal, BẮT BUỘC phải export:
```bash
ADB_SERVER_SOCKET="tcp:192.168.110.119:5037" \
TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml" \
python -u D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <target> --ss
```

---

## 3. Bản Chất Giao Diện: "Đăng Nhập Cả 2 Acc Mà Switcher Không Bung, Vẫn Ra Màn Chào Mừng Bạn Trở Lại?"

### Thắc mắc & Nhận định từ Người dùng:
*"Là sao đáng lẽ đăng nhập cả 2 acc thì account switcher phải bung ra. Chứ sao lại xuất hiện màn chào mừng bạn trở lại nữa"*

### Kết quả Thực nghiệm & Cơ chế TikTok v46.6.3 trên Android 8:
1. **Kiến trúc Single-Active Session**:
   - Khi thiết bị chỉ mới có 1 hoặc 2 tài khoản, TikTok bản v46.6.3 trên Android 8 quản lý theo cơ chế **One-tap Fast Login Hub** thay vì gom chung vào in-app switcher.
   - Khi đang ở Profile của tài khoản active:
     - Tên hiển thị (`sv6`) là text tĩnh, không có nút mũi tên chevron ▼ xổ xuống.
     - Trong *Cài đặt và quyền riêng tư*, ở đáy danh sách **chỉ có duy nhất nút "Đăng xuất"** (hoàn toàn không có dòng "Chuyển đổi tài khoản").
2. **One-Tap Login Hub ("Chào mừng bạn trở lại")**:
   - Khi bấm "Đăng xuất", TikTok không hề xóa session. Cả 2 nick cũ (`letam2502`, `bongbong02892`) đều nằm nguyên vẹn trong danh sách One-tap.
   - **Chuyển nick**: Bấm vào bất kỳ nick nào trên màn hình One-tap là vào thẳng Profile ngay lập tức (không cần mật khẩu hay OTP).
   - **Thêm nick mới**: Nút *"Thêm tài khoản khác"* và *"Đăng ký"* luôn hiện diện ở đáy màn hình One-tap để tiếp tục thêm các tài khoản tiếp theo.
