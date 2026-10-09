# ATX Session Dump via Device-Local Curl (Remote ADB / Dual Cluster)

## 1. Vấn đề với Remote ADB Server (Admin Cluster M201-M280)
- Khi chạy script từ Kibe điều khiển cụm Admin qua remote ADB daemon (`adb -H 192.168.110.119 -P 5037`):
  - Lệnh `adb forward tcp:0 tcp:7912` chỉ bind vào loopback `127.0.0.1` của máy Admin.
  - Windows Firewall phía máy remote thường block inbound các port động (50000+).
  - Client phía Kibe gọi `http://192.168.110.119:<port>/dump/hierarchy` hoặc `/session/<pid>.../jsonrpc/0` sẽ bị timeout/connection refused 100%, gây lỗi hàng loạt `ATX_SESSION_UNAVAILABLE`.

## 2. Giải pháp: Device-Local `atx-agent curl`
`atx-agent` tích hợp sẵn CLI `curl` ngay bên trong máy Android (`/data/local/tmp/atx-agent curl`).
Có thể gọi trực tiếp thông qua `adb.shell()` mà không cần tạo forward port TCP qua mạng LAN:

```bash
/data/local/tmp/atx-agent curl -X POST --data='{"jsonrpc":"2.0","id":"automation-core-ui-dump","method":"dumpWindowHierarchy","params":[true]}' http://127.0.0.1:7912/session/<pid>:com.github.uiautomator/jsonrpc/0
```
- Trả về toàn bộ cây UI XML hierarchy trong **< 0.5s**, hoàn toàn độc lập và không cần mở port forward TCP qua mạng LAN giữa Coordinator và Worker host!

## 3. Pitfalls & Kỹ thuật Xử lý (Invariant)
1. **Single-Quote Bắt Buộc Cho Body Data**:
   - Khi truyền json trong `--data=`, bắt buộc phải bọc bằng single quotes: `--data='{"jsonrpc":"2.0",...}'`.
   - Bắt buộc dùng `json.dumps(payload, separators=(',', ':'))` để loại bỏ khoảng trắng. Nếu có khoảng trắng không bọc kỹ, parser flag của `atx-agent` sẽ báo lỗi:
     `flag 'data' cannot be repeated, try --help` hoặc `unexpected id:, try --help`.
2. **Đọc Combined Output (stdout + stderr)**:
   - `atx-agent curl` ghi log request và response payload ra `stderr` (e.g. `curl.go:116: {"jsonrpc":"2.0",...} <nil>`).
   - Parser phải gộp cả hai: `combined = (res.stdout or "") + "\n" + (res.stderr or "")`.
   - Tìm vị trí `curl.go:`, lấy chuỗi con phía sau, rồi trích xuất JSON giữa `{` và `}`.
3. **Bypass Port Forwarding Khi Host là Remote**:
   - Trong `_ensure_forward(adb)`: Nếu `_is_remote_host(adb)` (host khác `127.0.0.1`/`localhost`), không gọi `adb forward` mà trả về luôn `ATX_DEVICE_PORT` (7912) với forward type `device_direct_remote`.
4. **Host Resolution Trong `_resolve_host` (Dual-Cluster Safety)**:
   - Hàm `_resolve_host(adb)` trong `automation-core/persistent_ui.py` phải kiểm tra `adb.host` và `ADB_SERVER_SOCKET` / `ADB_HOST` TRƯỚC cache global `_ACTIVE_REQUEST_HOST` để tránh stale host khi chạy xen kẽ giữa các cụm Kibe và Admin.
5. **Fallback Flow 2 Lớp (Defense-in-depth)**:
   - Khi chạy ở máy local, gọi request HTTP thông thường trước. Nếu request gặp ngoại lệ hoặc timeout, tự động fallback sang `_request_via_device_curl` để đảm bảo không bao giờ rớt lệnh dump khi atx-agent vẫn sống trên thiết bị.
