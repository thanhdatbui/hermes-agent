# RCA & Khắc Phục Lỗi Singbox Loopback 16 Máy Kibe (2026-11-04)

## 1. Bản Chất Sự Cố
- **Hiện tượng:** 12 máy thuộc nhóm 16 máy Kibe (`M33-M38`, `M71-M80`) đồng loạt bị chặn fail-closed ở khâu preflight với signature:
  `context deadline exceeded (Client.Timeout exceeded while awaiting headers)` khi kiểm tra egress IP qua `ifconfig.me/ip`.
- **Nguyên nhân gốc rễ (Root Cause):**
  - Cấu hình gộp Singbox (`singbox_full_160.json` / `generate_singbox_config.py`) tạo outbound cho 16 máy Kibe này trỏ ngược về chính địa chỉ IP và cổng inbound của router MikroTik:
    `proxy_m33 -> server: 192.168.110.2, server_port: 20033`
  - Khi điện thoại S7 gửi gói tin vào cổng `20033`, container Singbox cố mở kết nối TCP ra chính nó (Self-Loopback), gây cạn kiệt ephemeral ports:
    `ERROR: open connection to ifconfig.me:80 using outbound/http[proxy_m38]: dial tcp 192.168.110.2:20038: connect: cannot assign requested address`.

## 2. Kiến Trúc Phân Luồng Chuẩn 16 Máy Kibe (Anti-Loopback Invariant)
Toàn bộ 80 máy Kibe được chia làm 2 cụm rõ rệt:
1. **64 máy chạy MobiProxy Thái Bình (`M1..M32` & `M39..M70`):**
   - Inbound: `20001..20032` và `20039..20070`.
   - Outbound: `test.taadaa.click:5101..5138` (xác thực mobi1..mobi38).
2. **16 máy Kibe còn lại (`M33..M38` & `M71..M80`):**
   - **14 máy:** `M33-M37`, `M71-M75`, `M77-M80` trỏ ra 7 line PPPoE MikroTik Đà Nẵng:
     `server: mirotik1.taadaa.click`, ports `10001..10007`, auth `admin@1:admin@1`.
     *Mapping:*
     - M33, M73 -> Port 10001
     - M34, M74 -> Port 10002
     - M35, M75 -> Port 10003
     - M36, M77 -> Port 10004
     - M37, M78 -> Port 10005
     - M71, M79 -> Port 10006
     - M72, M80 -> Port 10007
   - **2 máy:** `M38` và `M76` trỏ ra proxy phụ trợ ngoài:
     `server: khoalee.duckdns.org`, port `16002`, auth `5ns08q:AmLmaMJ0`.

## 3. Quy Trình Nạp Cấu Hình Lên MikroTik Không Cần SSH Terminal
- Sinh file cấu hình minified:
  `generate_singbox_config(..., minified=True)` (dung lượng < 30KB).
- PATCH trực tiếp qua RouterOS REST API:
  `PATCH http://192.168.110.2:9090/rest/file/*8072575` với payload `{"contents": <json_string>}`.
- Khởi động lại container Singbox (`*6`):
  `POST /rest/container/stop` (chờ 3s) -> `POST /rest/container/start` (chờ 3s).
- Kiểm tra trạng thái: `GET /rest/container/*6` -> `status: running`.

## 4. Kỷ Luật GuardGate Khi Sửa Code Mới (Step By Step Invariant)
- Khi thêm code mới $\ge 15$ dòng trong các file `.py`, GuardGate kích hoạt quy tắc `case_invariant_require_step_by_step_structure`.
- Bắt buộc phải có comment định danh phân bước `# Step 1: ...`, `# Step 2: ...` trước các khối logic chính, đồng thời bổ sung assertion kiểm chứng tương ứng trong file test để pass Closeout Gate v2.
