---
name: farm-network-gate-contract
description: "Use when designing farm Wi-Fi/proxy safety gates."
version: 1.0.0
category: automation
tags: [farm, wifi, proxy, ssot, fail-closed, device-lock, evidence]
---

# Farm Network Gate Contract

Use this skill when a multi-device Android farm needs reliable Wi-Fi assignment, proxy mapping, recovery, or a guard against ad-hoc network changes. The goal is not merely to reconnect a phone: it is to make a wrong SSID/PSK/proxy mapping mechanically difficult or impossible.

## Design principles

1. **Single source of truth (SSOT).** Wi-Fi groups and proxy mappings are authoritative data, not caller-supplied strings. Keep Wi-Fi credentials and proxy endpoints in separate sources. Never infer a profile from the currently connected SSID.
2. **One canonical mutation primitive.** Expose an API shaped like `apply_profile(machine)`; the caller supplies only the machine identifier. The primitive resolves SSID, security, credential reference, subnet, and proxy endpoint from validated data. Reject caller-supplied SSID, PSK, host, or port.
3. **O(1) resolution after load.** Validate ranges once, reject overlaps/gaps and missing fields, then build an indexed `machine -> profile` map. Unknown or ambiguous machines fail closed; there is no fallback group and no guessed credential.
4. **Lock before mutation.** Acquire the machine/device lock before any write, reboot, profile removal, or join operation. Confirm serial provenance independently. A busy lock means untouched and blocked, not forceful takeover unless the operator explicitly authorizes preemption.
5. **Idempotency.** Read current state first. If the expected Wi-Fi, L3 route, and proxy are already healthy, return `NO_OP` without disrupting a running session.

## Required gate sequence

```text
validate SSOT
  -> resolve machine/profile/serial
  -> acquire device lock
  -> read current state and decide NO_OP vs apply
  -> apply exact resolved profile
  -> verify L2 Wi-Fi
  -> verify L3 address/route/gateway
  -> verify L4 proxy
  -> write sanitized evidence
  -> release lock
```

The sequence is one-way: if a gate fails, do not run downstream checks or change another layer to hide the failure.

## Layered verdicts

### L2: Wi-Fi association

Verify expected SSID/BSSID policy, association state, reason code, RSSI/link rate, and the absence of an unwanted active profile. `MIC failure`, `4-way handshake failure`, association rejection, or wrong-password disablement is `L2_AUTH_FAIL`/`FINAL_BLOCKED`. Do not try alternate passwords, roam to another farm group, or loop radio toggles.

### L3: IP, DHCP, and routing

Verify a farm-subnet IPv4 address, the expected gateway, default route on the Wi-Fi interface, and gateway reachability. Missing IP/route is `L3_NO_IP` or `L3_NO_GATEWAY`; it is not a proxy failure. A stale/static profile must be treated as a profile-state issue and verified after rebind.

### L4: Proxy

Only after L2 and L3 pass, verify the machine's resolved proxy endpoint, TCP connectivity, proxy authentication/HTTP status, and egress policy. A 407/502 or wrong port is an L4 verdict; never “fix” it by changing Wi-Fi.

## Fail-closed and anti-hardcode rules

- Unknown machine, serial mismatch, missing/changed profile hash, missing lock, mismatch on readback, or incomplete evidence => `FINAL_BLOCKED`.
- Never hardcode a group credential from memory or reuse a neighboring group’s password. Do not print PSKs in argv, logs, screenshots, reports, or exceptions.
- Add static lint/guard coverage that rejects literal SSID/PSK connection commands outside the canonical primitive.
- Auth/MIC failures have a bounded attempt policy; after the first confirmed credential failure, preserve evidence and stop rather than retrying a wrong configuration.
- Do not reboot AP/router, change transmit power, or move a phone between groups as an automatic response.

## Two-tier conflict verification protocol

Before authoring or modifying any gate, guard hook, or network script, verify against both tiers:

1. **Tier 1 — Existing system guards:**
   - `guard_android_proxy.py`: Android `http_proxy` MUST be RFC1918 LAN IP (`192.168.110.2:<port>`), never domains or public IPs.
   - `guard_cronjob_safety.py`: Windows subprocesses MUST include `creationflags=0x08000000` (`CREATE_NO_WINDOW`) or `-w hidden`.
   - `guard_device_bulkhead.py` & Hard Gate #5: ADB commands MUST include explicit `-s <serial>` and run inside `operator_device_lock`.
   - Codebase safety: strictly forbid broad disk sweeps (`os.walk`, `glob(recursive=True)`, `find`, `grep -r`), never edit protected system hook files.
2. **Tier 2 — Operator farm invariants:**
   - Direct exceptions: M67 and M69 are direct (`http_proxy` `:0`, bypass local Sing-box proxy).
   - SSID exception: M7 is permanently authorized to connect to SSID `Dat` (pass `19051995`) via Aruba; exempt from fleet `kibe 1` rule due to 5GHz hardware defect.
   - Rescue override: allow `force_preempt=True` in `operator_device_lock` during emergency machine rescues.
   - Nurture protection: return `NOOP_HEALTHY` when current state matches expected to avoid breaking active 25-worker TikTok sessions.
   - Network hierarchy: Sing-box LAN only, strictly no VPN, Ruijie > Aruba.
   - Verification suite: 100% offline mocked tests running under 30s.

## Control loop and anti-silent-loop discipline

- **Hard-stop on policy blocks:** When an action trips a guard, bulkhead, or permission check, STOP immediately. Never write ad-hoc scripts to bypass a guard.
- **Bounded retries (Circuit Breaker):** Max 2 attempts on a structural failure. On the 2nd failure, stop and report `BLOCKED` with evidence.
- **Mandatory progress reporting:** Never leave the operator in a silent loop exceeding 3 minutes during multi-step background work. Always emit a heartbeat.
- **Definitive completion:** Every task must terminate in one of four valid states: `SUCCESS`, `FAILED`, `BLOCKED`, or `NEEDS_OPERATOR`. Never allow unbounded or hanging states.

## Evidence and rollout

Each apply/readback record includes machine, serial, profile ID, profile hash, expected-vs-actual values, timestamp, lock ID, layer verdicts, and sanitized raw output. A screenshot is required for UI evidence and must be visually inspected before delivery.

Roll out in this order: read-only dry run; one idle canary per Wi-Fi group; verify complete L2→L3→L4 evidence; expand one group at a time; stop the first failing group; enable enforcement only after the canary matrix is green. Never infer whole-farm success from a single canary or launcher exit code.

## Minimum offline test matrix

Cover overlapping/gapped ranges, unknown machines, duplicate serials, changed profile hash, busy lock, caller-supplied SSID/PSK rejection, auth failure without retry, no IP, wrong gateway/route, wrong proxy port, proxy 407/502, readback mismatch, and healthy-profile no-op.

## Android legacy notes

For older Samsung Android builds (e.g. Galaxy S7 running Android 8):
- **Ruijie Gateway Static IP Conflict (`Converted to Static IP` Stalling — Áp dụng cả Kibe M1-M80 & Admin M201-M280):** Farm client devices across ALL clusters (Kibe M1–M80 and Admin M201–M280, 160 phones total) MUST operate on dynamic DHCP pool. Binding a phone's MAC to a static IP reservation in Ruijie Gateway (`EW3200GX-PRO`) locks the lease state to `Converted to Static IP`. When the phone resets Wi-Fi or refreshes supplicant state, Android's `DhcpClient` sends new transaction IDs that Ruijie fails to negotiate, causing indefinite DHCP starvation (`wlan0` stays on IPv6 link-local, ARP incomplete). Always delete farm phone MACs from Ruijie's Static IP table and let them acquire dynamic DHCP leases like the rest of the fleet. The canonical gate must fail closed for any static-IP reservation or static-IP fallback request targeting M1–M80 or M201–M280 (`FARM_DHCP_RANGES = ((1, 80), (201, 280))`); encode this as a pure helper (for example `validate_dynamic_dhcp_policy`) plus an offline regression test for M7 and M201/M240/M280, while preserving direct-proxy exceptions M67/M69. Do not rely on a comment or memory entry alone.
- **Pre-Join Hygiene (Clear Stale Proxy & Captive Portal):** If a device previously had `http_proxy` configured (`192.168.110.2:200xx`), Android routes initial DNS and captive portal probes (`generate_204`) through that proxy *before* acquiring an IP, leading to immediate network-unreachable errors, `isUsableInternet: false`, and connection flapping. Always run `settings put global http_proxy :0` and disable captive portal (`captive_portal_mode 0`, `captive_portal_detection_enabled 0`) *before* triggering the join activity.
- **Foreground App Requirement for `adbjoinwifi`:** On Samsung S7, `com.steinwurf.adbjoinwifi` must be kept in the foreground during the join and DHCP negotiation phases. Do NOT pass `-S` to `am start` (avoids killing the process beforehand), and do NOT send `input keyevent 3` (KEYCODE_HOME) prematurely inside `_join_wifi`. Send HOME only once at the very end of `apply_profile` after all L2-L4 layers complete.
- **Default Route Establishment Latency (`_wait_for_gateway`):** After DHCP leases an IPv4 address, Android's `ConnectivityService` requires 2–5 seconds to evaluate the link and install default routes (`ip route add default via ... dev wlan0`). A single-shot 0s gateway check immediately fails with `Network is unreachable`. Implement `_wait_for_gateway(serial, net, attempts=6, interval=2.0)` with bounded polling.
- **Stale profile sweep beyond ID 10:** Android retains stale Wi-Fi networks with IDs >= 10 (e.g. ID 10, ID 11). If a stale network was marked `blackListed` with `NETWORK_SELECTION_DISABLED_AUTHENTICATION_FAILURE`, hardcoded sweeps like `range(10)` miss it and cause false L2 auth-fail blocks. Always parse all configured IDs from `dumpsys wifi` (`ID: (\d+)`) and sweep `set(range(30)) | ids` via `service call wifi 14 i32 <ID>`.
- **ICMP ping `-I wlan0` failure on non-root:** On Android 8 non-root, running `ping -c 1 -W 3 -I wlan0 <IP>` fails with `Permission denied` or `connect: Network is unreachable` (returncode 2). Always ping without `-I` and fallback to TCP probes (`toybox nc` to Gateway port 80 or Sing-box proxy port `20000 + machine`) when ICMP is blocked or unsupported by router/OS.
- **`toybox nc` syntax compatibility:** Android toybox netcat does NOT support `-z` (which BSD nc uses). Use `toybox nc -w 3 -W 3 <host> <port> < /dev/null` or `-w 2 -q 0 <host> <port>`.
- **Post-association DHCP stall remediation:** In older devices, WPA2 association may complete (`<BROADCAST,MULTICAST,UP,LOWER_UP> state UP`) but Android fails to acquire IPv4 (only link-local IPv6 `fe80::...`). Implement `_renew_dhcp(serial)` (`dhcpcd -n wlan0`, toggle `svc wifi disable` -> `sleep 1` -> `svc wifi enable`), extend polling (`IP_POLL_ATTEMPTS = 15, IP_POLL_INTERVAL = 2.0s`), or fall back to static IP mapping from farm topology.
- **`--es` vs `-e` String Extra Typing on Android Shell:**
  Khi truyền tham số vào `com.steinwurf.adbjoinwifi` qua `am start`, BẮT BUỘC dùng cờ `--es` (explicit string extra), không được dùng `-e`. Cờ `-e` không xác định rõ kiểu dữ liệu, khi gặp SSID có dấu cách như `"kibe 1"`, Android shell và `am` parser dễ bị bóc tách nhầm làm cắt cụt chuỗi thành `"kibe"`, khiến máy quét tìm SSID rác không tồn tại. Bọc quote an toàn: `--es ssid "\"{net['ssid']}\"" --es password_type WPA --es password "\"{net['password']}\""`.
- **Triệt tiêu bẫy pop Settings giữa chừng (`WIFI_SETTINGS` Interruption):**
  CẤM chèn lệnh `am start -a android.settings.WIFI_SETTINGS` vào giữa vòng lặp poll chờ IP DHCP (`_wait_for_subnet_ip`). Việc ép mở Activity Cài đặt Wi-Fi khi máy đang chạy automation hoặc đang đàm phán DHCP ngầm sẽ làm gián đoạn UI của máy, đè màn hình app chính và làm văng focus của các tác vụ khác. DHCP cần được để cho hệ thống hoàn tất ngầm hoặc reboot máy nếu driver thật sự kẹt.
- **`am start -S` và Dọn dẹp Timer ngầm của `adbjoinwifi`:**
  Trước khi kích hoạt join mạng, bắt buộc thêm `-S` vào `am start -S -n com.steinwurf.adbjoinwifi/.MainActivity` (hoặc gọi `am force-stop` trước) để tiêu diệt bất kỳ instance hoặc timer retry ngầm nào đang chạy từ lần trước. Đồng thời, ngay sau khi kết thúc `_join_wifi`, BẮT BUỘC gọi `am force-stop com.steinwurf.adbjoinwifi` để app không tiếp tục lặp intent ngắt kết nối.
- **`/proc/net/arp` Bypass ICMP Non-Root:** Non-root Android thiếu `CAP_NET_RAW` làm lệnh ping gateway thất bại. Đọc trực tiếp `/proc/net/arp` để kiểm tra gateway IP có cờ hợp lệ (`flags != 0x0`) và MAC khác all-zero trên `wlan0`.
- **Anti-Paralysis / Anti-Whining Invariant (User Mandate):** Operator strictly forbids passively stopping at `BLOCKED` and crying/giving up. When a gate layer fails (e.g. `L3_NO_IP`), Coordinator MUST proactively extract physical evidence (`dumpsys wifi`, `ip addr show wlan0`, `logcat`), identify the root physical layer, and propose/execute deterministic remediation.
- **Wi-Fi Driver Throttle do Tắt/Bật Dồn Dập vs Phục Hồi Bằng Reboot:**
  - *Hiện tượng lừa:* Khi chạy loop thử lại gate liên tục, các lệnh `svc wifi disable -> svc wifi enable -> scan` dồn dập khiến kernel/firmware radio của Galaxy S7 bị throttle hoặc kẹt driver (`Supplicant state: DISCONNECTED, RSSI: -127`), trông như hỏng chip Wi-Fi phần cứng hoặc rụng sóng.
  - *Chẩn đoán phân biệt phần cứng vs kẹt driver:* Nếu trước đó máy từng kết nối WPA2 và Ruijie từng cấp lease IP DHCP (`Galaxy-S7` nhận IP và có lưu lượng) thì 100% chip Wi-Fi không hề hỏng phần cứng.
  - *Biện pháp phục hồi dứt điểm:* CẤM tiếp tục spam lệnh join/scan. Thực hiện khởi động lại máy qua script cứu hộ chuẩn: `python D:/Taadaa/tools/recover_stuck_s7.py --machine <N> --reboot` (kèm cooldown an toàn). Sau khi reboot (~35s), firmware Wi-Fi được re-initialize hoàn toàn sạch sẽ, máy lập tức kết nối lại AP và hoàn tất gate `APPLIED` / `NOOP_HEALTHY`.
  - *Giữ nguyên trạng thái khi đã ổn định:* Khi thiết bị vừa reboot xong hoặc đang bắt đầu đàm phán route, tuyệt đối không spam thêm các lệnh `_join_wifi` phá vỡ state. Chạy gate ở chế độ passive check (`NOOP_HEALTHY`) để bảo toàn phiên.
- **`am force-stop com.steinwurf.adbjoinwifi` Post-Join Hygiene (Triệt tiêu timer ngầm):**
  App `adb-join-wifi` khi được gọi qua intent sẽ giữ activity và timer nội bộ chạy ngầm. Nếu không dập tắt, timer của app cứ 4–5 giây lại bắn intent `CMD_ENABLE_NETWORK <id> true (disableOthers=true)` liên tục, làm đứt ngang kết nối của SSID chuẩn và ngắt quãng chu kỳ nhận DHCP / nạp route của Android. BẮT BUỘC gọi `_adb_shell(serial, "am force-stop com.steinwurf.adbjoinwifi")` ngay khi `_join_wifi` kết thúc (áp dụng cho mọi kết quả: `OK`, `TIMEOUT`, `AUTH_FAIL`).
- **Power Save Mode (PSM) Idle Timeout vs L4 Probe Tuning (Sửa Script, Cấm Báo Ảo):**
  - *Bẫy timeout 3s trúng chu kỳ PSM:* Khi điện thoại Galaxy S7 ở màn hình Launcher không có traffic video nặng, chip Wi-Fi Broadcom tự động bật IEEE 802.11 Power Save Mode (PSM) để giảm nhiệt. Lệnh probe `toybox nc -w 3 -W 3` quá ngắn sẽ bị timeout giả tạo (`nc: Timeout` / `No route to host`) dù proxy Sing-box vẫn sống tốt.
  - *Kỷ luật thực thi:* Khi phát hiện timeout do cơ chế sleep/PSM của máy, Coordinator BẮT BUỘC chủ động cập nhật script gate (tăng timeout probe lên 6s `-w 6 -W 6` và retry 3 lần ngắt quãng), TUYỆT ĐỐI KHÔNG giải thích lý do suông rồi để nguyên script cũ gây nghẽn gate liên tục.
  - *Vị trí ăng-ten vật lý trên Galaxy S7:* Nhìn từ mặt trước (màn hình), ăng-ten Wi-Fi nằm ở góc trên bên TRÁI (phía trên cụm phím Volume, ăn ra viền đỉnh máy). Nếu máy bị kẹt nẹp kim loại hoặc áp sát thanh sắt hộp của box, nhích nhẹ máy ra 2–3 cm để giải phóng vùng thu phát của ăng-ten.
- **`ECONNABORTED` ("Software caused connection abort") & Thermal Radio Throttling:**
  Khi thiết bị bị giã lệnh ADB / radio toggle liên tục kết hợp sạc nhanh, Broadcom PMIC/Wi-Fi chip bị quá nhiệt làm rớt kết nối TCP (`ECONNABORTED`). Sử dụng retry loop 3 lần với timeout 6s trong `_nc_probe` và để máy nghỉ ngơi 3–5 phút cho chip tản nhiệt, tuyệt đối không tiếp tục nã lệnh join dồn dập.
- **Port 5038 WinUSB Exclusive Hijacking (XiaoWei / JiWei Ghost Port):**
  Khi công cụ quản lý farm (như Tiểu Vi / XiaoWei) được bật hoặc crash để lại tiến trình mồ côi `adb.exe` chạy cổng `5038` (`-P 5038`), Windows WinUSB driver sẽ chuyển toàn bộ USB endpoints sang server 5038 theo cơ chế độc quyền. Hậu quả là cổng chính 5037 bị mất sạch máy (`device not found` hoặc `devices: ''`), gây hiểu lầm là rớt cáp hoặc máy sập nguồn. BẮT BUỘC kiểm tra `netstat -ano | findstr :5038` và gửi lệnh phẫu thuật O(1) diệt tiến trình 5038 qua PID hoặc `taskkill /F /PID <pid>` để trả toàn bộ thiết bị về lại cổng 5037 ngay lập tức mà không làm ảnh hưởng phần cứng.
- **S7 24/7 Idle Governance vs Daily Scheduled PC Reboot:**
  Dàn S7 farm chạy 24/7 không cần và CẤM reboot định kỳ hàng ngày. Lịch reboot tự động 05:20 sáng CHỈ khởi động lại 2 PC host (Kibe/Admin) để giải phóng thanh ghi USB controller, tuyệt đối không gửi lệnh reboot S7. Ép S7 reboot hàng ngày gây hao mòn chip nhớ eMMC, bão USB/DHCP và rớt atx-agent. Chỉ reboot S7 đơn lẻ khi kẹt shell sâu bằng `recover_stuck_s7.py`.

## References

- `references/m7-hardware-exception-and-alert-triage.md` — Machine 7 hardware exception (SSID Dat WPA2 passphrase, 5GHz association rejection on kibe 1), watchdog alert timestamp disambiguation, and anti-premature-rescue runbook.
- `references/s7-wifi-proxy-psm-and-port5038-incident.md` — Samsung S7 Wi-Fi/Proxy probe flapping, Power Save Mode (PSM) tuning, adbjoinwifi timer suppression, thermal throttling, and Port 5038 WinUSB exclusive hijacking runbook.
- `references/ruijie-static-ip-dhcp-conflict-and-enforcement.md` — Ruijie Gateway Static IP conflict on farm devices (M1-M80), lease stall ("Converted to Static IP"), DHCP starvation incident on M7, mechanical guard enforcement via validate_dynamic_dhcp_policy, and cleanup runbook.
- `references/s7-wifi-radio-throttle-and-reboot-protocol.md` — Samsung S7 Wi-Fi radio driver throttle vs hardware failure diagnosis, false-positive RSSI -127 panic, and deterministic reboot recovery protocol.
- `references/s7-android8-wifi-stack-quirks-and-dhcp-remediation.md` — Samsung S7 Android 8 quirks: stale network IDs >= 10, non-root ping -I socket errors, toybox nc syntax without -z, DHCP renewal, and anti-paralysis protocol.
- `references/network-gate-contract-and-m7-lesson.md` — the validated design review, failure pattern, and acceptance contract from the M7 incident.
- `references/two-tier-conflict-protocol-and-anti-silent-loop.md` — two-tier conflict verification protocol, operator invariants, anti-silent-loop control rules, and Advisor Sol streaming TTFT insight.
- `references/farm-network-gate-production-implementation-and-review-audit.md` — production implementation of farm_network_gate.py, resolution of 3 Claude Reviewer blocking findings, 36/36 tests, and live canary evidence.
