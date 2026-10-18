# Farm Network Gate: Production Implementation & Review Audit (18/10/2026)

## 1. Tổng Quan Kiến Trúc `farm_network_gate.py`

File thực thi chuẩn tắc duy nhất: `D:/Taadaa/tools/farm_network_gate.py`.
Khắc phục triệt để lỗi nạp nhầm mật khẩu Wi-Fi, lệnh ad-hoc không bọc device lock, và rò rỉ secret trên Taadaa Farm.

### Các thành phần cốt lõi:
1. **SSOT File:** `D:/Taadaa/machine-config/farm_wifi_profiles.json` (dải máy `min-max`, `ssid`, `password`, `proxy_port_base`).
2. **`load_and_validate_profiles(path=None)`:**
   - Kiểm tra cấu trúc danh sách không rỗng, đủ các trường bắt buộc (`min`, `max`, `ssid`, `password`).
   - Sắp xếp và đối soát từng cặp dải liền kề để phát hiện chồng lấn range (`WIFI_PROFILE_RANGE_OVERLAP`).
   - Tính toán SHA-256 của file cấu hình để gắn vào telemetry/evidence.
   - Biên dịch sẵn từ điển tra cứu $O(1)$ theo `machine_id`.
3. **`resolve_network(machine_id: int)`:**
   - Tra cứu $O(1)$ không cho phép caller truyền tham số SSID/password tự do.
   - Nhận diện các ngoại lệ direct (M67, M69) với port proxy `:0` và cờ `direct=True`.
   - Máy nằm ngoài dải hợp lệ lập tức ném lỗi `WIFI_PROFILE_UNRESOLVED`.
4. **`apply_profile(machine_id: int, serial: str = None, force_preempt: bool = False)`:**
   - Thẩm định đối soát Target Serial Provenance với `taikhoan_run_safe.xlsx`.
   - Kiểm tra tính lũy đẳng: nếu live state đã khớp SSID, subnet IPv4 và proxy mở thì trả về `NOOP_HEALTHY` mà không ngắt kết nối.
   - Bọc toàn bộ thao tác trong `operator_device_lock(machine=N, serial=serial, force_preempt=force_preempt)`.
   - Chẩn đoán 1 chiều L2 -> L3 -> L4 fail-closed.

---

## 2. Nhật Ký 3 Vấn Đề Chặn Duyệt Được Claude Reviewer Phê Chuẩn

Trong vòng thẩm định độc lập đầu tiên, Claude Reviewer đã đưa ra phán quyết `REJECTED` với 3 lỗi chặn duyệt. Cả 3 lỗi đã được khắc phục hoàn toàn ở vòng 2 (`VERDICT: APPROVED`):

### Vấn đề 1: Rò rỉ mật khẩu qua TimeoutExpired / Traceback
- **Lỗ hổng:** `am start` mang theo `--es password <pass>`. Khi lệnh bị timeout hoặc ném lỗi OS, chuỗi traceback mặc định in mảng argv trần ra stderr/console.
- **Giải pháp:**
  - Bọc hàm `_adb` và `_adb_shell` bằng khối try/except riêng biệt, bắt `TimeoutExpired` và `Exception` rồi ném lại ngoại lệ an toàn `AdbCommandError("ADB_TIMEOUT")` hoặc `AdbCommandError("ADB_ERROR:<Type>")` với cú pháp `from None` để triệt tiêu context mang secret.
  - Hàm `main()` bọc try/except toàn cục, chỉ in thông điệp lỗi sạch, tuyệt đối không xuất traceback trần ra console.

### Vấn đề 2: Vi phạm Target Serial Provenance & CLI thô sơ
- **Lỗ hổng:** Caller truyền `serial` tùy tiện được tin dùng ngay mà không đối chiếu với sổ cái. CLI quét `sys.argv` thủ công khiến các cờ lạ bị nhận nhầm thành serial.
- **Giải pháp:**
  - Luôn resolve `workbook_serial` từ `taikhoan_run_safe.xlsx` trước. Nếu caller truyền `serial != None`, bắt buộc so khớp `caller_serial == workbook_serial`, nếu lệch ném ngay `ValueError("MACHINE_SERIAL_MISMATCH")` trước khi đụng vào ADB hoặc Device Lock.
  - Dùng `argparse.ArgumentParser` chuẩn hóa giao diện dòng lệnh, từ chối mọi cờ lạ với exit code 2.

### Vấn đề 3: False Positive L2 `AUTH_FAIL` do lịch sử cũ trong dumpsys
- **Lỗ hổng:** Quét thô bạo toàn bộ `dumpsys wifi` với các marker `wrong_key`, `disabled_authentication` sẽ bị dính cờ lỗi cũ của các mạng Wi-Fi đã lưu từ trước.
- **Giải pháp:**
  - Hàm `_auth_fail_for_ssid(serial, target_ssid)` chia dump thành các khối ngăn cách bởi dòng trống.
  - Chỉ tính là lỗi xác thực nếu khối đó chứa marker lỗi VÀ đích danh nhắc tới `target_ssid` mà không chứa bất kỳ SSID lạ nào khác.

---

## 3. Nghiệm Thu Thực Tế (Evidence Matrix)

1. **Bộ Test Suite Offline (`tests/test_farm_network_gate.py`):**
   - Đạt **40/40 tests PASSED trong 0.82s** (100% mocked offline, không phụ thuộc phần cứng).
   - Bao phủ toàn diện: SSOT validation, range overlap, missing fields, M7 kibe 1, M44 kibe 2, M67/69 direct, machine unresolved, idempotency noop, force_preempt, L2 auth fail cấm retry, L3 no IP, L4 proxy down, `CREATE_NO_WINDOW`, sanitized password, serial mismatch check, CLI argparse validation, ping wlan0 interface, fallback gateway TCP probe, captive portal pre-disablement, block-scoped auth failure isolation.

2. **Canary trên Thiết Bị Thật & Post-Review Quirks Fixed:**
   - **Máy 6 (Máy đang chạy ổn định):**
     `python D:/Taadaa/tools/farm_network_gate.py 6`
     $\rightarrow$ `{"status": "NOOP_HEALTHY", "machine": 6, "ssid": "kibe 1", "proxy": "192.168.110.2:20006"}`
     *Xác nhận: Không làm gián đoạn phiên nuôi và worker đang chạy.*
   - **Pre-Join Hygiene & Routing Latency Fixes:**
     * *Pre-join Proxy Flush:* Xóa sạch proxy cũ (`settings put global http_proxy :0`) và tắt captive portal trước khi join, tránh bẫy Android định tuyến gói tin kiểm tra mạng qua proxy chết làm rớt kết nối Wi-Fi liên tục.
     * *Lifecycle adbjoinwifi:* Bỏ cờ `-S` (không force-stop app) và không bấm Home (`keyevent 3`) sớm; chỉ đưa app về Home ở cuối toàn bộ quy trình `apply_profile`.
     * *Routing Mount Latency:* Bọc kiểm tra gateway bằng `_wait_for_gateway(serial, net, attempts=6, interval=2.0)` để chờ kernel mount default route sau khi nhận DHCP lease.
   - **Máy 7 (Hiện trường sự cố):**
     `python D:/Taadaa/tools/farm_network_gate.py 7 --force-preempt`
     *Xác nhận: Tầng L2 đã kết nối thành công kibe 1 với pass 23102025 (`state UP`, `NETWORK_SELECTION_ENABLED`); 0 log lỗi MIC trên AP Aruba.*
