# Bẫy Substring ':0' trong Watchdog Formatters & Bổ sung Phân Loại Device Lock (2026-10-18)

## 1. Hiện tượng & Phản xạ Sai Lầm của Agent
- **Hiện tượng**: Báo cáo nuôi feed watchdog (`tiktok-feed-session-watchdog`) gửi Telegram thông báo:
  ```
  + Fail (11): M7, M10, M14, M24, M28, M30, M31, M50, M69, M74, M80
    - Chưa gán Proxy / Proxy :0 (2): M7, M69
  ```
- **Sai lầm nghiêm trọng của Coordinator**:
  - Không truy xuất hiện trường log gốc, vội vã suy diễn: *"M69 chạy Direct theo đúng kiến trúc mạng của farm (không qua proxy 110.2)..."*
  - Operator phản ứng gắt và chuẩn xác: *"Là sao làm gì có máy nào chạy direct? Lỗi script nào thì fix đi"*.
  - **Bất biến tối cao của Farm**: Toàn bộ dàn máy Phone Farm (M1–80 Kibe, M201–280 Admin) 100% chạy qua Proxy LAN `192.168.110.2:port` (Sing-box 20001..20080 / MikroTik 10008..10035). Farm tuyệt đối KHÔNG cho phép bất kỳ máy nào chạy Direct ra ngoài để tránh Direct IP Leak.

## 2. Nguyên nhân Kỹ thuật Gốc rễ (Root Cause)
Kiểm tra hiện trường log thực tế tại `D:/Taadaa/runtime/kibe/live/2026-10-18/row-6-200005/20261018-200151`:
- **Máy 7**:
  - Stop reason: `device lock active: path=C:\Users\Kibe\.codex\device-locks\machine_7.lock.json pid=33868 host=DESKTOP-3PFPGQC project=farm_network_gate machine=7 serial=9885f63030454d3055 started_at=2026-10-18T13:00:30.916287+00:00 command=D:/Taadaa/tools/farm_network_gate.py 7 --force-preempt`
  - Hiện trường thiết bị: Proxy đang gán trên Android `settings get global http_proxy` là `192.168.110.2:20007` (hoàn toàn bình thường).
- **Máy 69**:
  - Stop reason: `required router proxy is unreachable for ce12160c386c913101 (kill switch active or no connection): global proxy (192.168.110.2:20069) egress IP verification failed: 2026/10/18 18:02:19 goreq.go:390: GET /ip HTTP/1.1`
  - Hiện trường thiết bị: Proxy đang gán trên Android `settings get global http_proxy` là `192.168.110.2:20069`. Cổng Sing-box 20069 lúc đó bị disconnect từ router / WinError 10054.

**Tại sao cả hai đều bị gom vào nhãn "Chưa gán Proxy / Proxy :0"?**
- Trong `D:/Taadaa/tiktok-luot nuoi acc/scripts/watchdog/formatters.py`, hàm `classify_feed_failure(reason)` có đoạn:
  ```python
  if any(k in r for k in ("missing or :0", "http_proxy is missing", ":0", "proxy is not set on device", "missing proxy", "no proxy")):
      return "Chưa gán Proxy / Proxy :0"
  ```
- Substring `":0"` là một chuỗi 2 ký tự cực kỳ phổ biến trong các timestamp `HH:MM:SS`:
  - `started_at=2026-10-18T13:00:30` chứa `":0"` (ở cả `13:00` và `:00:30`).
  - `2026/10/18 18:02:19` chứa `":0"` (ở `:02`).
- Do điều kiện `":0"` nằm ngay đầu trong nhánh kiểm tra proxy, nó khớp trúng toàn bộ các thông báo lỗi có chứa timestamp giờ/phút/giây có số 0 ở đầu!
- Đồng thời:
  1. `classify_feed_failure` hoàn toàn thiếu nhánh phân loại cho `device lock active` / `device-lock`.
  2. `classify_feed_failure` thiếu từ khóa `egress ip` trong nhóm `"Nghẽn đường truyền Proxy / 4G"`.

## 3. Quy tắc Sửa Đổi & Khắc Phục Chuẩn
1. **Loại bỏ chuỗi trần `":0"`**:
   Thay bằng token chuẩn xác:
   ```python
   if any(k in r for k in ("missing or :0", "http_proxy is missing", "empty_or_zero", "empty or zero", "proxy is not set on device", "missing proxy", "no proxy")):
       return "Chưa gán Proxy / Proxy :0"
   ```
2. **Bổ sung phân loại Device Lock lên trước kiểm tra Proxy**:
   ```python
   if any(k in r for k in ("device lock active", "device-lock", "skipped-device-locked", "device lock")):
       return "Kẹt Device Lock"
   ```
3. **Bổ sung `egress ip` vào nhóm Nghẽn đường truyền Proxy / 4G**:
   ```python
   if any(k in r for k in (
       "proxy is unreachable",
       "proxy readiness timed out",
       "connection refused",
       "context deadline exceeded",
       "proxy timeout",
       "network is unreachable",
       "egress ip",
   )):
       return "Nghẽn đường truyền Proxy / 4G"
   ```
4. **Kiểm tra hiện trường thiết bị bằng `inspect_machine.py`**:
   - Khi có nghi vấn máy mất proxy hoặc chạy direct, dùng ngay lệnh trích xuất O(1):
     `python D:/Taadaa/tools/inspect_machine.py <N>`
   - Script đã được bổ sung đọc `settings get global http_proxy`, cho kết quả ngay trong < 1 giây mà không cần quét đĩa hay adb thủ công.
