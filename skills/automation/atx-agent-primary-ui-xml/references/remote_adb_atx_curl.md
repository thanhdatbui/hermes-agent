# Remote ADB Host & Device-Local ATX Curl Pattern

## 1. Vấn đề kiến trúc Remote ADB (Admin Cluster / Multi-Host Setup)
Khi host điều phối kết nối tới một máy trạm chạy ADB Server từ xa (ví dụ Admin machine tại `192.168.110.119:5037`):
- Lệnh `adb forward tcp:0 tcp:7912` chạy qua remote ADB server chỉ bind port forward vào loopback nội bộ `127.0.0.1` của máy trạm đó.
- Windows Firewall trên máy trạm chặn inbound dynamic port (50000+) từ mạng LAN.
- Host điều phối cố gắng kết nối HTTP `urllib.request.urlopen("http://<remote_ip>:<forwarded_port>/...")` sẽ bị **Timeout 100% (3000ms)**.
- Khi timeout lặp lại và reset session thất bại, hệ thống ném ngoại lệ:
  `capture-invalid:ui_dump_error: ATX_SESSION_UNAVAILABLE` lan rộng trên toàn bộ thiết bị của cụm remote.

## 2. Giải pháp Đột phá: Device-Local `atx-agent curl`
`atx-agent` tích hợp sẵn CLI `curl` ngay bên trong file nhị phân tại thiết bị Android (`/data/local/tmp/atx-agent curl`).
Thay vì cố gắng forward port TCP qua mạng LAN giữa các PC, ta thực thi lệnh trực tiếp qua kênh `adb.shell()`:

```bash
/data/local/tmp/atx-agent curl -X POST --data='{"jsonrpc":"2.0","id":"...","method":"dumpWindowHierarchy","params":[true]}' http://127.0.0.1:7912/session/<pid>:com.github.uiautomator/jsonrpc/0
```

### Lợi ích:
- **Tốc độ:** Thực thi hoàn toàn nội bộ trên điện thoại, trả về XML cây UI đầy đủ trong **< 0.5 giây**.
- **Miễn nhiễm mạng:** Hoàn toàn bypass Windows Firewall, loopback binding của Remote ADB, NAT và xung đột port trên host.
- **An toàn bộ nhớ:** Kế thừa toàn bộ khả năng chống OOM-kill (Exit code 137) của uiautomator stub session.

## 3. Các bẫy kỹ thuật bắt buộc phải tránh (Crucial Pitfalls)

### Bẫy 1: Format cờ `--data` của atx-agent curl
- CLI của `atx-agent curl` viết bằng Go (`goreq`). Nếu payload có khoảng trắng không bọc hoặc định dạng sai, CLI sẽ báo lỗi:
  `atx-agent: error: unexpected id:, try --help` hoặc `flag 'data' cannot be repeated`.
- **Cách khắc phục:**
  1. Dùng `json.dumps(payload, separators=(',', ':'))` để loại bỏ khoảng trắng dư thừa.
  2. Bọc toàn bộ payload trong cặp nháy đơn: `--data='{...}'`.

### Bẫy 2: Output logging ra Stderr thay vì Stdout
- `atx-agent curl` in HTTP request trace và response body ra `stderr` (hoặc phân bổ giữa stdout và stderr) theo cấu trúc:
  ```text
  2026/09/23 13:21:20 goreq.go:390: POST ...
  2026/09/23 13:21:20 curl.go:116: {"jsonrpc":"2.0","id":"test","result":"<?xml ..."} <nil>
  ```
- **Cách khắc phục:**
  1. Gộp cả stdout và stderr: `combined = (res.stdout or "") + "\n" + (res.stderr or "")`.
  2. Tìm mốc log `curl.go:`.
  3. Cắt chuỗi JSON từ vị trí `{` đầu tiên đến `}` cuối cùng và parse bằng `json.loads()`.

### Bẫy 3: Kiểm tra Exit Code & Telemetry
- Trước khi parse output, bắt buộc kiểm tra `res.exit_code == 0`. Nếu khác 0, log debug thời gian chạy `elapsed_ms` và trả về `None` ngay, tránh parse rác.
- Ghi nhận `entry["transport_mode"] = "device_curl"` hoặc `entry["transport_mode"] = "http_fallback_to_device_curl"` kèm `fallback_trigger` để phục vụ quan sát hệ thống (Observability).

### Bẫy 4: Precedence phân giải Host trong `_resolve_host`
- Trong môi trường multi-cluster (Kibe local `127.0.0.1` vs Admin remote `192.168.110.119`), hàm `_resolve_host(adb)` PHẢI ưu tiên:
  1. `getattr(adb, "host", None)`
  2. `os.environ.get("ADB_HOST")` hoặc `os.environ.get("ADB_SERVER_SOCKET")`
  3. Biến cache toàn cục `_ACTIVE_REQUEST_HOST`
  4. Mặc định `127.0.0.1`
- Nếu kiểm tra cache toàn cục trước `adb.host`, host của một phiên chạy local trước đó sẽ rò rỉ sang phiên remote, gây sai lệch nghiêm trọng.
