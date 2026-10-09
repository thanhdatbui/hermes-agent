# Admin Cluster Inventory Fallback & One-Tap Single Active Session Architecture

> **Date:** 2026-10-09  
> **Repo:** `D:/Taadaa/Tiktok_Reg`  
> **Script:** `tiktok_login_v1.py`  
> **Scope:** Máy cụm Admin (201–280), Samsung Galaxy S7 (Android 8), TikTok v46.6.3

---

## 1. Lỗi Khởi Chạy `tiktok_login_v1.py` Trên Cụm Admin: `Khong co STT <N> trong ACCOUNTS`

### Triệu chứng & Nguyên nhân:
Khi chạy:
```bash
python -u D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py 266 --email letam2502 --ss
```
Script lập tức dừng với traceback:
```text
RuntimeError: Khong co STT 266 trong ACCOUNTS
```
Hàm `resolve_device(stt)` trong `tiktok_login_v1.py` trước đây chỉ tra cứu biến tĩnh `ACCOUNTS` (chỉ chứa các máy STT 1–39/80 của cụm Kibe). Khi gọi cho máy thuộc cụm Admin (201–280), `resolve_device` không tìm thấy và crash ngay trước khi kết nối ADB.

### Giải pháp Chuẩn Hóa: Fallback sang `TARGET_INVENTORY_WORKBOOK`
Trong `tiktok_login_v1.py`, hàm `resolve_device(stt)` được nâng cấp:
1. Tra cứu `ACCOUNTS` trước (tương thích ngược với cụm Kibe).
2. Nếu không tìm thấy hoặc `device` rỗng, fallback sang `load_machine_devices(TARGET_INVENTORY_WORKBOOK)` (`taikhoan_run_safe.xlsx` hoặc workbook mapping theo host).
3. Nếu vẫn không thấy mới raise `RuntimeError`.

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

## 2. Bắt Buộc Cấu Hình `ADB_SERVER_SOCKET` Khi Chạy Độc Lập Trên Cụm Admin

### Triệu chứng:
```text
[device-lock] VPN GATE BLOCKED: device is offline or ADB/USB disconnected for ce0516052b95322202: device offline or ADB/USB disconnected: adb.exe: device 'ce0516052b95322202' not found
```
Script `tiktok_login_v1.py` sử dụng Xiaowei ADB (`C:\Program Files (x86)\xiaowei\tools\adb.exe`). Mặc định adb client sẽ nối tới `localhost:5037`. Trên host điều phối, các thiết bị cụm Admin được quản lý qua ADB server trên host remote `192.168.110.119:5037`.

### Lệnh Canonical Bắt Buộc:
```bash
ADB_SERVER_SOCKET="tcp:192.168.110.119:5037" \
TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml" \
python -u D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <target_id_or_email> --ss
```

---

## 3. Kiến Trúc "Single-Active Session" & Trung Tâm "One-Tap Login" Trên TikTok v46.x (Android 8)

### Thắc mắc & Hiểu lầm phổ biến:
*"Tại sao đã đăng nhập 2 tài khoản rồi mà Account Switcher ở Profile vẫn không bung ra, Settings cũng không có mục 'Chuyển đổi tài khoản', mà lại rơi vào màn hình 'Chào mừng bạn trở lại'?"*

### Cơ chế thực nghiệm trên Samsung Galaxy S7 (v46.6.3):
1. **Không có Switcher Dropdown khi chưa đủ liên kết sâu**:
   - Khi app TikTok trên thiết bị mới chỉ có 1-2 tài khoản và chưa hình thành multi-account session liên kết ở tầng runtime, TikTok **ẩn hoàn toàn nút dropdown (chevron ▼)** trên Profile (tên hiển thị `sv6` chỉ là plain text).
   - Trong menu *Cài đặt và quyền riêng tư*, ở đáy danh sách **chỉ có nút "Đăng xuất"**, hoàn toàn không render mục *"Chuyển đổi tài khoản"*.
2. **Màn hình "Chào mừng bạn trở lại" (One-Tap Hub) là bộ chuyển đổi tài khoản**:
   - Khi bấm "Đăng xuất" từ nick active hiện tại, TikTok **không hề xóa phiên**. Cả 2 tài khoản (ví dụ `bongbong02892` và `letam2502`) được lưu trữ an toàn trong KeyStore/One-tap session.
   - Khi vào lại Profile từ trạng thái này, app hiện màn hình *"Chào mừng bạn trở lại"*:
     - Chạm vào nick nào -> App kích hoạt lại phiên của nick đó trong 1-2s (không cần nhập lại mật khẩu hay OTP).
     - Muốn thêm tài khoản mới -> Bấm nút *"Thêm tài khoản khác"* hoặc *"Bạn không có tài khoản? Đăng ký"* ở đáy màn hình One-tap này.
3. **Kỷ luật Re-Login Trước khi Reg Bù (User Directive)**:
   - Nếu máy có dấu hiệu bị văng phiên (Account Switcher đơ / profile rỗng), **CẤM** cố ép chạy script reg tài khoản mới ngay.
   - BẮT BUỘC thực hiện kiểm tra và khôi phục (re-login) các nick cũ trước để đưa ít nhất 1 nick về trạng thái active sạch, sau đó mới tiến hành reg tài khoản cho slot còn thiếu.
