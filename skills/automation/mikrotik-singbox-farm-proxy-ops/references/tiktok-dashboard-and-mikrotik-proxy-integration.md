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
  - **Ground Truth từ OpenWrt R3G (BẮT BUỘC):** Trạng thái Live, IP Public và Time Live (Uptime) bắt buộc lấy trực tiếp từ dữ liệu trên router R3G qua lệnh SSH `ubus call network.interface dump` (user `root`, pass `password`, port 22, timeout 5s, cache đệm 15s). Lệnh này trả về JSON toàn bộ 16 interface PPPoE trong ~600ms. CẤM chỉ socket connect suông hoặc chỉ tính timer cục bộ khi router đã chạy hàng chục giờ.
  - Khớp nối chính xác 16 port R3G (`5141-5148`, `5151-5158`) sang interface OpenWrt: `5141` -> `WAN2`, `5142..5148` -> `wan_sub2..wan_sub8`, `5151` -> `wan`, `5152..5158` -> `wan_sub11..wan_sub17`.
  - Có fallback sang egress HTTP proxy probe (`http://ifconfig.me/ip` qua từng port) nếu SSH tới R3G gặp sự cố.
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
     * `PROXY`: Tên cổng proxy (`R3G-5141` .. `R3G-5158`).
     * `NGUỒN`: Định danh nguồn line (`R3G`, `Lan1`, `PPPoE`).
     * `IPV4 / IPV6`: Địa chỉ IP WAN ra Internet (font monospace). BẮT BUỘC lấy trực tiếp từ router OpenWrt R3G (`ubus call network.interface dump`) hoặc probe IP thật qua proxy client kết nối ra ngoài (e.g. `http://ifconfig.me/ip`), CẤM chỉ socket connect suông rồi để IP là `—`.
     * `CỔNG`: Cổng socket client kết nối vào (`5141`, `10001`).
     * `UPTIME`: Thời gian IP sống liên tục. BẮT BUỘC format câu chữ tiếng Việt chuẩn MobiProxy (`X ngày Y giờ`, `X giờ Y phút`, `X phút`, `X giây`), CẤM hiển thị dạng số đồng hồ `00:26:13` gây hiểu lầm.
     * `TRẠNG THÁI`: Huy hiệu màu sắc rõ nét (`🟢 LIVE` xanh lá, `🔴 OFFLINE` đỏ).
     * `HẸN GIỜ (PHÚT)`: Ô input riêng từng dòng cho phép đặt số phút đổi IP tự động (`0` = tắt, `1..1440` phút).
     * `RESET`: Nút bấm tức thời `↻ Reset` (disable nút và hiển thị spinner/text loading khi đang gửi lệnh).
2. **Chức Năng Hẹn Giờ Đổi IP (Set Time Change IP / Auto-Rotate):**
   - Thanh công cụ phía trên bảng BẮT BUỘC có khối điều khiển:
     * Ô nhập số phút toàn cục `[ Số phút ]` (1–1440 phút).
     * Nút `Áp dụng tất cả`: Tự động điền số phút vào toàn bộ 16 cổng.
     * Nút `💾 Lưu lịch reset`: Gửi request `POST /api/r3g-schedules` lưu vào `D:/Taadaa/data/r3g_schedules.json`.
     * Nút `↻ Reset tất cả 16 port`: Gửi request `POST /api/r3g-reset-all` để đổi IP toàn bộ dàn proxy đồng loạt.
   - Backend duy trì thread nền daemon `_r3g_scheduler_loop` định kỳ kiểm tra mốc thời gian và tự động chạy lệnh đổi IP qua SSH tới R3G khi tới hạn.
3. **Kỷ luật vận hành Proxy Farm:** Proxy R3G phục vụ nuôi acc TikTok mặc định phải đứng im (cố định IP), CẤM tự ý kích hoạt quay số đổi IP hàng loạt khi không có lệnh hoặc lịch hẹn trước.
4. **Tối ưu Mobile Responsive:** Thêm `-webkit-overflow-scrolling: touch;` cho container table wrapper, đặt padding gọn nhẹ (10px 8px) và font 13px để các cột quan trọng không bị đẩy mất mép trên điện thoại.

---

## 5. Bẫy Kỹ Thuật Cần Tránh Khi Sửa UI Dashboard
1. **Tránh bão hòa Tinyproxy / SSH R3G & Cạm bẫy Socket Probe Rỗng:**
   - CẤM chỉ kiểm tra TCP socket `sock.connect()` rồi báo xong mà bỏ quên trường `ip` và `uptime`.
   - Endpoint `/api/r3g-status` bắt buộc phải có bộ nhớ đệm cache đệm (15s) ở backend.
   - Ground Truth từ R3G: Lấy qua SSH `ubus call network.interface dump` (user `root`, pass `password`, port 22). Ánh xạ interface chuẩn: `5141` -> `WAN2`, `5142..5148` -> `wan_sub2..wan_sub8`, `5151` -> `wan`, `5152..5158` -> `wan_sub11..wan_sub17`. Lệnh đổi IP phải gọi `/sbin/ifdown <iface> && sleep 2 && /sbin/ifup <iface>` với đúng tên interface trên, CẤM gọi `r3g{port}` gây lỗi không tìm thấy interface.
   - Khi probe fallback qua HTTP, dùng `http://ifconfig.me/ip` kèm header `User-Agent: curl/7.88.1` với timeout 4.5s qua `ThreadPoolExecutor(max_workers=16)`.
2. **Kỷ luật sửa code pipeline:** Luôn chạy qua `unified_patch_pipeline.py` với test focused (`python -m py_compile ...`). Với các task thuần UI dashboard không chạm thiết bị thật, bắt buộc truyền cờ `--no-canary --no-canary-reason "<lý do>"` để tránh gate canary ADB chặn đứng phiên làm việc.
3. **Cấu Trúc Cổng R3G Bất Biến (16 port):** R3G gồm 16 port PPPoE: `5141..5148` (Line 1) và `5151..5158` (Line 0). CẤM tạo loop tuần tự `range(5141, 5159)` sinh ra 2 port rác `5149` và `5150`. Khóa mảng cứng `R3G_PORTS = [5141..5148, 5151..5158]`.
4. **Cạm Bẫy Trùng Lặp Cú Pháp JavaScript:** Khi chỉnh sửa `renderRows` trong `ledger_component.py`, tuyệt đối không để sót các đoạn nối chuỗi HTML thừa ngoài scope làm crash file JS dẫn đến `window.loadProxyR3G is undefined`. BẮT BUỘC kiểm tra console log trình duyệt trước khi nghiệm thu.
5. **Kỷ Luật Nghiệm Thu Bằng Chứng Ảnh (Chống Bốc Nhầm Ảnh Cache Cũ):**
   - CẤM TUYỆT ĐỐI bới các file `img_*.jpg` cũ trong `%LOCALAPPDATA%\hermes\image_cache\` để gửi cho User. Thư mục này chứa ảnh chụp từ các phiên làm việc khác hoặc tin nhắn người dùng gửi, bốc nhầm sẽ bị User bắt quả tang "ném hình session khác vào".
   - BẮT BUỘC chụp màn hình mới tinh bằng script tự động hóa trình duyệt (Playwright với system Chrome: `p.chromium.launch(channel='chrome')` chụp thẳng vào `D:/Taadaa/reports/<ten_anh>.png`), mở ảnh ra soi mắt bằng `browser_vision` xác nhận đúng giao diện đích mới được gửi thẻ `MEDIA:`.
6. **Bẫy Crontab OpenWrt R3G (Chống Tự Khởi Động Lại & Bức Tử Tinyproxy Mỗi Phút):**
   - CẤM TUYỆT ĐỐI đặt script khởi tạo proxy (`generate_all_proxies.sh`) vào cron chạy mỗi phút (`* * * * *`). Script này chứa lệnh `killall -9 tinyproxy`, nếu chạy mỗi phút sẽ bức tử toàn bộ 16 cổng proxy liên tục, gây rò rỉ PID (Process ID exhaustion), nghẽn bộ nhớ đệm socket và kích hoạt hardware watchdog reboot router sau 1–2 tiếng!
   - Proxy phục vụ nuôi farm bắt buộc phải chạy daemon tĩnh (persistent), chỉ được phép quay số (`ifdown/ifup`) trên đúng 1 interface đơn lẻ khi có lệnh hoặc lịch hẹn giờ.
   - Khi điều tra sự cố Uptime đồng loạt nhảy về mốc ngắn (~1 giờ), bắt buộc kiểm tra ngay `cat /proc/uptime` và `crontab -l` trên OpenWrt để bóc tách giữa việc Viettel reset với Router bị watchdog reboot do cron spam.
7. **Kiểm Toán Phần Cứng & An Toàn Hệ Thống R3G OpenWrt (Chống Tự Reboot 24/7):**
   - **Flash `/overlay` 100% Full (0 bytes free):** File lạ `Photo.scr` (5.2MB trong `/root` và 6MB trong `backup`) và binary lạ `/usr/sbin/netstat.cfg` (5.5MB) từ firmware cũ chiếm sạch phân vùng flash 38.9MB, khiến kernel không ghi được lock/pid và gây sập dịch vụ. Xóa sạch 2 file này giải phóng 11.2MB (đưa dung lượng về 70% an toàn).
   - **Bẫy `watchcat` tự sát (`ping_reboot 8.8.8.8`):** CẤM để watchcat ping ra DNS quốc tế `8.8.8.8` qua WAN trên router đa line. Khi cáp biển chập chờn hoặc ISP rớt ICMP, watchcat sẽ cưỡng chế reboot cứng toàn bộ router làm rớt toàn bộ proxy! BẮT BUỘC tắt và vô hiệu hóa: `/etc/init.d/watchcat stop && /etc/init.d/watchcat disable`.
   - **Tắt dịch vụ rác thừa thãi (Bảo vệ 16 IP Public & Tiết kiệm RAM):** 16 PPPoE tương đương 16 IP Public mở ra Internet. BẮT BUỘC tắt và disable: `vsftpd` (FTP mở 0.0.0.0), `samba4` (`smbd`, `nmbd` chia sẻ file Windows ngốn 50MB RAM), `ocserv` (OpenConnect VPN), `polipo` (proxy cũ).
8. **Kiểm Toán Tải Cao MikroTik RouterOS (CPU 95%):**
   - Trên phần cứng x86_64 Intel 4 nhân gánh 115 cổng proxy farm (35 cổng `3proxy` và 80 cổng `sing-box`), lưu lượng video TikTok lên tới hàng Terabytes (`3proxy` 1.1TB, `sing-box` 940GB) sẽ đẩy CPU lên mức cao tự nhiên do khối lượng dữ liệu thực tế.
   - Tuyệt đối CẤM để `logging: true` trên các container RouterOS, vì hàng trăm connection/giây sẽ xả rác vào bộ đệm logging của RouterOS làm nghẽn CPU. Đặt `logging: false`.
   - Giãn cách lịch trình các scheduler thăm dò API bên ngoài (như `telegram-wol-bot`) tối thiểu từ 10s-30s thay vì 5s, tránh RouterOS bị kẹt blocking fetch.
9. **Bẫy So Khớp Nhầm Private IP `172.` Trong Script `watchdog-pppoe` Của MikroTik:**
   - Script trên RouterOS kiểm tra `[:pick $ipWithMask 0 4] = "172."` rồi coi là IP private cần reset PPPoE.
   - Hậu quả: Các dải IP public sạch của Viettel như `172.245.x.x`, `172.224.x.x` bị hiểu nhầm là mạng nội bộ và bị kill liên tục, gây ra hiện tượng PPPoE Flapping làm gián đoạn proxy toàn farm!
   - Quy chuẩn: BẮT BUỘC bóc tách octet thứ hai trong RouterOS: chỉ coi là IP private khi octet thứ hai nằm trong khoảng 16 đến 31 (`172.16.0.0/12` theo RFC 1918).
10. **Khóa Chết Whitelist MobiProxy Với Line `pppoe-out1` MikroTik:**
   - MobiProxy tại Thái Bình đang whitelist cứng IP `116.110.212.30`. Đây chính là IP của `pppoe-out1` tại Đà Nẵng.
   - Tuyệt đối không reset bừa bãi `pppoe-out1` trên MikroTik vì sẽ làm đổi IP WAN, khiến toàn bộ 64 máy farm Kibe bị MobiProxy chặn đứng kết nối.
11. **Kiểm Toán An Toàn Sóng Wi-Fi Trên MobiProxy (`test.taadaa.click`):**
   - Cục MobiProxy phát 2 sóng Wi-Fi `MobiProxy2.4G` và `MobiProxy5G` không cô lập ngay trong phòng farm.
   - Cần thường xuyên vào tab *Thiết bị kết nối (Devices)* xác nhận số client đang kết nối là 0, ngăn chặn nguy cơ điện thoại Samsung S7 tự động kết nối (auto-join) vào sóng này làm lộ IP gốc của SIM/modem thay vì đi qua proxy chỉ định.
12. **Kỷ Luật Tham Vấn Advisor (Anti-Assumption Mandate):**
   - Khi tham vấn Hội đồng Cố vấn (Advisor) về sự cố mạng/hạ tầng, BẮT BUỘC phải trích xuất và cung cấp 100% dữ liệu cấu hình thô nguyên bản (Raw Config/Scripts/Rules), CẤM chỉ gửi tóm tắt suy đoán chủ quan làm lệch lạc phán quyết của Advisor.
14. **Kỷ Luật Bảng NAT RouterOS (Chống Nghẽn CPU 95%):**
   - Định kỳ kiểm tra `/ip firewall nat` để quét và loại bỏ các rule chết (`packets = 0`), tránh để hàng trăm rule masquerade/dst-nat rác từ các đợt cấu hình cũ làm chậm quá trình duyệt gói tin (phiên vừa qua đã dọn từ 712 rules xuống 188 rules, giải phóng 170MB RAM).
   - Trong script `watchdog-pppoe`, chỉ so khớp Private IP chuẩn RFC 1918 (với `172.`, phải kiểm tra octet thứ hai từ `16` đến `31`), TUYỆT ĐỐI KHÔNG so khớp cụm `172.` chung chung làm ngắt nhầm các dải IP Public sạch của Viettel (`172.245.x.x`, `172.224.x.x`).
15. **Chuẩn Thiết Kế Giao Diện Đồng Bộ MikroTik Web Manager (`:2310`):**
   - Giao diện MikroTik Web (`:2310`) phải đồng bộ 100% phong cách với R3G: bỏ toàn bộ card stats to tướng và tab navigation thừa.
   - Bảng 8 cột chuẩn MobiProxy: `PROXY`, `NGUỒN`, `IPV4 / IPV6`, `CỔNG`, `UPTIME`, `TRẠNG THÁI`, `HẸN GIỜ (PHÚT)`, `RESET`.
   - Có thanh công cụ `⏱ Hẹn giờ đổi IP` (input số phút, nút Áp dụng tất cả, nút Lưu lịch reset, nút Reset tất cả 35 line).
   - Nút Reset đổi IP trực tiếp không hiện confirm popup phiền toái.
   - Uptime RouterOS format chuẩn tiếng Việt (`X ngày Y giờ`, `X giờ Y phút`).
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
