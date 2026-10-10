---

name: farm-proxy-attachment

description: Verify or configure per-device proxy attachment for the Taadaa Android phone farm via the ViChanger app and the gan-proxy repo. Also covers MikroTik PPPoE management tools (local web dashboard, mikrotik_manager.py CLI, change-ip flow). Use when the user asks whether the farm proxy setup is correct/safe/legit ("gắn proxy ổn không", "vichanger fake không", "proxy qua app hay adb"), when a task touches D:\Taadaa\gan-proxy, vi_changer_runner.py, gan_proxy_fleet.py, or the per-device proxy mapping, or when building/using MikroTik management tools.

---



# Farm proxy attachment (Taadaa phone farm)

## 🛑 QUY TẮC CỐT LÕI (2026-09-03 — BỎ HOÀN TOÀN VICHANGER)
- **KỶ LUẬT PROXY THEO BẢN CHẤT LỖI (2026-09-30 — USER INVARIANT):**
  + **Lỗi do NỀN TẢNG (Platform Error):** Google Checkpoint, reCAPTCHA, bắt SĐT (`challenge/iap`), sai mật khẩu (`BLOCKED_WRONG_PASSWORD`), rate limit từ server TikTok/Google/Hotmail ➔ **TÍNH 1 LƯỢT DÙNG (TƯƠNG ĐƯƠNG SUCCESS)**, **Khóa IP/Port proxy đó ngay lập tức** đến hết ngày để bảo vệ an toàn tuyệt đối cho dàn nick, cấm nhồi nick khác vào IP đã bị nền tảng gắn cờ nghi vấn.
  + **Lỗi do SCRIPT / NỘI BỘ (Script Error):** GPM API timeout, thiếu mật khẩu trong Excel (`MISSING_PASSWORD`), tự động skip do filter nội bộ (`khoaleemagic`), crash CDP trước khi tải trang ➔ **KHÔNG TÍNH VÀO QUOTA IP**, giữ nguyên IP để thử lại tài khoản khác trong ngày (tài khoản lỗi script đánh dấu riêng tránh loop lặp lại).
  + Áp dụng thống nhất cho toàn bộ các cronjob login, reg, ver, 2fa, và oauth feeder toàn farm.
- **FARM ĐÃ BỎ HOÀN TOÀN VICHANGER:** Toàn bộ 80 máy Kibe chạy qua router MikroTik RouterOS và Container Singbox Mixed Inbound (`20001..20080` tương ứng máy 1..80 tại `192.168.110.2`).
- **CẤM TUYỆT ĐỐI GỌI VICHANGER / gan_proxy_fleet.py run:** Không bao giờ bật ViChanger app hay gửi broadcast `START_VPN` lên máy. ViChanger đã bị xóa khỏi toàn bộ consumer repos.
- **CÔNG CỤ GÁN PROXY CHUẨN DUY NHẤT:** `python D:\Taadaa\AI-Tools\scripts\set_proxy_farm_adb.py --machines <ID>` (gán `http_proxy=192.168.110.2:2000N` và tắt captive portal `captive_portal_mode=0`, `captive_portal_detection_enabled=0`).
- **Repo gan-proxy:** Chỉ giữ lại nguyên trạng làm tư liệu legacy, KHÔNG chạy trên dàn máy live.
- **CẢNH BÁO TOOL CẤP MẠNG QUA USB (NETLINK USB PRO / GNIREHTET / USB REVERSE TETHERING):**
  + **Bản chất kỹ thuật:** Chạy reverse tethering qua ADB (forward/reverse socket) + bắt buộc cài APK tạo `VpnService` trên điện thoại để gom traffic đẩy về PC.
  + **TẠI SAO CẤM ÁP DỤNG TRÊN DÀN TAADAA FARM (80 MÁY S7):**
    1. *Nghẽn băng thông USB & sập ADB host:* 80 máy S7 cắm chung hub USB phục vụ ADB commands, atx-agent, automation, scrcpy, video transfer. Nếu dồn toàn bộ lưu lượng tải video / feed TikTok qua cáp USB 2.0, Host controller của PC sẽ bị nghẽn bus nghiêm trọng, gây rớt thiết bị (`device offline`), ngắt kết nối ADB và đơ tool automation.
    2. *Bẫy VpnService trên Android 8 (S7 Exynos):* Tương tự bài học ViChanger cũ, VpnService chạy nền gây quá nhiệt máy, chai phồng pin và thường xuyên bị Samsung system_server OOM-kill ngầm làm đứt kết nối giữa chừng.
    3. *Xung đột định tuyến Proxy:* VpnService trên máy chiếm quyền `tun0`, xung đột trực tiếp với thiết lập `global http_proxy` trỏ vào Sing-box / MikroTik, làm mất khả năng quản lý và phân luồng proxy tập trung.
    4. *Rủi ro bảo mật:* Các tool trôi nổi đóng gói RAR đặt pass né quét virus của Google Drive/AV, không có chữ ký số, nguy cơ cấy trojan/stealer vào PC Kibe. Hạ tầng Wi-Fi Aruba + MikroTik + Singbox hiện tại là chuẩn mực tối ưu nhất cho farm.

## Kiến trúc MikroTik & Sing-box Proxy
- **Gateway LAN IP:** `192.168.110.2`
- **Cấu hình Phần cứng MikroTik Soft Router (x86 Mini PC):**
  + **Bản chất thiết bị:** Là Mini PC Soft Router x86_64 chạy **Intel Celeron J4125** (Gemini Lake, 4 nhân 4 luồng, boost 2.6GHz, GPU UHD 600) cài hệ điều hành RouterOS v7.18.2 Level 6.
  + **Dấu hiệu nhận biết trên RouterOS:** Lệnh `/system/resource` hiển thị `board-name: "x86 Default string Default string"` (do BIOS máy OEM/ODM Trung Quốc không ghi chuỗi DMI model). Kiểm tra `/system/resource/pci` sẽ thấy `device-id: 0x31f0` (Gemini Lake Host Bridge) và 4 card `0x125c` (Intel Ethernet Controller I226-V rev 4).
  + **Network Interfaces:** Trang bị 4 cổng mạng vật lý **Intel I226-V 2.5GbE** độc lập (`WAN1`, `ether2`, `ether3`, `WAN4`), MAC prefix `60:BE:B4` (S-Bluetech / OEM Soft Router Thâm Quyến: Topton, CWWK, Qotom, Kingnovy).
  + **RAM & Lưu trữ:** 8GB RAM DDR4 (trống ~7.9GB), 16GB mSATA/SSD chạy RouterOS + Container Sing-box/3proxy.
  + **🚨 CẤM CÀI AI AGENT / DEV TOOLS TRỰC TIẾP LÊN ROUTEROS BARE-METAL (08/10/2026):**
    * RouterOS là hệ điều hành mạng chuyên biệt, không có package manager, không có Python runtime đầy đủ, ổ cứng 16GB sẽ nhanh chóng bị cạn kiệt bởi venvs/git/logs.
    * RouterOS là huyết mạch mạng của 80 máy farm S7. Tác vụ AI Agent (phân tích AST, chạy test suite, build) gây spike CPU/RAM 100% sẽ làm drop packet, rớt kết nối PPPoE và sập đồng loạt toàn bộ farm.
    * Nếu muốn tận dụng phần cứng: Cắm thêm SSD 128-256GB -> cài Proxmox VE -> VM1 chạy RouterOS CHR gán riêng vCPU/RAM, VM2 chạy Ubuntu Server làm Agent host độc lập. Chi tiết: `references/mikrotik-minipc-hardware-audit-and-agent-coexistence.md`.
- **Cụm 80 cổng Sing-box Inbound:** Port `20001..20080` (`20000 + Số máy`)
- **Mapping Upstream trong Sing-box:** File `D:\Taadaa\AI-Tools\config\singbox_config.json`:
  + Inbound: `mixed-m<N>` (Port `20000+N`)
  + Route rule: `mixed-m<N>` -> `proxy_m<N>`
  + Outbound: `server: test.taadaa.click`, `server_port: 51XX`, `username: mobiX`, `password: TaadaaMobi#2026!`
- **Triệu chứng 'Wi-Fi đủ, Không có Internet' / Icon Wi-Fi Chấm Than (!) do Sập Upstream Proxy:**
  + **Dấu hiệu trực quan trên Aowee/Xiaowei:** Icon Wi-Fi trên status bar của máy Samsung S7 xuất hiện **dấu chấm than (!)**; khi mở TikTok xuất hiện banner lỗi *"Mạng của bạn không ổn định. Hãy nhấn để thử lại."* (Network unstable) hoặc *"Không có kết nối Internet"*.
  + **Bản chất kỹ thuật:** Wi-Fi nội bộ LAN (Aruba AP `kibe 1` / `kibe 2`) vẫn kết nối hoàn toàn bình thường, ping router và DNS 8.8.8.8 vẫn thông. Tuy nhiên do máy được cấu hình Android `global http_proxy` trỏ vào Sing-box (`192.168.110.2:20000+N`), mọi gói tin kiểm tra kết nối mạng (Captive Portal `http://connectivitycheck.gstatic.com/generate_204`) đều đi qua proxy. Khi upstream proxy bị sập/timed out/connection refused, Android không nhận được mã HTTP 204 nên đánh dấu kết nối Wi-Fi bị giới hạn và gắn dấu chấm than (!).
  + **Quy trình chẩn đoán O(1) thần tốc:**
    1. *Tra cứu mapping máy & upstream:* Mở `D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx`, tìm số máy `N` để lấy Serial và dòng proxy upstream (ví dụ: `khoalee.duckdns.org:16002:5ns08q:AmLmaMJ0` hoặc `test.taadaa.click:51XX`).
    2. *Tìm máy dùng chung upstream (Quy tắc 1 port = 2 máy):* Lọc cột proxy xem có máy thứ 2 nào dùng chung đường này không (ví dụ M38 và M76 dùng chung `khoalee.duckdns.org:16002`). Nếu 1 máy bị chấm than thì máy dùng chung chắc chắn cũng sẽ bị tương tự.
    3. *Probe 2 tầng kiểm chứng:*
       - Tầng 1 (Local Singbox port): Test `http://192.168.110.2:20000+N` tới `http://connectivitycheck.gstatic.com/generate_204`.
       - Tầng 2 (Direct Upstream proxy): Test thẳng `http://user:pass@host:port` ra ngoài Internet qua Python `urllib.request.ProxyHandler`.
       - *Lưu ý:* BẮT BUỘC URL-encode password (ví dụ `#` trong `TaadaaMobi#2026!` -> `%23`) để tránh vỡ cú pháp URI.
    4. *Kết luận:* Nếu upstream direct bị `timed out` / `Connection Refused` -> Báo cáo rõ do proxy upstream (Khoa Lee, MobiProxy) chết hoặc hết hạn, đề xuất user check bên bán hoặc thay line proxy mới vào `PROXYgandienthoai.xlsx`. Tuyệt đối không cắm đầu reset Wi-Fi hay reboot máy vô nghĩa.
- **Hệ quả trên Bot Automation (TikTok Reg / Video / Feed Session):**
  + *Reg / Video upload:* Proxy chết làm request treo -> bot tưởng chưa submit hoặc kẹt form -> spam bấm lại nhiều lần -> dính cờ rate-limit/spam đỏ (*'Please try again or log in with a different method'*).
  + *TikTok Account Switcher (Feed Session / Runner):* Khi Singbox trả về `502 Bad Gateway` / `Connection reset`, thao tác tap chuyển tài khoản trong Account Switcher không tải được session mới từ máy chủ TikTok, khiến giao diện âm thầm giữ nguyên nick cũ (`profile username still mismatched after switch`). Thiết bị kẹt lock ở `status: blocked` (`machine_N.lock.json`). Khi gặp lỗi switch không đổi nick, kiểm tra ngay proxy `192.168.110.2:2000N` trước khi nghi ngờ ADB tap trượt.
- **35 Line PPPoE:** Dải upstream `10001..10035` (`admin@1:admin@1`) / Dcom
- **Phân biệt HTTP 502 vs HTTPS qua 3proxy (2026-09-11):**
  + Khi test proxy bằng `urllib` hoặc `curl` với giao thức **HTTP (plain)**: 3proxy container trên RouterOS có thể trả về `502 Bad Gateway (Host Not Found or connection failed)` do resolver hoặc cơ chế handling raw HTTP.
  + **Bản chất thực tế:** Khi test bằng **HTTPS CONNECT** (`https://api.ipify.org`), kết nối tunnel hoạt động hoàn toàn bình thường (Status 200) và xuất đúng Public IP của đường PPPoE tương ứng. Vì hầu hết app (TikTok, Google, v.v.) đều chạy HTTPS, **không được vội kết luận 3proxy chết khi chỉ test qua plain HTTP**.
- **Quy tắc sửa MikroTik REST API cho Firewall / NAT (2026-09-11):**
  + **Tránh set rỗng:** PATCH `src-address: ""` sẽ bị MikroTik REST API từ chối với `400 Bad Request`. Nếu muốn bỏ trường lọc địa chỉ nguồn để dùng `src-address-list`, giải pháp an toàn là `DELETE` rule cũ và `PUT` tạo lại rule mới hoàn toàn không truyền `src-address`.
  + **Chống nhân bản NAT:** Khi gán dstnat rules cho dải port (10001..10035), luôn đọc danh sách rule hiện có trước để tránh tạo trùng nhiều bản ghi trên cùng 1 interface (gây rối và lãng phí bảng NAT).
- **Bắt buộc whitelist Subnet Singbox (`172.17.0.0/16`) trong `FPT_LAN` (2026-09-11):**
  + Trong cấu hình Sing-box, các máy `M33–M37` và `M71–M80` (trừ M76) route upstream ra các cổng `10001–10007` trên MikroTik.
  + Container Sing-box chạy trên interface `veth-singbox` với IP `172.17.0.2` (subnet `172.17.0.0/16`).
  + Nếu address-list `FPT_LAN` thiếu `172.17.0.0/16`, firewall filter `DROP_EXTERNAL_PROXY_PORTS` sẽ chặn toàn bộ kết nối upstream từ Sing-box ra các line PPPoE (`WinError 10054 / Connection forcibly closed`), khiến toàn bộ 14 máy này bị đứt mạng Internet.
  + Bắt buộc duy trì entry `{"list": "FPT_LAN", "address": "172.17.0.0/16"}` trong MikroTik RouterOS firewall address-list.
- **Phản hồi người dùng khi hỏi tình trạng kết nối:**
  + Người dùng cần câu trả lời dứt khoát, trực diện vào tình trạng thực tế: **(1) PC Kibe dùng được chưa? (2) Máy farm S7 dùng được chưa?**
  + Tuyệt đối không giải thích dông dài lý thuyết router trước khi chốt kết quả kết nối thực tế.
- **Quy tắc mapping Wi-Fi chuẩn 80 máy S7 (kibe 1 vs kibe 2) & MẬT KHẨU THỰC TẾ (2026-09-15):**
  + **Máy 01 – 40 (Cụm trên):** Luôn kết nối SSID `kibe 1` — **MẬT KHẨU: `23102025`** (đã xác thực qua `show running-config no-encrypt` trên Aruba AP `192.168.110.253`). TUYỆT ĐỐI KHÔNG nhập nhầm `19051995` vì sẽ dính lỗi bắt tay `인증 오류 발생` (Authentication failure).
  + **Máy 41 – 80 (Cụm dưới):** Luôn kết nối SSID `kibe 2` — **MẬT KHẨU: `19051995`**.
  + **Cụm Admin (Máy 200+):** SSID `admin 1` & `admin 2` (Pass: `19051995`).
  + **Lệnh kiểm tra pass rõ trên Aruba AP Virtual Controller (192.168.110.253):** SSH admin/n0spam@@ -> `show running-config no-encrypt` (phải thêm `no-encrypt` mới xem được pass rõ dạng wpa-passphrase, nếu không sẽ hiện hash mã hóa).
  + **Quy trình thay thế / lắp máy mới (Replace dead machine):**
    1. Kiểm tra serial máy mới qua `adb devices` và đối chiếu serial cũ trong `taikhoan_run_safe.xlsx`.
    2. Gỡ keyguard / AOD: `input keyevent 224 && wm dismiss-keyguard && input keyevent 3`.
    3. Kết nối Wi-Fi đúng SSID và Password (`kibe 1` -> `23102025`, `kibe 2` -> `19051995`).
    4. Cấu hình giờ và chống lỗi SSL: `settings put global auto_time 1 && settings put global auto_time_zone 1 && setprop persist.sys.timezone Asia/Ho_Chi_Minh`.
    5. Gán proxy Singbox: `settings put global http_proxy 192.168.110.2:20000+N` và tắt captive portal (`captive_portal_mode 0`).
    6. Tắt Google Play Protect verify để tránh nghẽn ADB: `settings put global verifier_verify_adb_installs 0 && settings put global package_verifier_enable 0`.
    7. Cài đặt APK: Tránh cài trực tiếp từ thư mục OneDrive nếu file đang bị sync stall; copy về đĩa cục bộ (`D:\Taadaa\tools\`) trước khi chạy `adb install` / `install-multiple`.
    8. Cập nhật serial mới vào toàn bộ các file mapping: `taikhoan_run_safe.xlsx`, `PROXYgandienthoai.xlsx`, `Tik1..8.xlsx`.
  + Khi kiểm tra kết nối từ máy farm lên proxy port trên MikroTik: dùng `toybox nc -w 2 192.168.110.2 <PORT> < /dev/null` trên ADB shell thay vì dựa vào `curl` (vốn không cài sẵn trên Android system binary).
- **Hardware Kill-Switch:** MikroTik Firewall tự động DROP toàn bộ traffic ra ngoài nếu máy chưa trỏ proxy `192.168.110.2:2000N` qua ADB để chống lộ Direct IP.
- **🚨 QUY TẮC MIKROTIK WAN DROP & HAIRPIN DNS CHO PC HOST KIBE (12/09/2026):**
  + **Bản chất sự cố:** Domain `mirotik1.taadaa.click` phân giải ra IP Public WAN `171.231.181.33`. Do firewall RouterOS có rule DROP WAN chặn bên ngoài truy cập vào dải port PPPoE `10001..10035` để bảo mật và không cấu hình Hairpin NAT, máy host Kibe khi kết nối bằng domain WAN bị timeout 30s (`WinError 10061`).
  + **Giải pháp chuẩn:** Server MikroTik thực tế nằm tại IP LAN `192.168.110.2:10001..10035`. BẮT BUỘC map file `C:\Windows\System32\drivers\etc\hosts`: `192.168.110.2 mirotik1.taadaa.click` để toàn bộ script host truy cập nội bộ với độ trễ siêu tốc (~0.45s).
  + **Tự động hóa Pool 67 Proxy cho Downloader:** Hợp nhất 32 cổng MobiProxy (`test.taadaa.click:5101..5132`) và 35 cổng MikroTik PPPoE LAN (`10001..10035`) qua `scripts/generate_67_proxy_pool.py`, xuất ra `proxy_pool_67.txt` làm pool master cố định cho toàn bộ downloader farm.
  + **Cơ chế Fail-over xoay Proxy:** Tuyệt đối không retry cục bộ trên 1 cổng proxy gặp lỗi (`[WinError 10061]`). Mọi vòng lặp tải metadata/video bắt buộc bắt ngoại lệ và gọi `next_proxy()` bốc ngay proxy mới từ pool để tiếp tục.
- **🚨 BẪY LỆCH GIỜ HỆ THỐNG S7 (NĂM 2016) GÂY LỖI SSL & FAKE "KHÔNG CÓ INTERNET" (2026-09-12):**
  + **Hiện tượng:** Máy kết nối Wi-Fi nhận IP bình thường, ping router thông, proxy sống, nhưng TikTok văng toast *"Không có kết nối Internet / Đã xảy ra lỗi / Thử lại sau"*, cờ `dumpsys connectivity` bị kẹt `lastValidated: false` vĩnh viễn dù proxy và mạng vẫn truyền được HTTP.
  + **Root cause:** Khi máy Samsung S7 bị reboot hoặc mất nguồn tạm thời mà setting `auto_time = 0` (tắt tự động cập nhật giờ), đồng hồ hệ thống bị tụt về mốc xuất xưởng (ví dụ `Sat Jan 2 2016`). Mọi kết nối HTTPS ra TikTok/Google bị từ chối ở tầng TLS handshake do chứng chỉ SSL năm 2026 chưa có hiệu lực tại thời điểm 2016 (`CertificateNotYetValid`).
  + **Kiểm tra O(1):** Chạy `adb -s <serial> shell date` so sánh với ngày giờ thực tế của PC host.
  + **Khắc phục tức thì:** Bật lại đồng bộ giờ tự động qua mạng:
    `adb -s <serial> shell "settings put global auto_time 1 && settings put global auto_time_zone 1"`
    Đồng hồ sẽ lập tức nhảy về năm 2026, Wi-Fi tự động chuyển `VALIDATED: true`, và TikTok load feed bình thường ngay lập tức mà không cần clear app data hay reboot.

- **🚨 BẪY GÁN PORT MIKROTIK TRỰC TIẾP & TIẾN HÓA BỎ PASS 3PROXY (2026-10-08):**
  + *Lịch sử (2026-09-12):* Trước đây dải port `10001..10035` trên MikroTik cài user/pass `admin@1:admin@1`. Android `settings put global http_proxy` không hỗ trợ auth nên gán trực tiếp bị lỗi `407 Proxy Authentication Required`.
  + *Tiến hóa kiến trúc (2026-10-08 — User Directive):* Đã gỡ bỏ hoàn toàn user/pass trên 3proxy container của MikroTik (`HTTP_USER=""`, `HTTP_PASS=""` trong `3proxy_envs`). Lý do: RouterOS đã có rule firewall `ALLOW_FPT_LAN_PROXY_PORTS` và `DROP_EXTERNAL_PROXY_PORTS` khóa chặt từ bên ngoài, chỉ cho phép subnet nội bộ `FPT_LAN` (`192.168.110.0/24`, `192.168.10.0/24`, `172.17.0.0/16`) sử dụng. Do đó không cần pass vẫn an toàn 100%.
  + *Checklist Bắt Buộc Đồng Bộ Full-Stack Khi Bỏ Pass Proxy MikroTik (ALL NƠI):*
    1. **MikroTik RouterOS:** PATCH `/container/envs/*3` và `*4` về rỗng `""` -> restart container `3proxy` (`*3`).
    2. **GPMLogin v3 (`:19995`):** Gọi API `PUT /api/v3/profiles/update/<id>` thay thế `raw_proxy` từ `mirotik1:port:user:pass` sang `mirotik1:port`.
    3. **9Router (`:20128`):** Gọi API `PUT /api/proxy-pools/<id>` gỡ bỏ `user:pass@` trong URL.
    4. **OmniRoute (`:20129`):** Cập nhật `proxy_registry` và JSON `provider_connections` trong `C:\Users\Kibe\.omniroute\storage.sqlite` (lưu ý: OmniRoute ưu tiên thư mục legacy `.omniroute` nếu tồn tại thay vì `AppData\Roaming`).
    5. **Excel Workbooks:** Cập nhật cột proxy trong cả `kibe/PROXYgandienthoai.xlsx` và `admin/PROXYgandienthoai.xlsx`.
    6. **Thiết bị Farm (ADB):** Gán thẳng `192.168.110.2:100xx` không pass cho dàn Admin qua `set_proxy_farm_admin_adb.py`.
  + *Bẫy Phân Biệt S7 ADB `offline` vs `missing` vs Nguồn Box:*
    * Khi user thắc mắc *"trên box đèn vẫn sáng, cáp vẫn nhận nhưng sao máy bị dis/offline"*: Đèn box sáng chứng minh chân nguồn 5V vẫn cấp điện nuôi máy, KHÔNG phải do mất nguồn.
    * Sự cố do Windows USB Selective Suspend ngắt kênh truyền Data để tiết kiệm điện và phần mềm điều khiển màn hình tập trung (Xiaowei/Zhiwei) giữ chặt I/O handle khiến ADB handshake thất bại. Cần kích hoạt High Performance Power Plan và tắt triệt để `EnhancedPowerManagementEnabled`, `DeviceSelectiveSuspended` trên toàn bộ USB Hubs trong Device Manager.
  + *Áp dụng hiện tại:*
    * **Dàn Admin (201..280):** Gán trực tiếp qua ADB vào cổng MikroTik PPPoE `192.168.110.2:10008..10035` (`set_proxy_farm_admin_adb.py`). Chạy trực tiếp không cần auth, độ trễ thấp nhất.
    * **Dàn Kibe (01..80):** Duy trì Sing-box `192.168.110.2:20001..20080` do phân luồng giữa MobiProxy (51xx) và MikroTik.
  + **Bắt buộc Fail-Closed trong Preflight:** Mọi máy đã map trong Excel BẮT BUỘC phải có `global http_proxy` khác `:0`. Nếu mất proxy hoặc rớt về `:0`, preflight văng lỗi dừng ngay, CẤM TUYỆT ĐỐI fallback sang cURL direct Wi-Fi.

- **Phân Biệt "Máy Có Mạng / Proxy 200 OK" vs "TikTok Bị Chặn / Không Load Được Feed" (2026-09-12):**
  + Khi probe hạ tầng (`toybox nc`, `curl -x`, ping) trả về `HTTP 200 OK` (hoặc test `generate_204` trả `204 No Content`), điều đó chứng minh đường truyền LAN, Sing-box, và upstream PPPoE/Proxy hoàn toàn sống.
  + **TUY NHIÊN**, nếu IP Public của line PPPoE đó (ví dụ dải IP bị dính blacklist của TikTok CDN/API) bị chặn hoặc trả lỗi `403 Forbidden` trên CDN / `404` trên auth endpoint: App TikTok trên thiết bị sẽ hiển thị *"Đã xảy ra lỗi / Thử lại sau"* (kèm nút `dcj` Thử lại) và không thể xem feed bình thường dù máy vẫn có mạng internet.
  + Khi user báo *"mất mạng"*, Coordinator phải kiểm tra song song: (1) Hạ tầng mạng/proxy thiết bị, và (2) Khả năng tải nội dung thật của app TikTok (mở app, đọc XML/screencap, nếu lỗi feed thì force-stop đóng app ngay tránh treo máy). Nếu IP bị TikTok chặn, cần reconnect PPPoE để đổi sang dải IP mới.

## Lệnh vận hành chuẩn
- **Gán proxy ADB cho máy mới/bật lại/toàn farm:**
  * Dàn Kibe (Máy 01..80): `python D:\Taadaa\AI-Tools\scripts\set_proxy_farm_adb.py --machines <ID>` (bỏ trống `--machines` để gán cả 80 máy vào Singbox `20001..20080`).
  * Dàn Admin (Máy 201..280): `python D:\Taadaa\AI-Tools\scripts\set_proxy_farm_admin_adb.py --machines <ID>` (gán toàn bộ máy vào Sing-box mixed inbound `192.168.110.2:20201..20280` tương ứng `20000+N`). Sing-box sẽ tự inject `admin@1:admin@1` chuyển tiếp ra dải MikroTik PPPoE `10008..10035`, giải quyết triệt để lỗi Android HTTP 407 và chặn đứng nguy cơ lộ IP Direct FPT `:0`!
- **Kiến Trúc Sing-box Đồng Nhất Toàn Farm (160 Inbound Ports) (2026-10-08):**
  * Container Sing-box trên MikroTik (`192.168.110.2`) phục vụ cả 2 cụm:
    - Kibe (1..80): Port `20001..20080` $\to$ upstream MobiProxy 51xx & MikroTik 10001..10007.
    - Admin (201..280): Port `20201..20280` $\to$ upstream MikroTik PPPoE 10008..10035.
  * Sinh cấu hình: `python D:/Taadaa/AI-Tools/scripts/generate_singbox_config.py` tự động gộp cả 2 file `kibe/PROXYgandienthoai.xlsx` và `admin/PROXYgandienthoai.xlsx`.
  * MikroTik Firewall: Rule NAT `*30E` và Filter `*15` / `*13` mở dải `20001-20280`.
- **Quy trình Đổi IP Đường PPPoE MikroTik & Bắt Buộc Restart Sing-box (2026-09-12):**
  1. *Thời gian ngắt kết nối BRAS:* Khi cần đổi IP cho 1 line PPPoE (`pppoe-outX`), nếu disable rồi enable lại quá nhanh (<15s), BRAS nhà mạng (Viettel/FPT) sẽ cấp lại **chính xác IP cũ**. BẮT BUỘC giữ `disabled=true` tối thiểu **30–35 giây** qua REST API hoặc script để giải phóng hoàn toàn session lease trên BRAS, sau đó mới bật lại để nhận dải IP mới.
  2. *Bắt buộc Restart Container Sing-box sau khi Line PPPoE đổi IP:* Khi line PPPoE thay đổi Public IP, các persistent socket upstream trong container Sing-box (`*6`) bị reset (`WinError 10054 / An existing connection was forcibly closed by remote host` hoặc `502 Bad Gateway`). BẮT BUỘC restart container Sing-box:
     `POST /rest/container/stop` với `{".id": "*6"}` -> chờ 3s -> `POST /rest/container/start` với `{".id": "*6"}`.
  3. *Xử lý TikTok kẹt màn hình "Đã xảy ra lỗi / Thử lại sau":* Sau khi xoay sang IP mới sạch và restart Sing-box, mở lại app TikTok và tap nút *"Thử lại"* (`com.ss.android.ugc.trill:id/dcj`, tâm `540, 1200`), bảng tin feed sẽ tải lại bình thường. Sau khi kiểm tra xong, luôn force-stop app (`am force-stop com.ss.android.ugc.trill`) đưa máy về Launcher.
- **Quy trình Hot-Update Cấu hình Sing-box từ Excel lên MikroTik (O(1)):**
  Khi thay đổi proxy mapping trong `PROXYgandienthoai.xlsx` (ví dụ chuyển máy sang dải PPPoE `mirotik1:10001..10007`):
  1. Sinh config JSON:
     `python D:/Taadaa/AI-Tools/scripts/generate_singbox_config.py --excel D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx --output D:/Taadaa/AI-Tools/config/singbox_config.json`
  2. Nạp file trực tiếp vào MikroTik qua REST API (không cần Winbox):
     Gửi request `PATCH http://192.168.110.2:9090/rest/file/*8072575` (file `docker/config/config.json`) với JSON `{"contents": "<full_json>"}` kèm header `Authorization: Basic YWRtaW46TjBzcGFtQEA=`.
  3. Khởi động lại container Sing-box:
     `POST /rest/container/stop` với `{".id": "*6"}` -> chờ 3s -> `POST /rest/container/start` với `{".id": "*6"}`.
  4. Xác thực kết nối:
     Kiểm tra probe từ host Kibe: test `http://connectivitycheck.gstatic.com/generate_204` qua proxy `http://192.168.110.2:20000+N` -> phải trả `HTTP 204`.
     Từ thiết bị S7 qua `toybox nc`.
     *Lưu ý đường dẫn ADB trên host Kibe:* `adb` không nằm trong `$PATH` của Git-Bash; dùng đường dẫn chuẩn `"/c/Program Files (x86)/xiaowei/tools/adb.exe"` (hoặc `C:\Program Files (x86)\xiaowei\tools\adb.exe`).
- **Phân biệt Lệch Mapping (Live Router vs File Excel vs GPM Profile):**
  Khi user hỏi máy N đang map với port nào mà có mâu thuẫn giữa các nguồn:
  + Nguồn 1: Cấu hình đang nạp thực tế trong container Sing-box (`singbox_config.json` trên MikroTik).
  + Nguồn 2: File quy hoạch chuẩn của user (`D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`).
  + Nguồn 3: Cấu hình proxy thực tế lưu trong GPM SQLite (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`).
  + **Bẫy lệch proxy GPM (2026-10-05):** Cột `Profiles.Name` chỉ là nhãn hiển thị ngoài UI (ví dụ `M13 - 5115 - ...`). Proxy thực sự của Chrome chạy theo trường `"Proxy"` trong chuỗi JSON ở cột `JsonData`. Nếu chỉ đổi tên profile ngoài UI mà không sửa `JsonData["Proxy"]`, profile sẽ chạy sai đường proxy (ví dụ kẹt `mirotik1:10021`). Luôn truy vấn `JsonData` để kiểm tra proxy thực tế của GPM profile. Quy trình chi tiết và truy vấn SQLite nằm ở `references/gpm-profile-proxy-desync-and-sqlite-jsondata-trap.md` trong skill `gpm-account-pool-automation`.
  Nếu router hoặc GPM chưa được sync lại, cấu hình live sẽ chạy theo bản cũ. Cần giải thích rõ nguồn nào đang chạy thực tế và nguồn nào là quy hoạch Excel, sau đó đồng bộ chuẩn xác.
- **Quy hoạch 1 Port = 2 Máy (Farm Kibe 80 máy) & Quy Tắc Cấp Tạm Tối Đa 3 Máy (2026-09-18):**
  - Toàn bộ 80 máy dùng đúng 40 proxy (mỗi proxy chia đều đúng 2 máy).
  - Cụm MikroTik PPPoE: `M33/M72` (10001), `M34/M73` (10002), `M35/M74` (10003), `M36/M75` (10004), `M37/M77` (10005), `M71/M78` (10006), `M79/M80` (10007).
  - Cụm MobiProxy: Các máy `01..32` ghép cặp với `39..70` qua `test.taadaa.click:5101..5138`.
  - **Quy tắc Cấp Proxy Tạm Thời Khi Upstream Chết (Emergency Temp Reassignment):**
    + Khi một line upstream bị chết (ví dụ `khoalee.duckdns.org` sập port), cho phép mượn tạm proxy đang sống khác trong farm Kibe.
    + **Nguyên tắc trần tỷ lệ:** Mỗi máy chết được gán vào 1 proxy sống riêng biệt, nâng số lượng máy dùng chung proxy đó từ 2 lên **TỐI ĐA 3 MÁY / PROXY**. Tuyệt đối không dồn quá 3 máy vào 1 port proxy.
    + **Ưu tiên hạ tầng:** Ưu tiên mượn dải MikroTik PPPoE LAN (`10001..10007`, ping ~50-70ms) thay vì MobiProxy remote để giữ độ trễ thấp và ổn định.
    + **Thực thi:** Cập nhật `PROXYgandienthoai.xlsx` -> chạy `generate_singbox_config.py` -> PATCH `docker/config/config.json` lên MikroTik -> restart container Singbox `*6` -> probe test HTTP 204 và chụp ảnh nghiệm thu.
- **Bản Chất Cụm MobiProxy test.taadaa.click (Thái Bình — Viettel PPPoE Multi-Session):**
  + Cụm box tại Thái Bình là router OpenWrt (MT7621) quay số đa phiên PPPoE (`pppoe-proxy01`..`pppoe-proxy38`) trên 1 đường cáp quang Viettel để lấy dải IP dân cư động (`117.1.x`, `116.107.x`, `171.224.x`...), **KHÔNG PHẢI SIM/Dcom 4G**.
  + Trên web MobiProxy, phiên PPPoE có thể hiển thị trạng thái đã nhận IP từ Viettel, nhưng nếu service mở port proxy (51xx) bị dừng thì Sing-box sẽ lập tức reset connection làm máy S7 mất mạng.
  + Kiểm tra kỹ thuật: Dùng socket probe `connect_ex` hoặc gọi API `/proxy_check?proxy=test.taadaa.click:51XX`. Trả về `{"result":"ok","content":"proxy_ok"}` là cổng sẵn sàng.
- **MobiProxy NAT Cổng Proxy (`legacy.nat_port`):** BẮT BUỘC PHẢI BẬT (`1`). Nếu TẮT (`nat_port: 0`), OpenWrt firewall trên box sẽ chặn toàn bộ kết nối WAN từ xa (Đà Nẵng / Sing-box) vào các cổng proxy `5101..5138` (`Connection refused` / `10061`), khiến Sing-box trả về `HTTP/1.1 502 Bad Gateway` và toàn bộ dàn máy S7 mất mạng hoàn toàn (`dumpsys connectivity` báo `lastValidated: false`). Khi BẬT (`nat_port: 1`), firewall OpenWrt mở luồng NAT/forwarding cho các cổng `51xx`, Sing-box lập tức trả về `200 OK` kèm đúng IP Public dân cư Viettel của từng luồng PPPoE và S7 có mạng trở lại (`lastValidated: true`). Chi tiết xem `references/mobiproxy-web-ops-and-auth-troubleshooting.md`.
- **Chống Spam Reset IP & Bảo vệ Cổng 1 (5101) Box MobiProxy:** Script watchdog/auto-healer (`mobiproxy_auto_healer.py`) BẮT BUỘC có Single-Instance Lock, Per-port Cooldown (300s), Cap tối đa 4 port/lần, giãn cách 2.0s giữa các API call. Trong script watchdog tự động chạy nền, giữ Cổng 1 (5101) trong `PROTECTED_HEAL_PORTS = {5101}` tránh flapping DDNS `test.taadaa.click`. *Lưu ý quan trọng khi User chỉ đạo hoặc khi cần tẩy sạch dải IP (Tainted Proxy Rotation):* Cổng 5101 hoàn toàn gửi lệnh `/proxy_recreat` đổi được bình thường, modem quay số xong daemon DDNS tự đẩy IP mới lên DNS sau 15s (xem chi tiết tại `references/tainted-proxy-rotation-and-decontamination.md`). Cron interval phải đặt `>= 5 phút` (`*/5 * * * *`), tránh đặt `*/1` gây treo daemon quản lý Nginx/USB của box. Khi cổng 1/DDNS rụng hoặc Nginx dính 502 Bad Gateway kéo dài do botnet quét, BẮT BUỘC pause ngay cron healer để tránh làm nghẽn CPU box.
- **Bão Scan Botnet & Vấn Đề Conntrack NAT Port (2026-09-09):** Khi mở NAT (`nat_port: 1`), botnet quét IP Viettel làm tràn bảng conntrack MT7621 khiến web admin sập (502 / timeout). Cloudflare không che được các cổng TCP proxy 51xx. Quy trình cứu box tự động: chạy watchdog loop bắt CSRF ngay khi PHP cổng 80 vừa nhả để gửi lệnh tắt NAT khẩn cấp (`proxy.nat` -> `enabled: false`). Về lâu dài yêu cầu seller đặt whitelist IP nguồn (IP Kibe/FPT) ngay tại firewall port forwarding của OpenWrt.
- **Sự Cố Bot Quét Brute-Force Proxy Public Gây Quá Tải Box OpenWrt (2026-09-09):**
  - *Hiện tượng:* Các cổng proxy 51xx mở ra Internet (`test.taadaa.click:5101..5138`) thường xuyên bị bot Internet quét IP/port và brute-force đăng nhập sai pass liên tục. Router OpenWrt (MT7621) bị cạn kiệt connection tracking / CPU, khiến web quản trị rơi vào `HTTP 502 Bad Gateway` hoặc rớt PPPoE cổng 1 làm mất DDNS.
  - *Hành động của bên bán:* Bên bán tắt `nat_port` (chặn WAN vào 51xx) để box hạ tải rồi reset IP toàn bộ port. Phải chờ 1-2 tiếng sau khi bên bán bật lại natport mới kết nối lại được.
  - *Quy tắc vận hành bên mình:* Khi phát hiện box sập hoặc bên bán thông báo đang tắt natport để hạ tải, **BẮT BUỘC pause ngay lập tức cronjob `mobiproxy-auto-healer-watchdog`**. Tuyệt đối không để script chạy nền tiếp tục bắn probe TCP / API `/proxy_recreat` dồn dập vào box đang nghẽn.
- **Truy vết Lịch sử Reset IP MobiProxy (O(1)):**
  + Cronjob: `mobiproxy-auto-healer-watchdog` (chạy mỗi 5 phút qua `cron_mobiproxy_healer.py` gọi `D:\Taadaa\AI-Tools\scripts\mobiproxy_auto_healer.py --check-and-heal`).
  + Log & Stats: `D:\Taadaa\AI-Tools\logs\mobiproxy_healer.log` (~750KB) và `mobiproxy_stats.json` (chứa `summary`, `ports`, `last_heal_times`).
  + Cú pháp timestamp log: `^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]` (có dấu ngoặc vuông).
  + Kiểm tra an toàn Cổng 1 (5101): Tìm các dòng `Triggering /proxy_recreat for port 5101` (phải bằng 0). Các dòng `[WARNING] [PROTECTED] Port 5101 is in PROTECTED_HEAL_PORTS. Skipping auto-heal to protect DDNS binding.` xác nhận cơ chế bảo vệ cổng đầu đang hoạt động chuẩn xác.
- **Kiểm tra trạng thái & fix Singbox:**
  `python D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py --check` / `--fix`.
- **Xác thực Egress IP từ PC:**
  `curl -s -m 10 -x http://192.168.110.2:<PORT> http://api.ipify.org`
  (Egress IP phải khác Direct IP farm `42.114.218.81`).
- **Xác thực từ thiết bị S7 (qua atx-agent curl hoặc toybox nc):**
  - *Lưu ý quan trọng:* `atx-agent` là Go binary không tự đọc Android `settings global http_proxy`. Nếu chạy trơn không có env proxy, nó sẽ đi Direct Wi-Fi. Bắt buộc truyền env `http_proxy` hoặc dùng `toybox nc`:
  ```bash
  # Cách 1: atx-agent curl với env proxy
  adb -s <serial> shell "http_proxy=http://192.168.110.2:<PORT> /data/local/tmp/atx-agent curl --timeout=5s http://api.ipify.org"

  # Cách 2: toybox nc (khuyên dùng, kiểm tra trực tiếp raw HTTP stream)
  adb -s <serial> shell 'printf "GET http://api.ipify.org/ HTTP/1.1\r\nHost: api.ipify.org\r\nProxy-Connection: close\r\n\r\n" | toybox nc -w 4 -W 4 -q 1 192.168.110.2 <PORT>'
  ```

## When to use
- Khi máy bị mất proxy, reboot lại hoặc mới cắm vào farm.
- Khi cần kiểm tra / gán lại proxy định tuyến toàn bộ dàn máy Kibe (1..80).
- Task liên quan đến hạ tầng mạng, MikroTik, Singbox, IP proxy của farm.



## MikroTik & Sing-box Proxy Architecture (2026-08-31)

Toàn bộ 80 máy Kibe chạy qua router MikroTik RouterOS (7.18.2) và Container Sing-box:
- **Router Quản trị:** REST API `192.168.110.2:9090` / `mirotik1.taadaa.click` (user `admin`, pass `N0spam@@`).
- **DNS Failure Distinction (2026-09-09):** `mikrotik1.taadaa.click` DNS record có thể biến mất/hết hạn (NXDOMAIN trên 8.8.8.8/1.1.1.1). Khi OmniRoute proxy logs báo ERROR rate cao trên `mikrotik1.taadaa.click:XXXX` nhưng PPPoE interfaces vẫn CONNECTED → đó là lỗi DNS, KHÔNG PHẢI lỗi router hay port. Luôn check `nslookup` trước khi kết luận router hỏng. Chi tiết trong `proxy-preflight-verification` → `references/mikrotik-api-and-port-probe-architecture.md`.
- **Cụm 80 cổng Sing-box:** Port `20001..20080` (`20000 + Số máy`).
- **35 Line PPPoE:** Dải upstream `10001..10035` (`admin@1:admin@1`).
- **Hardware Kill-Switch:** MikroTik Firewall tự động DROP toàn bộ traffic ra ngoài nếu máy chưa trỏ proxy `192.168.110.2:2000N` qua ADB để chống lộ Direct IP.
- **Tài liệu toàn tập:** `D:\Taadaa\AI-Tools\docs\infrastructure\mikrotik\mikrotik-master-network-handbook.md`.

## Quy tắc giao tiếp & Báo cáo lỗi gửi Admin / Bên ngoài (BẮT BUỘC)
Khi người dùng yêu cầu soạn nội dung báo cáo lỗi gửi admin bên ngoài / nhà cung cấp:
- **CHỈ GHI HIỆN TƯỢNG VÀ MÃ LỖI:** Nêu rõ Host, Port, mã lỗi (ví dụ: `Connection Refused`, `Timeout`, `HTTP 407`).
- **CẤM THÊM GIẢI PHÁP / HƯỚNG DẪN:** Tuyệt đối không tự ý viết thêm hướng dẫn fix, bước xử lý hay gợi ý cấu hình router trừ khi người dùng yêu cầu rõ ràng.
- **KỶ LUẬT LƯU TRỮ CASE STUDY & POSTMORTEM (User Correction 12/09/2026):**
  + Khi người dùng nói "lưu case này lại", **BẮT BUỘC lưu thẳng vào Git repository**:
    * Hạ tầng / Mạng / Proxy / Tools vận hành: lưu tại `D:\Taadaa\AI-Tools\docs\` (ví dụ: `farm-automation-cases.md`, `docs/infrastructure/`).
    * Script / Hook automation: lưu tại `D:\Taadaa\automation-core\docs\farm-automation-cases.md`.
  + **TUYỆT ĐỐI CẤM** tự ý tạo file postmortem vào thư mục `skills/` (chỉ dùng skill để hướng dẫn quy trình/công cụ cho agent, không dùng làm kho lưu case study dự án của farm).



## Pitfalls

- **🚨 BẪY TỰ Ý NHẢY SSID VÃNG LAI ("Dat") & QUY HOẠCH CỨNG PHÂN VÙNG WI-FI (2026-10-09 — USER CORRECTION):**
  * *User correction cốt tử:* Khi máy gặp lỗi Wi-Fi (`ASSOCIATION_REJECTION` từ AP chính), CẤM TUYỆT ĐỐI auto-healer hay agent tự ý nhảy sang SSID vãng lai ngoài luồng như `Dat` ("bị ngáo à, nhảy qua cái Dat thì có fake proxy k hay lộ mẹ ip direct").
  * *Bản chất rủi ro:* Mạng `Dat` cấp IP subnet `192.168.10.x` (khác dải LAN farm chuẩn `192.168.110.0/24`), gây lệch routing tới Sing-box Inbound `192.168.110.2:2000N` trên MikroTik, làm timeout kết nối proxy và tiềm ẩn nguy cơ an toàn IP.
  * *Quy hoạch cứng bất khả xâm phạm:*
    - M1–M40: Cố định `kibe 1` (Pass: `23102025`).
    - M41–M80: Cố định `kibe 2` (Pass: `19051995`).
    - M201–M240: Cố định `admin 1` (Pass: `19051995`).
    - M241–M280: Cố định `admin 2` (Pass: `19051995`).
  * *Xử lý bẫy `ASSOCIATION_REJECTION`:* Khi bị AP từ chối, Android 8 khóa cứng SSID vào `NETWORK_SELECTION_TEMPORARY_DISABLED`. Toggle `svc wifi` hay reboot không xóa được cờ. Dùng `adb-join-wifi.apk` với đúng SSID & Password để gọi `WifiManager.enableNetwork(netId, true)` từ tầng Java. Lưu ý: `adb-join-wifi` tự wrap `"` quanh SSID và Password, không truyền thêm dấu ngoặc kép. Nếu máy không kết nối được SSID chính sau 2 cấp cứu hộ, giữ nguyên lỗi để Watchdog báo cáo hiện trường cho kỹ thuật viên xử lý AP, CẤM đổi SSID. Chi tiết: `references/strict-wifi-partitioning-and-association-rejection-heal.md`.

- **🚨 BẪY ADMIN PC BỊ CƯỚP DHCP (ARUBA AP ROGUE DHCP) GÂY TREO RDP VÀO KIBE PC (2026-10-09):**
  * *Hiện tượng:* Người dùng mở Remote Desktop (`mstsc.exe`) trên Admin PC để vào Kibe PC (`192.168.110.123`) bị treo cứng ở *"Initiating remote connection..."*. Từ Kibe PC ping và SSH sang `192.168.110.119` bị 100% packet loss / timeout.
  * *Bản chất kỹ thuật:* AP Aruba IAP-315 (`192.168.110.251`) phát DHCP Offer dải `192.168.10.x` cướp lease card mạng Admin PC gán sang `192.168.10.77` (Gateway `192.168.10.254` trên MikroTik). Do Kibe PC dùng Gateway `192.168.110.1` (Ruijie) không có route về `192.168.10.0/24`, gói SYN-ACK bị Ruijie drop dẫn đến nghẽn định tuyến bất đối xứng (asymmetric routing stall).
  * *Quy trình cứu hộ O(1) qua MikroTik Jump-Host Tunnel:*
    1. Soi bảng ARP MikroTik qua REST API tìm MAC `22:33:4D:06:4C:26` để bốc IP lạc (`192.168.10.77`).
    2. Tạo cặp NAT rule tạm thời trên MikroTik: `dstnat` port 2222 -> `192.168.10.77:22` và `srcnat` masquerade.
    3. SSH qua cổng 2222, đẩy lệnh set IP tĩnh `192.168.110.119/24` (Gateway `192.168.110.1`, DNS `8.8.8.8, 1.1.1.1`, Persistent Route `192.168.10.0/24 -> 192.168.110.2`) bất đồng bộ qua `wmic process call create`.
    4. Xóa ngay 2 NAT rule tạm trên MikroTik, taskkill `mstsc.exe` treo cũ trên Admin.
    5. Chi tiết: xem `references/admin-pc-rdp-stall-and-rogue-dhcp-rescue.md`.

- **🚨 BẪY PHÂN BIỆT "MẤT WI-FI" VS "CHƯA GÁN PROXY / PROXY :0" TRONG BÁO CÁO WATCHDOG & PREFLIGHT (2026-10-09):**
  * *Hiện tượng:* Watchdog báo hàng loạt máy dính lỗi `Mất Wi-Fi/Proxy` khiến người dùng tưởng hệ thống mạng Wi-Fi hoặc router của farm bị sập ("Mạng cả đống sao báo lỗi Wi-Fi").
  * *Bản chất kỹ thuật:*
    1. Bộ lọc watchdog (như trong `feed_session_watchdog.py`) gom chung mọi từ khóa `wifi`, `wlan0`, `proxy`, `network` vào một nhãn hiển thị duy nhất là `Mất Wi-Fi/Proxy`.
    2. Thực tế phần lớn máy (chiếm >60-70% các ca fail dạng này) **vẫn bắt Wi-Fi và có Internet hoàn toàn bình thường**, nhưng bị kẹt ở chốt chặn an toàn `vpn_preflight` do:
       - **Thiếu cấu hình Proxy trên máy (`settings global http_proxy is missing or :0`):** Máy sau khi reboot hoặc lỏng USB bị mất biến proxy toàn cục. Preflight phát hiện không có proxy nên kích hoạt Fail-Closed Shield chặn đứng ngay lập tức để chống lộ Direct IP nhà mạng FPT.
       - **Cổng proxy MikroTik bị nghẽn egress:** Request kiểm tra IP ra `api.ipify.org` bị timeout/drop tại thời điểm tiền kiểm.
       - **Wi-Fi thật sự rớt:** Chỉ khi log ghi nhận `ASSOCIATION_REJECTION` (AP quá tải slot kết nối) hoặc `dumpsys connectivity: Wi-Fi not connected`.
  * *Quy tắc điều phối & Báo cáo chuẩn:*
    * Khi user thắc mắc hoặc khi phân tích log, **tuyệt đối không kết luận Wi-Fi hỏng khi chưa kiểm tra `dumpsys wifi` và `settings get global http_proxy`**.
    * Báo cáo phải bóc tách rõ: (1) Máy mất Wi-Fi thật, (2) Máy thiếu Proxy (`:0`), (3) Cổng proxy nghẽn egress.
    * Khắc phục O(1): Với máy bị `:0`, chạy lại script phủ proxy ADB (`set_proxy_farm_adb.py` cho Kibe, `set_proxy_farm_admin_adb.py` cho Admin) thay vì can thiệp vào router/AP.

- **🚨 BẪY QUÊN GÁN PROXY TRÊN DÀN ADMIN & QUY TRÌNH DẬP TẮT KHẨN CẤP 3 LỚP (2026-10-08):**
  * *Bản chất sự cố:* Cụm MikroTik Admin (`10008..10035`) bị mất mạng/timed out, nhưng dàn S7 Admin (201–280) vẫn mở TikTok chạy ầm ầm do trên máy chưa được gán proxy (`settings get global http_proxy` là `:0`). Hàm preflight thấy `:0` nhảy sang fallback direct Wi-Fi Ruijie AP bắt trúng IP mạng nhà FPT `1.53.55.190`, ngộ nhận là live IP hợp lệ gây Direct IP Leak toàn dàn.
  * *Quy trình Dập tắt Khẩn cấp 3 Lớp (Emergency Kill):*
    1. **Tầng 1 (Host Kibe):** Dừng tiến trình batch orchestrator `run-feed-session.ps1` và `run_tiktok.py` chỉ định dàn máy admin:
       `powershell "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'admin.taikhoan_run_safe|201,202,203' } | Stop-Process -Force"`
    2. **Tầng 2 (Host Admin via SSH):** Kill toàn bộ tiến trình workflow con trên PC Admin:
       `ssh admin-farm "powershell \"Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'tiktok_workflow' } | Stop-Process -Force\""`
       (nếu kẹt, dùng `taskkill /F /PID <PID> /T`).
    3. **Tầng 3 (Dàn máy thật via ADB đa luồng):** Chạy script đa luồng ADB (`ThreadPoolExecutor(max_workers=30)`) phát đồng loạt:
       `am force-stop com.ss.android.ugc.trill && input keyevent 3`
       Quét lại `pidof com.ss.android.ugc.trill` đảm bảo 100% thiết bị đã tắt app và về HOME.
  * *Khắc phục sau sự cố:* Bắt buộc chạy `python D:\Taadaa\AI-Tools\scripts\set_proxy_farm_admin_adb.py` để phủ lại proxy MikroTik cho 80 máy trước khi cho phép chạy lại bất kỳ flow nào.

- **Router onboarding over a direct Ethernet cable (Windows): verify the physical path before touching configuration.** A Windows adapter showing `Connected` or `Unidentified network` only proves link-layer state; it does not prove that the adapter is connected to the target Xiaomi/OpenWrt router. Before opening a browser or attempting SSH: (1) identify the exact adapter and its IPv4 address from `ipconfig`; (2) unplug/replug the cable and confirm that the same adapter changes link state; (3) read the actual default gateway/ARP entry; (4) probe the candidate management IP on HTTP/HTTPS/SSH. Do not infer the router IP from a shop sticker or from an assumed subnet (`192.168.5.1`, `192.168.88.1`) until a probe succeeds. Keep the farm/MikroTik Ethernet adapter untouched. If all candidate probes time out, report that remote configuration is not yet possible and ask for an adapter/port photo or exact link-state evidence; do not claim that setup is complete and do not drive UI actions blindly.

- **🚨 BẪY GỬI ROUTER RA TỈNH KHI CHƯA STAGING WAN DHCP & REVERSE TUNNEL (2026-10-08):**
  * *Bản chất sự cố & Cạm bẫy:* Khi chuẩn bị router OpenWrt (như Xiaomi R3G) để gửi ra tỉnh/xa quay PPPoE, nếu set cứng PPPoE với tài khoản ở nhà (hoặc tài khoản chưa active ở tỉnh) rồi đóng gói gửi đi: Khi người nhận cắm vào modem gia đình thông thường (cấp mạng qua DHCP), router KHÔNG THỂ quay PPPoE $\rightarrow$ không có internet $\rightarrow$ rớt toàn bộ kết nối từ xa. Lúc đó muốn cấu hình lại bắt buộc người ở xa phải có laptop cắm dây LAN và bật UltraViewer cực kỳ phiền toái.
  * *Sai lầm cắm cáp vào cổng LAN:* Cổng LAN chạy DHCP Server phát IP nội bộ; nếu cắm dây từ modem nhà vào cổng LAN sẽ bị xung đột 2 DHCP Server (loop/conflict) và router không có default gateway ra internet. Muốn nhận mạng từ modem nhà bắt buộc phải cắm vào cổng WAN.
  * *Kỷ luật Staging Offsite chuẩn 100%:*
    1. Cổng WAN (xanh) **bắt buộc để ở chế độ DHCP (`proto='dhcp'`)** trước khi đóng thùng.
    2. Cài sẵn **Overlay Tunnel ngầm tự động (WireGuard hoặc ZeroTier/Tailscale)** tự động kết nối outbound về Farm khi có bất kỳ kết nối internet nào.
    3. Khi gửi ra, người nhận chỉ cần cắm điện và cắm dây từ modem nhà vào cổng WAN. Router tự nhận DHCP có internet $\rightarrow$ Đường hầm tự kích hoạt đâm về Farm.
    4. Kỹ thuật viên ở nhà SSH/Web vào qua IP đường hầm để cấu hình đầy đủ (MACVLAN, mwan3, gán 16 IP, nạp sẵn user/pass PPPoE).
    5. Sau khi thợ chuyển modem sang Bridge mode, kỹ thuật viên từ xa mới chuyển cổng WAN sang PPPoE, tuyệt đối không bao giờ lo mất liên lạc.
  * *Kiến trúc Multi-WAN trên Xiaomi R3G (16 IP Thái Bình) & Cổng Cứu Hộ:* Bẻ cổng `lan2` (trắng ngoài cùng) thành `wan2` (`uci del_list network.@device[0].ports='lan2'`, gán vào interface `wan2` trong firewall zone `wan`). WAN xanh cắm Line 1 (8 session PPPoE), WAN2 trắng cắm Line 2 (8 session PPPoE / cổng cứu hộ DHCP fallback), LAN1 trắng ở giữa cắm Switch Farm chia cho 80 máy S7. Khi cần 3+ line, dùng Smart Switch chia VLAN 802.1Q cắm Trunk vào WAN xanh.
  * *Tailscale trên Flash 32MB OpenWrt & Headless Auth:* Tuyệt đối KHÔNG cài bản binary Go chính thức (`tailscale_mipsle.tgz` 35MB nén >70MB giải nén gây tràn flash); dùng bản OpenWrt IPK (`tailscale` + `tailscaled` ~9MB cài đặt). Chạy `tailscale up` ngầm và trích xuất URL duyệt web qua `tailscale status` / `logread` để tránh treo SSH. Chi tiết xem `references/xiaomi-r3g-multi-wan-and-offsite-staging-discipline.md`.

- **🚨 BẪY RÚT DÂY WAN1 MIKROTIK & SẬP TOÀN BỘ 60 POOL PPPOE (2026-10-06):** Cổng vật lý WAN1 trên MikroTik Soft Router (`192.168.110.2`) đang gánh đồng thời 60 interface macvlan (`macvlan1..macvlan60`) cho 60 client PPPoE (`pppoe-out1..pppoe-out60`). Tuyệt đối KHÔNG rút dây mạng ở cổng WAN1 để test router/box khác trừ khi có kế hoạch downtime toàn farm.

- **🚨 INVARIANT AEVB (ACTION-EVIDENCE VERIFICATION BARRIER — CHỐNG KHAI LÁO) (2026-10-06):**
  + `DISPATCH != RUNNING != SUCCESS`: Tuyệt đối cấm Coordinator tuyên bố thành công ("đã nạp xong", "đã hoàn thành") khi subagent chưa hoàn thành hoặc chưa có read-back evidence thực tế.
  + Cấm hướng dẫn User thực hiện thao tác vật lý (rút/cắm dây, đổi nguồn) khi trạng thái trước đó chưa đạt `VERIFIED_SUCCESS`.

- **🚨 BẪY TREO WEB MANAGER KIBE:2310 DO TRÙNG TIẾN TRÌNH PYTHON & SOCKET CONTENTION (2026-09-13):**
  - *Hiện tượng:* Người dùng mở `http://kibe:2310` trên Chrome thì web bị treo cứng: Header báo `⏳ Connecting...`, các thẻ RUNNING / DOWN / DISABLED / TOTAL chỉ hiện dấu gạch ngang (`-`), bảng interfaces xoay antenna `Loading...` vĩnh viễn không load được danh sách proxy.
  - *Nguyên nhân kỹ thuật:* Khi người dùng hoặc script khởi động `server.py` nhiều lần (ví dụ vừa chạy qua `run_hidden.vbs` vừa bật terminal/bat cũ), có **2 hoặc nhiều tiến trình Python cùng lắng nghe / kẹt trên port 2310** (hoặc tiến trình cũ kẹt socket TCP ở trạng thái `TimeWait`). HTTP server bị tắc luồng xử lý, request AJAX `/api/proxies` (vốn phải gọi MikroTik REST API để lấy 60 interfaces và đo uptime) bị drop hoặc timeout hoàn toàn.
  - *Quy trình xử lý O(1):*
    1. Quét tìm PID đang chạy `server.py`:
       `powershell "Get-CimInstance Win32_Process -Filter \"Name like '%python%' and CommandLine like '%server.py%'\" | Select ProcessId, CommandLine"`
    2. Kill sạch tất cả tiến trình `server.py` đang kẹt:
       `powershell "Stop-Process -Id <PID1>,<PID2> -Force"`
    3. Khởi động lại duy nhất 1 bản chạy ngầm qua launcher chuẩn:
       `powershell "Start-Process -FilePath 'wscript.exe' -ArgumentList 'D:\Taadaa\AI-Tools\tools\mikrotik_web\run_hidden.vbs' -WorkingDirectory 'D:\Taadaa\AI-Tools\tools\mikrotik_web'"`
       *Hoặc lệnh restart 1-dòng an toàn (không kill nhầm Python khác):*
       `powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 2310 -State Listen).OwningProcess -Force -ErrorAction SilentlyContinue; Start-Process (Get-Command python).Source -ArgumentList 'D:\Taadaa\AI-Tools\tools\mikrotik_web\server.py' -WindowStyle Hidden"` (bắt buộc có `-State Listen` để loại trừ kết nối TimeWait mang PID 0).
    4. Kiểm tra verify tức thì:
       `curl -s http://localhost:2310/api/status` (phải trả `connected: true` trong < 1.5s).
    5. Báo user chỉ cần bấm F5 lại tab Chrome là vào mượt ngay.

- **🚨 DECOMMISSIONING SITE CLOUD MIKROTIK (PAGES.DEV & WORKER) SANG LOCAL KIBE:2310 (2026-09-13):**
  - *Bối cảnh:* Trước đây hệ thống dùng song song `mikrotik-tool.pages.dev` + Cloudflare Worker `mikrotik-control.thanhdatbui1995.workers.dev` và web nội bộ `kibe:2310`.
  - *Lý do đóng site cloud:*
    1. Bảo mật yếu: Auth trên pages.dev check bằng client-side JS trong localStorage, API worker mở ra WAN dễ bị brute-force/scan botnet.
    2. Xung đột lịch đổi IP (Schedules) giữa Cloudflare Worker và local `server.py` (`schedules.json`).
    3. Trễ mạng và rủi ro rớt kết nối khi IP WAN thay đổi.
  - *Các bước đóng & cô lập RouterOS:*
    1. Siết Firewall Filter trên RouterOS: `PATCH /rest/ip/firewall/filter/*3` đặt `src-address-list: FPT_LAN` (chỉ cho phép `192.168.110.0/24`, `192.168.10.0/24`, `127.0.0.1`, `172.17.0.0/16` truy cập port 9090 REST API).
    2. Vô hiệu hóa rule NAT mở port 8090 từ WAN vào host: `PATCH /rest/ip/firewall/nat/*316` đặt `disabled: true`.
    3. Thống nhất tài liệu trong `AI-Tools` chuyển toàn bộ link sang `http://kibe:2310` hoặc `http://localhost:2310`.

- **🚨 BẪY CHẨN ĐOÁN MIKROTIK "TỰ RESET HOÀI" — TIẾNG "TÍC" HARDWARE REBOOT VS WATCHDOG PPPOE (2026-09-13):**
  - *Hiện tượng:* Người dùng nghe tiếng "tíc" phát ra từ phần cứng router và báo thiết bị tự reset liên tục (thực tế rớt mạng và đổi IP cổng 1 ít nhất 2 lần/tiếng).
  - *Bản chất kỹ thuật (Tiếng "tíc" phần cứng):*
    1. **Tiếng "tíc" = Còi chip BIOS POST / Rơ-le nguồn ngắt khi bo mạch khởi động lại:** Máy MikroTik này là PC x86 (Intel J4125 4-core, 8GB RAM). Khi máy kêu "tíc", đó là **REBOOT CỨNG / NGUỒN CỦA BO MẠCH**, hoàn toàn khác với việc ngắt line PPPoE mềm bằng script.
    2. **Thủ phạm 1: Hardware/Software Watchdog gốc ROM kích hoạt Reboot:** RouterOS có cấu hình mặc định hãng `/system watchdog watchdog-timer=yes ping-timeout=1m` (ĐÂY LÀ TÍNH NĂNG GỐC CỦA ROUTEROS TRONG KERNEL, KHÔNG PHẢI NGƯỜI DÙNG TỰ THIẾT KẾ). Khác hoàn toàn với script phần mềm `/system script watchdog-pppoe` (script 3m chỉ disable/enable line PPPoE dính CGNAT chứ không reboot máy). Khi cổng WAN bị tấn công SYN Flood hoặc brute-force dồn dập (trên port 8729 API-SSL hoặc 22/8291), kernel bị nghẽn dẫn đến watchdog timeout đếm ngược quá hạn và tự cưỡng chế ngắt nguồn reboot lại máy.
    3. **Thủ phạm 2: Nghẽn Socket & Resource Starvation dù CPU không tăng cao:** Con x86 4 core Intel có năng lực xử lý gói tin rất lớn, do đó khi bị scan/flood brute-force, CPU tổng vẫn hiển thị **2 - 3%** chứ không tăng vọt. Tuy nhiên, RouterOS giới hạn `max-sessions=20` trên các dịch vụ IP service. Khi botnet chiếm hết 20 socket chờ auth timeout, bảng kết nối bị mutex lock, mọi kết nối quản trị và heartbeat bị drop/timeout khiến watchdog tưởng kernel treo và ngắt nguồn.
    4. **Thủ phạm 3: Nguồn điện non tải / quá nhiệt:** Mini PC x86 vừa quay 35 PPPoE vừa chạy 3 Docker container (`sing-box`, `3proxy`, `api`). Nếu nguồn adapter 12V bị sụt áp (hoặc cắm chung ổ với dàn sạc 80 điện thoại farm), rơ-le nguồn sẽ nhảy ngắt máy.
  - *Quy trình khắc phục & Hardening chuẩn O(1) (Đã được Claude CLI & OmniRoute Review APPROVED 🟢):*
    * Khóa IP truy cập tầng socket: `/ip service set ssh address=192.168.110.0/24,192.168.10.0/24,100.64.0.0/10,42.112.229.255/32,42.118.214.93/32` (làm tương tự với `winbox`, `www`).
    * Tắt vĩnh viễn các service thừa dễ bị exploit/flood: `/ip service disable api,api-ssl,telnet,ftp,www-ssl`.
    * Tắt các vector scan lớp 2/WAN: `/tool bandwidth-server set enabled=no`, `/tool mac-server set allowed-interface-list=none`, `/tool mac-server mac-winbox set allowed-interface-list=none`.
    * Siết firewall filter rule port 8090 (Web Manager): bắt buộc gán `src-address-list=FPT_LAN`, cấm mở toang không lọc nguồn (`/ip firewall filter set 10 src-address-list=FPT_LAN`).
    * **Watchdog timer:** BẮT BUỘC BẬT LẠI `/system watchdog set watchdog-timer=yes` để làm phao cứu sinh cuối nếu router bị hang cứng thật sự; TUYỆT ĐỐI KHÔNG tắt vĩnh viễn vì sẽ làm router chết đứng nếu mất kết nối/đơ kernel mà không ai ở gần bấm nguồn vật lý.
    * Tắt log spam của container Sing-box: `/system logging set [find topics~"container"] disabled=yes`.
    * Cấu hình lưu log hệ thống ra đĩa SSD để tránh trôi log khi boot: `/system logging add action=disk topics=system,critical,warning,error`.
    * **QUY TẮC BACKUP LÊN REPO CÁ NHÂN (User Rule 2026-09-13):** Khi export file cấu hình backup RouterOS (`.rsc`), **TUYỆT ĐỐI KHÔNG TỰ Ý LỌC (SANITIZE) MẬT KHẨU/TOKEN/CREDENTIALS**. Vì repo `thanhdatbui/AI-Tools` là repository cá nhân nội bộ của user, việc lọc `***` làm máy admin khác hoặc script automation không thể import restore được cấu hình đầy đủ. Bắt buộc commit nguyên trạng bản export gốc (full raw config) lên Git.
    * **Audit & Review 2 Lớp (User Mandate 2026-09-13):** Mọi thay đổi lớn trên hạ tầng MikroTik/Network BẮT BUỘC phải gọi review độc lập: (1) OmniRoute combo `review` (:20129) để audit kiến trúc, và (2) Claude CLI (`claude -p`) quét dump JSON trạng thái thực tế để kiểm tra rà soát lỗ hổng sót trước khi chốt phiên.
    * Chi tiết xem `references/mikrotik-auto-reset-diagnosis-and-ssh-wan-hardening.md`.

- **🚨 BẪY SAMSUNG S7 "NO INTERNET AP" & CỜ `NET_CAPABILITY_VALIDATED` (2026-09-12):**
  - *Hiện tượng nghịch lý:* Trên máy S7, mở trình duyệt (Samsung Internet / Chrome) vào `api.ipify.org` hiển thị đúng IP mới và lướt web bình thường. Tuy nhiên, khi mở app TikTok thì văng ngay thông báo: *"Không có kết nối Internet. Vui lòng kết nối với Internet và thử lại"* và kẹt màn hình *"Đã xảy ra lỗi / Thử lại sau"*.
  - *Bản chất kỹ thuật:* Browser chỉ cần socket HTTP qua proxy toàn cục (`settings get global http_proxy`), nhưng app TikTok (engine TTNet/Cronet) kiểm tra cờ hệ thống `NetworkCapabilities.NET_CAPABILITY_VALIDATED`. Trên Samsung Android 8, nếu máy vừa boot hoặc kết nối Wi-Fi lúc proxy lỗi/chưa ready, tiến trình `WifiConnectivityMonitor` sẽ timeout captive portal và gán cờ `NetworkMonitor: No Internet AP - stay in current state` (`lastValidated: false`, Score tụt về 20).
  - *Tính chất bẫy:* Khi đã dính cờ này trong RAM `system_server`, tắt/bật Wi-Fi hay set lại proxy đều không xóa được cờ. TikTok thấy `VALIDATED: false` nên chủ động chặn request và báo lỗi mất mạng.
  - *Khắc phục chuẩn:* Đảm bảo proxy upstream và container Sing-box đã sống 100%, sau đó **soft-reboot lại máy** để Samsung xóa cờ phạt `No Internet AP` và cấp lại `VALIDATED: true`. Chi tiết xem `references/samsung-s7-no-internet-ap-and-tiktok-connectivity-trap.md`.

- **🚨 CẤM KẾT LUẬN FEED TIKTOK HỒI PHỤC KHI CHỈ ĐỌC TEXT XML NỀN (2026-09-12):**
  - *Bẫy quan sát:* Trong hierarchy XML của TikTok, các text viewpager như *"Chào mừng bạn trở lại!"*, *"Hãy thích và bình luận để xem thêm nội dung..."* vẫn nằm ở cây node bên dưới ngay cả khi màn hình đang bị che kín bởi dialog/lớp phủ lỗi mạng (`com.ss.android.ugc.trill:id/tux_status_view`, text *"Đã xảy ra lỗi / Thử lại sau"*, nút `dcj` *"Thử lại"*).
  - *Kỷ luật:* Coordinator TUYỆT ĐỐI KHÔNG được tuyên bố feed bình thường nếu chưa kiểm tra sự vắng mặt của các container lỗi (`tux_status_view`, `dcj`, `message_tv`) VÀ phải đối chiếu ảnh screencap thực tế.

- **⏱️ THỜI GIAN GIỮ NGẮT PPPOE ĐỂ NHẢ PHIÊN BRAS VIETTEL (>= 35 GIÂY) (2026-09-12):**
  - Khi ngắt kết nối PPPoE trên MikroTik (`/interface/pppoe-client/<id>` `disabled=true`) để đổi IP: Nếu enable lại quá nhanh (<15s), BRAS Viettel vẫn giữ lease cũ và cấp lại đúng IP vừa dùng (không đổi được IP).
  - BẮT BUỘC giữ `disabled=true` tối thiểu **30–35 giây** trước khi enable lại để BRAS cấp dải IP Public mới.
  - Sau khi line PPPoE có IP mới, BẮT BUỘC restart container Sing-box (`POST /rest/container/stop` -> wait 3s -> `start` với `{".id": "*6"}`) để tái tạo kết nối upstream, tránh lỗi `WinError 10054 / 502 Bad Gateway`.

- **BẪY ROUTEROS DEFAULT INPUT DROP KHI SIẾT WHITELIST SERVICE / API (2026-09-13):**
  - Khi thu hẹp rule firewall `chain=input` (ví dụ rule `*3` accept port 9090 REST API có `src-address-list=FPT_LAN`), nếu RouterOS **chưa có rule drop mặc định ở cuối chain input** (`action=drop, chain=input`), các gói tin từ WAN không khớp `FPT_LAN` sẽ tiếp tục đi lọt xuống cuối chain và được RouterOS chấp nhận ngầm định (default accept policy của RouterOS).
  - Kết quả: Cloudflare Worker bên ngoài hoặc IP lạ vẫn kết nối được vào port 9090 dù rule `*3` đã gán `FPT_LAN`.
  - **Cách xử lý triệt để:** Bắt buộc bổ sung rule DROP tường minh ở cuối chain input hoặc drop riêng port 9090 từ WAN:
    `/ip firewall filter add chain=input dst-port=9090 protocol=tcp in-interface-list=WAN action=drop comment="DROP_WAN_REST_API"`
    Hoặc drop port 9090 khi không thuộc FPT_LAN:
    `/ip firewall filter add chain=input dst-port=9090 protocol=tcp src-address-list=!FPT_LAN action=drop comment="DROP_NON_FPT_LAN_REST_API"`

- **ƯU TIÊN CÔNG CỤ LOCAL TRÊN CLOUD CHO QUẢN LÝ MIKROTIK & ĐÓNG SITE CLOUD (2026-09-12):** Khi quản lý MikroTik (đổi IP, xem trạng thái PPPoE, proxy list):
  - **CANONICAL DUY NHẤT:** Python HTTP server chạy local trên port `2310` (`D:\Taadaa\AI-Tools\tools\mikrotik_web\server.py`, launcher ngầm `run_hidden.vbs`). Kết nối trực tiếp LAN `192.168.110.2:9090`, truy cập qua Tailscale MagicDNS `http://kibe:2310` hoặc `http://localhost:2310`, whitelist IP cứng (`192.168.110.x`, `100.x`, `127.0.0.1`), không phụ thuộc internet/Cloudflare.
  - **ĐÓNG HOÀN TOÀN SITE CLOUD (`mikrotik-tool.pages.dev` & Cloudflare Worker):**
    * Repo `AI-Tools` đã thống nhất toàn bộ qua `kibe:2310`. Site Cloudflare Pages (`mikrotik-tool.pages.dev`) và backend worker (`mikrotik-control.thanhdatbui1995.workers.dev`) ĐƯỢC ĐÓNG/DECOMMISSION HOÀN TOÀN.
    * Lý do bắt buộc đóng: (1) Bảo mật yếu — auth chỉ nằm ở `localStorage` client-side JS, mở lỗ hổng cho botnet probe/brute-force WAN; (2) Nguy cơ xung đột lịch đổi IP (schedules) giữa Cloudflare Worker và local `schedules.json`; (3) DNS biến động khi reconnect PPPoE gây timeout cloud worker.
    * Đóng rule mở WAN port trên RouterOS (chỉ giữ rule whitelist `FPT_LAN` nội bộ).
  - **Pattern:** Embed HTML frontend trong Python server, serve trên port 2310, hỗ trợ 3 tabs (Dashboard với Uptime batch monitor, Schedules tự động đổi IP, API & cURL). Dùng `ThreadingHTTPServer` (KHÔNG dùng `HTTPServer` đơn luồng). Chạy ngầm bằng VBScript `run_hidden.vbs` gọi `pythonw.exe`.

- **🔥 CẤM TUYỆT ĐỐI GỌI `proxy.access_bulk` TRÊN BOX MOBIPROXY MT7621 (2026-09-09):**
  - **Bản chất hủy diệt:** API `POST /api.php?action=proxy.access_bulk` khi gọi sẽ ghi lại 40 file cấu hình VÀ restart đồng loạt 40 tiến trình 3proxy cùng một lúc. Chip MT7621 quá yếu → CPU 100% + OOM → PHP-FPM bị kernel kill → Nginx trả `502 Bad Gateway` vô thời hạn cho đến khi reboot.
  - **Lỗi trông có vẻ ổn nhưng thực ra đã gây sập:** API trả về `{"ok":true,"configs":40}` (ghi config thành công) nhưng sau đó box rơi vào 502 vì PHP chết trong lúc restart 40 proxy. Không bao giờ gọi `access_bulk` khi đang điều phối từ xa.
  - **CÁCH ĐÚNG để set auth/IP cho từng proxy:** Vào Web UI thủ công `http://test.taadaa.click/#proxies` → click từng proxy → "Cấu hình truy cập" → set từng cái một với delay tay giữa các lần → hoặc nhờ user tự thao tác tay trên web.
  - **Nếu PHP-FPM chết và web 502 vô thời hạn:** Không có cách phục hồi remote nếu không có SSH. BẮT BUỘC reboot box vật lý (rút nguồn cắm lại). SSH vào box thì gõ `/etc/init.d/php7-fpm restart`.
  - **Config đã ghi trước khi sập VẪN CÒN HIỆU LỰC:** Khi box reboot lại, các tiến trình proxy sẽ tự load lại file config đã ghi (`/usr/local/bin/proxyXX-6proxy.cfg`) → không cần set lại.

- **`proxy.access` GỌI NHIỀU LẦN CŨNG GÂY OOM (2026-09-10):**
  - **Bản chất:** Dù chỉ gọi `proxy.access` (set auth cho 1 proxy), mỗi lần gọi box vẫn phải xử lý PHP-FPM → ghi file config. Sau khoảng **13 lần gọi liên tiếp** (delay 30s/cổng), PHP-FPM bị OOM crash → 502. Nguyên nhân: PHP-FPM 7.4.28 trên OpenWrt bị memory leak, RAM không được nhả sau mỗi request.
  - **Chứng minh thực tế (2026-09-10):** Gọi `proxy.access` index 1..13 thành công, từ index 14 trở đi bắt đầu timeout/502. Box reboot lại → lỗi tương tự lặp lại vì config cũ đã được ghi.
  - **Kết luận:** Vấn đề KHÔNG phải do restart proxy (vì `proxy.access` không restart proxy) mà do **PHP-FPM memory leak**.
  - **CÁCH ĐÚNG DUY NHẤT:** Vào Web UI thủ công, set từng proxy bằng click tay. Click tay có delay tự nhiên giữa mỗi lần → PHP-FPM xử lý kịp → không OOM. Hoặc set từng proxy rồi chờ 5-10 phút mới set cổng tiếp theo.
  - **KHÔNG BAO GIỜ** gọi `proxy.access` qua API liên tiếp 32 lần dù delay 30s.

- **IP WHITELIST KHÔNG CHỐNG ĐƯỢC BOT SCAN (2026-09-10):**
  - **Hiểu lầm phổ biến:** Set `mode: iponly` + `allowed_ips: 42.119.145.61` → nghĩ rằng bot không thể quét được proxy.
  - **Sự thật:** Bot quét trực tiếp vào `IP:port` qua TCP handshake → box vẫn phải nhận TCP connection → CPU tốn resources để xử lý → vẫn gây load. IP whitelist chỉ chặn **sử dụng** proxy (bot không dùng được), nhưng **không chặn kết nối TCP**.
  - **Cách chống scan thật sự:** Tắt NAT (`nat_port: 0`) → firewall OpenWrt DROP toàn bộ TCP từ WAN → bot không connect được → 0% CPU load. Hoặc đặt whitelist IP ở tầng **MikroTik firewall** (iptables/nftables) trước khi packets đến box.
  - **So sánh 3 chế độ auth vs chống scan:**
    | Chế độ | Chặn bot dùng proxy | Chặn bot scan TCP | CPU load |
    |:---|:---|:---|:---|
    | `none` (không auth) | Không | Không | Cao |
    | `strong` (user/pass) | Có | Không | Vừa |
    | `iponly` (whitelist IP) | Có | Không | Vừa |
    | NAT TẮT | N/A (mất proxy) | **Có** | **0%** |
    | Firewall MikroTik whitelist | N/A | **Có** | **0%** |

- **PHẦN CỨNG BOX MOBIPROXY QUÁ YẾU CHO FARM 32 PROXY (2026-09-10):**
  - Box hiện tại: OpenWrt MT7621, RAM 128MB, CPU MIPS 2 nhân.
  - Không chịu được: `access_bulk` (restart 40 proxy cùng lúc), gọi `proxy.access` liên tiếp 13+ lần, hoặc NAT BẬT + bot scan đồng thời.
  - **Giải pháp thay thế:** Mini PC x86 (Intel N100/J4125, RAM 8GB, 4 cổng LAN 2.5GbE) chạy Ubuntu + iptables. Giá 1.5tr-2.5tr. Chạy được 100+ proxy, chống scan ở tầng firewall, không bao giờ OOM.
  - **Từ khóa tìm trên Shopee:** `mini pc 4 lan 2.5g n100 firewall` hoặc `topton n100 4 lan`.

- **THAO TÁC VỚI BOX MOBIPROXY: HƯỚNG DẪN QUA WEB UI THỦ CÔNG, KHÔNG TỰ ĐỘNG HÓA (2026-09-09):**
  - Khi user yêu cầu thao tác cấu hình trên box MobiProxy (set auth, IP whitelist, NAT...): **KHÔNG viết script tự động hóa, không dùng watchdog loop, không bắn lệnh bulk**. Box phần cứng yếu, không chịu được tải đột ngột.
  - **ĐÚNG:** Hướng dẫn user tự vào Web UI thực hiện thủ công, hoặc thực hiện từng lệnh API nhỏ lẻ (1 lệnh → chờ verify → mới lệnh tiếp theo).
  - **SAI:** Viết script watchdog kiểm tra 30s/lần, gọi `access_bulk` hàng loạt, loop retry API khi timeout.
  - User đã phàn nàn rõ: *"Vào giao diện web làm thì được. Cứ thích bắn lệnh bậy bạ phá hoại"*.

- **WATCHDOG CANH BOX KHI ĐANG TREO: GIÃN CÁCH TỐI THIỂU 120 GIÂY (2026-09-09):**
  - Khi cần canh box để thực hiện lệnh khi web hồi phục, **KHÔNG dùng interval < 120 giây**. Mỗi request TCP probe dù nhẹ nhưng box đang nghẽn CPU vẫn phải xử lý → làm kéo dài thời gian phục hồi.
  - Interval an toàn: **120 giây (2 phút)** mỗi lần probe.
  - Khi user bảo "canh rồi làm luôn": Phải hỏi rõ rồi mới chạy watchdog. Không tự ý chạy.

- **BẪY TÀN DƯ TÊN BIẾN VICHANGER TRONG CONSUMER REPOS (2026-09-08):**
  Một số consumer script cũ (như `register gmail/gmail_reg_v10.py`, `Hotmail/hotmail_login.py`) vẫn còn sót lại tên biến hoặc chuỗi log legacy như `VICHANGER_PROXY_MAPPING_PATH`, `VICHANGER_SERIAL_HEADERS`, `log("[vichanger-preflight] ...")`.
  - **THỰC TẾ 100%:** Farm đã dẹp sạch hoàn toàn ViChanger. Bên dưới các hàm này thực chất là gọi `automation_core.preflight.require_android_vpn` kiểm tra live egress IP qua `atx-agent curl` / Singbox local inbound (`192.168.110.2:20000+mid`).
  - **CẤM TUYỆT ĐỐI:** Agent không bao giờ được suy diễn là farm đang dùng ViChanger, không gọi lệnh `am broadcast vn.vichanger.app`, không hỏi user về ViChanger hay đề xuất xử lý app ViChanger. Khi gặp các biến này, hiểu ngay đó là wrapper kiểm tra Singbox/MikroTik Proxy chuẩn của farm.

- **Cloudflare Worker changeIp bug (2026-09-10):** Worker source (`mikrotik-worker/src/index.js`) had 30s timeout + silent error swallowing. When user clicked "Change IP" on web app and PPPoE took >30s to reconnect, Worker threw "không kết nối lại sau 30 giây". Fix: increase to 60s, add retry on enable failure, log errors with console.error. Worker deployed at `mikrotik-control.thanhdatbui1995.workers.dev`. Source backup at `C:\Users\Kibe\iCloudDrive\Backup_OneDrive\mirotik\mikrotik-worker\`.

- **Tailscale Hostname & MagicDNS for Web Manager (2026-09-10):**
  - Khi user muốn đổi URL truy cập ngắn gọn (ví dụ `http://kibe:8090` thay vì IP `100.88.164.111:8090` hay `http://sever:8090`):
    * Tên máy mặc định trên MagicDNS phụ thuộc vào Machine Name trong Tailscale Admin Console (`https://login.tailscale.com/admin/machines`).
    * Lệnh CLI `tailscale set --hostname=kibe` trên Windows không đổi được MagicDNS nếu Admin Console đã pin tên máy cũ (`sever`). Cách nhanh nhất là hướng dẫn user vào web console đổi Machine Name thành `kibe`.
    * Khuyên dùng tính năng "Add to Home Screen" trên Safari iOS để tạo icon PWA 1 chạm mở web quản lý, không cần nhớ port hay domain.

- **Config-to-Repo Persistence After MikroTik REST API Changes (2026-09-10):** Sau khi thay đổi cấu hình firewall/pppoe qua REST API trên MikroTik, PHẢI lưu bản ghi vào repo `D:\Taadaa\AI-Tools` để version control. Quy trình: (1) Export running config thành file `.rsc` text tại `docs/infrastructure/mikrotik/firewall-<name>-<date>.rsc`, (2) Cập nhật section tương ứng trong `docs/infrastructure/mikrotik/mikrotik-master-network-handbook.md`, (3) `git add` + `git commit` + `git push`. REST API không có endpoint `/system/save` hay `/export` trực tiếp — changes tự lưu trong running config và auto-save định kỳ. File `.backup` qua `/system/backup/save` chỉ restore binary, không dùng để review. User đã chủ động nhắc: *"lưu vào repo ai tool chứ?"* — không được để thay đổi infra chỉ sống trên router mà không có bản ghi trong repo.

- **FPT_LAN firewall pattern & Anti-Scan Rule Precedence (2026-09-10):**
  - *Mục đích:* Chặn botnet scan IP công khai vào các cổng proxy MikroTik PPPoE (10001-10035) và Sing-box (20001-20080), chỉ cho phép IP nội bộ farm (máy tính Kibe + phone farm kết nối AP Aruba).
  - *Cấu hình chuẩn:* Tạo `address-list` tên `FPT_LAN` chứa `192.168.110.0/24`, `192.168.10.0/24`, `127.0.0.1`. Đặt rule ALLOW `src-address-list=FPT_LAN dst-port=10001-10035,20001-20080 protocol=tcp`, theo sau là rule DROP catch-all `dst-port=10001-10035,20001-20080 protocol=tcp`.
  - **CRITICAL RULE PRECEDENCE PITFALL:** Always disable or remove unrestricted legacy accept rules placed above the drop/allow rules (such as `dst-port=10000-10039` or `20000-20039` accept rules without src-address filter). If left active above, all incoming Internet probes will be accepted before reaching the drop rule, rendering the whitelist useless. **This is the #1 cause of "whitelist not working" — the legacy accept rules at higher priority eat all traffic first.**
  - **35 PPPoE Port Pruning:** Farm uses exactly 35 PPPoE lines (`pppoe-out1` to `pppoe-out35`). Disable redundant lines (`pppoe-out46` to `pppoe-out60`) via REST API `/interface/pppoe-client/<id>` `{"disabled": "true"}` to free CPU/RAM.
  - **MikroTik Web Manager Tailscale Access (`server.py` on port 2310):** The local web manager whitelists `ALLOWED_IPS`. Set `100.` to allow the entire Tailscale CGNAT subnet (`100.64.0.0/10`), enabling mobile/remote access directly from phones via `http://kibe:2310` without exposing the port to public WAN or relying on Cloudflare Workers.
  - **🚨 BẪY TRUY CẬP WEB MANAGER KIBE:2310 TỪ IPHONE (IOS / SAFARI) (2026-09-16):**
    * *Hiện tượng:* Người dùng mở `kibe:2310` trên iPhone (Safari) thì báo lỗi không tải được trang hoặc văng sang Google Search.
    * *Nguyên nhân:*
      1. Safari trên iOS tự động ép sang HTTPS (`https://kibe:2310`) hoặc coi chuỗi `kibe:2310` là từ khóa tìm kiếm nếu thiếu tiền tố `http://`. Web server `server.py` chỉ chạy HTTP thường.
      2. iOS không hỗ trợ phân giải NetBIOS single-label hostname (`kibe`) trên mạng Wi-Fi LAN; và khi dùng Tailscale, tính năng iCloud Private Relay / DNS mặc định của iOS có thể chặn single-label domain trừ khi dùng FQDN.
    * *Giải pháp truy cập chuẩn ăn ngay 100%:*
      - **Cùng mạng Wi-Fi Farm (LAN):** Mở `http://192.168.110.123:2310`
      - **Bật Tailscale trên iPhone:** Mở `http://100.88.164.111:2310` (hoặc MagicDNS FQDN: `http://kibe.tail11bc77.ts.net:2310`)
      - *Bắt buộc luôn gõ đủ tiền tố `http://`*.
  - **🚨 BẪY WORKER TIMEOUT KHI RESTART HTTP SERVER `server.py` (2026-09-16):**
    * *Hiện tượng:* Dispatch worker subagent sửa `server.py` nhưng worker bị timeout 600s cạn iteration do chạy lệnh `python server.py` trực tiếp ở foreground terminal (`serve_forever()` block vĩnh viễn tiến trình shell).
    * *Quy tắc vận hành an toàn:*
      - CẤM TUYỆT ĐỐI chạy lệnh khởi động `server.py` ở chế độ foreground.
      - Kiểm tra cú pháp trước: `python -m py_compile D:/Taadaa/AI-Tools/tools/mikrotik_web/server.py`.
      - Lệnh restart ngầm 1 dòng chuẩn qua PowerShell (chỉ kill process đang LISTEN port 2310, tránh kill nhầm Python khác):
        `powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 2310 -State Listen).OwningProcess -Force -ErrorAction SilentlyContinue; Start-Process (Get-Command python).Source -ArgumentList 'D:\Taadaa\AI-Tools\tools\mikrotik_web\server.py' -WindowStyle Hidden"`
      - Sau đó `sleep 2` và test xác thực bằng `curl http://127.0.0.1:2310/api/status`.

  - **🚨 KHỞI ĐỘNG NGẦM MIKROTIK WEB MANAGER 100% ẨN & WINDOWS STARTUP (2026-09-19):**
    * *Hiện tượng:* Khởi động qua file `.bat` trong thư mục `Startup` (`C:\Users\Kibe\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\`) sẽ luôn bật cửa sổ console CMD đen trên desktop.
    * *Giải pháp vĩnh viễn 0-console:*
      1. Xóa file `.bat` cũ trong Startup: `mikrotik_web.bat`.
      2. Tạo file VBS `mikrotik_web.vbs` trong Startup gọi `run_hidden.vbs` với window style `0, False`:
         ```vbs
         Set WshShell = CreateObject("WScript.Shell")
         WshShell.CurrentDirectory = "D:\Taadaa\AI-Tools\tools\mikrotik_web"
         WshShell.Run "wscript.exe ""D:\Taadaa\AI-Tools\tools\mikrotik_web\run_hidden.vbs""", 0, False
         Set WshShell = Nothing
         ```
      3. File `run_hidden.vbs` tự tìm `pythonw.exe` (ưu tiên trong `AppData\Roaming\uv\python\...` hoặc `%LOCALAPPDATA%\Programs\Python\...`) để chạy `server.py`, loại bỏ hoàn toàn cửa sổ console CMD.
      4. Xác thực sau restart: kiểm tra `Get-NetTCPConnection -LocalPort 2310 -State Listen` để thấy `pythonw.exe` chiếm port và không còn process `python.exe` / `cmd.exe` nào lộ console.

  - **🚨 BẪY PYTHONW.EXE KHÔNG CÓ CONSOLE: SYS.STDERR/SYS.STDOUT LÀ NONE GÂY CRASH THẦM LẶNG & ERR_EMPTY_RESPONSE (2026-09-21):**
    * *Hiện tượng:* Web manager `kibe:2310` khởi động cùng Windows qua VBS gọi `pythonw.exe`, tiến trình vẫn LISTENING port 2310, nhưng khi người dùng mở trình duyệt vào trang thì lập tức bị "sập" / xoay đơ / báo `ERR_EMPTY_RESPONSE` (`curl: (52) Empty reply from server`).
    * *Nguyên nhân kỹ thuật (Root Cause):*
      - Trong môi trường GUI `pythonw.exe` trên Windows, Python không cấp console, do đó **`sys.stdout`** và **`sys.stderr`** đều nhận giá trị `None`.
      - Khi có bất kỳ request nào đến, `BaseHTTPRequestHandler` tự động gọi `self.log_message(...)`. Nếu hàm này hoặc bất kỳ lệnh nào trong server gọi `sys.stderr.write()` / `print()` mà không guard, Python sẽ văng ngoại lệ `AttributeError: 'NoneType' object has no attribute 'write'`.
      - Exception xảy ra ngay trong thread worker trước khi gửi HTTP status/headers, socket bị cưỡng chế đóng lập tức $\rightarrow$ client nhận `Empty reply from server`.
    * *Giải pháp chuẩn vĩnh viễn (Phải có ở đầu file `server.py`):*
      ```python
      import os, sys
      if sys.stdout is None:
          sys.stdout = open(os.devnull, "w", encoding="utf-8")
      if sys.stderr is None:
          sys.stderr = open(os.devnull, "w", encoding="utf-8")
      ```
      Đồng thời trong `log_message`:
      ```python
      def log_message(self, format, *args):
          if sys.stderr is not None:
              try:
                  ts = time.strftime("%H:%M:%S")
                  sys.stderr.write(f"[{ts}] {args[0]}\n")
              except Exception:
                  pass
      ```
  - **MikroTik Web Manager Feature Set (2026-09-10 & 2026-09-16):** The embedded `server.py` now includes three tabs:
    * **Dashboard** — PPPoE table with real-time uptime via batch monitor API.
    * **Schedules** — Auto change-IP cron (add/edit/delete/toggle schedules, persists to `schedules.json`, background runner `schedule_runner` daemon checks every 15-30s with `last_run` deduplication key `(id, current_time, yday)`).
    * **API & cURL** — Per-proxy cURL commands with one-click copy to clipboard for quick integration into scripts/AdsPower/Gologin.
    * **Lưu ý triển khai Frontend:** Bắt buộc cài đặt đầy đủ hàm `switchTab(tabName)` trong thẻ `<script>` để chuyển đổi `.tab-content` và cập nhật `.tab-btn.active`. Nếu thiếu `switchTab`, trình duyệt mobile sẽ báo lỗi JS và đơ toàn bộ thanh tab.
    * **Uptime via Batch Monitor:** Use comma-separated `.id` values in a single `/interface/pppoe-client/monitor` POST call (`{".id": "*5D,*5E,*5F", "duration": "1"}`) to fetch uptime for all 35 running lines in one request. Match results back to interfaces by `local-address` field.
  - **Tailscale MagicDNS Setup (2026-09-10):** To get a friendly hostname like `http://kibe:2310`:
    1. Open `https://login.tailscale.com/admin/machines`
    2. Find the server entry (shows as `sever` by default)
    3. Click `...` → `Edit machine name...` → change to `kibe` → Save
    4. MagicDNS updates in ~5s. Access via `http://kibe:8090` from any Tailscale device.
    * CLI `tailscale set --hostname=kibe` on Windows does NOT override Admin Console name — must edit in web console.
    * Tip: On iOS Safari, "Add to Home Screen" creates a PWA icon for one-tap access.
  - **Config Preservation in Repo:** Always export running MikroTik rules into `D:\\Taadaa\\AI-Tools\\docs\\infrastructure\\mikrotik\\` (`firewall-fptlan-proxy-rules-2026-09-10.rsc` and update `mikrotik-master-network-handbook.md`) and commit/push to `thanhdatbui/AI-Tools` so network changes are tracked in version control.
  - *Giải thích số liệu Packet vs Request khi User hỏi:*
    * Bộ đếm packet firewall trên RouterOS lưu trên RAM và tự reset về 0 mỗi khi reboot router. Thời gian tính bằng chính `system resource uptime`.
    * Trong TCP/IP, 1 request không bằng 1 packet (1 kết nối HTTP/TCP gồm 3-way handshake SYN/ACK, payload, ACK data, FIN/RST tốn 10-30+ packet). 57 triệu packet (~14GB) phản ánh lưu lượng dữ liệu tích lũy qua forward chain, bao gồm cả traffic hợp lệ của farm lẫn bot scan, KHÔNG PHẢI là 57 triệu request riêng lẻ.

- Plain `host:port` proxy = bypassable by TikTok. Ensure the Excel mapping uses the authenticated form.

- search_files fails on `D:\` → use terminal find/grep.

- Don't broad-search the filesystem when the user already named the repo.



## VPN gate and host-aware mapping (17/08/2026 — user rule "k bật vpn thì k đc chạy")



**Bug class that must never regress:** `vpn_preflight.DEFAULT_PROXY_MAPPING` in COMSUMER repos

hardcoded the kibe workbook (`D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`). On the admin

host (máy 200+, `TAADAA_HOST_CONFIG=admin.yaml`, workbook_root trống), `serial_is_mapped_in_workbook`

read the KIBE mapping → admin serials not found → `required=False` → VPN check skipped → **máy admin

không VPN vẫn chạy** (user caught it live on the 06:00 shift: "nhiều máy chưa có vpn vẫn chạy").



**Fix (canonical, all-repo):** mapping MUST resolve per host, never fall back to another host:

- `automation_core 0.4.46` adds `resolve_proxy_mapping_path()` — reads `TAADAA_HOST_CONFIG`

  workbook_root; for kibe → `kibe/PROXYgandienthoai.xlsx`; for admin (no file) → **raise**

  fail-closed (no kibe fallback, no silent exempt).

- Patched in EVERY consumer that hardcodes the mapping path: `tiktok-luot nuoi acc/vpn_preflight.py`,

  `tiktok-log-in` (cli.py + account_reconcile.py), `tiktok-add-bao-mat-f2a`, `add mail khoi phuc`,

  `register gmail` (gmail_reg_v10.py + guarded_device_reboot.py), `Hotmail/hotmail_login.py`,

  `gan-proxy/gan_proxy_fleet.py`, worktree `tiktok-log-in-recovery-adapter-p2-wt`.

  Verify with: `grep -rln "PROXYgandienthoai" --include=*.py D:/Taadaa/ | grep -viE "venv|site-packages|\.git|tests"` → must be EMPTY for runtime code.

- Non-git repos (register gmail, Hotmail, gan-proxy) patched in place (no commit possible).



**Live IP Verification (20/08/2026 — commit `c5036cb` in `automation-core`):**
- Chỉ kiểm tra `tun0 UP` và `dumpsys connectivity` là KHÔNG ĐỦ vì khi upstream proxy chết, `tun0` ở local vẫn `UP`, TikTok tự động fallback ra Direct Wi-Fi IP gây lộ footprint toàn farm.
- `check_android_vpn` và `require_android_vpn` bổ sung `verify_live_ip=True`: bắt buộc gửi broadcast `vn.vichanger.app.GET_IP` tới `vn.vichanger.app/.AdbCaller`.
- Điều kiện PASS: `result=200` và `data="<IP>"` hợp lệ; nếu `result=0` (proxy chết) $\rightarrow$ BLOCK ngay lập tức (fail-closed), tuyệt đối không cho mở TikTok.
- **Phân biệt `result=0` vs `broadcast exception: adb command timed out`**:
  - `result=0`: Upstream proxy sập / chết port / xác thực lỗi $\rightarrow$ kiểm tra port proxy ngoài bằng `curl -I -m 10 http://host:port` (phải trả 407/200, không timeout).
  - `broadcast exception: adb command timed out`: ADB hoặc tiến trình `vn.vichanger.app` trên máy bị nghẽn tạm thời dẫn đến quá thời gian chờ lệnh broadcast. `tun0` và kết nối VPN vẫn đang giữ; kiểm tra lại bằng lệnh broadcast thủ công `am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller` nếu trả `result=200` thì VPN và proxy vẫn bình thường.
- **TUYỆT ĐỐI KHÔNG BỎ GATE NÀY:** Khi user hỏi *"có nên bỏ kiểm tra trên máy / chỉ check bên ngoài"* khi thấy nhiều máy báo `MissingVpnRecoveryError`: Phải giải thích rõ việc kiểm tra `GET_IP` trên máy là chốt chặn cuối cùng ngăn Android fallback về direct Wi-Fi. Khi nhiều máy dừng phiên cùng lúc, kiểm tra phân nhóm host mapping (`PROXYgandienthoai.xlsx`) bằng `curl -x` và `am broadcast ... GET_IP` để xác định chính xác cụm proxy nào đang sập (ví dụ: `mirotik1.taadaa.click` hoặc `khoalee.duckdns.org` mất mạng/chết port) thay vì tắt gate bảo vệ.
**Quy trình chẩn đoán khi nhiều máy báo MissingVpnRecoveryError / TimeoutError proxy readiness:**
  0. **Phân biệt Proxy chết thật vs Stale Marker trong Device Readiness:**
     Nếu curl/nc ra egress IP vẫn 200 OK nhưng preflight hoặc soft-reboot báo `proxy readiness timed out for <serial>`:
     - Kiểm tra file marker tại `C:\Users\Kibe\.codex\device-readiness\<hash>.json` (hash map theo serial).
     - Nếu kẹt `"state": "proxy_pending"` từ phiên cũ sau soft-reboot:
       ```python
       import sys
       sys.path.insert(0, 'D:/Taadaa/automation-core/src')
       from automation_core.readiness import mark_proxy_state
       mark_proxy_state('<serial>', 'proxy_ready')
       ```
     - Lệnh trên giải phóng tức thì cờ readiness mà không cần reboot lại máy.
  1. Đọc mapping `D:\\OneDrive\\TaadaaData\\kibe\\PROXYgandienthoai.xlsx` nhóm theo host (`test.taadaa.click`, `mirotik1.taadaa.click`, `khoalee.duckdns.org`).
  2. Test `curl -x http://user:pass@host:port https://api.ipify.org` (hoặc Python `urllib.request.ProxyHandler`) bên ngoài theo cụm port để xác định box nào đang sập toàn diện hay chỉ chết port lẻ.
  3. Kiểm tra DNS DDNS của box (`nslookup <host>`) và ping/port check để phân biệt sập nguồn/mất mạng WAN với lỗi xác thực auth (407) hay rate-limit.
  4. Bắn broadcast trực tiếp: `adb -s <serial> shell am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller`. Lưu ý: Khi `tun0` chưa lên, `GET_IP` có thể trả về chính Direct IP của mạng Wi-Fi farm (`result=200, data="<Host Direct WAN IP>"`). Luôn đối chiếu với Host Public IP để phát hiện Direct IP Leak.
  5. Nếu proxy upstream timeout/sập: Báo cáo danh sách cổng chết / box chết cho user kiểm tra box/nguồn/sim, KHÔNG sửa code hay bypass gate bảo vệ. Sau khi box online lại, Watcher sẽ tự gán lại VPN và giải phóng hiện trường.

**Cách check proxy đúng cho nhiều máy cùng lúc (học từ 2026-08-23):**
- `tun0 UP` + `ping 8.8.8.8 OK` + thiếu `default route qua tun0` **KHÔNG CÓ NGHĨA là proxy die** — ViChanger không push default route kiểu OpenVPN, routing của nó hoạt động qua VpnService tunnel. Cấm kết luận proxy hỏng dựa trên `ip route` hay `wget/curl` trên shell Android.
- `wget` / `curl` / `python3 urllib` trên shell Android cũng **không lấy được public IP** vì ViChanger intercept traffic ở tầng VpnService của Android apps, không hook command line shell.
- **Cách đúng duy nhất:** broadcast với `-n vn.vichanger.app/.AdbCaller` và đọc `result=200` + `data="<IP>"`:
  ```python
  import subprocess, re
  r = subprocess.run([adb, "-s", serial, "shell", "am", "broadcast",
      "-a", "vn.vichanger.app.GET_IP",
      "-n", "vn.vichanger.app/.AdbCaller"],
      capture_output=True, text=True, timeout=10)
  match = re.search(r'data="([^"]+)"', r.stdout)
  ok = "result=200" in r.stdout and match
  ip = match.group(1) if match else ""
  ```
- `result=0` (không có `.AdbCaller` hoặc broadcast không có `-n`) → không có IP → sai kết quả. Luôn dùng `-n vn.vichanger.app/.AdbCaller`.
- **Phát hiện lộ IP gốc (Direct IP Leak):** Luôn so sánh IP lấy từ ViChanger với Host Public IP (`https://api.ipify.org`). Nếu trùng (ví dụ các port `mirotik1.taadaa.click:1000x` trỏ về router nội bộ không qua 4G/Dcom), máy đang dùng direct IP farm. TikTok có thể cho reg 1 acc nhưng sau đó rate-limit toàn bộ các máy khác cùng IP.
- **Tự động gắn lại proxy qua Watcher sau reboot:** Khi reboot máy, watcher `gan_proxy_fleet.py watch` (chạy ngầm trên PC) sẽ tự động bắt sự kiện thiết bị online và gán lại proxy theo `PROXYgandienthoai.xlsx`.
- **Cảnh báo Serial Drift:** KHÔNG lấy serial từ log cũ hoặc manifest tạm. Luôn tra cứu serial chuẩn từ file `D:\OneDrive\Tiktok\Tik1.xlsx` (hoặc `PROXYgandienthoai.xlsx`), vì một số file tracking/manifest tạm (như `taikhoan_run_safe.xlsx`) có thể bị ghi đè ngày tháng vào cột serial (ví dụ `23/08/2026`). Dùng `Tik1.xlsx` sheet `TaiKhoan` làm single source of truth cho `STT ↔ Serial ADB`.
- **Môi trường Python khi chạy probe/script:** Trên host Windows này, các thư viện `openpyxl`/`requests` nằm trong virtualenv `D:\Taadaa\python-envs\automation\Scripts\python.exe`. Khi gọi bằng subprocess/terminal, cần `env -u PYTHONPATH -u PYTHONHOME` để tránh xung đột binary/C-extension với venv của Hermes CLI.
- **Tiêu chuẩn nhịp độ Reg TikTok an toàn:** Mỗi ngày chỉ reg **tối đa 1 acc / máy / ngày** (trên proxy sạch 4G/Dcom xoay IP). Không dùng IP direct của farm để reg hàng loạt tránh bị TikTok quét dải IP.



**Recovery ladder (core `recover_missing_android_vpn`, wired in `vpn_preflight.require_vichanger_connected`):**

VPN fail on a MAPPED machine → (1) GanProxy reassign (`proxy_pending` + wait `wait_for_proxy_ready` 60s) → (2) **Stage-2 Direct Proxy Reconnect** (đọc mapping `PROXYgandienthoai.xlsx` → gọi `vi_changer_runner.set_proxy` trực tiếp tại chỗ → verify `verify_live_ip=True`) → (3) soft-reboot 1× (`soft_reboot_and_wait`: reboot → unlock → wait proxy/VPN) → (4) still fail → `MissingVpnRecoveryError` FINAL_BLOCKED (never runs VPN-less). Chi tiết: `references/stage2-direct-proxy-reconnect-and-live-ip-20260824.md`. Bounded reboot "1-2 lần tránh loop lỗi do gan proxy" is the user's framing — do NOT loop reboot beyond the core ladder.



## References
- `references/aruba-iap-40-device-allocation-and-anti-ssid-failover.md` — **[MỚI 09/10/2026 — USER MANDATE]** Kỷ luật cấm tuyệt đối fallback sang SSID ngoài ('Dat') hoặc đảo máy sang AP khác (phá vỡ quy hoạch 40 máy/AP), kiến trúc Aruba IAP Master (.251) vs Slave CLI, xử lý triệt để bẫy Android 8 `NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION` qua UI Manage Networks, và bảng chuẩn SSID/Pass farm (kibe 1: 23102025 vs kibe 2: 19051995).
- `references/admin-pc-rdp-stall-and-rogue-dhcp-rescue.md` — **[MỚI 09/10/2026]** Cứu hộ lỗi RDP Admin PC treo do Aruba AP cướp DHCP (192.168.10.77), phân tích nghẽn định tuyến bất đối xứng (Asymmetric Routing) với Ruijie, và quy trình zero-touch jump-host tunnel qua MikroTik REST API khóa IP tĩnh bất đồng bộ (wmic non-blocking).
- `references/strict-wifi-partitioning-and-association-rejection-heal.md` — **[MỚI 09/10/2026 — USER CORRECTION]** CẤM TUYỆT ĐỐI fallback sang SSID vãng lai ("Dat") tránh lệch subnet và nguy cơ an toàn IP; bảng quy hoạch cứng 4 cụm SSID (kibe 1: 23102025, kibe 2/admin 1/admin 2: 19051995); cơ chế bẻ khóa bẫy ASSOCIATION_REJECTION trên Android 8 qua adb-join-wifi.
- `references/concurrent-adb-proxy-healing-and-ap-ssid-failover.md` — **[MỚI 09/10/2026]** Kỹ thuật gán proxy ADB đa luồng (ThreadPoolExecutor O(1) <10s) chống timeout tuần tự khi có máy offline, bóc tách 5 nhóm lỗi watchdog, cấm tuyệt đối fallback sang SSID ngoài luồng (như 'Dat') để chống lệch subnet và rủi ro Direct IP leak, quy hoạch chuẩn mật khẩu kibe 1 (23102025) vs kibe 2 (19051995), và xử lý bẫy ASSOCIATION_REJECTION / BSSID Blocklist trên Android 8.
- `references/tainted-proxy-rotation-and-decontamination.md` — **[MỚI 09/10/2026]** Quy trình truy vết và xoay sạch IP proxy (MobiProxy 51xx + MikroTik 100xx) khi tài khoản dính cờ trảm nền tảng, bẫy bảo vệ cổng 5101 (DDNS anchor), cửa sổ ngắt BRAS 40s và đối soát delta IP.
- `references/mikrotik-3proxy-noauth-and-fullstack-proxy-sync.md` — **[MỚI 08/10/2026]** Sự cố lộ IP FPT trên dàn Admin do bẫy Preflight Direct Fallback khi máy mang proxy `:0`, giải pháp bỏ pass 3proxy container MikroTik (tận dụng firewall FPT_LAN), quy trình đồng bộ full-stack proxy (GPM, 9Router, OmniRoute, Excel, ADB), và chốt chặn Fail-Closed triệt để.
- `references/admin-vs-kibe-mikrotik-direct-proxy-architecture.md` — Kiến trúc Direct LAN Proxy MikroTik (10008..10035) cho Farm Admin vs Singbox Mixed Port (20001..20080) cho Farm Kibe.
- `references/mikrotik-minipc-hardware-audit-and-agent-coexistence.md` — **[CẬP NHẬT 08/10/2026]** Phương pháp trích xuất cấu hình phần cứng MikroTik Soft Router O(1) qua Winbox cache + SSH paramiko, phân tích cấm chạy AI Agent trực tiếp trên RouterOS bare-metal, bẫy RouterOS x86 không hỗ trợ Back-to-Home / Cloud, bẫy RouterOS REST API nuốt biến `$` khi nạp script (bắt buộc escape `\$`), quy trình triển khai script Telegram Bot WoL native 24/7 trên MikroTik (`telegram-wol-bot`, `@vps_hermes_Taadaa_bot`) nhận diện ngôn ngữ tự nhiên bật máy Kibe/Admin từ xa không cần lệnh gạch chéo `/`, và hướng dẫn cấu hình WoL cho PC Admin (Huananzhi X99-F8D / Realtek NIC / ErP Ready).
- `references/admin-unassigned-proxy-direct-leak-incident-20261008.md` — Postmortem sự cố Farm Admin lộ IP FPT do máy mang proxy `:0` lọt vào preflight direct fallback và quy trình dừng khẩn cấp 3 lớp (2026-10-08).
- `references/fast-proxy-and-tiktok-live-triage-pattern.md` — **[MỚI 05/10/2026]** Quy trình triage kiểm tra nhanh O(1) đa tầng (Host probe, Device toybox nc, Wi-Fi system state, TikTok live check) khi user nghi ngờ/hỏi lỗi proxy.
- `references/mikrotik-auto-reset-diagnosis-and-ssh-wan-hardening.md` — **[MỚI 13/09/2026]** Chẩn đoán sự cố MikroTik "tự reset hoài": phân biệt reboot RouterOS vs PPPoE flapping do watchdog-pppoe 3m, khắc phục bão brute-force SSH/Winbox từ WAN làm nghẽn socket max-sessions=20 bằng IP Service whitelist, và truy vấn thống kê lỗi proxy qua OmniRoute SQLite.
- `references/mikrotik-cloud-decommissioning-and-wan-hardening.md` — **[MỚI 12/09/2026]** Quy trình đóng site Cloudflare Pages (mikrotik-tool.pages.dev) và Cloudflare Worker, cô lập REST API port 9090 về FPT_LAN, tắt NAT WAN port 8090, chuyển canonical duy nhất sang kibe:2310 (Local + Tailscale).
- `references/samsung-s7-no-internet-ap-and-tiktok-connectivity-trap.md` — **[MỚI 12/09/2026]** Bẫy Samsung S7 "No Internet AP" & TikTok chặn mạng dù Browser ra internet bình thường: Cơ chế cờ `NET_CAPABILITY_VALIDATED` của Cronet/TTNet, timeout captive portal của Samsung `WifiConnectivityMonitor`, và quy trình soft-reboot xóa cờ phạt.
- `references/master-67-proxy-pool-and-failover-downloader.md` — Master 67 Proxy Pool (32 MobiProxy + 35 MikroTik PPPoE LAN 192.168.110.2), sửa lỗi Hairpin DNS domain mirotik1 qua hosts file, tối ưu downloader 20 workers song song và cơ chế fail-over xoay proxy tức thì khi yt-dlp gặp lỗi.
- `references/downloader-mikrotik-proxy-pool-and-silent-failure-pitfall.md` — Bẫy direct proxy cào lỗi ngầm không báo, ưu thế tuyệt đối của Pool 69 MikroTik LAN, và cơ chế Smart Idle downloader tự ngắt khi đủ 640 folder.
- `references/replacement-device-onboarding-and-wifi-mapping.md` — Quy trình thay thế & onboarding máy Farm S7 mới (Mật khẩu Wi-Fi kibe 1: 23102025 vs kibe 2: 19051995, cấu hình phần cứng S7, Singbox proxy 20000+N, cài đặt TikTok 55 Split APKs + Outlook + ATX, và cập nhật serial Excel/codebase).
## References
- `references/samsung-s7-global-proxy-subnet-and-toybox-nc-probing.md` — Quy trình kiểm tra và probe proxy trên Samsung S7 qua toybox nc.
- `references/mikrotik-singbox-whitelist-and-concise-status-reporting.md` — **[MỚI 11/09/2026]** Whitelist subnet Singbox Container (172.17.0.0/16) trong FPT_LAN, lỗi reset kết nối 10054 và quy tắc báo cáo trực diện.
- `references/mikrotik-web-manager-and-pppoe-management.md` — Local Web Manager (localhost:8090) + PPPoE management tools + REST API reference + Cloudflare DDNS script + User preference: local tools over cloud.
- `references/mikrotik-singbox-phone-farm-proxy-guide.md` — Sổ tay vận hành MikroTik RouterOS & Sing-box Mixed Inbound Proxy (port 20001..20080) và quy tắc báo cáo lỗi cho Admin.
- `references/network-level-pbr-and-transparent-proxy-gateway.md` — Kiến trúc định tuyến Policy-Based Routing (PBR) & Transparent Proxy Gateway trên RouterOS / MikroTik / Mini PC thay thế gán proxy trên S7.
- `references/mobiproxy-web-ops-and-auth-troubleshooting.md` — MobiProxy Web UI (test.taadaa.click), xử lý lỗi 407 Proxy Authentication Required và quy trình chuẩn hóa `host:port`.
- `references/proxy-upstream-death-and-live-ip-gate-20260820.md` — Lỗ hổng Proxy sập nhưng `tun0 UP` ảo + TikTok fallback Direct IP leak & cơ chế xác thực Live IP (`GET_IP` broadcast != Direct IP).
- `references/9router-antigravity-and-mobiproxy-sync.md` — Chi tiết quy trình xử lý khi Box MobiProxy đổi IP WAN / sập mạng & tự động phục hồi Proxy Pools trên 9Router.
- `references/proxy-special-chars-url-encoding.md` — Chuẩn hóa URL encode/unquote idempotent cho proxy có ký tự đặc biệt (`#`, `@`, `!`, `:`) tránh lỗi 407 và fragment cắt cụt URL.
- `references/samsung-s7-global-proxy-subnet-and-toybox-nc-probing.md` — Quy trình gán global http_proxy + captive portal mode 0, xử lý lỗi lệch subnet kibe 1 (192.168.10.x) / kibe 2 (192.168.110.x), và kỹ thuật test live egress IP qua toybox nc trên Samsung S7.
- `references/two-step-proxy-attachment-and-lock-handling-20260903.md` — Quy trình 2 bước gán proxy (ADB global → ViChanger VPN) + xử lý Device Lock conflict khi job TikTok khác đang chạy.
- `references/vichanger-cleanup-plan-20260903.md` — **PLAN: Xoá ViChanger hoàn toàn khỏi toàn bộ codebase**, chỉ giữ Singbox/MikroTik transparent proxy. Files to delete/rewrite, verification method, current status.
- `references/mobiproxy-botnet-scan-and-auth-hardening-20260909.md` — Sự cố botnet scan làm sập box MT7621, giải pháp auth IP whitelist, API flow đầy đủ, pitfall `proxy.access_bulk` gây PHP OOM, quy trình khẩn cấp phục hồi.
- `references/mobiproxy-api-patterns-and-pitfalls-20260910.md` — MobiProxy Web API patterns: auth flow, endpoints, `access_bulk` vs `proxy.access` OOM, bot scan vs auth mode, PHP-FPM memory leak, replacement hardware recommendation.
- `references/mobiproxy-scanguard-and-replacement-hardware-20260910.md` — MobiProxy v3.0.67 Scan Guard (kernel firewall API proxy.scan_guard.save, non-restarting O(1) IP update), so sánh phần cứng thay thế, và **[MỚI 16/09/2026] Thẩm định kiến trúc chuyên sâu từ Sol (GPT-5.6-Sol-High) cho Xiaomi R3G V1** (MT7621A + 256MB RAM: footprint WireGuard kernel vs Sing-box/Xray OOM, tắt WiFi tối ưu nhiệt/CPU, và mô hình tunnel kín chống bot scan cho farm 80 máy S7).
- `references/xiaomi-r3g-openwrt-admin-pc-onboarding-workflow.md` — **[MỚI 16/09/2026]** Quy trình cấu hình Xiaomi R3G V1 (OpenWrt) qua Admin PC: nhận diện topology Kibe SSH -> Admin PC (Ethernet 2) -> R3G (192.168.5.1), giải phóng DHCP Ethernet 2, và quy tắc bắt mạng trước set Bridge mode/PPPoE trước khi gửi thiết bị.
- `references/xiaomi-r3g-openwrt-setup-and-action-evidence-gate.md` — **[MỚI 06/10/2026]** Cấu hình Xiaomi R3G (ImmortalWrt MT7621A), bẫy rút dây WAN1 sập 60 PPPoE pool MikroTik, và Invariant Action-Evidence Verification Barrier (AEVB — Chống khai láo / Premature Resolution / Kỷ luật đợi subagent xong mới báo).
- `references/xiaomi-r3g-multi-wan-and-offsite-staging-discipline.md` — **[MỚI 08/10/2026]** Kiến trúc Multi-WAN trên Xiaomi R3G (bẻ LAN2 thành WAN2 gánh 2 line quay 16 IP tại Thái Bình, mở rộng VLAN 3+ line), cạm bẫy set cứng PPPoE trước khi gửi đi tỉnh, và quy trình Staging Offsite WAN DHCP + Auto-Connecting Tunnel.
- `references/sqlite-wal-bloat-and-session-storage-failure.md` — **[MỚI 06/10/2026]** Sự cố lỗi "session storage could not be written / disk full" khi state.db phình 14GB + WAL checkpoint bị kẹt; lệnh giải phóng tức thì `PRAGMA wal_checkpoint(TRUNCATE)`.
- `references/ip-circuit-breaker-and-partner-isolation-runbook.md` — **[MỚI 10/10/2026]** Kiến trúc Cầu dao tự ngắt IP (IP Circuit Breaker), dữ liệu thực nghiệm 301 ca nhả follow cascading failure (70.6% co-run vs 36.4% solo), và cơ chế safe-skip bảo vệ máy anh em cùng IP.
- `references/mikrotik-rest-api-firewall-config-20260910.md` — Step-by-step MikroTik REST API workflow: audit filter rules, create FPT_LAN address-list, add ALLOW/DROP rules, disable unrestricted rules, restrict generic forwards, disable redundant PPPoE lines, export config to repo, verify egress.

