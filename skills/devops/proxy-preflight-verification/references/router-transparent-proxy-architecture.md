# Router-Level Transparent Proxy Architecture & Dual-Route Preflight

## Architecture Overview
In the modernized Taadaa Farm architecture (August 2026), per-device App VPNs (`vn.vichanger.app` creating `tun0` interface) are replaced by Router-Level Transparent Proxy:
- **Router / Gateway**: MikroTik + Sing-box + DHCP Aruba assigns static IPs to phones over Wi-Fi (`wlan0`).
- **Router Kill Switch**: If a mapped proxy upstream dies, the router cuts WAN access for that device's local IP.
- **On-Device State**: Phones operate over plain Wi-Fi (`wlan0`), with no `tun0` interface and no ViChanger app running.

## Dual-Route Preflight Contract (`check_android_vpn`)
The shared `automation_core.preflight` module handles both legacy App VPN and new Router Transparent Proxy:

1. **Precedence Rules**:
   - Explicit parameter `interface="wlan0"` or `interface="tun0"` takes absolute priority.
   - Environment variable `TAADAA_PROXY_MODE="router"` or `"vichanger"` applies when `interface="auto"`.
   - Default `interface="auto"` probes `tun0` first; if UP, uses legacy route; otherwise routes via `wlan0`.

2. **Router Mode (`wlan0`) Verification Rules**:
   - `wlan0` interface UP with valid IP (`192.168.x.x`).
   - Dynamic default gateway discovery via `ip route show dev wlan0` (handles diverse router topologies).
   - Fast ping probe to gateway IP and fallback `8.8.8.8` (bounded timeout <= 3.0s). Note: Sing-box/MikroTik transparent proxies often drop ICMP to public IPs; gateway ping confirms physical Wi-Fi connection.
   - **Ping Substring Safety**: Match `" 0% packet loss"` or `"1 received"`, NEVER unpadded `"0% packet loss"` (which substring-matches `"100% packet loss"`).
   - **Dumpsys NetworkAgent Isolation**: Use bounded balanced-brace block parser (`_iter_network_agent_blocks`) with hard boundary at next `NetworkAgentInfo` marker.
   - **Capability Token Boundary**: Cut off trailing properties inside block (`re.split(r"\s+[A-Za-z0-9_]+:", raw_caps)[0]`) so fields like `foo: VALIDATED` never leak into the capability token set.
   - **Pure CIDR Version-Independent Public IPv4**: Validate public egress IP purely against IANA deny-list `_NON_PUBLIC_IPV4_NETWORKS` without relying on version-dependent `ipaddress.is_global` properties. Whitelist explicit carve-outs `192.0.0.9` (PCP Anycast) and `192.0.0.10` (TURN Anycast) before checking `/24` deny-list.

3. **Thread-Safe Proxy Mapping Cache**:
   - All cache reads, writes, and reloads in `get_default_proxy_mapping()` and `reset_proxy_mapping_cache()` must execute strictly inside `with _RESOLVED_PROXY_MAPPING_LOCK:` (no unlocked fast-path reads).
   - Test suites must use `setUp()` / `tearDown()` with `reset_proxy_mapping_cache()` to guarantee 100% test state isolation.

3. **`tun_up` Semantics**:
   - `AndroidVpnPreflight.tun_up` strictly reflects whether `tun0` is UP.
   - `AndroidVpnPreflight.interface` indicates the effective interface (`wlan0` vs `tun0`).
   - Internal boolean `interface_up` is evaluated according to effective route, ensuring legacy callers reading `tun_up` are not misled.

## Route-Aware Fast Recovery (`require_vichanger_connected`)
- **Router Mode (`wlan0`)**: Fast recovery attempts `svc wifi enable` once, sleeps 2s, and re-probes. If still failing, raises `ConsumerPreflightError` immediately (fail-closed).
  - *Pitfall Prevention*: NEVER invoke ViChanger watcher reassign or device soft-reboot on `wlan0` devices. Doing so causes 4–6 minute worker blocking per machine and triggers cascading farm-wide device locks.
- **Legacy Mode (`tun0`)**: First runs host-side fast socket probe `_proxy_server_live` (timeout 1.5s). If host port is closed/refused, fails fast in 1.5s; if alive but device lost tunnel, invokes `recover_missing_android_vpn`.

## Diagnostic Signatures & Triage
- **Alert Signature**: `required router proxy is unreachable for <serial> (kill switch active or no connection): wlan0 interface down or unassigned IP; dumpsys connectivity: Wi-Fi not connected`
  - *Distinction*: This is **NOT** a VPN (ViChanger / `tun0`) error. The device is operating in Router Transparent Proxy mode via `wlan0`.
  - *Root Cause Triage*:
    1. Check `adb devices`: If the serial is missing or `offline`, the phone dropped physical USB/ADB connection or powered off.
    2. If ADB is alive: `ip addr show wlan0` and `dumpsys wifi` indicate Wi-Fi AP disconnect, DHCP lease failure, or disabled Wi-Fi interface.
    3. Fail-Closed Behavior: The runner halted cleanly before launching apps to prevent leaking direct IP traffic.

## Migration Operations
When switching a farm from ViChanger to Router Proxy:
1. Stop host watcher: Kill `proxy-watcher-only-tray.ps1` / `GanProxyWatcherTray`.
2. Stop device VPNs: Run `adb -s <serial> shell am force-stop vn.vichanger.app` across all devices.
3. Verify route: `adb -s <serial> shell ping -c 1 -W 1 8.8.8.8` should succeed via `wlan0`.
