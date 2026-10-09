---
name: proxy-preflight-verification
description: Verify Android tunnel, VPN state, proxy liveness, and real egress IP for device automation; diagnose why a registration proceeded after an apparently successful preflight.
---

# Proxy Preflight Verification

Use for mapped Android devices, TikTok registration, proxy/VPN watchdogs, and any incident where a `CONNECTED` log conflicts with a dead proxy or direct egress.

## Core model

Never collapse these into one boolean:

1. `tun0` exists and is UP: the tunnel interface exists.
2. Android reports VPN `CONNECTED`: the VPN network agent is connected.
3. ViChanger `GET_IP` returns `result=200` plus a non-empty IP: the configured proxy path answered at that instant.
4. The returned public IP differs from a direct host egress probe: the traffic actually exits through a different public IP.

`VPN CONNECTED` is not proof of proxy liveness or IP substitution. `result=0`, missing `data`, timeout, or empty IP is unverified/dead for a mapped target.

## Incident workflow

1. Read the target's exact batch log around preflight and registration start.
2. Align timestamps before drawing conclusions. A current failure does not prove an earlier failure.
3. Inspect the historical source commit, interpreter, runner environment, and live-IP flag used at that timestamp; do not use only today's source.
4. Confirm the target was actually mapped to a non-empty proxy. An unmapped target may legitimately skip the required gate.
5. Inspect the preflight implementation and wrapper. A fail-closed shared helper may raise correctly while a consumer wrapper can still log a permissive status string or ignore the boolean/error decision.
6. Determine whether verification was one-shot. A preflight pass is a point-in-time observation, not a lease; if the proxy dies later, the flow needs a second gate immediately before registration.
7. Compare proxy-returned IP and direct host IP from comparable timestamps. If either is missing, report `UNVERIFIED`, not “fake IP confirmed”.

## Required evidence

For every mapped target, preserve a redacted structured record containing target/serial, timestamp, `tun_up`, Android VPN state, `GET_IP` result, returned IP, retry count, error, direct host egress IP, interpreter/runtime, source revision, live-IP flag, and whether a second preflight ran.

Logs saying only `vpn preflight: CONNECTED` are insufficient. A later watchdog result cannot retroactively prove the earlier egress route.

## Safe behavior

Investigation is read-only by default: do not reassign proxy, restart ADB, restart VPN, clear app data, rerun registration, or alter the device unless explicitly requested. Redact proxy credentials, tokens, OTPs, email passwords, and other secrets.

For a mapped device, a failed live-IP check must fail closed. Do not weaken the gate to tunnel-only status. If the evidence is incomplete, stop the target and report the exact missing proof.

## Common interpretations

- `BLOCK VPN_PREFLIGHT_BLOCKED ... GET_IP failed`: the fail-closed gate worked (proxy upstream dead/unreachable while tun0 is UP).
- `vpn preflight: CONNECTED proxy_ip=<IP>` then `preflight_phase passed`: the gate passed with verified non-empty live proxy IP.
- `MACHINE_IN_USE`: that invocation did not enter device registration, even if it emitted a preflight line.
- Later `GET_IP result=0`: later proxy failure; correlate, do not backdate it.

## Invariant for Consumer Repos (Tiktok_Reg, Feed Session & Gmail Reg)
1. Mapping resolution MUST use `serial_is_mapped_in_workbook` with normalized header aliases (`phoneId`, `deviceId`, `serial`), never hardcoded column indices.
2. Registration & automation scripts MUST hardcode `verify_live_ip=True` (never allow env vars to disable it).
3. Preflight MUST require `status.allowed`, `status.connected`, AND non-empty `status.proxy_ip` before proceeding to app launch:
   - **Global HTTP Proxy Egress Fail-Closed Invariant (2026-09-28)**:
     * **Cạm bẫy direct curl fallback & LAN ping bypass**: Trong `automation_core.preflight.check_android_vpn`, khi thiết bị có cấu hình `global_proxy` (như Sing-box container `192.168.110.2:200xx`), nếu upstream proxy chết (502 Bad Gateway / Connection Refused / timeout), lệnh probe IP qua proxy sẽ thất bại.
     * **Nguy cơ**: Nếu script fallback sang direct `atx-agent curl` (không truyền env proxy) hoặc chấp nhận điều kiện `ping_ok and wifi_validated`, thiết bị có thể lấy được IP WAN của mạng Wi-Fi LAN hoặc ping thông gateway nội bộ `192.168.110.1`, dẫn đến việc preflight ngộ nhận `allowed=True`. Trong khi đó, app người dùng (TikTok, Google) bắt buộc đi qua global proxy bị 502, làm app mở lên switch account/văng lỗi vô ích.
     * **Quy tắc bắt buộc**: Khi `global_proxy` tồn tại: (1) CẤM fallback sang direct curl; (2) CẤM dùng LAN ping / Wi-Fi validation để bypass khi proxy egress fail; (3) Bắt buộc `ip_verified = egress_ip_ok` chỉ khi probe thành công public IPv4 hợp lệ qua đúng proxy đó. Nếu probe qua proxy lỗi, lập tức ngắt phiên fail-closed (`allowed=False`) trước khi chạm vào app.
   - **LAN Ping Fallback Trap in `automation-core`**: Trong chế độ transparent router proxy (`wlan0`), `check_android_vpn` có điều kiện nghiệm thu: `if egress_ip_ok or (ping_ok and wifi_validated): ip_verified = True`. Khi upstream proxy (4G dongle/server) bị sập hoặc trả `502 Bad Gateway`, việc probe IP public thất bại (`egress_ip_ok=False`), nhưng do điện thoại vẫn ping được default gateway trong LAN (`ping_ok=True`) và Wi-Fi vẫn kết nối (`wifi_validated=True`), hàm sẽ trả về `allowed=True` nhưng `proxy_ip=""` (chuỗi rỗng).
   - Nếu consumer repo (như `gmail_reg_v10.py`) chỉ kiểm tra `require_android_vpn().allowed` mà KHÔNG kiểm tra `vpn_status.proxy_ip`, script sẽ ngộ nhận proxy còn sống, mở app và lập tức dính lỗi mất mạng (như `[04b][GMS_NO_NETWORK] transient Google network screen`).
   - Mọi consumer BẮT BUỘC phải cài chốt chặn:
     ```python
     proxy_ip = str(getattr(vpn_status, "proxy_ip", "") or "").strip()
     if vpn_required and (not getattr(vpn_status, "allowed", False) or not proxy_ip):
         raise ConsumerPreflightError(f"Proxy verification failed: live proxy IP proof missing")
     ```
   - **Bắt buộc cài chốt chặn Device Proxy & Direct Fallback Block (2026-10-08)**:
     * Trên Android, nếu thiết bị có tên trong mapping workbook (`vpn_required`), nhưng cấu hình `settings get global http_proxy` trên máy bị rỗng, `null` hoặc `:0`, hàm preflight KHÔNG ĐƯỢC fallback sang direct Wi-Fi probe (vì direct probe sẽ bắt IP WAN nhà mạng FPT thông thường, tạo false-positive pass và gây Direct IP Leak toàn dàn nick).
     * Mọi consumer runner (cả `vpn_preflight.py` trong feed session và `run_post.py` trong upload video) BẮT BUỘC phải kiểm tra trước:
       ```python
       if vpn_required:
           p_out = adb.shell(["settings", "get", "global", "http_proxy"], timeout=3.0, check=False)
           p_val = str(getattr(p_out, "stdout", "") or "").strip()
           if not p_val or p_val.lower() in ("null", ":0", "none", "0.0.0.0:0"):
               logger.error("[PREFLIGHT_PROXY_MISSING] device=%s settings_proxy=%s", serial, p_val)
               raise ConsumerPreflightError(f"required Android VPN/proxy is not set on device: settings global http_proxy is missing or :0 for {serial}")
       ```
     * Khi kiểm tra `allowed=True`, BẮT BUỘC verify `status.proxy_ip` không rỗng và khác WAN direct host.
     * **Telemetry & Regression Test Gate**: Mọi thay đổi logic fail-closed BẮT BUỘC đi kèm:
       (1) Log telemetry cấu trúc `[PREFLIGHT_FAIL_CLOSED]` / `[PREFLIGHT_PROXY_MISSING]` ghi rõ device, interface, proxy_ip.
       (2) Bộ unit test mô phỏng đủ 4 nhánh lỗi: proxy `:0`, proxy rỗng, server port đóng/refuse, và preflight pass nhưng thiếu live IP proof (xem `tests/test_vpn_preflight_proxy_guard.py` và `tests/test_vpn_preflight_post.py`).
   - **Chuẩn Hóa Tiền Tố Log & Mapping Constants (2026-09-08)**: Trong toàn bộ consumer scripts (đặc biệt `gmail_reg_v10.py`), loại bỏ hoàn toàn các tiền tố log legacy `[vichanger-preflight]` đổi thành `[proxy-preflight]`, và thay thế `VICHANGER_PROXY_MAPPING_PATH` bằng `FARM_PROXY_MAPPING_PATH`. Farm đã ngắt hoàn toàn app ViChanger, mọi kiểm tra thực tế diễn ra ở tầng router transparent proxy / global ADB proxy.
4. **Router Transparent Proxy Preflight & Route Isolation**:
   - **Dual-Route Architecture**: Explicit `interface` argument (`"wlan0"` vs `"tun0"`) takes absolute precedence over `TAADAA_PROXY_MODE`. All preflight helpers (`require_android_vpn`, `check_android_vpn`, `run_consumer_after_vpn_preflight`) default to `interface="auto"` (uses `tun0` if UP, else `wlan0`), preventing router-proxy farm devices from erroneously failing closed looking for ViChanger `tun0`.
   - **Router Mode Preflight (`wlan0`)**: Requires (1) `wlan0` UP with assigned IP, (2) `dumpsys connectivity` confirms `WIFI CONNECTED` and strictly `VALIDATED` (rejecting `NOT_VALIDATED`, intermediate states, or VPN `VALIDATED`), (3) fast bounded ping to dynamically resolved default gateway (xem quy tắc fallback gateway phía dưới) and fallback `8.8.8.8`, and (4) egress IP validation via `/data/local/tmp/atx-agent curl --timeout=5s http://icanhazip.com` strictly verified against version-independent IANA non-public CIDRs with `192.0.0.9/.10` Anycast carve-outs.
   - **Dynamic Gateway Fallback & Android Policy Routing**:
     * Trên Android 7+, lệnh `ip route show dev wlan0` chỉ hiển thị routing table `main` và KHÔNG chứa `default via` (do default route nằm trong policy routing table 0 / table 1014).
     * TUYỆT ĐỐI KHÔNG fallback về gateway tĩnh hardcode (như `192.168.10.254`) khi regex không khớp, vì sẽ làm ping fail trên các máy thuộc subnet khác (ví dụ `192.168.110.0/24`).
     * Thứ tự resolve gateway động bắt buộc: (1) `ip route show dev wlan0` -> (2) Trích xuất từ `dumpsys connectivity` đã đọc sẵn (`0.0.0.0/0 -> <gateway> wlan0`) -> (3) Suy diễn subnet gateway `.1` từ IP gán trên `wlan0` (`inet 192.168.110.X` -> `192.168.110.1`).
     * Đặt timeout ping `-W 2` (2 giây) thay vì `-W 1` để tránh false-negative rớt ping khi Wi-Fi lag đột ngột >1000ms.
   - **Route-Isolated Recovery**: For `wlan0` router mode, execute a full Wi-Fi toggle cycle (`svc wifi disable` -> `sleep 1.0` -> `svc wifi enable`) once then fail-closed immediately. NEVER call ViChanger watcher or soft-reboot on router devices (prevents cascading device locks and worker thread starvation).
   - **Thread-Safe Cache & Hermetic Tests**: Synchronize proxy mapping cache fully under `threading.Lock()` without unlocked reads, and ensure test fixtures reset cache before/after all tests.
   - **Ping Substring Pitfall & Mock Prefix Matching**:
     * `"0% packet loss"` is inside `"100% packet loss"`. Always check `" 0% packet loss"` or regex `r"\b0%\s+packet\s+loss"` to avoid false-positive ping matches.
     * Trong các test mock ADB (`FakeAdb`, `OfflinePingAdb`), tuyệt đối không match cứng số gói `args[:4] == ["ping", "-c", "1", "-W"]`; bắt buộc dùng prefix check `args[:2] == ["ping", "-c"]` để fixture tự tương thích khi thay đổi số gói probe. Mock kiểm tra killswitch router phải đặt `atx_curl=""` để tránh việc IP public mặc định làm pass nhầm cổng `egress_ip_ok`.
   - **Single-Packet Ping Sensitivity & MikroTik VLAN 10 ICMP Drop**:
     * Khi thiết bị có SSID rác đang kích hoạt chu kỳ quét ngầm (`CTRL-EVENT-SSID-TEMP-DISABLED`), một lệnh probe đơn lẻ `ping -c 1 -W 2` tới gateway có thể bị rớt 100% gói do RF drop tức thời dù kết nối tổng thể vẫn sống. Cần dùng `ping -c 2 -W 2` và kiểm tra `re.search(r"\b[1-9]\d*\s+received\b", ping_text)` để bắt ít nhất 1 gói thành công.
     * Trên mạng có MikroTik VLAN 10 (`192.168.10.x`), router gateway `192.168.10.254` cấu hình drop gói ICMP Echo Request và subnet không route trực tiếp ICMP ra `8.8.8.8`. Khi có `global_proxy` (vd `192.168.110.2:20051`), bắt buộc đưa IP máy chủ proxy (`192.168.110.2`) vào danh sách ping probe targets (`gw_ip`, `proxy_host`, `8.8.8.8`).
     * **Egress IP Precedence over ICMP**: HTTP proxy chỉ forward TCP, không forward ICMP. Khi `egress_ip_ok` đã trích xuất thành công public IPv4 hợp lệ qua proxy (`atx-agent curl`), thiết bị đã thực sự thông mạng internet. Điều kiện nghiệm thu phải chấp nhận `egress_ip_ok or (ping_ok and wifi_validated)` để tránh fail-closed oan khi ICMP bị firewall chặn.
   - **AdbClient Constructor Positional Argument Pitfall**: Constructor `AdbClient.__init__` có chữ ký `(self, adb_path: str = 'adb', serial: str | None = None, ...)`. Truyền serial theo dạng vị trí thứ nhất (`AdbClient('988678543555413857')`) sẽ khiến runtime hiểu nhầm serial là đường dẫn file binary ADB (`adb executable not found: <serial>`). BẮT BUỘC truyền keyword `AdbClient(serial='<serial>')` hoặc đủ 2 đối số vị trí `AdbClient('adb', '<serial>')`.
   - **`tun_up` Semantics**: Keep `tun_up` strictly for `tun0` tunnel presence; use `interface_up` for the active route to avoid breaking legacy callers.
5. **Fast Fail-Closed Server Socket Probe (Batch Starvation Prevention)**:
   - When an entire proxy server host/port is down/refused from the outside, running full recovery (watcher reassign + soft-reboot timeout: 4-6 minutes/device) across dozens of devices exhausts the `ThreadPoolExecutor` worker pool and starves devices with live proxies.
   - Consumer preflight must perform a fast TCP probe (`connect_ex` with timeout <=1.5s) on the mapped proxy host/port. If the port is refused/closed at the server level, fail-closed immediately (`blocked-vichanger-vpn`) in <=1.5s, skipping the multi-minute recovery wait to instantly yield worker threads to healthy devices.
6. **Phân biệt Batch Process vs Device Action khi Server Proxy sập**:
   - Khi dải proxy chết hàng loạt, tiến trình batch (`powershell / run-feed-session.ps1`) trên host vẫn sống để duyệt qua danh sách và quản lý lifecycle phiên.
   - Thiết bị Android thật bị fail-closed chặn đứng 100% tại preflight (`swipes_completed=0`), tuyệt đối không lướt feed bằng Direct IP. Luôn tách rõ điều này khi báo cáo.
7. **Chẩn đoán Phân tầng Sự cố VPN / Proxy / Wi-Fi (Triage 3 tầng khi lỗi hàng loạt)**:
   - **Tầng 1 (Wi-Fi / DHCP nội bộ / Treo chip)**: Chạy `adb -s <serial> shell ip addr show wlan0` và `dumpsys wifi`. Nếu `wlan0` ở trạng thái `NO-CARRIER`/`DORMANT` hoặc báo `Device wlan0 does not exist`, hoặc `dumpsys wifi` ghi nhận `level2FailureCode=DHCPUNKNOWN` / rớt kết nối (`DISCONNECTED`) trên toàn dàn $\rightarrow$ Nguyên nhân là Access Point (AP) / Router DHCP nội bộ bị treo hoặc chip Wi-Fi trên máy bị treo $\rightarrow$ Khởi động lại AP/Router Wi-Fi hoặc reboot máy.
   - **Tầng 2 (Upstream Proxy Box / Server Port Refused / WAN)**: Nếu điện thoại vẫn nhận IP Wi-Fi nội bộ nhưng host probe port proxy bị từ chối (`Server Port Live: False` do port đóng) hoặc ViChanger `GET_IP` trả `result=0` $\rightarrow$ Kiểm tra cụm server proxy (Mikrotik/MobiProxy/4G proxy server), nguồn/sim hoặc routing firewall.
   - **Tầng 3 (App ViChanger / ADB Transport / Rớt cáp USB)**: Nếu serial không có trong `adb devices` $\rightarrow$ Rớt kết nối cáp vật lý / hub USB. Preflight đã được trang bị cơ chế kiểm tra `is_connection_lost(stderr)` ở probe đầu tiên để ngắt sớm và báo trực tiếp `device offline or ADB/USB disconnected`, không bị lọt vào lỗi mạng Wi-Fi/Proxy. Nếu Wi-Fi và proxy ngoài đều sống nhưng lệnh broadcast `GET_IP` bị timeout (`broadcast exception: adb command timed out`) $\rightarrow$ Do nghẽn adbd hoặc ViChanger treo nhẹ, bắn lại broadcast thủ công để kiểm tra.
8. **MikroTik PPPoE Uptime vs Proxy Listener Socket Desync & Quản trị Tự động**:
   - Web dashboards/tools (ví dụ: `mikrotik-tool.pages.dev`) chỉ hiển thị trạng thái kết nối interface PPPoE (`pppoe-outX: CONNECTED`, uptime 22h+), KHÔNG phản ánh socket listener của dịch vụ HTTP/SOCKS proxy hoặc NAT port forwarding.
   - Từng dải port cụ thể (ví dụ: 10001–10007, 10009) có thể bị treo socket / Connection Refused trong khi các port khác (ví dụ: 10008, 10010–10035) trên cùng một router MikroTik và cùng IP public vẫn OPEN và hoạt động bình thường.
   - Luôn quét toàn diện TCP socket (`socket.connect_ex`) và probe egress HTTP proxy thực tế (`urllib.request / curl -x`) trên từng port để xác định chính xác tập hợp port sống/chết, không kết luận dựa trên trạng thái interface PPPoE của router.
   - **Quản trị MikroTik tự động qua REST API & Quét Sing-box Proxy Cluster (Farm Infrastructure)**:
     * Endpoint nội bộ: `http://192.168.110.2:9090/rest` (User: `admin`, Pass: `N0spam@@`).
     * Script công cụ tích hợp sẵn: `D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py` (`--check`, `--fix`, `--reconnect <line_num>`).
     * Dàn 80 máy Kibe sử dụng cụm Sing-box container (192.168.110.2:20001..20080) và quản trị gán proxy ADB qua `AI-Tools/scripts/set_proxy_farm_adb.py`.
     * **Công cụ quét nhanh toàn bộ 80 cổng proxy Sing-box**: Chạy script đi kèm skill `python <skill_dir>/scripts/scan_singbox_farm_proxies.py --host 192.168.110.2 --workers 30` (hoàn thành quét 80 cổng trong ~1.5s, tự động phân loại OK / 502 Bad Gateway / RESET / REFUSED / TIMEOUT và xuất báo cáo).
   - **Quy tắc báo cáo lỗi gửi bên thứ 3/admin**: Khi user yêu cầu viết lỗi gửi admin, CHỈ ghi ngắn gọn hiện tượng và IP/port lỗi, TUYỆT ĐỐI KHÔNG tự ý chèn giải pháp/hướng dẫn khắc phục khi chưa được yêu cầu.\n   - **MikroTik REST API Firewall Config & Anti-Scan Workflow (2026-09-10):**
  - **Endpoint**: `http://192.168.110.2:9090/rest` (User: `admin`, Pass: `N0spam@@`).
  - **Step-by-step workflow:**
    1. Audit filter rules: `GET /ip/firewall/filter`
    2. Create FPT_LAN address-list: `PUT /ip/firewall/address-list` with `{"address": "192.168.110.0/24", "list": "FPT_LAN", "comment": "FPT LAN - allowed to use proxy"}` (repeat for `192.168.10.0/24`, `127.0.0.1`)
    3. Add ALLOW rule: `PUT /ip/firewall/filter` with `{"chain": "forward", "action": "accept", "protocol": "tcp", "dst-port": "10001-10035,20001-20080", "src-address-list": "FPT_LAN", "comment": "ALLOW_FPT_LAN_PROXY_PORTS"}`
    4. Add DROP catch-all: `PUT /ip/firewall/filter` with `{"chain": "forward", "action": "drop", "protocol": "tcp", "dst-port": "10001-10035,20001-20080", "comment": "DROP_EXTERNAL_PROXY_PORTS"}`
    5. Disable unrestricted legacy rules: `PATCH /ip/firewall/filter/<id>` with `{"disabled": "true"}` for rules matching `dst-port=10000-10039`, `20000-20039`, `20001-20080` without src-address filter
    5. Restrict generic forwards: Update `ALLOW_FARM_ADMIN_FORWARD` with `src-address-list=FPT_LAN`
    6. Disable redundant PPPoE lines: `PATCH /interface/pppoe-client/<id>` with `{"disabled": "true"}` for lines 46-60
    7. Verify egress: `curl -x http://admin@1:admin@1@192.168.110.2:10001 http://api.ipify.org`
  - **Config Preservation:** Export running config to `docs/infrastructure/mikrotik/firewall-fptlan-proxy-rules-<date>.rsc` and update `mikrotik-master-network-handbook.md`, then git commit/push.
  - **Packet vs Request Explanation:** Firewall packet counters on RouterOS count TCP packets (RAM, reset on reboot, tracked by uptime). One HTTP request = 10-30+ packets (SYN, SYN-ACK, ACK, payload, FIN/RST). 57M packets = ~14GB traffic, NOT 57M individual requests.
9. **ADB Transport Disconnect Fail-Fast in Preflight (Tránh báo nhầm lỗi Proxy/Wi-Fi)**:
   - Khi thiết bị mất kết nối ADB / rớt cáp USB / offline (`device '...' not found`, `device offline`, `error: closed`, `protocol fault`, `adb command timed out`), `adb.shell` với `check=False` trả về `ok=False` cùng thông báo lỗi trong `stderr` hoặc ném `ADBError`.
   - Preflight (`check_android_vpn` trong `automation_core.preflight` và `require_vichanger_connected` trong `vpn_preflight.py`) BẮT BUỘC kiểm tra `is_connection_lost(stderr)` ở probe đầu tiên (`tun0` hoặc `wlan0`) để lập tức fail-fast và trả mã lỗi `device offline or ADB/USB disconnected: <stderr>`.
   - Tuyệt đối không để exception / failure do mất ADB lọt xuống nhánh `else` ghi nhận nhầm thành `wlan0 interface down or unassigned IP` / `dumpsys connectivity: Wi-Fi not connected` / `required router proxy is unreachable`, tránh việc runner kích hoạt recovery Wi-Fi (`svc wifi enable`) vô ích và phát cảnh báo Telegram sai lệch hiện trường.
10. **Global HTTP Proxy Resolution & atx-agent Output Capture (Tránh false positive egress IP validation)**:
   - Trên dàn máy dùng proxy Wi-Fi (gán qua `settings put global http_proxy <host>:<port>`), subnet Wi-Fi nội bộ không route direct internet. Lệnh `/data/local/tmp/atx-agent curl` chạy trong adb shell không tự nhận proxy settings nếu không truyền biến môi trường `http_proxy` / `HTTP_PROXY`.
   - Preflight `check_android_vpn` bắt buộc đọc `settings get global http_proxy` (hoặc `global_http_proxy_host` / `global_http_proxy_port`). Nếu có proxy, gọi probe với env `http_proxy=http://<proxy>` `HTTP_PROXY=http://<proxy>`, sau đó mới fallback về direct probe.
   - **`atx-agent` Go STDERR logging**: `atx-agent curl` ghi nhận log request và output IP (`curl.go:116: <IP>`) ra **STDERR**, không phải STDOUT. Parser trích xuất IP bắt buộc kiểm tra cả `stdout` và `stderr` (`f"{stdout}\n{stderr}"`), tuyệt đối không chỉ đọc `stdout` vì sẽ nhận chuỗi rỗng và gây false-positive fail-closed.
   - **DNS Resolver IP Exclusion**: `atx-agent curl` ghi log DNS resolution `time="..." level=info msg="dns resolve 114.114.114.114"`. Hàm trích xuất IP bắt buộc ưu tiên định dạng log `curl.go:<line>: <IP>` và loại trừ các IP DNS public nổi tiếng (`114.114.114.114`, `8.8.8.8`, `1.1.1.1`, v.v.) để tránh bắt nhầm IP DNS resolver thay vì IP public ra ngoài thực tế.
   - **Windows ADB shell quoting**: Khi truyền lệnh qua `adb.shell()` trên Windows, tránh dùng `['sh', '-c', '...']` vì ADB CLI tự ghép khoảng trắng làm mất dấu nháy của script. Nếu proxy URL chỉ chứa ký tự chuẩn (`^[a-zA-Z0-9.\-_]+:\d+$`), truyền thẳng không bọc nháy đơn để tránh shell quoting mismatch: `[f"export http_proxy=http://{global_proxy}; export HTTP_PROXY=http://{global_proxy}; /data/local/tmp/atx-agent curl --timeout=5s http://icanhazip.com"]`. Chỉ dùng `shlex.quote` làm fallback khi chuỗi proxy chứa ký tự đặc biệt.
   - **atx-agent curl Direct Fallback Trap on Global Proxy Devices (Cạm bẫy Fallback Direct Egress)**:
     * Trên các máy Android cấu hình `settings global http_proxy` (như Sing-box `192.168.110.2:200xx` trỏ ra MobiProxy `test.taadaa.click`), `atx-agent` là tiến trình Go chạy trong shell adb nên không tự động kế thừa proxy Java của Android nếu không truyền biến môi trường `http_proxy`.
     * Khi upstream proxy chết (ví dụ MobiProxy `test.taadaa.click` sập, Sing-box trả `502 Bad Gateway`), hàm probe qua proxy thất bại (`egress_ip_ok=False`).
     * **Cạm bẫy chí mạng**: Nếu code preflight fallback sang probe direct `atx-agent curl` (không truyền proxy) và Wi-Fi vẫn có egress ra internet (hoặc mạng FPT thông thường), `atx-agent` sẽ bắt được IP WAN direct của router (`1.53.55.190`) $\rightarrow$ ngộ nhận `egress_ip_ok=True` và cho PASS PREFLIGHT.
     * Trong khi đó, ứng dụng TikTok trên Android bắt buộc đi qua `global http_proxy` $\rightarrow$ gặp 502/mất mạng $\rightarrow$ app vẫn bị mở lên vô ích, cố switch account và văng lỗi "Không có kết nối".
     * **Quy tắc bất biến**: Khi thiết bị có `global_proxy`, **CẤM TUYỆT ĐỐI fallback sang direct probe**. Probe qua proxy thất bại BẮT BUỘC phải fail-closed ngay lập tức (`blocked-proxy-vpn: proxy egress failed`).
   - **atx-agent curl Timeout under High RTT / Weak Wi-Fi RSSI (Tránh false positive fail-closed)**:
     * Khi sóng Wi-Fi của máy farm bị suy hao (RSSI <= -80 dBm, ví dụ SignalStrength: -81 dBm) hoặc mạng chập chờn, ping default gateway có thể lên tới 500ms–1000ms+.
     * Nếu đặt `--timeout=3s` quá ngắn cho `atx-agent curl`, tiến trình DNS lookup + proxy handshake + TLS/HTTP GET sẽ vượt ngưỡng 3s và bị ngắt giữa chừng trên toàn bộ 3 endpoints, dẫn đến lỗi giả mạo: `global proxy egress IP verification failed: all public IP check endpoints failed or atx-agent missing` và `Internet validation failed (Wi-Fi not VALIDATED...)`.
     * Timeout cho `atx-agent curl` khi probe qua proxy bắt buộc đặt tối thiểu 5s (ví dụ `--timeout=5s`). Đồng thời shell timeout của lệnh ADB phải lớn hơn hẳn (`max(timeout, float(curl_timeout) + 2.0)`) để wrapper không kill ADB trước khi Go binary in stderr.
     * Bổ sung cơ chế retry đa vòng (`attempts = max(1, retries + 1)`) với sleep ngắn `time.sleep(0.8)` giữa các lượt probe toàn bộ endpoints để vượt qua các đợt beacon scan / RF fade tức thời của Wi-Fi.
     * Khi user hỏi *"Mất wifi hay gì v"* khi gặp alert này: Kiểm tra 3 bước O(1) để phân định: (1) `ip addr show wlan0` & `dumpsys connectivity` xem state CONNECTED và SignalStrength; (2) `ping -c 3 <gateway>`; (3) `curl -x` từ host và device qua proxy. Nếu cả 3 đều phản hồi thì Wi-Fi và Proxy không chết mà do probe timeout bị thắt quá chặt.
11. **ADB Probe Timeout Self-Healing & Transport Auto-Reconnect (Xử lý ADB Transport Timeout)**:
   - **Phân loại Timeout đúng bản chất**: `CONNECTION_LOST_MARKERS` bắt buộc chứa `"adb command timed out"`. Khi lệnh ADB probe (`ip addr show wlan0`, `dumpsys connectivity`, v.v.) bị timeout, hàm `is_connection_lost` nhận diện chính xác đây là lỗi transport/socket nghẽn, ngăn việc nhầm lẫn thành lỗi proxy router hay kill switch (`required router proxy is unreachable`).
   - **Cơ chế Tự phục hồi (Self-Healing Reconnect)**:
     1. Khi preflight probe gặp `ADBError` timeout hoặc transport disconnect, script tự động kích hoạt `adb.reconnect()` / `_reconnect_device()`.
     2. Nghỉ 2.0s để socket ADB phía host/daemon tái lập transport.
     3. Thực hiện lại `check_android_vpn` lần 2. Nếu probe lần 2 thành công, runner tiếp tục flow bình thường.
     4. Nếu sau khi auto-reconnect mà probe vẫn báo offline / timeout, script fail-closed với mã lỗi chuẩn `device is offline or ADB/USB disconnected for {serial}`.
   - **Cập nhật Error Detail mới nhất**: Trong các luồng retry phục hồi mạng router (`svc wifi enable`), chuỗi lỗi ném ra bắt buộc lấy từ kết quả probe mới nhất (`retry_status.error`), tuyệt đối không dùng lại `initial_status.error` cũ đã lỗi thời.
12. **Fast O(1) Public IP & TCP Socket Probe on Android Devices (Tránh broad scan / nc -z pitfall)**:
   - **Cạm bẫy `toybox nc -z` trên Android**: Android `toybox nc` KHÔNG hỗ trợ flag `-z` (`nc: Unknown option z`). Khi probe socket TCP từ shell Android không root, BẮT BUỘC dùng cú pháp:
     `adb -s <serial> shell "echo | toybox nc -w 2 <proxy_ip> <proxy_port>; echo \$?"` (trả về 0 = OPEN, 1 = TIMEOUT/REFUSED).
   - Khi cần kiểm tra nhanh IP public của máy Android farm:
     * **CẤM TUYỆT ĐỐI dùng `grep -rn`, `find`, hoặc `search_files` quét diện rộng ổ đĩa:** Quét tìm file script check IP trong các cây thư mục lớn trên Windows làm treo terminal 15+ phút (timeout 900s).
     * **Cách 1 (Từ Host qua Proxy gán):** Đọc port proxy của máy qua `adb shell settings get global http_proxy` (vd `192.168.110.2:20007`), sau đó dùng script Python trên Host truy vấn `http://api.ipify.org` qua proxy handler đó (chạy < 1s).
     * **Cách 2 (Trực tiếp từ thiết bị không cần curl/root):** Dùng `toybox nc` gửi HTTP GET request thẳng qua port proxy gán:
       `adb -s <serial> shell "printf 'GET http://api.ipify.org/ HTTP/1.1\r\nHost: api.ipify.org\r\nConnection: close\r\n\r\n' | toybox nc -w 5 -W 5 <proxy_ip> <proxy_port>"`
       Trả về raw response HTTP kèm IP public lập tức.
       *Lưu ý cạm bẫy Cloudflare Cookie:* Phản hồi raw HTTP chứa headers, trong đó cookie `Set-Cookie: __cf_bm=...-1.0.1.1-...` có chuỗi version dạng `1.0.1.1`. Regex quét IP không được bắt nhầm chuỗi này trong header; ưu tiên dùng `atx-agent curl` trong code automation vì Go runtime chỉ trả về body response.
13. **Chẩn đoán Lệch Subnet DHCP & Xung Đột SSID Rác (Tầng 1 Wi-Fi vs Tầng 2 Proxy)**:
   - **Hiện tượng ICMP sống nhưng TCP Proxy Socket Timeout**: Khi máy farm ping ICMP tới gateway và server proxy `192.168.110.2` đều PASS (0% loss), nhưng `atx-agent curl` hoặc TCP probe sang port proxy báo `i/o timeout` hoặc `connection refused` cục bộ:
     * Kiểm tra subnet `ip -4 addr show wlan0`: Dàn farm có thể bị phân mảnh thành 2 subnet cùng tồn tại trên switch/AP (ví dụ `192.168.110.0/24` cấp bởi Ruijie gateway `192.168.110.1` vs `192.168.10.0/24` cấp bởi MikroTik pool `dhcp_vlan10_kibe`).
     * Kiểm tra SSID rác trong `dumpsys wifi`: Các SSID cũ không hợp lệ (ví dụ `Dinh Khoi_5G`, `Dat-1`) còn lưu trong Wi-Fi config khiến Android liên tục quét ngầm và kích hoạt chu kỳ `AUTHENTICATION_FAILURE` (`wlan0: CTRL-EVENT-SSID-TEMP-DISABLED`), gây rớt gói TCP và drop luồng proxy.
     * Quy trình xử lý dứt điểm: (1) Xóa mạng rác: với Android 9/10+ dùng `cmd wifi forget-network <id>`; với Samsung S7 Android 8.0 lệnh `cmd wifi` không hỗ trợ (`No shell command implementation`), phải mở `am start -a android.settings.WIFI_SETTINGS` và quên mạng qua UI/atx-agent; (2) Reset adapter: `svc wifi disable && sleep 2 && svc wifi enable` (hoặc `adb reboot` nếu cần renew sạch DHCP); (3) Chạy `python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_adb.py --machines <N>` để refresh proxy và tắt captive portal.
14. **Xung đột 2 DHCP Server trên L2 Broadcast Domain (DHCP Race Condition giữa MikroTik và Ruijie)**:
   - **Hiện tượng**: Dàn máy farm bị phân mảnh nhận 2 dải IP khác nhau (`192.168.110.x` từ Ruijie `.1` và `192.168.10.x` từ MikroTik `ether3` `.254`). CẤM TUYỆT ĐỐI dùng từ ngữ gây hiểu lầm như "dải khách" để giải thích cho user (đây là VLAN 10 của MikroTik bị gán nhầm untagged lên ether3, không phải mạng khách).
   - **Nguyên nhân**: DHCP Server `dhcp_vlan10_kibe` trên MikroTik bị gán trực tiếp lên cổng vật lý untagged `ether3` thay vì sub-interface `vlan10_kibe`, chạy song song với DHCP Server của Ruijie trên cùng switch Layer 2. Khi MikroTik reboot hoặc routing table chưa ổn định, các gói tin TCP từ dải `192.168.10.x` sang cụm Singbox proxy `192.168.110.2:200xx` bị drop/timeout, kích hoạt preflight fail-closed.
   - **Xử lý triệt để**: Vô hiệu hóa `dhcp_vlan10_kibe` trên MikroTik qua REST API `PATCH /rest/ip/dhcp-server/*1` (`{"disabled": "true"}`), sau đó rolling cycle Wi-Fi (`svc wifi disable && sleep 2 && svc wifi enable`) để toàn bộ farm thống nhất nhận dải `192.168.110.x` từ Ruijie. Chi tiết trong `references/dhcp-dual-server-race-and-mikrotik-vlan10-remediation.md`.
15. **On-Device Global HTTP Proxy Precedence in Socket Probe (Workbook Desync & Mass Fail-Closed Prevention)**:
   - **Nguy cơ False-Positive Fail-Closed hàng loạt**: Khi dàn farm chuyển đổi sang cụm proxy mới (ví dụ Sing-box container trên `192.168.110.2:20001..20080` gán qua `settings put global http_proxy`) nhưng file mapping trên host (`PROXYgandienthoai.xlsx`) vẫn lưu cấu hình proxy cũ đã sập (như `test.taadaa.click:51xx`), việc hàm `_proxy_server_live` chỉ đọc proxy từ file Excel sẽ khiến probe TCP tới proxy cũ bị từ chối/đóng (`connect_ex != 0`). Hệ thống sẽ kích hoạt fast fail-closed (`required Android VPN/proxy is unreachable: proxy server port is closed/refused`) làm dừng hàng loạt toàn bộ dàn máy ngay từ giây đầu preflight, dù proxy thật trên máy đang sống 100%.
   - **Quy tắc trích xuất proxy bắt buộc cho `_proxy_server_live`**:
     * Luôn truyền đối tượng `adb` (hoặc serial) vào hàm probe.
     * Ưu tiên đọc proxy thực tế đang active trên thiết bị qua lệnh: `adb.shell(["settings", "get", "global", "http_proxy"])`.
     * Chỉ fallback sang file mapping workbook (`PROXYgandienthoai.xlsx`) khi thiết bị không trả về proxy hợp lệ (hoặc trả về `null`, `:0`, `none`).
     * Sau khi lấy được chuỗi `host:port`, mới thực hiện `socket.connect_ex` với timeout <= 1.5s. Chi tiết trong `references/on-device-global-proxy-probe-precedence-20260906.md`.
16. **MobiProxy / 4G Dongle Web Dashboard WAN IP vs Proxy Listening Port Desync & Quy trình Khôi phục**:
   - Web dashboard của hệ thống quản lý 4G proxy (như MobiProxy trên `test.taadaa.click`) hiển thị danh sách modem (`proxy01`, `proxy02`, `proxy03`...) với trạng thái IPv4 nhà mạng (ví dụ `117.5.56.134`) chỉ chứng minh dongle/SIM đã kết nối mạng di động.
   - Có IP WAN KHÔNG ĐỒNG NGHĨA cổng proxy (`server_port`, ví dụ `5103`) đang mở. Tiến trình proxy service (3proxy/tinyproxy) của từng modem riêng biệt có thể bị crash, dừng hoặc lỗi gán port, dẫn đến `Connection Refused` trên cổng 5103 trong khi các cổng lân cận (5104, 5106) vẫn OPEN.
   - Khi upstream proxy đóng cổng, Sing-box container (cổng `20000+N`, ví dụ `20034`) sẽ ngắt kết nối (`Connection reset by peer / 10054`), khiến Android trên máy farm đánh dấu Wi-Fi có chấm than (`desc="Tín hiệu Wi-Fi đủ.,Không có Internet."`).
   - Quy tắc kiểm tra: Luôn kiểm tra cổng TCP (`socket.connect_ex`) và HTTP handshake (`curl -x`) tới đúng `server:server_port` upstream từ host, không kết luận 'proxy bình thường' chỉ dựa trên ảnh chụp giao diện quản trị web.
   - **Quy trình vận hành & Khôi phục trực tiếp trên MobiProxy Control (`test.taadaa.click`)**:
     * URL truy cập: `http://test.taadaa.click/login.php` (Mật khẩu: `n0spam@@`).
     * Vượt modal chào mừng: Click nút "Đồng ý" tại modal "Cam kết sử dụng".
     * Điều hướng: Chọn menu "⇄ Danh sách proxy" trên thanh bên trái.
     * Cấu trúc cổng: Bảng điều khiển gồm 32 modem proxy `proxy01` → `proxy32` (tương ứng cổng HTTP `5101` → `5132`).
     * Quy hoạch ghép cặp Sing-box: Cụm Sing-box `192.168.110.2:20001..20080` ánh xạ 2 máy / 1 proxy upstream (ví dụ Máy 08 và Máy 46 cùng trỏ về `test.taadaa.click:5108` - `proxy08`, user `mobi8` / pass `TaadaaMobi#2026!`).
     * Khôi phục khi proxy ngắt: Khi kiểm tra thấy trạng thái "Đã ngắt" / IPv4 trống (`IPv4: —`) / Sing-box trả `502 Bad Gateway` hoặc Connection Refused: gõ tìm kiếm `proxyXX`, bấm nút "Reset proxyXX". Hệ thống sẽ tái khởi động modem, tự động xin IP WAN IPv4/IPv6 mới và mở lại cổng proxy trong vòng vài giây mà không cần reboot box hay can thiệp vật lý.

17. **MobiProxy REST API Auto-Healing & Sing-box Upstream 502 Remediation**:
    - **Triệu chứng 502 trên Sing-box & Hiện tượng "Mất Wi-Fi" giả trên TikTok**:
      * Cổng Sing-box `192.168.110.2:200xx` vẫn mở và điện thoại farm vẫn ping thông router LAN, nhưng HTTP request bị trả về `502 Bad Gateway` hoặc socket reset. Nguyên nhân là do cổng upstream trên MobiProxy `test.taadaa.click:51xx` bị rớt kết nối nhà mạng hoặc service proxy của modem bị crash (`Connection Refused`).
      * **Triệu chứng trên UI app (TikTok)**: App hiện thông báo *"Không có kết nối. Tự động tải video về qua Wi-Fi để xem ngoại tuyến? [OK]"*. Người vận hành thường ngộ nhận là "máy mất Wi-Fi", nhưng kiểm tra `ip addr show wlan0` thì Wi-Fi vẫn UP và có IP LAN bình thường. Trong automation, lỗi này làm hỏng bước load profile/tài khoản, dẫn đến lỗi giả mạo: `[ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH`.
    - **Cạm bẫy False-Positive của `proxy_check` và `proxy_getlist` API**:
      * Cả `proxy_getlist` (`status: "true"`) và `proxy_check` (`{"result":"ok","content":"proxy_ok"}`) có thể báo OK dựa trên kết nối WAN của modem trong khi cổng TCP `51xx` thực tế đang bị `Connection Refused`.
      * BẮT BUỘC kiểm tra bằng TCP probe (`socket.connect_ex`) hoặc `curl -s -m 3 -x http://test.taadaa.click:<PORT> ...` từ host, hoặc probe qua Sing-box `curl -x http://192.168.110.2:200xx`.
    - **Khôi phục tự động qua REST API không cần UI**:
      * Endpoint danh sách 32 proxy: `GET http://test.taadaa.click/proxy_getlist?token=mpx_b0feb089e0a6b5224043d4c7bf6de34dc6a3a8ec552745aa`.
      * Cấu trúc 32 cổng thực tế: 4 nhóm LAN x 8 cổng (`5101..5108`, `5111..5118`, `5121..5128`, `5131..5138` - bỏ qua các số đuôi 09, 10). Auth tương ứng `mobi{port - 5100}:TaadaaMobi#2026!`.
      * Endpoint kiểm tra 1 port: `GET http://test.taadaa.click/proxy_check?proxy=test.taadaa.click:<PORT>&token=<TOKEN>`.
      * Endpoint kích hoạt modem quay số lại (Auto-Heal): `GET http://test.taadaa.click/proxy_recreat?proxy=test.taadaa.click:<PORT>&token=<TOKEN>` -> trả về `RECREAT_PROXY_DONE` (cổng proxy sẽ mở lại sau 2-3s mà không cần reboot box).
    - **Watchdog & Auto-Healer Script (Hermes Cronjob)**:
      * Script lõi: `D:\Taadaa\AI-Tools\scripts\mobiproxy_auto_healer.py` (`--check-and-heal`, `--daemon --interval 60`, `--stats`, `--json`) tự động quét 2 lớp (API + TCP socket) đa luồng < 1.5s, auto-recreate và lưu thống kê lịch sử die/heal vào `D:\Taadaa\AI-Tools\logs\mobiproxy_stats.json`.
      * Watchdog tự động: Chạy ngầm qua cronjob `mobiproxy-auto-healer-watchdog` (chu kỳ `*/1 * * * *`, `no_agent: true` qua script `C:\Users\Kibe\AppData\Local\hermes\scripts\cron_mobiproxy_healer.py`), tự động quét và hồi sinh trong 60s, không tốn tài nguyên agent.
    - **Bản chất Singbox Multiplexing & Lỗi 502 khi tải dồn**:
      * Cụm 80 máy farm chia sẻ 32 modem 4G (tỷ lệ 2–3 máy / 1 modem). Khi nhiều máy chạy batch upload video / lướt feed đồng thời, số lượng connection TCP tăng vọt làm service proxy (3proxy) trên modem bị crash/đóng cổng (`Connection Refused`).
      * Local socket Singbox `192.168.110.2:200xx` luôn OPEN trong mạng nội bộ, nên hệ điều hành Android không biết modem chết trước, app TikTok vẫn mở lên và chỉ báo "Không có kết nối" khi dữ liệu trả về mã 502 Bad Gateway.
      * Tự động hồi sinh: Lệnh `proxy_recreat` kích hoạt modem quay số lại, vừa change IP vừa khởi động lại dịch vụ proxy mở lại cổng trong 3–5s.
    - **Chẩn đoán hiện tượng 'Lúc chạy lỗi rớt mạng, kiểm tra lại thì không lỗi' (PPPoE & Modem Renegotiation)**:
      * Khi các máy chạy batch đêm (đặc biệt qua cổng MikroTik PPPoE `10005..10007` hoặc modem 4G) báo lỗi `Khong co ket noi Internet`: Kiểm tra log đối chiếu mốc thời gian. Các đợt PPPoE renegotiation / đổi IP WAN thường kéo dài 1-2 phút lúc rạng sáng, làm icon Wi-Fi hiện chấm than và khiến script fail-fast đúng lúc đó. Vài phút sau khi đường truyền tái lập, proxy thông suốt trở lại. Khi giải thích cho user, phải chỉ rõ mốc thời gian rớt mạng tạm thời từ log hiện trường, tránh kết luận hời hợt gây hoang mang.
    - **Quy tắc giao tiếp với User**: Khi user hỏi "Là phải change IP trên port X à" hoặc "Cái mày làm là change IP", thừa nhận và xác nhận trực tiếp, ngắn gọn (bản chất `proxy_recreat` là reset modem để change IP và mở lại port), tuyệt đối tránh giải thích rườm rà chẻ chữ gây khó chịu cho user.

   - **Phân biệt MobiProxy Web UI / Nginx 502 vs Proxy Service Ports**:
     * Box MobiProxy đặt tại mạng ngoài (nhà đối tác/người quen, không nằm trong farm LAN). Khi domain `test.taadaa.click` trả `502 Bad Gateway` trên web/API, KHÔNG ĐƯỢC chỉ nhìn vào web để kết luận proxy chết.
     * Cần phân biệt 2 kịch bản probe:
       (a) **Qua Sing-box nội bộ (`192.168.110.2:200xx`)**: Nếu Sing-box có route nội bộ tới modem hoặc proxy vẫn thông, probe qua Sing-box sẽ phản ánh việc farm có ra được internet hay không.
       (b) **Trực tiếp từ Host tới cổng MobiProxy (`test.taadaa.click:5101..5138`)**: Luôn probe trực tiếp tầng TCP socket (`socket.connect_ex`) và HTTP egress có auth (`mobiX:TaadaaMobi#2026!`) trên từng cổng 51xx, TUYỆT ĐỐI KHÔNG dùng web dashboard/API làm đại diện cho các cổng proxy khi người dùng yêu cầu kiểm tra cổng proxy hoạt động.
   - **ADB Path trên máy Farm Kibe**: Khi PATH thiếu ADB, binary ADB sẵn có nằm tại `C:/Users/Kibe/.GemPhoneFarm/app/adb-tool/adb.exe`. Không dùng `find /` quét toàn bộ ổ C gây timeout terminal.
   - **Package Name TikTok Farm**: Gói ứng dụng TikTok trên dàn máy S7 là `com.ss.android.ugc.trill` (không phải `com.zhiliaoapp.musically`). Khi khởi động hoặc kiểm tra focus, dùng `com.ss.android.ugc.trill`.

## Reference

See `references/atx-curl-direct-fallback-trap.md` for atx-agent curl direct fallback trap on global proxy devices and fail-closed egress requirements.
See `references/mobiproxy-rest-api-auto-healing-and-consumer-preflight.md` for MobiProxy REST API specifications, auto-healing automation, and Sing-box upstream pairing architecture.
See `references/on-device-global-proxy-probe-precedence-20260906.md` for on-device global HTTP proxy probe precedence and workbook desync prevention.
See `references/dhcp-dual-server-race-and-mikrotik-vlan10-remediation.md` for DHCP dual-server race condition resolution and MikroTik REST API disable steps.
See `references/router-transparent-proxy-architecture.md` for router transparent proxy specs, ping substring safety, and route precedence.
See `references/proxy-preflight-incident-pattern.md` for the condensed evidence matrix and reporting template.
See `references/batch-process-vs-device-fail-closed-explanation.md` for explaining host batch processes vs device fail-closed behavior.
See `references/mikrotik-api-and-port-probe-architecture.md` for MikroTik REST API management and per-port socket probe architecture.
See `references/mikrotik-web-management-tool-architecture.md` for the `mikrotik-tool.pages.dev` web management tool (Cloudflare Pages → Worker → Router API), HTTP 522 diagnostic workflow, DNS staleness failure after "Change IP", and `mikrotik_manager.py` CLI quick reference.
See `references/samsung-s7-android8-dhcp-vlan-mismatch-and-rogue-ssid-20260906.md` for Samsung S7 Android 8.0 DHCP VLAN mismatch (192.168.10.x vs 192.168.110.x), cmd wifi limitation, rogue SSID scan interference, and recovery workflow.
See `references/samsung-s7-rtc-clock-loss-and-wifi-zone-recovery-20260903.md` for Samsung S7 RTC clock loss, Wi-Fi zone allocation, and media reservation recovery.
See `references/m13-dhcp-subnet-fragmentation-and-rogue-ssid-investigation-20260906.md` for DHCP subnet fragmentation (192.168.10.x vs 192.168.110.x), toybox nc syntax on Android, and rogue SSID isolation.
See `references/m51-ping-probe-preflight-icmp-drop-and-proxy-egress-20260906.md` for Machine 51 ping probe failure, MikroTik VLAN 10 ICMP drop, proxy host ping target, and egress IP validation precedence over ICMP.
See `references/singbox-port-mapping-and-proxy-recreat-422-pitfall.md` for Sing-box (200xx) vs upstream MobiProxy (51xx) port mapping, the 422 API error, machine→port resolution, and heal retry patterns.
See `references/dual-cluster-wifi-auto-healer-and-preflight-toggle.md` for dual-cluster parity in Wi-Fi auto-healing and preflight radio toggle architecture.
See `references/wifi-toggle-recovery-and-following-tab-false-network-20260924.md` for Wi-Fi toggle recovery, dual-cluster parity in auto-healer, and TikTok following tab false network error diagnosis.
See `references/omniroute-upstream-error-vs-proxy-error.md` for OmniRoute upstream error (403/429) vs proxy error diagnosis, Antigravity IP-based blocking pattern, DNS spelling pitfall, and error modal field reference.
See `references/android-system-server-crash-wifi-recovery.md` for Android system_server crash diagnosis, two-tier Wi-Fi recovery, and guarded reboot implementation.
See `scripts/scan_singbox_farm_proxies.py` for concurrent proxy cluster scanner (ports 20001..20080 on 192.168.110.2).

18. **Phân biệt Lỗi Upstream Provider vs Lỗi Proxy (OmniRoute `ERROR` Log Triage)**:
   - **Nguyên tắc vàng**: OmniRoute proxy log ghi `STATUS: ERROR` KHÔNG có nghĩa proxy/MikroTik bị hỏng. Cột `PROXY` chỉ ghi tên host:port mà request đi qua — mã lỗi thật sự đến từ **upstream provider** (Google Antigravity, OpenRouter, v.v.), không phải từ proxy trung gian.
   - **Quy trình chẩn đoán bắt buộc**:
     1. **Click vào dòng ERROR** trong OmniRoute dashboard → đọc modal chi tiết → ghi nhận **mã lỗi trong ô LỖI** (ví dụ `[403]: Antigravity upstream error (403)`, `[429]: Antigravity upstream error (429)`).
     2. **Xác định Cấp độ (Mức)**:
        - `DIRECT` = request đi thẳng từ OmniRoute qua proxy tới upstream URL → lỗi 403/429 là do **upstream provider từ chối** (hết quota, IP bị flag, abuse detection).
        - `PROVIDER` = request đi qua provider relay của OmniRoute → lỗi có thể do provider relay hoặc combo failover.
     3. **Xác định Model đích**: Lỗi 403/429 trên `antigravity/claude-sonnet-4-6` là do tài khoản Antigravity hết quota hoặc bị Google block IP. Lỗi trên `gemini-3.8-flash-tiered` thì tương tự.
     4. **So sánh giữa các cổng**: Nếu cổng X luôn SUCCESS còn cổng Y luôn ERROR → nguyên nhân là **IP public exit khác nhau** qua PPPoE, không phải cổng proxy hỏng.
   - **Các mã lỗi thường gặp**:
     - `403 Forbidden` = Tài khoản Antigravity/OAuth token hết hạn, bị Google revoke, hoặc IP exit bị flag abuse → cần refresh token hoặc đổi IP PPPoE.
     - `429 Too Many Requests` = Rate limit từ upstream → OmniRoute retry/failover sẽ tự xử lý, không cần can thiệp thủ công.
     - `502 Bad Gateway` = Upstream service down hoặc proxy socket crash → cần check TCP probe trực tiếp.
     - `Connection Refused / Timeout` = Proxy socket chết → đây mới là lỗi proxy thật, cần heal/recreate.
19. **MikroTik PPPoE Public DNS vs Internal LAN Probe & Firewall DROP_EXTERNAL Pitfall**:
    - **Hiện tượng**: Kiểm tra các cổng proxy MikroTik (`10001..10007`) qua tên miền DDNS/Public IP (vd `mirotik1.taadaa.click:1000x` trỏ về IP WAN `171.231.195.2`) bị báo `CLOSED / Connection Refused / 10035` dù PPPoE đã có IP và đang chạy bình thường.
    - **Nguyên nhân cốt lõi**:
      1. **Firewall DROP_EXTERNAL**: RouterOS có rule `chain=forward dst-port=10001-10035 action=drop comment=DROP_EXTERNAL_PROXY_PORTS` và chỉ mở `accept` cho danh sách `FPT_LAN` (`192.168.110.0/24`, `192.168.10.0/24`). Mọi request đi từ host/bên ngoài vòng qua IP public WAN đều bị firewall DROP thẳng tay.
      2. **Địa chỉ probe đúng**: BẮT BUỘC probe trực tiếp qua IP LAN `192.168.110.2:10001..10007` thay vì qua domain/public IP `mirotik1.taadaa.click` để tránh bị firewall drop giả mạo.
    - **Quy tắc kiểm tra phân tầng**: Khi chẩn đoán sự cố MikroTik báo có IP nhưng không kết nối được:
      - BƯỚC 1: Probe HTTP egress trực tiếp từ LAN `http://admin@1:admin@1@192.168.110.2:1000x` -> nếu PASS thì core proxy và PPPoE hoàn toàn khỏe mạnh.
      - BƯỚC 2: Kiểm tra tầng Sing-box trung gian (`192.168.110.2:200xx`). Nếu LAN trực tiếp PASS nhưng Sing-box trả timeout -> lỗi nằm ở container Sing-box bị nghẽn sau khi router khởi động lại, không phải lỗi PPPoE/MikroTik.

20. **Kiểm tra Proxy Port Trực Tiếp vs Web Management Tool**:
    - Khi user yêu cầu kiểm tra proxy có dùng được không: **BẮT BUỘC kiểm tra tầng TCP socket và HTTP egress trực tiếp trên port proxy** (`socket.connect_ex` + `urllib/curl` có auth qua proxy).
    - **TUYỆT ĐỐI KHÔNG** chỉ kiểm tra web quản trị (như `login.php` hay dashboard port 80/443/8090) rồi kết luận proxy hỏng khi web lỗi (ví dụ web trả 502 do nginx/PHP-FPM sập nhưng 3proxy trên modem/router có thể vẫn hoạt động, hoặc ngược lại). Proxy liveness CHỈ được xác nhận bởi HTTP proxy handshake thực tế.

21. **Triage Lỗi 'MikroTik Có IP Mà Không Chạy' (Internal vs External Loopback Trap)**:
    - **Triệu chứng**: `mirotik1.taadaa.click:10001..10007` probe từ máy farm/host báo `CLOSED (10035)` / Timeout dù router có uptime và các interface PPPoE đều `running=true` và có public IP.
    - **Bản chất**: Firewall MikroTik cấu hình rule `DROP_EXTERNAL_PROXY_PORTS` (`chain=forward dst-port=10001-10035 action=drop comment=DROP_EXTERNAL_PROXY_PORTS`). Khi request đi tới domain public `mirotik1.taadaa.click`, router nhận gói từ interface WAN hoặc không match address-list `FPT_LAN` và DROP ngay lập tức.
    - **Xác minh O(1)**: BẮT BUỘC probe trực tiếp IP LAN nội bộ `http://admin@1:admin@1@192.168.110.2:10001..10007` qua Python `urllib.request`. Nếu probe LAN thành công ra IP public $\rightarrow$ 3proxy và PPPoE sống 100%, lỗi thuần túy do firewall chặn external/loopback domain.
    - **Khắc phục cho thiết bị**: Gán proxy trực tiếp qua IP LAN `192.168.110.2:100xx` thay vì dùng domain ngoài hoặc thông qua container Sing-box trung gian khi Sing-box bị nghẽn upstream.

22. **Cảnh báo User Khi Kiểm Tra MobiProxy (Tránh Kiểm Tra Web Dashboard / Domain)**:
    - Box MobiProxy đặt tại mạng ngoài (nhà người quen/đối tác), KHÔNG cùng mạng hay phụ thuộc vào nhà user (mất điện nhà user không làm mất điện box MobiProxy).
    - Khi kiểm tra tình trạng cổng MobiProxy, TUYỆT ĐỐI KHÔNG chỉ probe web `http://test.taadaa.click/login.php` hay API web (thường trả 502 do PHP-FPM / bot scan). BẮT BUỘC probe trực tiếp TCP socket & HTTP egress có auth (`mobiX:TaadaaMobi#2026!`) thẳng vào cổng `5101..5138` của IP host.

23. **Android `system_server` Crash Ngầm Gây Báo Giả 'Wi-Fi not connected' (Triage Service Liveness O(1))**:
    - **Hiện tượng**: Farm Alert báo `blocked-proxy-vpn` kèm lý do `required router proxy is unreachable ... dumpsys connectivity: Wi-Fi not connected` hoặc `wlan0: state DOWN`.
    - **Cạm bẫy quy kết nhầm**: Người vận hành hoặc agent thường suy diễn là Router Wi-Fi sập sóng hoặc Proxy port bị hỏng. Nhưng khi probe proxy trực tiếp từ host (`curl -x http://<proxy> ...`) thì proxy vẫn SỐNG 100%.
    - **Chẩn đoán O(1) qua ADB**:
      * Kiểm tra dịch vụ hệ thống: `adb -s <serial> shell "dumpsys wifi | head -n 3"` và `adb -s <serial> shell "dumpsys window | head -n 3"`.
      * Nếu trả về: `Can't find service: wifi` hoặc `Can't find service: window`: Đây là bằng chứng xác thực tiến trình lõi Android Framework `system_server` đã bị crash ngầm.
      * Kernel Linux và daemon `adbd` (qua USB) vẫn phản hồi, nhưng toàn bộ subsystem quản lý Wi-Fi, Window, ActivityManager đã chết cứng, kéo theo giao diện `wlan0` bị ngắt.
    - **Xử lý dứt điểm & Tự động hóa trong Runner (2026-09-23)**:
      * Lệnh `svc wifi enable` hoàn toàn vô hiệu khi service wifi không tồn tại (sẽ báo lỗi hoặc exit code 135/139).
      * BẮT BUỘC reboot thiết bị: `adb -s <serial> reboot`. Sau khi boot lại, Android Framework tái khởi động sạch và máy sẽ tự động bắt lại Wi-Fi và thông proxy bình thường.
      * **Đã tự động hóa vào `python_runner/core/vpn_preflight.py` (`require_proxy_connected`)**: Khi preflight phát hiện Wi-Fi down và `svc wifi enable` trả về dead service (`Can't find service` hoặc exit code 135/139), script tự động phát lệnh `reboot`, đợi `sys.boot_completed == 1` (timeout 90s), và re-check Wi-Fi với cờ loop guard `_wifi_reboot_attempted` (tối đa 1 lần/máy) để tự giải cứu mà không cần can thiệp thủ công. Chi tiết: `references/android-system-server-crash-wifi-recovery.md`.

24. **Cơ Chế Khôi Phục Wi-Fi Khi Rớt Sóng / Treo DHCP (Toggle Radio vs Enable Đơn Thuần & Quét Dual-Cluster)**:
    - **Cạm bẫy `svc wifi enable` đơn thuần trong Preflight**:
      * Khi thiết bị Android (đặc biệt Samsung S7 Android 7/8) bị rớt sóng AP, nghẽn AP tạm thời hoặc kẹt DHCP, công tắc Wi-Fi trong Cài đặt hệ thống thực tế vẫn đang ở trạng thái ON.
      * Lệnh `svc wifi enable` đơn thuần không kích hoạt lại quá trình kết nối hay xin cấp lại DHCP lease, dẫn đến probe vòng 2 tiếp tục văng `dumpsys connectivity: Wi-Fi not connected` và kích hoạt kill-switch đóng cổng (`blocked-proxy-vpn`).
      * **Quy tắc sửa đổi**: Phải thực hiện chu kỳ toggle trọn vẹn: `svc wifi disable && sleep 1 && svc wifi enable` (chờ 3-4s cho card mạng quét và nhận IP) trước khi probe lại.
    - **Phạm vi Watchdog Tự Khôi Phục Wi-Fi (`farm_wifi_auto_healer.py`) Bắt Buộc Đủ 2 Cụm & Quét Song Song (Dual-Cluster Parity & ThreadPoolExecutor)**:
      * Watchdog tự phục hồi Wi-Fi nền (cronjob `farm-wifi-auto-healer`) nếu chỉ quét `adb devices` cục bộ sẽ bỏ sót toàn bộ 80 máy Farm Admin (`192.168.110.119:5037`).
      * BẮT BUỘC watchdog phải quét cả 2 cluster: Kibe Local và Admin Remote (`-H 192.168.110.119 -P 5037` kết hợp file `admin/PROXYgandienthoai.xlsx`), tự động toggle radio khi phát hiện mất IP `192.168.110.x` để tránh máy Admin bị kill-switch ngắt phiên.
      * BẮT BUỘC dùng `ThreadPoolExecutor(max_workers=20)` chạy song song 160 máy để hoàn tất toàn farm trong ~6.3s, tuyệt đối tránh quét tuần tự gây nghẽn timeout 500-600s.
    - **Phân biệt Rớt Wi-Fi Thật vs Báo Giả Rớt Mạng Trên Tab Following của TikTok**:
      * Khi kịch bản nuôi chuyển sang tab "Đã follow" (Following) trên nick chưa follow ai (hoặc danh sách following rỗng), TikTok hiển thị màn hình: *"Đã xảy ra lỗi. Vui lòng thử lại."* kèm nút *"Thử lại"*.
      * Bộ phân loại `classify_screen` bắt trúng từ khóa lỗi/thử lại nên ngộ nhận là rớt mạng (`manual-needed:network`), ngắt phiên sớm dạng `manual-needed:network` dù Wi-Fi trên máy vẫn căng 3 vạch và proxy hoàn toàn bình thường.
      * Khi chẩn đoán alert rớt mạng nuôi feed, bắt buộc kiểm tra step dừng: nếu là `switch_following` thì đây là giao diện rỗng của TikTok, không phải rớt mạng vật lý hay proxy chết.

25. **Kiến Trúc Mạng Farm Admin & Chẩn Đoán Báo Mất Mạng Ảo (Windows NCSI vs Wi-Fi Độc Lập)**:
    - **Độc lập giữa PC Host và Dàn Điện Thoại**:
      * Cáp USB nối từ dàn máy điện thoại (ví dụ 201–280 trên PC Admin) vào PC CHỈ phục vụ điều khiển ADB và truyền hình ảnh màn hình lên app screen-mirroring (Jiwei / Xiaowei). Hệ thống KHÔNG sử dụng USB reverse tethering.
      * Toàn bộ thiết bị Android kết nối Internet độc lập qua Wi-Fi riêng (SSID `admin 2`, 5GHz, dải `192.168.110.x`). Do đó, kể cả khi PC Admin mất kết nối Internet, dàn điện thoại vẫn cào feed, upload, render hoặc xem video bình thường nếu Wi-Fi/Proxy vẫn thông.
      * Khi màn hình Jiwei hiện ô xám/đen báo *"Phone disconnected, please check"* (như máy 229, 255, 273): Đây là lỗi lỏng cáp USB hoặc nghẽn cổng Hub USB làm rớt kết nối ADB giữa PC và điện thoại, TUYỆT ĐỐI KHÔNG suy diễn thành lỗi mất mạng Internet.
    - **Windows NCSI False Alarm (Icon Quả Địa Cầu / No Internet Trên Taskbar)**:
      * Trên máy PC cắm nhiều card mạng (ví dụ Ethernet LAN `192.168.110.119` + Ethernet phụ `192.168.5.127` + adapter ảo Tailscale `100.120.x.x`), cơ chế Network Connectivity Status Indicator (NCSI) của Windows kiểm tra toàn bộ adapter. Nếu adapter phụ/ảo báo `NoTraffic`, Windows sẽ hiển thị icon Taskbar thành Quả địa cầu ("No Internet Access") dù card Ethernet chính vẫn ra Internet hoàn toàn bình thường.
      * Luôn kiểm tra thực tế bằng `Test-NetConnection google.com -Port 443` hoặc `Test-NetConnection 8.8.8.8 -Port 53`, không kết luận PC mất mạng chỉ qua icon Taskbar.
    - **ADB Path Trên Farm Admin (`192.168.110.119`)**:
      * Binary ADB trên PC Admin không nằm trong PATH mặc định, mà nằm tại `"C:\Program Files (x86)\xiaowei\tools\adb.exe"`. Khi SSH từ xa từ controller Kibe, bắt buộc gọi trực tiếp đường dẫn này hoặc trỏ adb client qua daemon port `5037`.

26. **🚨 BẪY CHÍ MẠNG: THIẾT BỊ MAPPED NHƯNG CHƯA GÁN PROXY TRÊN MÁY & DIRECT IP LEAK FALLBACK (2026-10-08)**:
    - **Hiện tượng sự cố:** Proxy cụm Admin (`mirotik1.taadaa.click:10001..10035` / `192.168.110.2:10008..10035`) sập hoàn toàn / timed out 100%. Tuy nhiên, script automation (`tiktok_workflow`) trên các máy Samsung S7 Admin (201–280) vẫn mở app và chạy bình thường.
    - **Nguyên nhân kép:**
      1. Trên máy S7 Admin, `settings get global http_proxy` trả về `:0` (hoặc rỗng) do chưa được chạy script gán proxy ADB (`set_proxy_farm_admin_adb.py`).
      2. Trong `automation_core.preflight.check_android_vpn`, khi `global_proxy` là `None`, code rơi vào nhánh `else` gọi `_probe_atx_curl_public_ip` trực tiếp không truyền proxy. Do Wi-Fi AP (`admin 2`) thông ra WAN FPT thông thường, probe bắt được IP WAN FPT (`1.53.55.190`), ngộ nhận là IP egress hợp lệ và cho pass preflight (`is_safe=True`). Toàn bộ dàn máy Admin bị lộ IP gốc và dính chung IP FPT.
    - **Quy tắc bất biến:** Khi thiết bị đã được map trong `PROXYgandienthoai.xlsx` (`required=True`), nếu trên máy `global_proxy` trả về `:0` hoặc probe IP trùng với IP mạng nhà FPT (`1.53.55.190`), BẮT BUỘC fail-closed ngay lập tức (`DIRECT_IP_LEAK_BLOCKED`), CẤM TUYỆT ĐỐI fallback sang direct probe. Chi tiết: `references/admin-s7-unassigned-proxy-direct-leak-incident-20261008.md`.

## Reference

See `references/singbox-dns-failure-on-mikrotik-pppoe-outage-20261009.md` for Singbox proxy stalling on MikroTik PPPoE outage, DNS context deadline exceeded, and two-tier triage between upstream MobiProxy and local wrapper (2026-10-09).
See `references/fpt-dual-path-lan-alive-vs-mikrotik-pppoe-down-20261009.md` for FPT dual-path architecture (LAN alive vs MikroTik PPPoE RX-zero outage), bridge port misplugging, and Singbox container routing failure (2026-10-09).
See `references/admin-unassigned-proxy-direct-leak-incident-20261008.md` for the Admin S7 unassigned proxy and direct IP leak incident postmortem, root causes, and 3-tier emergency kill procedure (2026-10-08).
See `references/ap-transient-disconnect-vs-batch-preflight-window-20261008.md` for the AP transient disconnect vs batch preflight timing collision pattern (2026-10-08).
See `references/adb-disconnect-false-proxy-missing-and-rogue-ssid-roam-20261009.md` for ADB transport disconnect false-positive proxy missing and rogue SSID roaming investigation (2026-10-09).
See `references/adb-disconnect-vs-missing-proxy-preflight-triage-20261009.md` for fail-fast invariant, AdbResult attribute safety, and fast adb kill-server recovery workflow (2026-10-09).
See `references/adb-disconnect-vs-missing-proxy-preflight-20261009.md` for distinguishing ADB transport disconnect/timeout from missing device proxy (:0) and space-containing SSID escaping in adb-join-wifi (2026-10-09).

27. **AP Wi-Fi Transient Disconnect vs Batch Preflight Concurrency Window (Kill-Switch False Alarm)**:
    - **Hiện tượng**: Hàng loạt 70–80 máy farm đồng loạt bị ngắt phiên ngay tại tiền kiểm (`final_status: blocked-proxy-vpn`, lý do: `dumpsys connectivity: Wi-Fi not connected`), `total_swipes_completed: 0`.
    - **Bản chất**: Khi Access Point (AP Ruijie / Mikrotik) bị chớp sóng, reload cấu hình hoặc reboot chớp nhoáng kéo dài chỉ 3–5 giây. Nếu tiến trình batch runner (như `multi-machine-feed-session`) khởi chạy và thực hiện kiểm tra `vpn_preflight.py` đúng vào khoảng trống vài giây đó, kiểm tra `wlan0` / `dumpsys connectivity` thấy chưa kết nối sẽ kích hoạt ngay cơ chế Kill-Switch an toàn (`blocked-proxy-vpn`) để chống Direct IP Leak.
    - **Đối soát hiện trường O(1)**:
      * Kiểm tra lịch sử kết nối: `adb -s <serial> shell "dumpsys wifi | grep -E 'SUPPLICANT_STATE_CHANGE_EVENT' | tail -n 10"`.
      * Nếu thấy chuỗi: `state: DISCONNECTED` (ví dụ 14:03:00) $\rightarrow$ `state: ASSOCIATING` $\rightarrow$ `state: COMPLETED` (ví dụ 14:03:06): Thiết bị thực tế chỉ mất sóng trong vài giây và đã tái kết nối thành công ngay sau đó.
      * Không vội vã can thiệp vật lý AP hoặc xóa Wi-Fi khi log đối soát cho thấy máy đã kết nối lại bình thường ở ca kế tiếp.
    - **Quy trình phục hồi máy bị thiếu proxy sau reboot**:
      * Kibe Local: Chạy `python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_adb.py [--machines N]` (gán Sing-box `192.168.110.2:20001..20080`).
      * Admin Farm: Chạy qua SSH `ssh admin-farm "powershell -Command \"python -u D:/Taadaa/AI-Tools/scripts/set_proxy_farm_admin_adb.py\""` (gán MikroTik `192.168.110.2:10008..10035`).

28. **ADB Transport Disconnect False-Positive 'Proxy Missing or :0' & Rogue SSID Roam Storm (2026-10-09)**:
    - **Cạm bẫy 'Proxy missing or :0' khi rớt USB/ADB**: Khi `adb shell settings get global http_proxy` chạy trên máy bị offline / rớt cáp USB (`device not found` / `offline`), `adb.shell` trả về stdout rỗng. Code preflight nếu chỉ check `if not p_val or p_val == ':0'` sẽ ngộ nhận thành "máy chưa cài proxy", làm sai lệch chẩn đoán từ lỗi cáp USB sang lỗi mạng/cấu hình. Bắt buộc kiểm tra `p_out.ok` và `is_connection_lost(stderr)` trước khi parse giá trị proxy.
    - **Bão Roam SSID Rác gây 'Wi-Fi not connected' tạm thời (10-15s)**: Khi AP chính (`kibe 1`) chớp sóng ngắn, máy lưu SSID rác (như `VIETTEL_9rXX3G`) sẽ cố roam sang và dính `AUTHENTICATION_FAILURE_WRONG_PSWD`. Android mất 10–15s ở state `DISCONNECTED` trước khi quay lại AP chính. Batch preflight quét trúng cửa sổ này sẽ kích hoạt fail-closed `Wi-Fi not connected`. Cần kiểm tra `dumpsys wifi` bắt `AUTHENTICATION_FAILURE_EVENT` để quên mạng rác trên máy.
    - Chi tiết xem `references/adb-disconnect-false-proxy-missing-and-rogue-ssid-roam-20261009.md`.

29. **Chẩn đoán Cổng WAN Link-OK Nhưng RX-Zero & PPPoE LCP Lowerdown (2026-10-09)**:
    - **Bẫy "Vẫn cắm bình thường mà"**: Đèn cổng WAN MikroTik vẫn sáng xanh (`status: link-ok, rate: 1Gbps`) chỉ chứng minh tầng vật lý PHY giữa 2 card mạng có điện. Hoàn toàn không chứng minh thiết bị đầu bên kia (modem/converter FPT) đang truyền dữ liệu ở tầng Layer 2 / quang.
    - **Telemetry phân định O(1) bằng Bắt Gói & Delta Lưu Lượng**:
      1. Đo biến thiên lưu lượng 2 giây: TX delta > 0 (MikroTik bắn gói PADI tìm server) nhưng RX delta = 0 bytes (không có byte nào phản hồi).
      2. Chạy `/tool/sniffer` bắt gói 3 giây: 100% gói tin là `direction: tx`, 0% `direction: rx`.
      3. RouterOS log báo liên tục: `LCP lowerdown` / `LCP down event in starting state`.
    - **Nguyên nhân cốt lõi**: Cục modem/converter FPT bị mất tín hiệu quang (đèn LOS đỏ / PON nháy) hoặc chip switch của modem bị treo cứng (Hardware Freeze) nên không đẩy frame qua cổng LAN; hoặc cáp mạng đứt ngầm 1 chiều.
    - **Khắc phục**: Yêu cầu Operator kiểm tra đèn LOS/PON trên cục FPT, rút nguồn modem FPT 10s cắm lại (reboot cứng) và cắm chặt lại cáp LAN giữa 2 thiết bị. Chi tiết xem `references/ethernet-link-ok-but-rx-zero-pppoe-lcp-lowerdown-20261009.md`.

30. **Phân biệt Mạng LAN FPT Gia Đình Sống vs Tuyến Viettel PPPoE MikroTik Bị Ngắt (Farm Topology & RX-Zero Trap 2026-10-09)**:
    - **Bối cảnh & Phản xạ Operator**: Khi Coordinator báo mạng PPPoE mất tín hiệu làm preflight chặn upload, Operator phản xạ: *"ủa mạng LAN đang xài cục FPT đó bth mà? ở mikrotik wan1 cắm vào line mạng viettel xoay pppoe, wan 2 trống, wan 3 cắm vào switch rujie của fpt"*.
    - **Sơ đồ đấu nối thực tế trên MikroTik x86 Mini PC (`192.168.110.2`)**:
      1. **Cổng WAN 1 (`ether1`)**: Cắm vào modem/converter **VIETTEL** (tài khoản FTTH `d511_gftth_khoind5`). Tuyến này dùng để quay 60 phiên PPPoE (`pppoe-out1..60` qua `macvlan1..60`) phục vụ proxy xoay `10001..10035` và cung cấp default route cho router. CẤM TUYỆT ĐỐI nhầm sang modem FPT!
      2. **Cổng WAN 2 (`ether2`)**: TRỐNG (không cắm dây).
      3. **Cổng WAN 3 (`ether3`)**: Cắm vào switch **Ruijie của FPT** (`192.168.110.1`, IP WAN `1.55.80.51`). Tuyến này cấp mạng LAN nội bộ, Wi-Fi và mạng gia đình cho PC Kibe (hoàn toàn độc lập với line Viettel).
    - **Hiện tượng khi Viettel gặp sự cố**: Mạng nhà FPT (Kibe PC, Telegram) vẫn chạy bình thường, nhưng toàn bộ 34 line PPPoE trên web manager `kibe:2310` báo DOWN (`0/34 running`), cổng WAN1 nhận RX = 0 bytes, `LCP lowerdown`.
    - Chi tiết xem `references/ethernet-link-ok-but-rx-zero-pppoe-lcp-lowerdown-20261009.md` và `references/viettel-pppoe-outage-singbox-default-route-loss-20261009.md`.

31. **Bẫy Đứt Egress Cụm Sing-box (MobiProxy 4G) Khi Line PPPoE Rớt Mạng (2026-10-09)**:
    - **Nghịch lý Operator thắc mắc**: *"cục viettel lỗi thì mất proxy mikrotik thôi, còn dây từ switch rujie cắm vào mini pc làm single box liên quan éo gì?"* (Các cổng Sing-box `20001..20080` thực chất trỏ ra server 4G MobiProxy ngoài `test.taadaa.click:51xx`, tại sao lại chết theo Viettel?).
    - **Bản chất kiến trúc routing RouterOS**:
      1. Container `sing-box` chạy bên trong MikroTik Mini PC (IP `172.17.0.2`, gateway `172.17.0.1`).
      2. Dây Ruijie FPT cắm vào `ether3` chỉ là kết nối LAN (`192.168.110.2/24`), **hoàn toàn KHÔNG có default route `0.0.0.0/0 gateway=192.168.110.1`** trong bảng định tuyến `main`.
      3. Tuyến Default Route `0.0.0.0/0` duy nhất của bảng `main` được cấp động bởi interface `pppoe-out1` (trên line Viettel với cờ `add-default-route=true`).
      4. Khi Viettel đứt quang/treo converter $\rightarrow$ `pppoe-out1` ngắt kết nối $\rightarrow$ RouterOS tự động **xóa sạch Default Route `0.0.0.0/0`** khỏi bảng `main`.
      5. Mini PC và Docker container Sing-box bị cô lập không còn đường ra Internet để forward traffic tới MobiProxy `test.taadaa.click:5118`.
      6. Cổng Sing-box `192.168.110.2:20016` vẫn mở cổng TCP nội bộ, nhưng mọi HTTP proxy request đều bị RouterOS drop do không có route ra ngoài $\rightarrow$ văng `context deadline exceeded` (Timeout) $\rightarrow$ Runner fail-closed an toàn tại preflight.
    - Chi tiết xem `references/viettel-pppoe-outage-singbox-default-route-loss-20261009.md`.

32. **Hiện Tượng 'Active default network: none' Sau Khi Wi-Fi Reconnect (Network Unreachable Trap 2026-10-09)**:
    - **Hiện tượng**: Thiết bị Android (Samsung S7) vừa tái kết nối Wi-Fi, lệnh `ip addr show wlan0` đã có IP hợp lệ (`inet 192.168.110.x/24`), `ping <gateway>` PASS (0% loss), nhưng lệnh `atx-agent curl` hoặc `toybox nc` sang proxy cổng LAN `192.168.110.2:200xx` văng ngay: `connect: network is unreachable`.
    - **Bản chất Android Policy Routing**:
      1. `ip addr` phản ánh tầng Linux network interface đã nhận IP từ DHCP server.
      2. Nhưng subsystem `ConnectivityService` của Android Framework cần 3–8 giây để hoàn tất captive portal probe và transition network agent.
      3. Trong cửa sổ này, `dumpsys connectivity` ghi nhận: `Active default network: none`.
      4. Bảng `ip rule` của Android đẩy toàn bộ luồng mạng chưa gán fwmark tới table 1014 (default network). Khi default network là `none`, routing rule rơi xuống dòng cuối cùng: `32000: from all unreachable`. Mọi socket TCP mới mở ra từ shell CLI / daemon chưa gán uid mark bị nhân Linux chặn đứng với lỗi `ENETUNREACH (Network is unreachable)`.
    - **Quy tắc chẩn đoán & Chờ ổn định**:
      * Kiểm tra `adb shell "dumpsys connectivity | grep 'Active default network'"`: Nếu trả về `none` hoặc ID đang chuyển tiếp, chỉ cần chờ 5–10 giây cho `Active default network` gán ID hợp lệ (ví dụ `network{1131}`).
      * Tuyệt đối không vội vã kết luận mạng LAN bị đứt hay reboot router khi gặp `connect: network is unreachable` ngay sau khi toggle Wi-Fi.
    - Chi tiết xem `references/android-active-default-network-none-policy-routing-trap-20261009.md`.

33. **Dual-Cluster Batch Alert Triage: [DEVICE_OFFLINE] ADB Timeout & PPPoE Port Closed (2026-10-10)**:
    - **Hiện tượng**: Farm Alert diện rộng trên cụm Admin (M201–M280) xuất hiện đồng thời 2 cụm lỗi vượt ngưỡng kép: (1) `[DEVICE_OFFLINE] adb command timed out` (10 máy) và (2) `proxy server port is closed/refused` (17 máy).
    - **Bản chất kép & Xung đột cửa sổ bảo trì**:
      1. **Scheduled PC Reboot Window (04:45)**: Cronjob `farm-scheduled-pc-reboot` khởi động lại PC lúc 04:45 sáng (Thứ 2, 4, 7). Batch chạy đúng lúc USB host và router vừa lên lại.
      2. **ADB Transport Daemon Saturation**: Host Admin (`192.168.110.119`) cắm 80 máy qua hub USB. Khi batch chạy đồng loạt 80 tiến trình shell (`ip addr`, `dumpsys`), daemon ADB (`C:\Program Files (x86)\xiaowei\tools\adb.exe`) bị bão hòa buffer socket transport. Tham số timeout probe trong `vpn_preflight.py` bị thắt ở 6s gây timeout lệnh và bị hook bắt thành `[DEVICE_OFFLINE]`. Thiết bị vật lý vẫn cắm, sạc pin bình thường, không rớt USB.
      3. **PPPoE Renegotiation Fast Fail-Closed**: Các cổng MikroTik PPPoE xoay IP định kỳ lúc rạng sáng (1–2 phút), hàm `_proxy_server_live` fast probe TCP `connect_ex` thấy port từ chối lập tức fail-closed <=1.5s để bảo vệ nick không bị lướt bằng Direct IP FPT.
    - **Vá mã nguồn & Kỷ luật điều phối ("K fix đc lỗi à")**:
      * Nâng timeout probe retry trong `vpn_preflight.py` lên `12.0s` và đồng bộ sang Admin PC để chống false-positive timeout khi 80 máy tải dồn.
      * Chuẩn hóa parser `inspect_machine.py` hỗ trợ tiền tố `M<N>` (`M204` -> `204`).
      * Không chỉ giải thích hiện trường mà BẮT BUỘC rà soát lỗ hổng timeout/retry của runner để vá triệt để trước khi báo resume.
    - Chi tiết xem `references/dual-cluster-batch-alert-adb-timeout-and-pppoe-renegotiation-20261010.md`, `references/scheduled-reboot-window-collision-and-adb-probe-timeout-20261010.md`, và `references/batch-alert-code-hardening-anti-complacency-20261010.md`.
