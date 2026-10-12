---
name: android-farm-host-operations
description: "Use when farm devices drop, USB hangs, or entering BIOS."
---

# Android Farm Host Operations

References:
- `references/x99-ehci-usb-reboot-governance-and-adb-auth.md` — Quy chuẩn reboot Farm hàng ngày trước Ca trưa (TFT Game Guard), xử lý dứt điểm lỗi ADB unauthorized sau reboot và khống chế concurrency USB 2.0.
- `references/x99-ehci-pnp-limit-and-daily-reset-architecture-20261010.md` — Phân tích giới hạn phần cứng Live-Disable PnP trên Intel X99 EHCI (HRESULT 0x8004100c), bằng chứng transport ID liên tiếp, hạ MaxWorkers 25 và kiến trúc Preflight Auto-Reboot định kỳ (10/10/2026).
- `references/aruba-wifi-recovery-and-anti-drift-incident-20261009.md`

Scripts:
- `scripts/safe_usb_guard.py` — Script nguồn mẫu giám sát và reset EHCI bus theo ngưỡng.
- `scripts/wait_admin_reboot.py` — Theo dõi tự động chu kỳ reboot Admin PC qua SSH, chờ khởi động ADB daemon và đối soát danh sách máy online.

Use when phone farm devices drop from ADB/PC, USB controllers hang, entering UEFI/BIOS fails, or setting up host-level hardware recovery on phone farm controller PCs.

## 1. Bản Chất Lỗi Văng Hàng Loạt Máy ADB / Tool Quản Lý (XiaoWei/Jiwei)
- **Sai lầm chẩn đoán:** Đổ lỗi cho "Power Balance" (High Performance, USB Selective Suspend, PCIe ASPM). Khi farm đang hoạt động, cổng USB luôn có traffic nên Windows không bao giờ tự ru ngủ cổng.
- **Nguyên nhân gốc rễ phần cứng:**
  1. Mainboard farm (như Huananzhi X99-F8D / dual Xeon) thường bị tắt chip Intel USB 3.0 xHCI trong BIOS, dồn 80 máy vào 2 controller USB 2.0 EHCI (`8D26`, `8D2D`).
  2. Băng thông USB 2.0 trần chỉ 35-40 MB/s. Khi 30-40 worker chạy đồng loạt gọi `screencap` (~2MB/ảnh PNG) hoặc kéo video/app, xuất hiện I/O spike dồn dập làm nghẽn bus, tràn endpoint, controller treo thanh ghi phần cứng $\rightarrow$ văng toàn bộ hub.
  3. Reset PC cứu được là do gửi tín hiệu System Bus Reset giải phóng thanh ghi controller, không phải do cài đặt nguồn.

## 2. Công Cụ Cứu Nhanh Tại Chỗ & Giới Hạn Live-Reset Chip EHCI (Main X99)
- **Nguồn repo quản lý (SSOT):** `D:\Taadaa\tools\services\Taadaa_Service\reset_usb_bus.bat`
- **Vị trí triển khai trên Host:** `C:\Taadaa_Service\reset_usb_bus.bat` (Desktop shortcut: `RESET_USB_ADMIN.lnk`).
- **Cơ chế script:**
  ```cmd
  @echo off
  taskkill /F /IM adb.exe >nul 2>&1
  powershell -Command "Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Enhanced Host Controller' } | Disable-PnpDevice -Confirm:$false; Start-Sleep 2; Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Enhanced Host Controller' } | Enable-PnpDevice -Confirm:$false"
  wscript.exe "C:\Taadaa_Service\start_adb_hidden.vbs"
  ```
- **BẪY THỰC TẾ PHẦN CỨNG (HRESULT 0x8004100c):**
  * Trên Windows với chipset Intel C610/X99 (`8D26`, `8D2D`), lệnh `Disable-PnpDevice` trên controller PCI EHCI **BỊ TỪ CHỐI** với lỗi `Disable-PnpDevice : Not supported (HRESULT 0x8004100c - NotImplemented)`.
  * Lệnh `pnputil /restart-device` trên controller này cũng trả về `System reboot is needed to complete configuration operations! (Exit code 194)`.
  * **Hệ quả:** Script chỉ thực chất kill và khởi động lại tiến trình `adb.exe`, **KHÔNG HỀ ngắt điện hay reset xung nhịp phần cứng 2 chip EHCI**.
  * Nếu cụm máy bị văng do kẹt uevent/socket USB phần cứng (như Box 4 rụng 8 máy), script chạy xong máy vẫn giữ nguyên trạng thái `offline`.
  * **Tại sao máy bị kẹt socket ngay cả khi IDLE (không chạy script gì):**
    - Khi EHCI controller hoặc nhánh hub bị nghẽn buffer/drop packet một lần, thanh ghi phần cứng bị kẹt và pipe `/dev/android_adb` trên Linux kernel của điện thoại bị đứt.
    - Do đường nguồn VBUS 5V vẫn duy trì, điện thoại vẫn tưởng cáp đang cắm bình thường nên nhân Linux **không kích hoạt uevent để khởi động lại daemon `adbd`**.
    - Vì vậy, thiết bị sẽ kẹt cứng ở trạng thái `offline` hoặc mất hẳn khỏi `adb devices` mãi mãi cho đến khi có xung ngắt nguồn điện vật lý (System Bus Reset từ BIOS khi khởi động lại máy, hoặc rút cáp USB).
  * **Kỷ luật vận hành tự động (User Invariant):** 
    - **CẤM TUYỆT ĐỐI** bắt người dùng đi rút cắm dây cáp vật lý ("rút dây còn phiền hơn reset máy") hoặc yêu cầu canh reset PC thủ công trước mỗi ca.
    - **Thực tế vận hành không bật XiaoWei:** Farm vẫn có thể văng máy do I/O micro-spikes (30–40 worker cùng dump XML/screencap dồn vào băng thông USB 2.0 trần 35 MB/s) hoặc tiếp xúc cáp Box 4.
    - **Giải pháp tự động hóa 100%:** Áp dụng cơ chế **Preflight Auto-Reboot trước Ca** (gọi `shutdown /r /t 2` qua SSH nếu có cụm máy kẹt socket). Với `AutoAdminLogon = 1`, PC tự khởi động lại trong ~45 giây và kéo toàn bộ 80 máy lên xanh trước ca chạy hoàn toàn tự động.
    - **Kết quả thực nghiệm đã kiểm chứng (10/10/2026):** Sau reboot Admin PC, 79/79 thiết bị vật lý nhận đủ 100%, 0 máy offline, M269 mất ADB phục hồi lập tức. 8 máy unauthorized tự handshake xanh khi bật lại XiaoWei.

## 3. Worker Concurrency & Khống Chế Nghẽn USB 2.0 (Hạ Tải Tránh Văng Trong Ca)
- **Tác động của số lượng Worker song song (`MaxWorkers`):**
  * Mặc định `MaxWorkers = 40` khiến 40 máy cùng bắn command ADB (heartbeat, am start, dump window, logcat) dồn dập vào 2 chip USB 2.0 (băng thông trần 35 MB/s).
  * Sau 10–20 phút, hiện tượng lệch pha thời lượng video (Phase Drift) tạo ra các đợt microframe congestion gây rớt gói tin trên nhánh cáp dài/yếu (Box 4).
  * **Hạ `MaxWorkers` từ 40 xuống 25 workers (`run-feed-session.ps1`):**
    - Khóa trần an toàn ở cấp parameter binding: `[ValidateRange(1, 30)]` và gán mặc định `[int]$MaxWorkers = 25`.
    - Giảm 40% xung nhịp I/O trên bus USB 2.0, hạn chế tối đa rớt gói tin microframe trong phiên nuôi.
    - Thời lượng ca nuôi 80 máy tăng từ 35–40 phút lên ~60 phút, vẫn nằm trọn vẹn trong cửa sổ ca 2 tiếng an toàn.
    - Bổ sung structured JSON telemetry: `[TELEMETRY_METRIC] {"event": "feed_session_launch", "max_workers": 25, "target_machines": 30}` phục vụ giám sát vận hành.
  * **Kết hợp kép:** Reset máy trước ca (làm sạch 100% máy xanh) + Giảm worker (chống nghẽn trong ca) là bộ giải pháp vận hành tối ưu nhất.

## 4. Kiến Trúc Tự Động Hóa Reboot Đầu Ngày (Daily Safe Reboot) & Quy Tắc Khung Giờ Chống Ồn Giấc Ngủ
- **Nguồn repo quản lý (SSOT):** `D:\Taadaa\tools\services\Taadaa_Service\farm_preflight_daily_reset.py`
- **Vị trí triển khai trên Host:** `C:\Taadaa_Service\farm_preflight_daily_reset.py`
- **Quy tắc tiếng ồn phần cứng & Khung giờ giấc ngủ (User Invariant):**
  * Bo mạch chủ server/X99 khi POST/reset phần cứng sẽ ép quạt chạy 100% PWM (max RPM) trong 5–10 giây và còi buzzer BIOS kêu bíp. Không có lệnh phần mềm nào có thể can thiệp làm êm quạt ở tầng BIOS POST.
  * **CẤM TUYỆT ĐỐI** đặt lịch reboot tự động vào ban đêm hoặc rạng sáng (như 05:30 sáng) khi người dùng đang ngủ vì tiếng hú quạt gây giật mình mất giấc ngủ.
  * Còi BIOS bíp: Rút thẳng cục còi buzzer cắm trên chùm chân Front Panel của mainboard (hoặc dán băng dính điện đen bịt lỗ còi onboard) để tắt vĩnh viễn tiếng bíp.
- **Khung giờ vàng reboot an toàn (User Directed: "Trước ca trưa 11:35"):**
    - **Lịch kích hoạt chính thức:** **11:35 trưa hàng ngày** qua Task Scheduler `Taadaa_Farm_Daily_Reboot_1135` (thay thế các task cũ 05:30 và 07:45).
    - **Dòng chảy thời gian thực tế:**
      * `06:00 - ~09:30`: Ca 1 (Phiên 1 và Phiên 2) đã hoàn thành toàn bộ.
      * `11:35`: Task thức dậy kiểm tra điều kiện an toàn:
        - **TFT Game Guard (User Invariant — Chỉ chặn khi đang trong trận đấu thực sự):** Script kiểm tra `League of Legends.exe`. Nếu đang trong trận đấu TFT 3D $\rightarrow$ **HỦY REBOOT NGAY (`ABORT`)** để bảo vệ ván cờ của user, không bị xử thua AFK.
        - **Cho phép reboot khi ở hàng chờ / sảnh chờ:** Nếu chỉ mở `LeagueClient.exe` / Riot Client (lobby / queue) $\rightarrow$ **VẪN TIẾN HÀNH REBOOT BÌNH THƯỜNG**.
        - **Mọi tác vụ nền khác (farm, cào video, render ffmpeg, sync, cron):** Đều được phép tự động reboot làm sạch.
      * `11:35:05`: SSH reboot Admin PC, rồi reboot Kibe PC. Cả 2 máy boot vào Desktop lúc ~11:36 với 100% máy xanh.
      * `12:00`: Ca 2 (Trưa) bắt đầu chạy với bus USB và RAM hoàn toàn sạch sẽ (có 24 phút đệm).
    - Khung giờ giữa trưa người dùng đã thức, giải quyết triệt để tiếng ồn quạt server POST trong lúc ngủ.
- **Tự động phục hồi Cào & Render sau Reboot trên Admin Farm:**
  * Admin PC có `AutoAdminLogon = 1`, Windows tự nạp vào Desktop của user `Admin` sau khởi động lại.
  * Các tiến trình cào (`run_admin_downloader`) và render (`ffmpeg.exe` xử lý video tại `D:\video goc may 2`) nằm trong Startup $\rightarrow$ Tự động hồi sinh và tiếp tục làm việc mà không cần bấm tay.
- **Quy trình tự động song song (Silent Watchdog — không gửi tin nhắn rác Telegram):**
  1. Kiểm tra an toàn: Quét `~/.codex/device-locks`. Nếu có $\ge 1$ máy bận lock $\rightarrow$ **HỦY REBOOT NGAY**.
  2. Nếu 0 active lock: Gọi SSH sang Admin PC ra lệnh `shutdown /r /t 2`.
  3. Chờ 3 giây cho SSH đóng socket sạch sẽ, kích hoạt lệnh local trên Kibe PC: `shutdown /r /t 5`.
  4. Cả 2 máy tính đều đã có `AutoAdminLogon = 1` $\rightarrow$ Tự động vào thẳng Desktop sau ~60 giây, các Task Scheduler tự khởi chạy lại ADB Server và Hermes Gateway.
  5. Ghi log lịch sử tại `C:\Taadaa_Service\daily_reset.log`.

## 5. Khai Tử Watchdog Reset Mềm USB (`safe_usb_guard.py` & `Taadaa_Safe_USB_Guard_15m`)
- **Kết luận thực nghiệm & Quyết định hủy bỏ (User Directed 12/10/2026: "Vô dụng thì tắt cụ nó đi"):**
  1. **Bản chất vô dụng:** Lệnh phần mềm (`reset_usb_bus.bat`, `Disable-PnpDevice`) không thể giải phóng thanh ghi phần cứng Intel X99 (lỗi `HRESULT 0x8004100c`) và không thể giải quyết giới hạn Endpoint. Ngưỡng kích hoạt trong code (`< 50` máy) khiến nó không bao giờ cứu được các ca rụng chùm 8–9 máy.
  2. **Tác hại nghiêm trọng (Bung cửa sổ CMD phá game):** Task Scheduler chạy bằng `python.exe` cứ mỗi 15 phút lại giật bung cửa sổ console đen lên màn hình desktop, in log rồi tắt $\rightarrow$ làm cướp focus chuột/phím và văng game của người dùng (TFT / League of Legends).
  3. **Trạng thái chính thức:** **ĐÃ VÔ HIỆU HÓA VĨNH VIỄN (DISABLED) TRÊN CẢ 2 MÁY ADMIN VÀ KIBE**.
     - Admin PC: `schtasks /change /tn "Taadaa_Safe_USB_Guard_15m" /disable`
     - Kibe PC: `schtasks /change /tn "Taadaa_Safe_USB_Guard_15m" /disable`
     - Hermes Cron Kibe: Đã xóa sổ vĩnh viễn cronjob `farm-adb-transport-healer`.
  4. **KỶ LUẬT ĐIỀU PHỐI (USER INVARIANT):**
     - **CẤM TUYỆT ĐỐI** đăng ký lại các cron/task reset mềm USB trên cả 2 máy. Reset PC (Reboot) định kỳ lúc 11:35 trưa là cơ chế DUY NHẤT thực sự hiệu quả để làm sạch thanh ghi USB phần cứng.
     - **CẤM BẮT USER TỰ GÕ LỆNH:** Khi user đang chơi game hoặc bận mà báo có cửa sổ lạ/lỗi trên máy Admin, Coordinator **BẮT BUỘC tự chủ động SSH sang Admin xử lý ngầm**, TUYỆT ĐỐI KHÔNG ĐƯỢC đưa lệnh bắt user tự mở PowerShell/CMD gõ tay!
     - **Triệt tiêu cửa sổ Console nháy khi user chơi game:** Toàn bộ script Python trên cả 2 máy (Kibe & Admin) phải được cài `sitecustomize.py` ép cờ `CREATE_NO_WINDOW (0x08000000)`. Scheduled Task và VBScript runner trên Windows bắt buộc dùng `pythonw.exe` hoặc `wscript.exe` với `SW_HIDE`, cấm chạy trần `python.exe` trên interactive desktop session.

## 7. Bệnh Bàn Phím Mất Tín Hiệu & Cách Vào BIOS (Main X99)
- **Triệu chứng 1 (Trước khi vào BIOS):** Khi khởi động, tại logo main xoay tròn thì bàn phím tắt đèn, chỉ sáng khi vào màn hình gõ pass Windows. Bấm Delete / F2 không vào được BIOS.
  * **Nguyên nhân:** Mainboard bật Fast Boot / Ultra Fast Boot, bỏ qua khởi tạo USB keyboard ở giai đoạn POST (POST rút ngắn < 0.5s) hoặc bàn phím cắm vào cổng USB phụ/hub nối tầng.
  * **Hiện tượng có pass nhưng restart không bắt gõ:** Trong Registry `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon` có `AutoAdminLogon = 1` (set qua `netplwiz`), Windows tự nạp credentials từ LSA Secrets và vào thẳng Desktop.
  * **Cách vào BIOS từ Windows (100% thành công):**
    - Chạy shortcut Desktop: `VAO_BIOS_NGAY.lnk` (gọi `C:\Taadaa_Service\enter_bios.bat` chứa lệnh `shutdown /r /fw /t 2`).
    - Hoặc mở CMD Administrator chạy: `shutdown /r /fw /t 0` (ép firmware nhảy thẳng vào UEFI BIOS Setup).
    - Hoặc giữ phím `Shift` + bấm `Restart` $\rightarrow$ `Troubleshoot` $\rightarrow$ `Advanced options` $\rightarrow$ `UEFI Firmware Settings`.
  * **Cắm bàn phím chuẩn:** Cắm trực tiếp vào cổng USB 2.0 màu ĐEN nằm cao nhất ngay dưới cổng tròn PS/2 ở mặt sau case.

- **Triệu chứng 2 (ĐÃ VÀO TRONG MÀN HÌNH BIOS NHƯNG PHÍM CHUỘT LIỆT HOÀN TOÀN, ĐÈN TẮT NGÚM):**
  * **Bản chất kỹ thuật (Bẫy kinh điển của Phone Farm):** Trình điều khiển USB sơ khai trong BIOS AMI Aptio chỉ có bộ nhớ đệm cực nhỏ (chỉ quản lý được 8 - 16 thiết bị). Khi khởi động vào BIOS mà vẫn cắm 4 Box Hub và 78-80 điện thoại, BIOS bị **tràn bộ đệm USB Stack (Enumeration Overflow / Timeout)** $\rightarrow$ BIOS tự động ngắt điện toàn bộ hệ thống USB để chống treo máy, kéo theo bàn phím và chuột bị liệt sạch.
  * **Quy trình xử lý chuẩn 10 giây:**
    1. Rút tạm 4 dây cáp USB tổng của các Box Farm ra khỏi thùng máy PC (chỉ chừa lại 1 dây bàn phím cắm cổng USB đen sau case).
    2. Bấm Restart lại máy $\rightarrow$ Đèn bàn phím sẽ sáng ngay lập tức trong BIOS và điều khiển phím mũi tên mượt mà.
    3. Cài đặt BIOS xong, bấm F10 lưu lại. Chờ máy boot vào tới màn hình Windows mới cắm lại 4 dây cáp tổng của Farm.

## 8. Bẫy Tử Thần: xHCI Mode (USB 3.0) Onboard vs Giới Hạn Endpoint Main X99
- **BẪY CHẾT NGƯỜI (CẤM ENABLE xHCI ONBOARD CHO DÀN 80 MÁY):**
  * Trên bo mạch chủ X99 (Huananzhi X99-F8D / chipset Intel C610 series), bộ điều khiển xHCI Onboard (`8D31`) có giới hạn cứng phần cứng là **tối đa 96 USB Endpoint Contexts**.
  * Mỗi điện thoại Samsung S7 bật gỡ lỗi USB (MTP, ADB, Modem) ngốn tới **8 đến 10 endpoints**.
  * Khi `xHCI Mode = Enabled`: Cắm đến máy thứ 9 là **CHÁY SẠCH BỘ ĐỆM ENDPOINT** $\rightarrow$ Windows báo lỗi **Code 43** hàng loạt (`VID_0000&PID_0000`), **chỉ nhận đúng 8 máy, 67+ máy còn lại liệt hoàn toàn**!
  * **Quy tắc bắt buộc trên cổng Onboard:** BẮT BUỘC giữ **`xHCI Mode = Disabled`** trong BIOS (`IntelRCSetup` $\rightarrow$ `PCH Configuration` $\rightarrow$ `USB Configuration`). Khi Disabled, bo mạch bàn giao cổng lại cho 2 controller USB 2.0 cổ điển (`EHCI1` và `EHCI2`) không bị giới hạn 96 endpoint, nhận đủ 78–80 máy mượt mà.
- **GIẢI PHÁP ĐỂ 80 MÁY CHẠY ỔN ĐỊNH TRÊN EHCI USB 2.0 (KHÔNG BỊ SẬP BUS):**
  * Băng thông USB 2.0 trần ~35 MB/s. Để không bị nghẽn bus làm văng cả dàn khi chạy auto script:
    1. **Khống chế I/O nặng bằng Gate & Contention Telemetry (`automation_core.adb`):**
       - Khởi tạo `_HeavyIoGate(_HEAVY_IO_LIMIT)` bọc `threading.BoundedSemaphore(8)` (biến môi trường: `TAADAA_ADB_IO_SEMAPHORE_LIMIT`).
       - **Telemetry & Contention Tracking:** Theo dõi biến trạng thái `_active`, `_waiting`, và `_total_contention_events`. Khi số luồng chờ > 1 hoặc đang chạm trần `_limit`, gate tự động ghi `logger.warning("adb heavy-io semaphore contention detected active=%s limit=%s waiting=%s total_contention=%s")` và `logger.debug` khi acquire/release để quan sát áp lực I/O của farm.
       - **Canonical Command Classification (`_is_heavy_io`):** Không dùng matching chuỗi đơn giản (dễ false positive). Chuẩn hóa bóc tách:
         * Top-level commands trong `_HEAVY_IO_COMMANDS = frozenset({"pull", "push", "install", "install-multi-package", "sync", "backup", "restore", "exec-out", "screencap"})`.
         * Shell commands: bóc tách `shell_command = " ".join(normalized[1:])` và kiểm tra các payload tốn bus (`screencap`, `screenrecord`, `cat /dev/`, `tar `, `dd `, `logcat -f`, `pull `, ` > `).
         * Các lệnh thao tác UI nhẹ (`input tap`, `input keyevent`, `dumpsys`) đi thẳng không chờ.
       - **Không làm kéo dài ca nuôi:** 95% thời lượng nuôi là trên máy điện thoại (xem video 15–45s). Thao tác chụp ảnh/dump XML chỉ mất ~0.1s. Với 8 token, thông lượng đạt ~60-80 lượt I/O/giây $\rightarrow$ hầu như không có độ trễ chờ đợi, nhưng triệt tiêu hoàn toàn cú sốc tức thời khi nhiều máy chụp ảnh cùng mili-giây.
    2. **Đặc thù Screencap Samsung S7 Android 8:**
       - Lệnh nhị phân `/system/bin/screencap` trên Android 8 chỉ hỗ trợ cờ `-p` (PNG) hoặc raw framebuffer RGBA (nặng tới 14.7MB cho màn 2K). Không hỗ trợ xuất trực tiếp JPEG từ binary hệ thống.
       - Do đó giải pháp kiểm soát lưu lượng bắt buộc dựa vào Semaphore I/O để chặn spike, kết hợp nén phía client nếu cần lưu trữ.
    3. **CẢNH BÁO TỬ HUYỆT - CẤM DÙNG MULTI-ADB SERVER & REVERSE TETHERING:**
       - **CẤM Multi-ADB Server:** Chẻ cổng 5038/5039 sẽ phá vỡ tương thích của `atx-agent` (port 7912), `xiaowei` và các tool mặc định 5037.
       - **CẤM Cấp mạng qua USB (Reverse Tethering / Gnirehtet):** Cực kỳ nguy hiểm! Điện thoại sẽ ăn thẳng IP mạng LAN gốc FPT của PC Admin, lộ IP gốc và TikTok sẽ trảm hàng loạt tài khoản ngay lập tức. Mạng internet của farm BẮT BUỘC đi qua Wi-Fi gán Proxy MikroTik (`192.168.110.2:100xx`). ADB qua Wi-Fi cũng không khả thi vì làm nghẽn sóng vô tuyến Access Point với 80 máy.
    4. **Cơ chế Báo Cáo & Cảnh Báo Khi Có Lỗi I/O (Observability Loop):**
       - Lỗi USB/Screencap được phân loại chi tiết trong `summary.json` của từng máy (`usb-timeout`, `screencap-failed`, `capture-invalid`).
       - `feed_session_watchdog.py` tổng hợp kết quả từng Ca: nếu tỷ lệ lỗi > 30% sẽ tự động bắn Telegram `RED ALERT`.
       - `safe_usb_guard.py` được lập lịch chạy định kỳ 15 phút (Task `Taadaa_Safe_USB_Guard_15m`), tự kiểm tra 0 active locks trước khi giải phóng chip EHCI.
- **BẪY ĐIỀU PHỐI CLOSEOUT TẠI FARM REPOS (SOL HIGH AUTO-REPAIR & 3-STRIKE INVARIANT):**
  * **User Invariant ("Thiết kế Closeout Sol High tự làm"):** Khi Closeout Gate của repo core/farm bị reject (<85 điểm), Coordinator BẮT BUỘC để Sol High (:20129) tự tạo bản vá độc quyền trước qua `sol_repair.py` (First-Responder Monopoly).
  * **CẤM TUYỆT ĐỐI:** Cấm Coordinator tự tiện nhảy vào sửa code bừa bãi hoặc dispatch Worker Gemini mò mẫm làm cháy budget 10 phút khi Sol Repair chưa hỏng.
  * **Điều Kiện Fallback Sang Worker:** CHỈ fallback khi có 1 trong 4 bằng chứng cứng: (1) `sol_repair.py` exit != 0, crash hoặc timeout; (2) trả về `valid: false`; (3) hậu kiểm `git diff --numstat > 30` dòng; (4) patch của Sol làm fail focused test.
  * **Strike 3 Hand-off:** Nếu trượt 3 lần liên tiếp trên cùng scope_hash, CẢ Coordinator, Worker VÀ Sol Repair ĐỀU PHẢI STOP, chuyển quyền bàn phím cho Claude CLI.
  * **Khắc phục 2 điểm nghẽn Closeout Gate thường gặp với ADB Heavy I/O:**
    1. *Shell Command Heuristic:* Tránh dùng substring thô sơ (`in shell_command`). Phải dùng `shlex.split` duyệt canonical command names (`screencap`, `screenrecord`, `uiautomator`, `logcat`, `tar`, `dd`, `cp`) và kiểm tra binary redirect streams (`/dev/graphics`, `cat /dev/`, `>`, `>>`).
    2. *Test tải đồng thời (Concurrency Stress Test):* Bộ test BẮT BUỘC có test đa luồng (`ThreadPoolExecutor` 20 workers) chứng minh `max_observed <= _limit` (kẹp cứng $\le 8$), không gây starvation, và release token an toàn về 0.
- **GIẢI PHÁP PHẦN CỨNG NẾU MUỐN NÂNG CẤP LÊN USB 3.0 (CÂN 80–200 MÁY):**
  * Tuyệt đối không trông chờ vào xHCI onboard của main X99.
  * **CẢNH BÁO BẪY TRÀN ENDPOINT KHI MUA CARD PCIE USB 3.0 (CHỐNG LẶP LẠI LỖI CODE 43):**
    - Nếu mua loại card PCIe USB 3.0 giá rẻ dùng **1 chip điều khiển duy nhất** (1x Renesas uPD720201 hoặc 1x VIA VL805 chia sẻ 4 cổng) mà cắm dồn cả dàn 80 máy vào: **SẼ BỊ LỖI Y CHANG NHƯ LÚC BẬT USB 3.0 TRONG BIOS**! Con chip đó cũng bị trần 64–96 Endpoints, chỉ nhận được 8–10 máy là dính Code 43 (`VID_0000&PID_0000`) tê liệt toàn bộ máy còn lại.
    - **Quy tắc mua & lắp đặt chuẩn 100% hoạt động (Thực dụng & Tiết kiệm):**
      * **Phương án thực dụng (Khuyên dùng trước):** Mua **1 Card PCIe x1 rời trước** (~150k–200k trên Shopee/Lazada). Cắm Box 4 (dải M261–M280 hay rụng nhất) hoặc cả Box 3 + 4 sang card mới để chia lửa. Trên mainboard giữ lại Box 1 + 2 (40 máy) chạy trong ngưỡng an toàn của 2 chip EHCI onboard. Sau này nếu cần mở rộng thêm mới mua card thứ 2.
      * **Tương thích tuyệt đối với Automation & atx-agent (CẤM HOANG MANG):** ADB Server và `atx-agent` (port 7912) định danh thiết bị theo **Device Serial duy nhất** và dùng `adb forward`. Cắm máy qua nhiều Card PCIe độc lập và cổng onboard chạy song song HOÀN TOÀN KHÔNG làm đổi port, không xung đột script và không phải sửa bất kỳ dòng code nào.
      * **Nguồn phụ (BẮT BUỘC):** Phải chọn loại card có **chân cắm nguồn SATA 15-pin (hoặc Molex 4-pin)** cắm trực tiếp từ nguồn máy tính (PSU) để chống sụt áp khe PCIe. Tuyệt đối không mua card trần không có nguồn phụ.
      * **Chipset:** Chọn chip **Renesas/NEC uPD720201/uPD720202** hoặc **VIA VL805**. Windows 10/11 tự nhận driver gốc Microsoft xHCI, cắm vào nhận ngay trong 5 giây, không cần cài driver ngoài.
      * **Bẫy Review Shopee & Cung Cấp Link Sản Phẩm Trực Tiếp (User Rule 12/10/2026):**
        - Khi tìm mua card trên sàn thương mại điện tử (Shopee), BẮT BUỘC cung cấp link sản phẩm trực tiếp (`/product/{shopid}/{itemid}` hoặc `...-i.{shopid}.{itemid}`) của đúng mẫu chip Renesas/NEC D720201 có chân nguồn phụ SATA. CẤM TUYỆT ĐỐI chỉ ném link trang tìm kiếm chung (`/search?keyword=...`) làm user bực mình ("mày đưa link trang tìm kiếm chứ phải link sp đâu").
        - Cảnh giác với rating tổng thể: Sản phẩm đạt 4.8⭐ (600+ đã bán) như con 195k vẫn có thể bị sập trên farm vì 95% khách mua cắm chuột/phím nhẹ. Phải đào sâu review có bình luận của dân cắm Box Phone (đã có cảnh báo 1⭐: *"Ae cắm thêm box phone không ổn chút nào ae nhé! Cân nhắc khi mua"* do chip hub chia sẻ băng thông). Luôn ưu tiên card dùng chip Host Controller độc lập Renesas D720201 chuẩn server.
  * Tài liệu đặc tả kỹ thuật chi tiết lưu tại repo: `D:\Taadaa\tools\docs\HARDWARE_USB_FARM_PCIE_GUIDE.md` (bản sao lưu: `D:\Taadaa\docs\HARDWARE_USB_FARM_PCIE_GUIDE.md`).

## 9. Quy Hoạch Phần Cứng Mở Rộng Farm (80 - 200 Máy)
- **Giới hạn 1 card USB:** 1 chip Host Controller chỉ chịu được 64 - 96 USB Endpoint contexts (mỗi S7 tốn 3-5 endpoints). 1 card chỉ cân tối đa 40 - 50 máy.
- **Dàn 200 máy trên main Dual Xeon X99:** Bắt buộc cắm 3 đến 4 Card PCIe USB 3.0 độc lập (chip Renesas uPD720201 / VIA VL805 có nguồn phụ SATA/Molex) vào các khe PCIe x16/x1 trống, mỗi card gánh 1 nhánh 50-60 máy.
- **Sơ đồ cắm 4 Box Farm chuẩn trên bo mạch Huananzhi X99-F8D (8 cổng / 4 tầng):**
  * Mặt sau case có 8 cổng USB chia làm 4 tầng dọc (mỗi tầng 1 cặp 2 lỗ: 2 tầng xanh phía trên, 2 tầng đen phía dưới).
  * **Quy tắc cắm vàng: "Mỗi tầng cắm đúng 1 dây Box Farm"**:
    - Tầng 1 (xanh): Cắm Box 1 | Lỗ 2 để trống.
    - Tầng 2 (xanh): Cắm Box 2 | Lỗ 2 để trống.
    - Tầng 3 (đen): Cắm Box 3 | Lỗ 2 cắm Bàn phím.
    - Tầng 4 (đen): Cắm Box 4 | Lỗ 2 cắm Chuột.
  * **Lợi ích kép:** Vừa chia đều 4 Box sang 2 chip EHCI độc lập (Tầng 1-2 vào EHCI #1, Tầng 3-4 vào EHCI #2, mỗi bên gánh đúng 40 máy), vừa tránh sụt áp đường mạch 5V (không dồn 2 Box công suất lớn vào chung 1 cặp cổng).
- **Hiện tượng Phase Drift dù có Max Workers 40:** Giới hạn 40 workers chỉ cân tải CPU/Proxy. Cơ chế `machine_launch.py` stagger lúc mở app sau 5-15 phút sẽ bị lệch pha do thời lượng video khác nhau, dẫn tới 10-20 máy vô tình chụp ảnh (`screencap`) trùng giây $\rightarrow$ gây spike nghẽn USB 2.0. Giải pháp căn cơ là cắm thêm Card PCIe USB 3.0 mở rộng riêng hoặc dùng Semaphore khống chế I/O trong script (tuyệt đối không bật xHCI Onboard của mainboard).

## 10. Hermes Gateway Telegram Cold Boot vs Reconnect
- **Cơ chế Telegram Adapter:** Khi PC reset (Cold Boot, `is_reconnect=False`), cờ `drop_pending_updates=True` được kích hoạt.
- **Hệ quả:** Mọi tin nhắn gửi đến bot Telegram trong lúc PC đang tắt/reboot đều bị server Telegram hủy bỏ (purge). Bot sẽ không thấy các tin nhắn này sau khi online lại.

## 11. Bẫy Treo Remote ADB Portproxy & Dịch Vụ IP Helper (iphlpsvc) Trên Host Admin
- **Hiện tượng:** Từ host controller (Kibe PC), lệnh gọi ADB tới remote host (Admin `192.168.110.119:5037`) văng lỗi `adb.EXE: protocol fault (couldn't read status): connection reset` hoặc lệnh `inspect_machine.py <N>` bị timed out liên tục.
- **Bản chất kỹ thuật:**
  1. Trên Windows host phụ (Admin PC), cổng `5037` được publish ra ngoài mạng LAN cho Kibe PC qua Windows Portproxy:
     `netsh interface portproxy add v4tov4 listenaddress=192.168.110.119 listenport=5037 connectaddress=127.0.0.1 connectport=5037`
  2. Dịch vụ đảm nhận chuyển tiếp TCP portproxy trong Windows là **IP Helper (`iphlpsvc`)** chạy dưới tiến trình `svchost.exe`.
  3. Khi daemon `adb.exe` cục bộ trên Admin PC bị crash, restart ngầm hoặc khi nhiều request ADB từ xa dồn dập, backend `127.0.0.1:5037` bị đóng nhưng `svchost.exe` vẫn tiếp tục lắng nghe trên `192.168.110.119:5037`. Khi Kibe PC bắt tay TCP, `svchost.exe` chuyển tiếp vào backend đã chết và nhận RST $\rightarrow$ Kibe PC bị `connection reset`.
  4. Hơn nữa, `iphlpsvc` có thể bị treo trạng thái session nội bộ khiến kết nối mới bị drop hoặc không kết nối lại được vào `127.0.0.1:5037` dù adb daemon đã online.
- **Quy trình cứu hộ O(1) từ xa qua SSH (Không cần khởi động lại Windows):**
  1. Cưỡng chế restart dịch vụ IP Helper trên Admin PC:
     ```cmd
     ssh admin-farm "powershell -Command \"Restart-Service iphlpsvc -Force\""
     ```
  2. Đảm bảo daemon `adb.exe` cục bộ trên Admin PC đang chạy:
     ```cmd
     ssh admin-farm "\"C:\Program Files (x86)\xiaowei\tools\adb.exe\" start-server"
     ```
  3. Thao tác trên giải phóng hoàn toàn socket portproxy kẹt trong ~3 giây, kết nối Remote ADB thông suốt ngay lập tức.

## 12. Chẩn Đoán Từ Xa Qua MikroTik REST API & Đánh Thức Máy Farm (WoL)
- **Địa chỉ & Xác thực:** `http://192.168.110.2:9090` (HTTP Basic Auth: `admin:N0spam@@`).
- **Kiểm tra trạng thái nguồn/kết nối vật lý của Host PC:**
  - Gọi `GET /rest/ip/dhcp-server/lease`.
  - So khớp MAC máy đích (ví dụ Admin PC: `22:33:4D:06:4C:26`):
    * `status == "bound"`: Máy đang bật nguồn, giữ IP LAN hợp lệ (`192.168.110.119`).
    * `status == "waiting"`: Máy đang tắt nguồn hoàn toàn hoặc card mạng bị ngắt kết nối vật lý với switch.
- **Gửi lệnh Wake-on-LAN (WoL) đánh thức PC từ xa:**
  - Bắn request POST tới endpoint WoL của MikroTik:
    ```python
    requests.post(
        "http://192.168.110.2:9090/rest/tool/wol",
        auth=("admin", "N0spam@@"),
        json={"mac": "22:33:4D:06:4C:26", "interface": "ether3"},
        timeout=5,
    )
    ```
- **Kiểm tra hạ tầng PPPoE Multi-WAN & 3proxy:**
  - Khi script automation (reg/login/nuoi acc) báo `VPN GATE BLOCKED: global proxy (192.168.110.2:100xx) egress IP verification failed: context deadline exceeded`:
    1. Kiểm tra 60 đường PPPoE: `GET /rest/interface/pppoe-client`.
    2. Nếu số đường `running == 0`, đường quang WAN1/FPT đang bị rớt hoặc mất tín hiệu ISP.
    3. Kiểm tra log: `GET /rest/log`. Nếu thấy `PPPoE-Watchdog: pppoe-outXX not running -> Resetting...` và `pppoe-outX: terminating... - disconnected`: Toàn bộ proxy ngõ ra đang bị tê liệt. **BẮT BUỘC giữ nguyên Fail-Closed**, tuyệt đối không bypass VPN gate.

## 13. Kỷ Luật Xử Lý Split APK Farm & Bẫy Downgrade (TikTok Trill)
- **Kỷ luật xóa ngay thư mục APK lỗi / phân mảnh (User Invariant):**
  - Khi phát hiện một thư mục APK trong kho (ví dụ `apk-bank/.../v47.0.3`) bị lỗi thiếu file split dynamic modules, gây lỗi trích xuất native thư viện (`INSTALL_FAILED_CONTAINER_ERROR`) hoặc thiếu Dex class (`NoClassDefFoundError`):
  - **CẤM TUYỆT ĐỐI** giữ lại để chắp vá hay sửa mò.
  - **BẮT BUỘC XÓA SẠCH TRIỆT ĐỂ NGAY LẬP TỨC** (`shutil.rmtree` / `rm -rf`) để tránh lây nhiễm và ngăn các tool/worker khác quét nhầm.
- **Trích xuất Split APK chuẩn từ máy đang hoạt động mượt mà:**
  - Khi cần clone/đồng bộ bản APK chuẩn sang máy mới/máy lỗi, trích xuất trực tiếp từ máy chuẩn (ví dụ Máy 267):
    1. Lấy danh sách đường dẫn: `adb shell pm path com.ss.android.ugc.trill`
    2. Pull toàn bộ các file split (thường là 55 file) về thư mục staging.
- **Vượt bẫy `INSTALL_FAILED_VERSION_DOWNGRADE` khi cài Split APK:**
  - Nếu máy đã từng bị nạp đè `versionCode` cao hơn, cờ `-d` (`--downgrade`) của Android thường vẫn từ chối cài đè bản split cũ.
  - **Quy trình gỡ sạch và cài mới chuẩn xác:**
    1. Xóa dữ liệu app: `adb shell pm clear com.ss.android.ugc.trill`
    2. Gỡ bỏ hoàn toàn package: `adb uninstall com.ss.android.ugc.trill` (hoặc `cmd package uninstall`)
    3. Tạo install session mới: `adb shell cmd package install-create -r` $\rightarrow$ lấy `session_id`.
    4. Ghi từng file APK vào session: `pm install-write -S <size> <session_id> <name> <file_path>`
    5. Commit session: `adb shell pm install-commit <session_id>` $\rightarrow$ nhận `Success`.

## 14. Bệnh Tiểu Vi (XiaoWei/Jiwei - Tauri/WebView2) Không Bật Được / Ghost Process
- **Hiện tượng:** Click đúp icon Tiểu Vi trên Desktop không có phản hồi, không mở cửa sổ giao diện, không báo lỗi popup gì.
- **Bản chất kỹ thuật (Trích xuất từ log `app_rCURRENT.log`):**
  1. Tiểu Vi xây dựng trên nền tảng **Tauri (Rust + Microsoft Edge WebView2)**.
  2. Khi máy tính bị reset đột ngột hoặc thay đổi cấu hình hiển thị, thư mục cache WebView2 tại `%LOCALAPPDATA%\xiaowei\EBWebView` bị hỏng trạng thái (`Local State` / shader cache).
  3. Khi khởi động, Tauri runtime gặp lỗi:
     `failed to create webview: WebView2 error: WindowsError(Error { code: HRESULT(0x80070057), message: "The parameter is incorrect." })`
  4. Cửa sổ giao diện GUI không được tạo ra (`MainWindowHandle = 0`), nhưng tiến trình Rust nền `xiaowei.exe` vẫn tiếp tục chạy ngầm với hơn 120 threads ngốn 45MB RAM.
  5. Tauri có cơ chế Single-Instance Mutex: mỗi khi người dùng click shortcut để mở lại, tiến trình mới phát hiện tiến trình `xiaowei.exe` cũ đang chạy nên tự động thoát ngay lập tức.
- **Quy trình cứu hộ O(1) từ xa qua SSH hoặc CMD Admin:**
  1. Cưỡng chế kill tiến trình `xiaowei.exe` đang chạy ngầm:
     ```cmd
     taskkill /F /IM xiaowei.exe
     ```
  2. Xóa hoặc đổi tên thư mục cache WebView2 bị hỏng:
     ```powershell
     powershell -Command "Rename-Item -Path '$env:LOCALAPPDATA\xiaowei\EBWebView' -NewName 'EBWebView_bak' -ErrorAction SilentlyContinue"
     ```
  3. Sau khi dọn cache, bấm mở lại Tiểu Vi trên Desktop $\rightarrow$ WebView2 tự động tái tạo profile sạch và cửa sổ GUI 80 máy hiển thị lên ngay lập tức.

## 15. Phân Biệt Rớt Cả Cụm Hub vs Chập Chờn Tiếp Xúc Cáp Micro-USB Từng Máy
- **Bẫy vội vàng kết luận:** Khi thấy Tiểu Vi báo 1-2 ô cam (Disconnected) trong khi tổng số máy online trên ADB đạt 77-79 máy:
  * Tuyệt đối không vội vàng reset USB bus hay nghi ngờ sập hub.
  * Đối soát serial máy lỗi với danh sách máy lân cận trong `PROXYgandienthoai.xlsx` (ví dụ máy 224 có serial `ce0416041158642b05`):
    - Nếu các máy nằm cùng Box / cùng cổng (như 223 và 225) vẫn online xanh lè $\rightarrow$ Dây tổng, hub và USB controller hoàn toàn bình thường 100%.
    - Lỗi khu trú tại đầu cắm Micro-USB đít máy hoặc cổng sạc của chính con máy đó: tiếp xúc chập chờn, khi rung lắc khay hoặc khi Tiểu Vi kéo luồng stream thì sụt áp/rớt data tức thời.
- **Quy tắc slot trống vật lý đã biết trước trên Farm:**
  * **Máy 255 trên Admin Farm:** Không có máy vật lý (slot trống). Tuyệt đối không báo cáo 255 là "máy lỗi" hay "máy sập" gây hoang mang cho người dùng.

## 16. Hiện Tượng Điện Thoại Sáng Đèn/Lên Nguồn Nhưng Tiểu Vi Không Nhận & Bệnh Flapping
- **Bản chất phần cứng cáp Micro-USB (Nguồn vs Dữ liệu):**
  * Cáp Micro-USB có 4 đường tín hiệu: 2 đường nguồn ngoài cùng (Pin 1: VCC 5V, Pin 5: GND) và 2 đường dữ liệu ở giữa (Pin 2: D-, Pin 3: D+).
  * **Hiện tượng:** Máy điện thoại cắm vào màn hình sáng, đèn sạc bật, máy lên nguồn bình thường NHƯNG máy tính báo `Present: False` hoặc Tiểu Vi không nhận.
  * **Nguyên nhân:** Chân tiếp xúc Micro-USB bị lỏng hoặc chân D+/D- bị bám bụi/oxy hóa. Cáp chỉ ăn điện sạc (Power Only) nhưng đứt đường dữ liệu (Data Lost).
- **Hiện tượng Flapping & Lỗi Socket 10061 trên Tiểu Vi:**
  * Khi máy vừa khởi động lại hoặc khi lay nhẹ dây cáp, chân data tiếp xúc chập chờn 1-2 giây rồi ngắt.
  * Trong log Tiểu Vi (`app_rCURRENT.log`) xuất hiện:
    `ERROR [xiaowei::android::client] conn_and_check_dummy_byte: <serial>: No connection could be made because the target machine actively refused it. (os error 10061)`
    `ERROR [xiaowei::android::command] install_input: DeviceError(UnknownDevice("<serial>"))`
  * Ngay khi Tiểu Vi mở kết nối stream hình hoặc cài input helper, tải I/O tăng lên làm sụt áp chân data chập chờn $\rightarrow$ máy văng ngay lập tức.
  * Khi 78/80 máy online mà chỉ có 1-2 máy bị ô cam "Điện thoại đã ngắt kết nối" (như máy 10, 30): Tuyệt đối không reset bus USB hay reset PC. Lỗi khu trú tại đầu cáp Micro-USB (chân D+/D- dão hoặc bẩn) hoặc chân socket sạc trên S7. Vệ sinh cồn hoặc thay cáp đồng ngắn <= 30cm (AWG 24/28).
  * Giảm tải bus USB: Khóa XiaoWei stream ở 720p/480p, 15 FPS và bitrate <= 1.5 Mbps/máy để giảm 50% tải I/O microframe trên 2 chip EHCI.
  * Ngoài ra, nếu máy mới boot vào màn hình khóa hoặc chưa ấn "Always allow" trên popup "Allow USB debugging?", Android cũng sẽ từ chối kết nối (`os error 10061`).
- **Kỷ Luật Báo Cáo Số Lượng Máy Online (Chống Khai Láo / "Mõm"):**
  * **CẤM TUYỆT ĐỐI** lấy snapshot tức thời 1 lần của lệnh `adb devices` ngay sau khi reboot máy để vội vàng tuyên bố "ĐÃ NHẬN ĐỦ 79/80". Máy đang trong giai đoạn boot có thể nhấp nháy online 1 giây rồi rớt ngay (flapping).
  * **Quy tắc nghiệm thu chuẩn:** Bắt buộc kiểm tra tính ổn định (Stability Check): quét `adb devices` tối thiểu 2 lần cách nhau 3–5 giây VÀ đối soát danh sách thiết bị ổn định. Nếu có máy rớt/thiếu so với slot thực tế, phải nêu đích danh số máy đang chập chờn/thiếu (ví dụ: "78 máy online ổn định, máy 224 đang chập chờn/chưa nhận data") thay vì làm tròn số để báo cáo lấy thành tích.

## 17. Bẫy Lệch Subnet Wi-Fi & Quy Trình Khôi Phục Wi-Fi 2 Cấp (09/10/2026)
- **Tai nạn fallback SSID bậy:** Khi máy mất Wi-Fi, CẤM TUYỆT ĐỐI cho nhảy sang SSID ngoài farm (`Dat`, `Dat-1`, `BOX 2`...). Nhảy SSID lạ sẽ bị cấp dải IP `192.168.10.x` thay vì dải chuẩn Farm `192.168.110.x`, gây đứt socket tới Singbox/3proxy trên MikroTik và nguy cơ lộ IP Direct FPT.
- **Cố định quy hoạch 40 máy/AP:** M01–M40 (`kibe 1` - pass `23102025` - AP .253), M41–M80 (`kibe 2` - pass `19051995` - AP .252), M201–M240 (`admin 1` - pass `19051995` - AP .251), M241–M280 (`admin 2` - pass `19051995` - AP .250). CẤM dồn máy sang AP khác.
- **Bẫy chuỗi ADB-Join-Wifi & Lifecycle Activity:**
  * Lệnh `am start` trên Android shell BẮT BUỘC dùng `--es ssid "<SSID>"` hoặc nháy đơn bọc chuỗi (ví dụ: `am start ... -e ssid 'admin 1'`). Nếu không bọc nháy, Android shell sẽ cắt mất số sau dấu cách khiến máy nhảy vào SSID rác `admin` / `kibe` gây mất mạng cả cụm.
  * `MainActivity` của `adb-join-wifi` chỉ nhận extras khi `onCreate()` (không có `onNewIntent`). Khi đã có tiến trình chạy ngầm, BẮT BUỘC chạy `am force-stop com.steinwurf.adbjoinwifi` và `pkill -f steinwurf` trước khi gọi lệnh join mới.
  * Samsung Korean ROM (`SM-G930S`): Lệnh `service call wifi 14` (removeNetwork) bị chặn bởi Samsung security check (`Neither user 2000 nor current process has android.permission.CHANGE_WIFI_STATE`). Phải dùng `adb-join-wifi` (gọi `enableNetwork(id, true)` với cờ `disableOthers=true`) để vô hiệu hóa các mạng rác.
- **Kỷ luật điều phối Batch & Tốc độ xử lý (User Invariant):**
  * Khi quét/chữa lành Wi-Fi toàn farm (80–160 máy), BẮT BUỘC dùng `ThreadPoolExecutor(max_workers=20)` cùng `with_device_lock`.
  * CẤM chạy tuần tự hoặc worker thấp (<=8) làm kéo dài hàng chục phút/1 tiếng. 20 workers hoàn tất 154 máy trong < 60 giây.
  * Phải liên tục tổng hợp và báo cáo tiến độ/kết quả cho người dùng, không được để im lặng kéo dài.

- **Bẫy Rogue DHCP trên AP Master:** Master AP `.251` có thể còn tồn tại pool DHCP cũ (`192.168.10.0/24`). Bắt buộc xóa bằng SSH: `no ip dhcp kibe_dhcp` để MikroTik là DHCP Server duy nhất.
- Quy trình phục hồi 2 cấp: Cấp 1 (Radio toggle) ➔ Cấp 2 (`adb-join-wifi` kèm `--es`). Thất bại thì giữ hiện trường báo watchdog, CẤM gán bừa mạng khác.
- Chi tiết: `references/aruba-wifi-recovery-and-anti-drift-incident-20261009.md`.

## 18. Kiến Trúc Giám Sát Đa Tầng Farm (Kibe PC vs Admin PC Watchdogs)
- **Tầng 1: Khôi phục Socket/Transport ADB (`farm-adb-transport-healer`):**
  * Chạy trên Kibe PC qua cronjob `121a95f18996` mỗi 3 phút (`*/3 * * * *`).
  * Quét song song cả 2 cụm: Kibe Local và Admin Remote (`192.168.110.119:5037`).
  * Khi phát hiện thiết bị bị `offline` hoặc kẹt lệnh shell quá 2.5s $\rightarrow$ tự động gọi `adb reconnect` và wake up màn hình (`keyevent 224`) để cứu sống socket ngay lập tức mà không cần reset máy tính.
  * **Giới hạn kỹ thuật của Tầng 1 (Soft Reconnect):** Lệnh `adb reconnect offline` chỉ gửi gói điều khiển `A_SYNC`. Nếu nhân Linux (`/dev/android_adb`) trên điện thoại bị nghẽn socket pipe, hoặc khi Tiểu Vi/Phóng Phi đang stream dồn dập 70+ màn hình làm nghẽn microframe USB 2.0, gói handshake bị drop khiến thiết bị lập tức văng ngược lại `offline` hoặc mất hẳn khỏi ADB.
- **Tầng 2: Giám sát Reset Bus EHCI Phần Cứng (`safe_usb_guard.py`):**
  * Kiểm tra 0 device lock $\rightarrow$ reset 2 chip EHCI Windows qua PowerShell trong 3 giây.
  * Hiện trạng triển khai: **ĐÃ CÀI ĐẶT TRÊN CẢ 2 MÁY** (Task Scheduler `Taadaa_Safe_USB_Guard_15m` trên Admin PC và Kibe PC, chu kỳ 15 phút).
  * **Ngưỡng an toàn (Threshold Safety):** Script chỉ kích hoạt khi `số máy online < 50 máy` (sập diện rộng). Nếu chỉ rụng lẻ một nhánh 7–9 máy (ví dụ còn 71–72 máy online), Tầng 2 chủ động **SKIP** để bảo vệ các ca nuôi đang chạy của các máy còn lại.
  * **Dấu hiệu nhận diện sụt data cả cụm Hub (Consecutive Transport IDs):** Kiểm tra `adb devices -l`: nếu các máy offline mang `transport_id` liên tiếp (ví dụ `14745..14752`), đây là bằng chứng phần cứng cả nhánh Box bị sụt data tại cùng một mili-giây.
  * Quy tắc chẩn đoán Tiểu Vi vs ADB: Khi Tiểu Vi chập chờn ô cam ("Điện thoại đã ngắt kết nối"), thiết bị THỰC SỰ BỊ RỚT KHỎI ADB (`device not found`). Nguyên nhân là do Tiểu Vi kéo đồng thời 80 luồng stream video ($100\text{--}150\text{ Mbps}$) dồn vào 2 chip USB 2.0 EHCI (`1C2D`/`1C26` trên Kibe; `8D26`/`8D2D` trên Admin), làm nghẽn microframe dẫn đến drop packet trên các máy có cáp Micro-USB hơi dão. Bình thường không mở Tiểu Vi thì farm chạy auto rất êm; chỉ mở khi cần soi và watchdog Tầng 3 sẽ tự tắt sau 20 phút.
- **Tầng 3: Giải phóng Bus USB từ Tiểu Vi (`xiaowei-idle-auto-close-kibe`):**
  * Chạy trên Kibe PC qua cronjob `0a4a81f4f164` mỗi 5 phút.
  * Theo dõi API Windows `GetLastInputInfo`: nếu không có thao tác chuột/phím quá 20 phút $\rightarrow$ tự động `taskkill /F /IM xiaowei.exe` để ngắt toàn bộ 80 luồng stream màn hình, giải phóng hoàn toàn bus USB 2.0.
- **Tầng 4: Khống chế I/O Script Automation (`_HeavyIoGate`):**
  * Bounded Semaphore 8 tokens trong `automation_core.adb` bảo vệ bus USB 2.0 khi các script chạy auto chụp màn hình / kéo file.
  * Lưu ý: Semaphore này chỉ quản lý code Python nội bộ, KHÔNG khống chế được luồng stream của app bên thứ ba như Tiểu Vi (cần giảm trực tiếp trên UI XiaoWei: 720p/480p, 15 FPS).

## 19. Bẫy ADB Daemon Chạy Dưới Quyền SYSTEM vs User Interactive (Admin) Gây Lỗi Unauthorized Hàng Loạt Trên XiaoWei
- **Triệu chứng:** Sau khi máy tính khởi động lại, `adb devices` báo hàng loạt máy (như M243, M251, M257, M266, M267, M269, M270, M273) ở trạng thái `unauthorized`. Trên giao diện XiaoWei/Jiwei, các máy này hiện icon đứt cáp màu cam ("Phone disconnected, please check"), không thể click phóng to hay điều khiển, dù phần cứng USB PnP vẫn `Present: true`.
- **Nguyên nhân cốt lõi (User Session Mismatch & Thiếu ADB_VENDOR_KEYS toàn cục):**
  1. Khi Windows vừa boot lên, nếu có Scheduled Task chạy ngầm dưới quyền `NT AUTHORITY\SYSTEM` (Session 0) như `Taadaa_Safe_USB_Guard_15m` gọi lệnh `adb devices`, daemon `adb.exe` sẽ được khởi tạo dưới quyền `SYSTEM` và chiếm cổng `127.0.0.1:5037`.
  2. Biến môi trường `$ADB_VENDOR_KEYS` cấp Machine chưa được gán, daemon `SYSTEM` đọc key từ `systemprofile` hoặc không có key $\rightarrow$ điện thoại từ chối handshake key RSA và rơi vào `unauthorized`.
  3. Lỗi cú pháp trong script khởi động `start_admin_adb.bat`: lệnh `if %0% equ 0 exit /b 0` (thay vì `%errorlevel%`) khiến kiểm tra port listening bị sai.
  4. Khi phần mềm XiaoWei mở lên trên màn hình Desktop (chạy dưới interactive user `ADMIN-PC\Admin`, Session 1), nó kết nối vào cổng 5037 đã bị `SYSTEM` chiếm giữ $\rightarrow$ XiaoWei không thể mở socket shell hay start minitouch/minicap trên thiết bị `unauthorized` $\rightarrow$ XiaoWei hiển thị icon đứt cáp màu cam, đánh lừa người dùng rằng máy bị rút cáp hoặc sập nguồn.
- **Quy trình vá dứt điểm 3 bước (Permanently Fix để không bao giờ bị lại sau reboot):**
  1. **Bước 1 — Khóa biến môi trường toàn cục `ADB_VENDOR_KEYS` (Cấp Machine):**
     ```powershell
     [Environment]::SetEnvironmentVariable('ADB_VENDOR_KEYS', 'C:\Users\Admin\.android\adbkey', 'Machine')
     ```
     Đảm bảo bất kể user nào gọi ADB (SYSTEM hay Admin), daemon đều nạp đúng 100% key RSA chuẩn của Farm.
  2. **Bước 2 — Chuyển quyền Scheduled Task `Taadaa_Safe_USB_Guard_15m` sang User `Admin`:**
     Trong `setup_usb_guard_task.ps1`, bỏ cờ `-User "SYSTEM"` để task đăng ký dưới user interactive hiện tại (`Admin`):
     ```powershell
     Register-ScheduledTask -TaskName "Taadaa_Safe_USB_Guard_15m" -Action $action -Trigger $trigger -Settings $settings -Force
     ```
     Ngăn chặn hoàn toàn việc daemon ADB bị SYSTEM chiếm cổng 5037 lúc máy vừa boot.
  3. **Bước 3 — Sửa cú pháp kiểm tra cổng trong `start_admin_adb.bat`:**
     ```bat
     @echo off
     netstat -ano | findstr ":5037" | findstr "LISTENING" >nul 2>&1
     if %errorlevel% equ 0 exit /b 0
     wscript.exe "C:\Taadaa_Service\start_adb_hidden.vbs"
     ```
  4. **Cứu hộ tức thời nếu đang bị chiếm cổng:**
     Kiểm tra username sở hữu tiến trình adb:
     `(Get-Process | Where-Object { $_.ProcessName -eq 'adb' } -IncludeUserName).UserName`
     Nếu là `NT AUTHORITY\SYSTEM`: kill ngay `taskkill /F /IM adb.exe` và chạy `Start-ScheduledTask -TaskName 'Taadaa_ADB_User_Remote'` để đưa về quyền `Admin`. 100% máy xanh trở lại lập tức.

## 16. Quy Chuẩn Quản Lý & Lưu Trữ Cấu Hình Farm Lên Git (`taadaa-farm-tools`)
- **Nguyên tắc Invariant (User Directed: "Từ h đẩy hết vào repo quản lí đi"):** CẤM để các file cấu hình host và script dịch vụ phần cứng trôi nổi ngoài git (như ở thư mục mẹ `D:\Taadaa\` hay `C:\Taadaa_Service\`). BẮT BUỘC phiên bản hóa và đẩy tập trung vào repo quản lý trung tâm `taadaa-farm-tools` (`D:\Taadaa\tools`):
  - `machine-config/`: `kibe.yaml` (M1–80), `admin.yaml` (M201–280), `hermes-admin-config.yaml`.
    * `services/Taadaa_Service/`: `safe_usb_guard.py`, `reset_usb_bus.bat`, `start_adb_hidden.vbs`, `setup_usb_guard_task.ps1`.
    * `docs/`: `HARDWARE_USB_FARM_PCIE_GUIDE.md` (đặc tả kỹ thuật Card PCIe USB 3.0 rời Renesas/VIA cho farm 80–200 máy).
  - **Đồng bộ & Lưu trữ Não Trợ Lý Toàn Cục (Assistant Brain Backup lên `Hermes` repo):**
    * Toàn bộ hiến pháp và ký ức của trợ lý (`SOUL.md`, `memories/MEMORY.md`, `memories/USER.md`, `HERMES_SUBAGENT_RULES.md`, `AGENTS.md`) được sao lưu vào `D:\Taadaa\Hermes\deploy\hermes-home\` và đẩy lên GitHub `thanhdatbui/hermes-agent.git`.
    * Script `deploy\sync-from-kibe.ps1` hỗ trợ khôi phục 1-click toàn bộ não trợ lý trên máy mới/Admin PC.
    * Pre-push hook của `Hermes` được cấu hình miễn trừ `skills/*` và governance files để tránh bị chặn bởi Closeout Gate `DIFF_TOO_LARGE`.
  - **Lợi ích vận hành:** Toàn bộ hạ tầng farm được quản lý tập trung trên GitHub (`https://github.com/thanhdatbui/taadaa-farm-tools.git`). Khi cài đặt PC controller mới (Kibe hoặc Admin) hoặc cần khôi phục Windows sau sự cố, chỉ cần `git pull` repo `tools` là có đầy đủ toàn bộ cấu hình, script cứu hộ USB và tài liệu vận hành mà không lo thất lạc.

## 17. Quy Trình Chẩn Đoán Phân Tầng 3 Trạng Thái Thiết Bị (Mất Cả Vật Lý vs Mất ADB Còn PnP vs ADB Offline)
- **Tình huống kích hoạt:** Khi màn hình tool quản lý/投屏 (Tiểu Vi / Phóng Phi / AoWei / Jiwei) xuất hiện các ô màu cam báo "Phone disconnected, please check".
- **Bản chất kỹ thuật phân tầng (Triage 3 ranh giới):**
  1. **Slot trống vật lý / Mất cả vật lý:**
     * Windows PnP không tìm thấy InstanceId `USB\VID_...` (`Present: false` hoặc không tồn tại trong thiết bị USB).
     * *Lưu ý quy tắc đặc biệt:* Máy 255 trên Admin Farm là slot trống vật lý đã biết trước, cấm báo sập máy.
     * Với các máy khác: Rút cáp, đứt nguồn 5V VBUS hoặc máy sập nguồn hoàn toàn.
  2. **Mất hẳn khỏi ADB nhưng vẫn cắm vật lý (Hardware Connected, ADB Vanished):**
     * Windows PnP vẫn nhận diện thiết bị composite (`USB\VID_04E8&PID_6860\<SERIAL>` với `Status: OK`, `Present: true`).
     * `adb devices` hoàn toàn không có serial này (không xuất hiện cả ở dạng `offline`).
     * *Nguyên nhân:* Interface con ADB (`...&ADB\...`) bị lỗi driver/driver stack treo, hoặc tiến trình daemon `adbd` trên Android bị crash/kill ngầm mà không nhả VBUS.
  3. **ADB `offline`:**
     * `adb devices` vẫn liệt kê serial nhưng ở trạng thái `offline`.
     * Windows PnP `Present: true`.
     * *Nguyên nhân:* Kết nối vật lý và endpoint ADB vẫn tồn tại, nhưng socket handshake giữa host `adb.exe` và daemon `adbd` trên điện thoại bị timeout, flapping, hoặc màn hình khóa chưa accept USB debugging. Thường tự phục hồi qua `farm-adb-transport-healer` (`adb reconnect`).
- **Quy trình truy vấn O(1) an toàn (Không vi phạm Hard Guard ADB & Không quét đĩa):**
  * Lấy danh sách ADB an toàn: Chạy script chuẩn hóa `python D:/Taadaa/tools/inspect_machine.py`.
  * Truy vấn phần cứng PnP qua PowerShell (Kibe Local hoặc qua SSH tới Admin PC):
    ```powershell
    Get-PnpDevice -Class USB | Where-Object { $_.Present -eq $true } | Select-Object InstanceId, Status, FriendlyName
    ```
  * So khớp serial từ `USB\VID_04E8&PID_6860\<SERIAL>` với file mapping `PROXYgandienthoai.xlsx` của từng cụm (Kibe: M01–M80, Admin: M201–M280) để phân loại chính xác từng máy.





