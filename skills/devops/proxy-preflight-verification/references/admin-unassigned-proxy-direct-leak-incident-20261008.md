# Incident Postmortem: Farm Admin S7 Direct IP Leak via Preflight Direct Fallback (2026-10-08)

## 1. Hiện tượng & Bối cảnh
- **Cảnh báo của User:** Proxy MikroTik Admin (`10008..10035` / `mirotik1.taadaa.click`) mất mạng hoàn toàn (timed out 100%), nhưng trên app Jiwei (极卫安卓投屏), dàn máy S7 Admin (201–280) vẫn mở TikTok lướt feed, xem livestream ầm ầm.
- **Mức độ nghiêm trọng:** P0 (Direct IP Leak toàn bộ dàn Farm Admin 80 máy ra dải IP mạng nhà FPT `1.53.55.190`).

## 2. Chuỗi nguyên nhân gốc rễ (Root Cause Chain)

### Lỗ hổng 1: Dàn S7 Admin chưa được gán proxy trên hệ điều hành (`:0`)
- Dàn Kibe (M01–80) đã được gán cứng Singbox port `192.168.110.2:20000+N` qua `set_proxy_farm_adb.py`.
- Dàn Admin (M201–280) dù đã được quy hoạch trong `admin/PROXYgandienthoai.xlsx` trỏ về dải port MikroTik Direct `10008..10035`, nhưng trên thực tế thiết bị Android thật vẫn đang ở trạng thái mặc định:
  `settings get global http_proxy` $\rightarrow$ `:0` (Rỗng / Direct).
- Script gán `AI-Tools/scripts/set_proxy_farm_admin_adb.py` chưa được chạy đồng bộ trên dàn Admin sau các đợt reset.

### Lỗ hổng 2: Cạm bẫy Direct Fallback trong `check_android_vpn` (`automation_core/preflight.py`)
- Khi `run_post.py` hoặc runner gọi `require_android_vpn(adb, required=True)`:
  1. `serial_is_mapped_in_workbook` xác nhận máy có trong Excel $\rightarrow$ `required = True`.
  2. Hàm `check_android_vpn` gọi `_get_device_global_http_proxy(adb)` $\rightarrow$ trả về `:0` $\rightarrow$ gán `global_proxy = None`.
  3. Do `global_proxy is None`, code nhảy vào nhánh fallback nguy hiểm:
     ```python
     else:
         extracted_ip, last_err, conn_lost = _probe_atx_curl_public_ip(adb, ...)
     ```
  4. Lệnh này chạy `/data/local/tmp/atx-agent curl` probe trực tiếp qua Wi-Fi mà không truyền biến môi trường proxy.
  5. Wi-Fi `admin 2` (Ruijie AP) phát từ mạng FPT thông thường (chưa đi qua MikroTik), nên probe bắt được ngay IP WAN FPT: **`1.53.55.190`**.
  6. Code thấy có IPv4 công cộng hợp lệ nên đánh dấu `egress_ip_ok = True`, `ip_verified = True`, `is_safe = True`!
  7. **Hậu quả:** Preflight PASS cho mở TikTok, toàn bộ dàn nick dùng chung IP mạng nhà FPT `1.53.55.190` thay vì qua proxy MikroTik.

### Lỗ hổng 3: `_proxy_server_live` bị lừa bởi local LAN TCP socket
- Trong kịch bản MikroTik bị rớt kết nối ra ngoài (mất PPPoE / rớt WAN FPT): Cục router MikroTik và container 3proxy vẫn cắm điện trong LAN `192.168.110.2`.
- Cổng `10025` trên LAN vẫn mở và phản hồi tín hiệu TCP handshake (SYN-ACK).
- Lệnh probe `lan_res = s_lan.connect_ex(("192.168.110.2", p_port))` trả về `0` (thành công), khiến tầng host-side ngộ nhận là Proxy vẫn sống nhăn răng.

### Giải pháp Kiến trúc Triệt để (User Directive 2026-10-08)
1. **Gỡ bỏ mật khẩu 3proxy trên MikroTik:** Sửa biến môi trường container 3proxy `HTTP_USER=""` và `HTTP_PASS=""`. Vì RouterOS đã có rule firewall `ALLOW_FPT_LAN_PROXY_PORTS` chỉ cho phép LAN `FPT_LAN` kết nối và `DROP_EXTERNAL_PROXY_PORTS` chặn ngoài WAN, việc bỏ pass hoàn toàn an toàn và triệt tiêu vĩnh viễn lỗi Android `407 Proxy Authentication Required`.
2. **Gán cứng port MikroTik Direct cho S7 Admin:** Toàn bộ 58 máy S7 Admin được gán trực tiếp port `192.168.110.2:10008..10035` (`set_proxy_farm_admin_adb.py`).
3. **Khóa chết Preflight Fail-Closed:** Vá `vpn_preflight.py` và `run_post.py` chặn đứng nếu `settings get global http_proxy` là `:0`, rỗng hoặc không probe được public IP qua proxy. Cấm tuyệt đối fallback Wi-Fi direct.

## 3. Quy trình Dập tắt Khẩn cấp 3 Lớp (Emergency Kill Procedure)
Khi phát hiện sự cố Direct IP Leak hoặc dàn farm chạy chui khi proxy sập:
1. **Lớp 1 (Điều phối trên Host Kibe):**
   - Kill sạch các tiến trình orchestrator `run-feed-session.ps1` và `run_tiktok.py` đang phát lệnh nuôi dàn 201–280:
     `powershell "Stop-Process -Id <PIDs> -Force"`
2. **Lớp 2 (Workflow trên Host Admin qua SSH):**
   - Kill sạch các tiến trình `tiktok_workflow` đang thực thi upload/post ngầm trên PC Admin:
     `ssh admin-farm "taskkill /F /IM python.exe /T" (hoặc lọc PID CommandLine ~ tiktok_workflow)`
3. **Lớp 3 (Cưỡng chế trên Thiết bị Thật qua ADB đa luồng):**
   - Chạy Python script đa luồng (`ThreadPoolExecutor(max_workers=30)`) phát đồng loạt 2 lệnh trên toàn bộ 78 thiết bị:
     `am force-stop com.ss.android.ugc.trill`
     `input keyevent 3` (HOME)
   - Quét lại kiểm chứng `pidof com.ss.android.ugc.trill` phải bằng 0 trên 100% thiết bị.

## 4. Invariant Bắt Buộc Khắc Phục (Anti-Direct Fallback Invariant)
1. **FAIL-CLOSED khi máy có trong Excel nhưng mang proxy `:0`:**
   Khi `required=True` (máy thuộc diện bắt buộc proxy):
   Nếu `_get_device_global_http_proxy(adb)` trả về `None`, `:0`, `null`, `none` $\rightarrow$ **FAIL-CLOSED NGAY LẬP TỨC**:
   `raise ConsumerPreflightError("BLOCKED_MISSING_DEVICE_PROXY: device is mapped in workbook but global http_proxy is :0")`
   CẤM TUYỆT ĐỐI fallback sang probe Direct Wi-Fi.
2. **Kiểm tra Đối chiếu IP Mạng Nhà (Direct WAN Blacklist Check):**
   Nếu IP trích xuất được từ thiết bị trùng khớp với IP Direct WAN của Farm (`1.53.55.190`, `42.114.218.81`) $\rightarrow$ **FAIL-CLOSED**:
   `raise ConsumerPreflightError(f"DIRECT_IP_LEAK_DETECTED: device egress IP {proxy_ip} matches host direct WAN IP")`
3. **Đồng bộ gán proxy trước khi khởi động Runner:**
   Trước khi chạy bất kỳ ca nuôi hay upload nào trên dàn Admin, bắt buộc chạy:
   `python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_admin_adb.py`
   để đảm bảo 100% thiết bị có port `10008..10035` gán cứng trong hệ thống.
