# ADB Transport Two-Phase Healing & Infrastructure Watchdog Standards

## 1. Kỷ Luật Nâng Cấp Watchdog Hạ Tầng (Chống Phân Mảnh)
- Khi gặp sự cố thiết bị offline, kẹt socket ADB transport, hoặc lỗi stream XiaoWei/JiWei: **TUYỆT ĐỐI CẤM tự ý tạo script cứu hộ mới độc lập**.
- Hệ thống đã có sẵn cronjob hạ tầng **`farm-adb-transport-healer`** (Job ID: `121a95f18996`, chạy mỗi 3 phút `*/3 * * * *`, kịch bản: `farm_adb_transport_auto_healer.py`). Mọi cải tiến hoặc sửa lỗi BẮT BUỘC thực hiện trực tiếp trên kịch bản này.
- Khi cập nhật `farm_adb_transport_auto_healer.py`, bắt buộc đồng bộ song song:
  * Bản chạy chính: `C:\Users\Kibe\AppData\Local\hermes\scripts\farm_adb_transport_auto_healer.py`
  * Bản đồng bộ OneDrive: `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\farm_adb_transport_auto_healer.py`
  * Bản deploy repo: `D:\Taadaa\Hermes\deploy\hermes-home\scripts\farm_adb_transport_auto_healer.py`

## 2. Ưu Tiên Đường Dẫn ADB XiaoWei (Chống Lệch Phiên Bản)
- Trên host Kibe, phần mềm chiếu màn hình XiaoWei chiếm giữ server socket port 5037 bằng binary riêng tại `C:\Program Files (x86)\xiaowei\tools\adb.exe` (ADB v34.0.1).
- Nếu script healer hoặc client ưu tiên binary khác (như GemPhoneFarm ADB v35.0.1), client sẽ gửi các bản tin handshake không tương thích hoặc gây restart daemon ngầm, làm rớt stream hàng loạt máy.
- **Quy tắc bắt buộc:** `ADB_KIBE` trong mọi script watchdog phải ưu tiên:
  ```python
  ADB_KIBE = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
  if not os.path.exists(ADB_KIBE):
      ADB_KIBE = r"C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe"
  ```

## 3. Two-Phase Verification Invariant (Chống Báo Cáo Ảo "Cứu Sống")
- **Bẫy Báo Cáo Ảo Cũ:** Gọi `adb reconnect offline` hoặc `reconnect` rồi lập tức ghi nhận `healed_list.append(...)` mà không kiểm tra lại hiện trường thực tế. Khi gặp lỗi phần cứng Hub USB (`Port Reset Failed`), watchdog cứ 3 phút lại in báo cáo giả "Đã cứu sống N thiết bị".
- **Cơ Chế Chuẩn Hai Pha (Two-Phase Verification):**
  1. **Phase 1 (Act):** Phát lệnh phục hồi nguyên tử (`reconnect offline` hoặc `reconnect` + `keyevent 224` wake screen).
  2. **Phase 2 (Verify):**
     * Đối với máy offline: Chờ 1.0s, quét lại `adb devices`. CHỈ KHI serial có trong danh sách và trạng thái là `device` mới được ghi nhận `healed`.
     * Đối với máy HUNG: Phát lệnh ping `echo 1` qua ADB shell (timeout 2.5s). CHỈ KHI stdout trả về `"1"` mới được xác nhận `healed`.
  3. **Fail-Safe & Silent Watchdog:** Nếu sau khi reconnect thiết bị vẫn `offline`, script không được thêm vào `healed_list`. Toàn bộ `stdout` giữ rỗng 100% khi không có máy nào được cứu sống thực sự.

## 4. Triage Phân Biệt Lỗi Phần Mềm vs Lỗi Phần Cứng Hub USB
- **Lỗi Phần Mềm (Tự Cứu Được):** `adb devices` báo `offline` do desync daemon, hoặc `device` nhưng shell timeout > 2.5s. Lệnh `adb reconnect` giải phóng được socket và đưa máy về bình thường.
- **Lỗi Phần Cứng (Cần Thao Tác Vật Lý):**
  * Windows Device Manager / PnP báo `Unknown USB Device (Port Reset Failed)`, `Configuration Descriptor Request Failed`, hoặc `Device Descriptor Request Failed`.
  * Sau `adb reconnect offline`, máy vẫn trơ ra `offline`.
  * **Hành động:** Chuyển L3 BLOCKED, thông báo rõ vị trí Hub USB cần tắt/bật lại nguồn hoặc rút cắm lại cáp uplink USB.
