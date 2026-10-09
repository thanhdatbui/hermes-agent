# Samsung S7 Security Code Automation via Device Lock for Google OAuth & Sign-in

## 1. Mục đích & Bối cảnh
Khi đăng nhập Google hoặc cấp quyền OAuth Antigravity / Codex trên GPMLogin (Chrome Core 142), Google thường yêu cầu xác minh bảo mật nâng cao đối với tài khoản gắn trên thiết bị thật (Galaxy S7):
- `challenge/ootp`: Google yêu cầu nhập mã bảo mật ngoại tuyến (Security Code) 10 chữ số từ thiết bị Android.
- `challenge/dp`: Google gửi prompt về thiết bị, sau khi bấm *"Cách xác minh khác"* / *"Thử cách khác"* sẽ chuyển sang chọn *"Mã bảo mật"*.

Kỹ thuật này tự động hóa 100% việc lấy mã 10 số từ Samsung Galaxy S7 thông qua ADB + ATX-Agent (port 7912) kết hợp `acquire_device_lock` để chống xung đột với các cron job nuôi nick/TikTok farm đang chạy.

---

## 2. Chuẩn Hóa Device Lock & Đánh Thức S7

### Khóa thiết bị bắt buộc:
```python
import sys
sys.path.insert(0, r"D:\Taadaa\automation-core\src")
from automation_core.device_lock import acquire_device_lock

with acquire_device_lock(
    machine=str(machine_id),
    serial=serial,
    project="gpm-login",
    bypass_proxy_readiness=True,
    force_preempt=True
) as lease:
    # Thực hiện thao tác ADB
    # LƯU Ý: Đối tượng `DeviceLockLease` sở hữu thuộc tính `lease.lock_paths` (list),
    # TUYỆT ĐỐI KHÔNG gọi `lease.lock_path` (sẽ ném AttributeError).
```
- `force_preempt=True`: Vượt qua stale locks nếu phiên trước bị gián đoạn.
- `bypass_proxy_readiness=True`: Không bắt buộc VPN/Proxy S7 phải rảnh vì thao tác lấy mã hoàn toàn là offline cục bộ trong Google Play Services.
- **Tra cứu Serial/Proxy chuẩn farm**:
  Sử dụng `automation_core.preflight.resolve_proxy_mapping_path()` để đọc `PROXYgandienthoai.xlsx` (Sheet `Proxy`, Col 0: `Máy`, Col 1: `device ID` / serial, Col 2: `proXy`).
  Profile GPM thường đặt tên theo cấu trúc `{mid} - {email} - {proxy_port}`, dùng regex `r"^(\d+)\s*-\s*"` để trích xuất `machine_id`.
- **Cổng forward ATX chuẩn**:
  Áp dụng quy ước `tcp:{17000+mid}` -> `tcp:7912` (M10 -> 17010, M55 -> 17055). Thiết lập bằng `adb -s <serial> forward tcp:{17000+mid} tcp:7912`.
  Dump UI siêu tốc qua `GET http://127.0.0.1:{17000+mid}/dump/hierarchy` (trả về JSON có field `"result"` chứa XML).
- **Phát hiện ADB Transport Stalled**:
  Trước khi dump hoặc mở intent, luôn kiểm tra `adb -s <serial> shell echo ok` với timeout bounded 5s. Nếu timeout (như M68 dính transport stall), fail-closed hoặc báo lỗi chụp ảnh thay vì để request treo 900s.

### Đánh thức màn hình & mở khóa (Keyguard):
```python
# Đánh thức màn hình tránh tình trạng màn hình tắt/khóa
subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP"], capture_output=True, timeout=5)
subprocess.run([ADB_EXE, "-s", serial, "shell", "wm", "dismiss-keyguard"], capture_output=True, timeout=5)
# Vuốt mở khóa màn hình
subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "swipe", "500", "1500", "500", "500"], capture_output=True, timeout=5)
```

---

## 3. Quy Trình Điều Hướng UI Google Play Services Mới (2026 UI)

Khởi chạy intent trực tiếp:
```bash
adb -s <SERIAL> shell am start -n com.google.android.gms/.app.settings.GoogleSettingsLink
```

### Chi tiết luồng UI (ATX XML Hierarchy - Samsung S7 Android 7):
1. **Kiểm tra Account Active:** Đọc text email trên màn hình Google Settings.
2. **Đổi Tài Khoản:** Nếu tài khoản hiển thị khác `target_email`:
   - Nút Switcher chuẩn trên S7: Node có `content-desc="chuyển đổi tài khoản"` (hoặc `"Switch account"`) tại đỉnh màn hình (`bounds=[924,108][1044,228]`), hoặc avatar/email switcher.
   - Khi tap vào, một bottom-sheet / dialog hiển thị danh sách toàn bộ email trên máy xuất hiện.
   - Quét tìm node có text chứa `target_email` và click chọn.
3. **Bỏ Qua Onboarding Popups (nếu có):**
   - Nếu xuất hiện dialog *"Đừng để bị mất quyền truy cập vào Tài khoản Google của bạn"*, tìm và tap nút *"Bỏ qua"* (bounds x=[810,948], y=[967,1027]) để hiển thị đầy đủ danh mục cài đặt.
4. **Mở Quản lý Tài Khoản:**
   - Tap vào nút **"Tài khoản Google"** (`content-desc="Tài khoản Google"` hoặc `text="Tài khoản Google"`).
5. **Vào Mục Bảo Mật (Security):**
   - Tìm mục **"Bảo mật và đăng nhập"** hoặc tab **"Bảo mật"** (`Security`).
   - Nếu chưa thấy: vuốt cuộn màn hình (`input swipe 500 1500 500 500 300`).
6. **Vào Mã Bảo Mật (Security Code):**
   - Vuốt cuộn màn hình tìm node text / desc chứa `"mã bảo mật"` hoặc `"security code"` và tap vào.
7. **Trích xuất mã 10 số:**
   - Tìm các text có định dạng số (loại bỏ khoảng trắng và ký tự định dạng Unicode `\u202d`).
   - Lấy 10 chữ số đầu tiên (`cleaned[:10]`).
8. **Dọn dẹp (BẮT BUỘC trong `finally`):**
   - Gửi `input keyevent 3` (HOME) để đưa màn hình S7 về trang chủ trước khi nhả Device Lock.

---

## 4. Hàm Chuẩn Triển Khai (`get_s7_security_code`)

```python
def parse_bounds(b_str: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    if not b_str: return None, None
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b_str)
    if not m: return None, None
    return (int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2

def get_s7_security_code(machine_id: int, serial: str, target_email: str) -> Optional[str]:
    if not serial: return None
    logger.info(f"[M{machine_id:02d}] Acquiring device lock on {serial} to fetch Security Code...")
    try:
        with acquire_device_lock(
            machine=str(machine_id),
            serial=serial,
            project="gpm-login",
            bypass_proxy_readiness=True,
            force_preempt=True
        ):
            atx_port = 17000 + machine_id
            subprocess.run([ADB_EXE, "-s", serial, "forward", f"tcp:{atx_port}", "tcp:7912"], capture_output=True, timeout=5)
            time.sleep(0.5)

            def dump_ui():
                for _ in range(3):
                    try:
                        r = requests.get(f"http://127.0.0.1:{atx_port}/dump/hierarchy", timeout=4)
                        if r.status_code == 200 and r.json().get("result"):
                            return ET.fromstring(r.json()["result"])
                    except Exception:
                        time.sleep(0.4)
                return None

            try:
                subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP"], capture_output=True, timeout=5)
                subprocess.run([ADB_EXE, "-s", serial, "shell", "wm", "dismiss-keyguard"], capture_output=True, timeout=5)
                subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "swipe", "500", "1500", "500", "500"], capture_output=True, timeout=5)
                subprocess.run([ADB_EXE, "-s", serial, "shell", "am", "start", "-n", "com.google.android.gms/.app.settings.GoogleSettingsLink"], capture_output=True, timeout=5)
                time.sleep(2.0)

                # 1. Switch target account if needed
                root = dump_ui()
                if root is not None:
                    for node in root.iter("node"):
                        t = node.attrib.get("text", "")
                        if "@gmail.com" in t.lower() and target_email.lower() not in t.lower():
                            x, y = parse_bounds(node.attrib.get("bounds"))
                            if x and y:
                                subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "tap", str(x), str(y)], capture_output=True, timeout=5)
                                time.sleep(1.5)
                                picker = dump_ui()
                                if picker:
                                    for pn in picker.iter("node"):
                                        if target_email.lower() in pn.attrib.get("text", "").lower():
                                            tx, ty = parse_bounds(pn.attrib.get("bounds"))
                                            if tx and ty:
                                                subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "tap", str(tx), str(ty)], capture_output=True, timeout=5)
                                                time.sleep(2.0)
                                                break
                                break

                # 2. Tap Google Account
                root = dump_ui()
                if root is not None:
                    for node in root.iter("node"):
                        t = node.attrib.get("text", "").lower()
                        if any(k in t for k in ["tài khoản google", "google account"]):
                            x, y = parse_bounds(node.attrib.get("bounds"))
                            if x and y:
                                subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "tap", str(x), str(y)], capture_output=True, timeout=5)
                                time.sleep(2.0)
                                break

                # 3. Tap Security tab
                root = dump_ui()
                if root is not None:
                    for node in root.iter("node"):
                        t = node.attrib.get("text", "").lower()
                        if any(k in t for k in ["bảo mật", "security"]):
                            x, y = parse_bounds(node.attrib.get("bounds"))
                            if x and y:
                                subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "tap", str(x), str(y)], capture_output=True, timeout=5)
                                time.sleep(1.5)
                                break

                # 4. Find and tap Security Code
                for _ in range(3):
                    root = dump_ui()
                    if root is not None:
                        found = False
                        for node in root.iter("node"):
                            t = (node.attrib.get("text", "") + " " + node.attrib.get("content-desc", "")).lower()
                            if any(k in t for k in ["mã bảo mật", "security code"]):
                                x, y = parse_bounds(node.attrib.get("bounds"))
                                if x and y:
                                    subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "tap", str(x), str(y)], capture_output=True, timeout=5)
                                    time.sleep(2.0)
                                    found = True
                                    break
                        if found: break
                    subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "swipe", "960", "800", "960", "300"], capture_output=True, timeout=5)
                    time.sleep(0.7)

                # 5. Extract 10-digit code
                root = dump_ui()
                if root is not None:
                    for node in root.iter("node"):
                        t = node.attrib.get("text", "").replace("\u202d", "").replace(" ", "")
                        cleaned = re.sub(r"\D", "", t)
                        if len(cleaned) >= 10:
                            code = cleaned[:10]
                            logger.info(f"[M{machine_id:02d}] Extracted Security Code: {code}")
                            return code
            finally:
                subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "3"], capture_output=True, timeout=5)
    except Exception as e:
        logger.error(f"[M{machine_id:02d}] S7 Error: {e}")
    return None
```

---

## 5. Tích Hợp Vào Flow OAuth OmniRoute (`add_oauth_omniroute.py`)

Khi tự động hóa OAuth Antigravity trên trình duyệt GPM:
1. **Bắt Challenge:** Khi URL chuyển thành `challenge/ootp` hoặc input có name `Pin` / `totpPin` nhưng không có secret TOTP hoặc Google từ chối TOTP, hoặc màn hình `challenge/selection` có phương thức "Mã bảo mật".
2. **Tra cứu S7 Mapping từ `master_gmail_manager.xlsx` (Sheet `Kibe_Farm_S7`):**
   - Đọc Cột 1: `Email`
   - Đọc Cột 7: `Số Máy Farm` (ví dụ `"Máy 10"` -> dùng `re.search(r"(\d+)", ...)` trích xuất `machine_id = 10`)
   - Đọc Cột 9: `Serial Thiết Bị (Device ID)` (ví dụ `"988627464e374e3234"`)
   - Đọc Cột 11: `Tên Profile GPM` (ví dụ `"10 - thachnha1103199810@gmail.com - 5112"`)
   - Đối chiếu với SQLite `profile_data.db` của GPM qua `ProfilePath` (chứa suffix `-05092026`) hoặc `Name` profile.
3. **Lấy Mã & Điền:** Gọi `get_s7_security_code` lấy mã 10 số, điền vào ô input và nhấn Enter.
   - *Bảo vệ TypeError*: Luôn kiểm tra `if not xml: return None` trước khi gọi `ET.fromstring(xml)` để tránh văng `TypeError: a bytes-like object is required, not 'NoneType'` khi ATX capture trả về None lúc giao diện đang chuyển tiếp.
4. **Exchange & Gán Proxy 1:1:** Sau khi bắt được callback code:
   - Gửi code lên `POST /api/oauth/antigravity/exchange`.
   - Tìm proxy registry ID có port khớp với proxy profile GPM (`5101..5138`).
   - Gán proxy qua `PUT /api/settings/proxies/assignments` với `{"scope": "account", "scopeId": connection_id, "proxyId": proxy_id}`.
   - Kích hoạt model catalog qua `POST /api/providers/{connection_id}/sync-models`.
