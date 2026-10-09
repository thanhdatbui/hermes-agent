# Quy Trình Đóng Site Cloud (mikrotik-tool.pages.dev) & Khóa Chặt WAN REST API MikroTik

> **Ngày cập nhật:** 2026-09-12  
> **Áp dụng:** Router MikroTik x86 (192.168.110.2), Web Manager Kibe (port 2310), Tailscale MagicDNS.

---

## 1. Bối Cảnh & Lý Do Bắt Buộc Đóng Site Cloud

Trước đây, hệ thống sử dụng:
- **Frontend:** `https://mikrotik-tool.pages.dev` (Cloudflare Pages).
- **Backend:** `https://mikrotik-control.thanhdatbui1995.workers.dev` (Cloudflare Worker).

### Các Lỗ Hổng & Rủi Ro Nghiêm Trọng Của Site Cloud:
1. **Lỗ hổng xác thực Client-side:**
   - Password đăng nhập lưu trong `localStorage` và kiểm tra bằng JavaScript client (`DEFAULT_WEB_PASS = 'n0spam@@'`).
   - Bất kỳ ai mở F12/Source đều thấy mật khẩu hoặc có thể gọi trực tiếp API vào Worker URL mà không cần qua web.
2. **Nguy cơ phơi nhiễm REST API ra Internet:**
   - Để Cloudflare Worker gọi được vào router, RouterOS bắt buộc phải mở port `9090` trên WAN (`mirotik1.taadaa.click:9090`), dẫn đến việc hàng nghìn botnet/scanner liên tục quét cổng và thử brute-force.
3. **Xung đột lịch chạy (Schedule Race Conditions):**
   - Khi cả Cloudflare Worker và local `server.py` (`schedules.json`) cùng cấu hình tự động đổi IP, hai bên sẽ kích re-dial trùng nhau làm gián đoạn proxy khi farm đang feed/reg TikTok.

---

## 2. Giải Pháp Chuẩn Hóa: `kibe:2310` (Local + Tailscale)

Hạ tầng đã thống nhất chuyển 100% sang **MikroTik Web Manager**:
- **Source:** `D:\Taadaa\AI-Tools\tools\mikrotik_web\server.py`
- **Launcher ngầm:** `run_hidden.vbs` (chạy qua `pythonw.exe`, không hiện console).
- **Cổng dịch vụ:** `2310` (`ThreadingHTTPServer`).
- **Truy cập nội bộ:** `http://localhost:2310` (PC Kibe).
- **Truy cập từ xa / Mobile:** `http://kibe:2310` qua Tailscale MagicDNS.
- **Bảo mật tuyệt đối:** Whitelist IP cứng trong code (`ALLOWED_IPS` gồm `192.168.110.x`, `100.x` Tailscale CGNAT, `127.0.0.1`), chặn đứng 100% truy cập từ Internet.

---

## 3. Các Bước Đóng Kênh WAN Trên RouterOS (O(1) REST API)

### Bước 1: Khóa chặt Port 9090 (REST API) chỉ cho phép `FPT_LAN`
Lệnh PATCH qua REST API RouterOS:
```http
PATCH http://192.168.110.2:9090/rest/ip/firewall/filter/*3
Authorization: Basic YWRtaW46TjBzcGFtQEA=
Content-Type: application/json

{
  "src-address-list": "FPT_LAN",
  "comment": "REST API internal (FPT_LAN only)"
}
```
*Tác dụng:* Chỉ cho phép `192.168.110.0/24` (máy Kibe, máy Admin), `192.168.10.0/24`, `127.0.0.1`, `172.17.0.0/16` kết nối vào REST API port 9090. Cloudflare Worker và botnet ngoài WAN bị ngắt kết nối ngay lập tức.

### Bước 2: Tắt Rule DST-NAT Cũ Forward Port Web từ WAN
```http
PATCH http://192.168.110.2:9090/rest/ip/firewall/nat/*316
Authorization: Basic YWRtaW46TjBzcGFtQEA=
Content-Type: application/json

{
  "disabled": true
}
```
*Tác dụng:* Hủy bỏ rule NAT forward port `8090` từ `pppoe-out1` vào PC Kibe `192.168.110.123`.

---

## 4. Kiểm Chứng Sau Khi Đóng (Verification)

1. **Kiểm tra truy cập nội bộ `kibe:2310`:**
   ```bash
   curl -s http://localhost:2310/api/status
   # Kết quả: {"connected": true, "version": "7.18.2 (stable)", ...}
   ```
2. **Kiểm tra ngắt kết nối Cloudflare Worker:**
   ```bash
   curl -s --connect-timeout 8 "https://mikrotik-control.thanhdatbui1995.workers.dev/api/ip"
   # Kết quả: Timeout hoặc lỗi kết nối về router
   ```
3. **Cập nhật tài liệu dự án:**
   Xóa bỏ link `https://mikrotik-tool.pages.dev` trong `docs/infrastructure/mikrotik/mikrotik-management-and-troubleshooting-guide.md`, thay thế bằng `http://localhost:2310` và `http://kibe:2310`.
