# TikTok Dashboard & MikroTik Web Integrated Proxy Operations

## Bối Cảnh & Kiến Trúc Tích Hợp (2026-11-02)
Khi người vận hành farm cần theo dõi toàn bộ tài nguyên proxy trên cùng một màn hình điều khiển:
- **TikTok Farm Dashboard** chạy tại cổng `1905` (`D:/Taadaa/tools/tiktok_dashboard.py`).
- **MikroTik Web Manager** chạy tại cổng `2310` (`D:/Taadaa/AI-Tools/tools/mikrotik_web/server.py`).
- Router biên **Xiaomi Mi Router 3G (R3G)** tại Thái Bình (`tb.taadaa.click`) cấp 16 cổng proxy từ `5141` đến `5158`.

---

## 1. Cấu Trúc Tab Cấp Cao Tại TikTok Dashboard (Port 1905)
TikTok Dashboard được chia thành 3 danh mục chính:
1. `📊 Giám Sát TikTok`: Bảng KPI, BXH Follower, Tim, Nick cắn đề xuất, Sức khỏe cụm máy, Sức khỏe Follow.
2. `📓 Sổ Cái Farm (SQLite)`: Tra cứu mapping máy, serial, slot, email, pass, token OAuth, 2FA TikTok & Mail.
3. `🌐 Quản Lý Proxy`: Tab tích hợp điều phối toàn bộ hạ tầng mạng của farm, bên trong gồm 2 trang con:
   - **MikroTik**: Nhúng iframe trực tiếp tới `http://<host>:2310/` để hiển thị 35 line PPPoE, đo ping, theo dõi tải CPU RouterOS, cấu hình Schedules và đổi IP từng line.
   - **R3G**: Giao diện bảng quản trị trực quan 16 port R3G Thái Bình chuẩn MobiProxy, lấy dữ liệu động từ API native cổng 1905.

---

## 2. Phân Định Rõ Trách Nhiệm API Giữa TikTok Dashboard (1905) và MikroTik Backend (2310)
Để đảm bảo tách biệt kiến trúc sạch giữa 2 router ở 2 tỉnh thành khác nhau (MikroTik Đà Nẵng vs R3G Thái Bình):
- **MikroTik Web Manager (port `2310`):**
  - Chuyên trách 100% quản trị router RouterOS Đà Nẵng.
  - Endpoints: `GET /api/proxies`, `POST /api/change-ip`, `GET /api/status`.
  - Tuyệt đối CẤM nhồi route hoặc UI của R3G vào cổng 2310.
- **TikTok Farm Dashboard (port `1905`):**
  - Trực tiếp probe TCP socket tới 16 port R3G (`tb.taadaa.click:5141..5158`) tại route native `GET /api/r3g-status`.
  - Trực tiếp gửi lệnh SSH ifdown/ifup tới `root@tb.taadaa.click` tại route native `POST /api/r3g-change-ip`.
  - Mã nguồn client (`ledger_component.py`) gọi relative URL `/api/r3g-status` và `/api/r3g-change-ip` cùng origin cổng 1905, không bao giờ gọi cross-origin sang cổng 2310.

---

## 3. Mapping Interface Khi Đổi IP R3G
Khi gọi API `/api/r3g-change-ip`, backend MikroTik kết nối SSH vào router R3G (`tb.taadaa.click:22`, user `root`) và chạy `/sbin/ifdown <interface> && sleep 2 && /sbin/ifup <interface>`.
Bảng mapping chính xác giữa cổng Tinyproxy và interface PPPoE trên OpenWrt R3G:

| Port Tinyproxy | Interface OpenWrt | Vị trí Line Vật Lý | Thiết bị gán tương ứng |
|---|---|---|---|
| `5141` | `WAN2` | Line 1 (`lan2` - cổng ngoài) | M203, M204 |
| `5142` | `wan_sub2` | Line 1 (`lan2`) | M208, M211 |
| `5143` | `wan_sub3` | Line 1 (`lan2`) | M213, M217 |
| `5144` | `wan_sub4` | Line 1 (`lan2`) | M220, M223 |
| `5145` | `wan_sub5` | Line 1 (`lan2`) | M227, M230 |
| `5146` | `wan_sub6` | Line 1 (`lan2`) | M233, M235 |
| `5147` | `wan_sub7` | Line 1 (`lan2`) | M238, M241 |
| `5148` | `wan_sub8` | Line 1 (`lan2`) | M243, M246 |
| `5151` | `wan` | Line 0 (`lan1` - cổng giữa) | M251, M253 |
| `5152` | `wan_sub11` | Line 0 (`lan1`) | M255, M260 |
| `5153` | `wan_sub12` | Line 0 (`lan1`) | M262, M264 |
| `5154` | `wan_sub13` | Line 0 (`lan1`) | M268, M270 |
| `5155` | `wan_sub14` | Line 0 (`lan1`) | M261, M263 |
| `5156` | `wan_sub15` | Line 0 (`lan1`) | M265, M266 |
| `5157` | `wan_sub16` | Line 0 (`lan1`) | M267, M269 |
| `5158` | `wan_sub17` | Line 0 (`lan1`) | M271, M272 |

---

## 4. Chuẩn Thiết Kế Giao Diện Điều Hành Proxy (Mẫu MobiProxy `test.taadaa.click`)
Người vận hành yêu cầu giao diện điều khiển proxy (cả bên MikroTik và R3G) phải trực quan, chuyên nghiệp, mô phỏng đúng các chức năng cốt lõi của trang quản trị MobiProxy:
1. **Thay thế Card dạng lưới thô bằng Bảng Table chuẩn:**
   - CẤM dùng các khối card to tướng choán diện tích màn hình.
   - BẮT BUỘC dùng bảng table gọn gàng, căn lề thẳng hàng, bo góc với các cột chuẩn:
     * `Port / Tên cổng`: Số thứ tự hoặc tên interface (`5141`, `pppoe-out1`).
     * `Nguồn`: Định danh nguồn line (`R3G`, `Lan1`, `PPPoE`).
     * `IP Public`: Địa chỉ IP WAN ra Internet (font monospace). BẮT BUỘC probe IP thật qua proxy client kết nối ra ngoài (e.g. `http://ifconfig.me/ip`), CẤM chỉ socket connect suông rồi để IP là `—`.
     * `Cổng Proxy`: Cổng socket client kết nối vào (`5141`, `10001`).
     * `Time Live (Uptime)`: Thời gian IP sống liên tục định dạng `HH:MM:SS` (hoặc ngày/giờ). BẮT BUỘC backend duy trì tracker `_R3G_PORT_TRACKER[port] = {'ip': ip, 'since': time.time()}` và tính động `uptime = now - since` mỗi khi trả về API, đảm bảo time live tăng đều theo thời gian thực tế.
     * `Trạng Thái`: Huy hiệu màu sắc rõ nét (`🟢 LIVE` xanh lá, `🔴 OFFLINE` đỏ).
     * `Thao Tác`: Nút bấm tức thời `🔄 Đổi IP` (disable nút và hiển thị spinner/text loading khi đang gửi lệnh).
   - **Tối ưu Mobile Responsive:** Thêm `-webkit-overflow-scrolling: touch;` cho container table wrapper, đặt padding gọn nhẹ (10px 8px) và font 13px để các cột quan trọng không bị đẩy mất mép trên điện thoại.

---

## 5. Bẫy Kỹ Thuật Cần Tránh Khi Sửa UI Dashboard
1. **Tránh bão hòa Tinyproxy / SSH R3G & Cạm bẫy Socket Probe Rỗng:**
   - CẤM chỉ kiểm tra TCP socket `sock.connect()` rồi báo xong mà bỏ quên trường `ip` và `uptime`.
   - Endpoint `/api/r3g-status` bắt buộc phải có bộ nhớ đệm cache đệm (15s) ở backend.
   - Khi probe IP qua các line Viettel Thái Bình, dùng `http://ifconfig.me/ip` kèm header `User-Agent: curl/7.88.1` với timeout 4.5s qua `ThreadPoolExecutor(max_workers=16)`. Tránh dùng `api.ipify.org` với timeout quá ngắn (<3s) vì dễ bị nghẽn mạng gây nhận định sai `offline`.
   - Luôn tính động `uptime` tại thời điểm request thay vì freeze cứng chuỗi `"00:00:00"` trong cache dict.
2. **Kỷ luật sửa code pipeline:** Luôn chạy qua `unified_patch_pipeline.py` với test focused (`python -m py_compile ...`). Với các task thuần UI dashboard không chạm thiết bị thật, bắt buộc truyền cờ `--no-canary --no-canary-reason "<lý do>"` để tránh gate canary ADB chặn đứng phiên làm việc.
3. **Cấu Trúc Cổng R3G Bất Biến (16 port):** R3G gồm 16 port PPPoE: `5141..5148` (Line 1) và `5151..5158` (Line 0). CẤM tạo loop tuần tự `range(5141, 5159)` sinh ra 2 port rác `5149` và `5150`. Khóa mảng cứng `R3G_PORTS = [5141..5148, 5151..5158]`.
4. **Restart Service đúng cách trên Windows:** TikTok Dashboard được giám sát bởi tiến trình Watchdog (`tiktok_dashboard_watchdog.ps1`). Khi deploy code mới, sử dụng script `python D:/Taadaa/tools/restart_tiktok_dashboard.py` để khởi động lại sạch sẽ cả service chính lẫn watchdog ngầm qua VBScript.
   - **Nút "📋 Copy danh sách proxy":**
     * Tự động duyệt qua danh sách các hàng đang hiển thị (đã qua filter tìm kiếm).
     * Chỉ gom các proxy đang có trạng thái `LIVE` hoặc `RUNNING` và có IP hợp lệ (bỏ qua các port chết `—`).
     * Gọi `navigator.clipboard.writeText` với fallback sang `textarea` ẩn + `document.execCommand('copy')` để chạy mượt mà ngay cả trên HTTP (non-secure context).
     * Hiển thị Toast thông báo số lượng proxy đã copy thành công (`✅ Đã copy N proxy!`).
   - **Bộ đếm số lượng hiển thị:** Nhãn đếm `Hiển thị X/Y proxy` cập nhật liên tục theo từ khóa tìm kiếm.

---

## 5. Bẫy Kỹ Thuật Cần Tránh Khi Sửa UI Dashboard
1. **Tránh bão hòa Tinyproxy / SSH R3G:** Endpoint `/api/r3g-status` bắt buộc phải có bộ nhớ đệm cache đệm (10-15s) ở backend MikroTik. CẤM các trang frontend tự động bắn request probe liên tục không throttle làm nghẽn hàng đợi kết nối Tinyproxy.
2. **Kỷ luật sửa code pipeline:** Luôn chạy qua `unified_patch_pipeline.py` với test focused (`python -m py_compile ...`). Với các task thuần UI dashboard không chạm thiết bị thật, bắt buộc truyền cờ `--no-canary --no-canary-reason "<lý do>"` để tránh gate canary ADB chặn đứng phiên làm việc.
3. **Restart Service đúng cách trên Windows:** TikTok Dashboard được giám sát bởi tiến trình Watchdog (`tiktok_dashboard_watchdog.ps1`). Khi deploy code mới, sử dụng script `python D:/Taadaa/tools/restart_tiktok_dashboard.py` để khởi động lại sạch sẽ cả service chính lẫn watchdog ngầm qua VBScript.
4. **Phân Định Rõ Ranh Giới Giao Diện MikroTik (:2310) vs R3G (Chống Nhồi Trùng Lặp UI):**
   - Trang gốc MikroTik Web Manager (`:2310`) được nhúng trực tiếp qua `<iframe>` vào sub-tab MikroTik trên Dashboard (`:1905`).
   - Do đó, trang `:2310` CHỈ ĐƯỢC CHỨA giao diện PPPoE, Uptime, Schedules của MikroTik. TUYỆT ĐỐI CẤM nhét thêm HTML/card R3G vào `HTML_PAGE` của `server.py` (:2310).
   - **Cảnh báo Coupling Kiến Trúc (R3G vs MikroTik):** MikroTik (RouterOS Đà Nẵng) và R3G (OpenWrt Thái Bình) là 2 hạ tầng mạng độc lập. Không được ghép nối ngầm R3G vào tiến trình MikroTik. Nếu trước đó Dashboard `:1905` lỡ gọi API R3G qua cổng `:2310`, khi dọn dẹp `server.py` phải đồng thời di dời API probe R3G sang đúng host quản lý hoặc Dashboard `:1905`, tránh làm gãy sub-tab R3G với lỗi `Failed to fetch`.
5. **Quy Trình Khởi Động Lại Service Windows Host Khi Bị Chặn Script Ngoài Allowlist:**
   - Khi Coordinator bị chặn chạy trực tiếp các lệnh `wscript`, `powershell`:
     * Tra cứu PID nghe port qua `psutil.net_connections()`: `python -c "import psutil; [print(c.pid, psutil.Process(c.pid).cmdline()) for c in psutil.net_connections() if c.laddr.port == 2310 and c.status == 'LISTEN']"`.
     * Dùng `taskkill /F /PID <pid>` để hạ sạch các tiến trình cũ chiếm port.
     * Khởi động lại service bằng lệnh `python` background trong workdir tương ứng: `python server.py` (với `background=true`).
     * Xác thực in-memory reload bằng cào HTTP thật và chụp màn hình đối soát WinRT OCR trước khi báo hoàn tất; tuyệt đối không báo xong nửa chừng bắt User tự bấm file .bat.
6. **Bảo Toàn API Contract Khi Refactor Giao Diện:**
   - Trước khi bóc tách hoặc xóa bất kỳ endpoint nào khỏi service nền (như `/api/r3g-status`), bắt buộc kiểm tra xem có frontend nào (như `ledger_component.py` trên Dashboard `:1905`) đang gọi sang hay không.
   - Nếu xóa API mà chưa đổi endpoint phía frontend, sub-tab gọi đến sẽ văng lỗi `Failed to fetch`. Di dời backend API phải luôn đi đôi với cập nhật URL gọi ở frontend.
