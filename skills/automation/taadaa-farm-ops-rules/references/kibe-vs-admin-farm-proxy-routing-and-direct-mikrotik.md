# Kibe vs Admin Farm Proxy Routing & Direct MikroTik LAN (11/09/2026)

## 1. Bối cảnh & Cấu trúc mạng 2 Dàn Farm

Hệ thống Taadaa Farm gồm 2 dàn thiết bị độc lập chạy trên cùng lớp mạng LAN MikroTik:
- **Router MikroTik:** Gateway `192.168.110.2` (hoặc `192.168.10.254` tùy subnet/cổng ether).
- **Line PPPoE:** 35 lines (`pppoe-out1` .. `pppoe-out35`), mỗi line có dải IP WAN động độc lập.

### So sánh kiến trúc 2 bên:

| Tiêu chí | Dàn PC Admin (Máy 201..280) | Dàn PC Kibe (Máy 01..80) |
|---|---|---|
| **Mapping File** | `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx` | `D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx` |
| **Dải máy** | 80 máy (`201` đến `280`) | 80 máy (`01` đến `80`) |
| **Loại proxy gán** | Đi thẳng MikroTik LAN (`192.168.110.2:10008..10035`) | Kết hợp: MobiProxy (`5101..5138`), MikroTik (`10001..10007`) |
| **Cơ chế định tuyến** | **Đi trực tiếp LAN** — 94 rule Mangle (`FARM_ADMIN_MAY_xxx`) & NAT thẳng theo IP LAN sang từng `pppoe-outX`. KHÔNG qua Singbox container. | **Đi qua Singbox container trung gian** (`20001..20080`), Singbox nhận port 200xx rồi chuyển tiếp ra upstream tương ứng. |
| **Script gán** | `scripts/set_proxy_farm_admin_adb.py` | `scripts/set_proxy_farm_adb.py` |

---

## 2. Bài học cốt tử & Cạm bẫy kỹ thuật (Pitfalls)

### Cạm bẫy 1: Quên đọc config đối chiếu giữa 2 PC (Admin vs Kibe)
- **Triệu chứng:** Khi user nhắc "Bữa fix cho các máy đó đi trực tiếp từ LAN qua MikroTik bên PC Admin rồi, không qua Singbox nữa", agent tự suy đoán hoặc giải thích lý thuyết thay vì đọc ngay file mapping và script cấu hình của Admin.
- **Quy tắc bắt buộc:**
  1. Luôn đọc file mapping của Admin: `D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx`.
  2. Đọc script cấu hình tương ứng trong repo `AI-Tools`: `scripts/set_proxy_farm_admin_adb.py`.
  3. Kiểm tra rule Mangle / NAT thực tế trên MikroTik (`/ip/firewall/mangle`, `/ip/firewall/nat`) để xác nhận luồng đi trực tiếp hay qua container.

### Cạm bẫy 2: Lỗi 407 Proxy Authentication Required khi gán thẳng cổng 100xx
- **Nguyên nhân:** Cổng `10001..10035` của MikroTik được quản lý bởi container `3proxy` và yêu cầu xác thực (`admin@1:admin@1`). Lệnh Android `settings put global http_proxy 192.168.110.2:1000x` không hỗ trợ nhúng credentials trực tiếp.
- **Cách xử lý chuẩn:**
  - Nếu đi qua Singbox trung gian (`200xx`): Singbox tự đệm credentials trước khi bắn sang port `1000x`.
  - Nếu đi trực tiếp không qua Singbox: Thiết bị phải dùng ViChanger (`vn.vichanger.app.SET_PROXY` với chuỗi `host:port:user:pass`) hoặc trên MikroTik phải cấu hình IP whitelist bypass auth cho dải IP LAN của farm.

### Cạm bẫy 3: Whitelist Singbox container vào `FPT_LAN`
- Container Singbox chạy trên dải `172.17.0.0/16`.
- Nếu firewall forward trên MikroTik có rule drop external ports (`DROP_EXTERNAL_PROXY_PORTS`), toàn bộ gói tin từ Singbox gửi sang `10001..10035` sẽ bị drop nếu `172.17.0.0/16` chưa được thêm vào address-list `FPT_LAN`.
- **Lệnh thêm whitelist trên MikroTik:**
  ```json
  POST /ip/firewall/address-list
  {"list": "FPT_LAN", "address": "172.17.0.0/16", "comment": "Singbox Container - allowed to use proxy"}
  ```

---

## 3. Phong cách phản hồi khi User gắt / yêu cầu kiểm tra cấu hình
1. **Kiểm tra file cấu hình trước, giải thích sau:** Khi user nhắc tới cấu hình Admin hay bất kỳ repo/máy nào, việc đầu tiên là đọc file thực tế (`.xlsx`, `.json`, `.py`, `.yaml`).
2. **Không giải thích vòng vo, không phỏng đoán:** Trả lời trực diện bằng số liệu và trạng thái kiểm tra thực tế:
   - File mapping thực tế nói gì?
   - Cổng nào đang mở?
   - Máy nào đang kết nối?
   - Cần thao tác lệnh gì tiếp theo?
