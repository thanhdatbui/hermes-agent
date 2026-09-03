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

## Invariant for Consumer Repos (Tiktok_Reg & Feed Session)
1. Mapping resolution MUST use `serial_is_mapped_in_workbook` with normalized header aliases (`phoneId`, `deviceId`, `serial`), never hardcoded column indices.
2. Registration scripts MUST hardcode `verify_live_ip=True` (never allow env vars to disable it).
3. Preflight MUST require `status.allowed`, `status.connected`, and non-empty `status.proxy_ip` before proceeding to app launch.
4. **Router Transparent Proxy Preflight & Route Isolation**:
   - **Dual-Route Architecture**: Explicit `interface` argument (`"wlan0"` vs `"tun0"`) takes absolute precedence over `TAADAA_PROXY_MODE`. All preflight helpers (`require_android_vpn`, `check_android_vpn`, `run_consumer_after_vpn_preflight`) default to `interface="auto"` (uses `tun0` if UP, else `wlan0`), preventing router-proxy farm devices from erroneously failing closed looking for ViChanger `tun0`.
   - **Router Mode Preflight (`wlan0`)**: Requires (1) `wlan0` UP with assigned IP, (2) `dumpsys connectivity` confirms `WIFI CONNECTED` and strictly `VALIDATED` (rejecting `NOT_VALIDATED`, intermediate states, or VPN `VALIDATED`), (3) fast bounded ping to dynamically resolved default gateway (from `ip route show dev wlan0`) and fallback `8.8.8.8`, and (4) egress IP validation via `/data/local/tmp/atx-agent curl --timeout=3s http://icanhazip.com` strictly verified against version-independent IANA non-public CIDRs with `192.0.0.9/.10` Anycast carve-outs.
   - **Route-Isolated Recovery**: For `wlan0` router mode, only try `svc wifi enable` once then fail-closed immediately. NEVER call ViChanger watcher or soft-reboot on router devices (prevents cascading device locks and worker thread starvation).
   - **Thread-Safe Cache & Hermetic Tests**: Synchronize proxy mapping cache fully under `threading.Lock()` without unlocked reads, and ensure test fixtures reset cache before/after all tests.
   - **Ping Substring Pitfall**: `"0% packet loss"` is inside `"100% packet loss"`. Always check `" 0% packet loss"` or regex `r"\b0%\s+packet\s+loss"` to avoid false-positive ping matches.
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
   - **Quản trị MikroTik tự động qua REST API (Farm Infrastructure)**:
     * Endpoint nội bộ: `http://192.168.110.2:9090/rest` (User: `admin`, Pass: `N0spam@@`).
     * Script công cụ tích hợp sẵn: `D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py` (`--check`, `--fix`, `--reconnect <line_num>`).
     * Dàn 80 máy Kibe sử dụng cụm Sing-box container (192.168.110.2:20001..20080) và quản trị gán proxy ADB qua `AI-Tools/scripts/set_proxy_farm_adb.py`.
   - **Quy tắc báo cáo lỗi gửi bên thứ 3/admin**: Khi user yêu cầu viết lỗi gửi admin, CHỈ ghi ngắn gọn hiện tượng và IP/port lỗi, TUYỆT ĐỐI KHÔNG tự ý chèn giải pháp/hướng dẫn khắc phục khi chưa được yêu cầu.
9. **ADB Transport Disconnect Fail-Fast in Preflight (Tránh báo nhầm lỗi Proxy/Wi-Fi)**:
   - Khi thiết bị mất kết nối ADB / rớt cáp USB / offline (`device '...' not found`, `device offline`, `error: closed`, `protocol fault`), `adb.shell` với `check=False` trả về `ok=False` cùng thông báo lỗi trong `stderr`.
   - Preflight (`check_android_vpn` trong `automation_core.preflight` và `require_vichanger_connected` trong `vpn_preflight.py`) BẮT BUỘC kiểm tra `is_connection_lost(stderr)` ở probe đầu tiên (`tun0` hoặc `wlan0`) để lập tức fail-fast và trả mã lỗi `device offline or ADB/USB disconnected: <stderr>`.
   - Tuyệt đối không để exception / failure do mất ADB lọt xuống nhánh `else` ghi nhận nhầm thành `wlan0 interface down or unassigned IP` / `dumpsys connectivity: Wi-Fi not connected` / `required router proxy is unreachable`, tránh việc runner kích hoạt recovery Wi-Fi (`svc wifi enable`) vô ích và phát cảnh báo Telegram sai lệch hiện trường.
10. **Global HTTP Proxy Resolution & atx-agent Output Capture (Tránh false positive egress IP validation)**:
   - Trên dàn máy dùng proxy Wi-Fi (gán qua `settings put global http_proxy <host>:<port>`), subnet Wi-Fi nội bộ không route direct internet. Lệnh `/data/local/tmp/atx-agent curl` chạy trong adb shell không tự nhận proxy settings nếu không truyền biến môi trường `http_proxy` / `HTTP_PROXY`.
   - Preflight `check_android_vpn` bắt buộc đọc `settings get global http_proxy` (hoặc `global_http_proxy_host` / `global_http_proxy_port`). Nếu có proxy, gọi probe với env `http_proxy=http://<proxy>` `HTTP_PROXY=http://<proxy>`, sau đó mới fallback về direct probe.
   - **`atx-agent` Go STDERR logging**: `atx-agent curl` ghi nhận log request và output IP (`curl.go:116: <IP>`) ra **STDERR**, không phải STDOUT. Parser trích xuất IP bắt buộc kiểm tra cả `stdout` và `stderr` (`f"{stdout}\n{stderr}"`), tuyệt đối không chỉ đọc `stdout` vì sẽ nhận chuỗi rỗng và gây false-positive fail-closed.
   - **DNS Resolver IP Exclusion**: `atx-agent curl` ghi log DNS resolution `time="..." level=info msg="dns resolve 114.114.114.114"`. Hàm trích xuất IP bắt buộc ưu tiên định dạng log `curl.go:<line>: <IP>` và loại trừ các IP DNS public nổi tiếng (`114.114.114.114`, `8.8.8.8`, `1.1.1.1`, v.v.) để tránh bắt nhầm IP DNS resolver thay vì IP public ra ngoài thực tế.
   - **Windows ADB shell quoting**: Khi truyền lệnh qua `adb.shell()` trên Windows, tránh dùng `['sh', '-c', '...']` vì ADB CLI tự ghép khoảng trắng làm mất dấu nháy của script. Truyền trực tiếp lệnh compound: `[f"export http_proxy=http://{global_proxy}; export HTTP_PROXY=http://{global_proxy}; /data/local/tmp/atx-agent curl --timeout=3s http://icanhazip.com"]`.

## Reference

See `references/router-transparent-proxy-architecture.md` for router transparent proxy specs, ping substring safety, and route precedence.
See `references/proxy-preflight-incident-pattern.md` for the condensed evidence matrix and reporting template.
See `references/batch-process-vs-device-fail-closed-explanation.md` for explaining host batch processes vs device fail-closed behavior.
See `references/mikrotik-api-and-port-probe-architecture.md` for MikroTik REST API management and per-port socket probe architecture.
