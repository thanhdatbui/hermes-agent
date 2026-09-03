# MikroTik REST API Management & Proxy Port Probe Architecture

## 1. Fast Socket Probe vs Authenticated Proxy Verification
- A raw TCP socket probe (`socket.connect_ex`) on a router proxy port checks whether the listener port is open.
- When proxy ports require authentication (`--proxy-user admin@1:admin@1`), testing HTTP egress via `urllib.request.ProxyHandler` or `curl -x` confirms both the socket listener and upstream routing are operational.
- When an upstream port cluster (e.g. ports 10001-10007) is refused while other ports (10008, 10010-10035) work, it indicates listener or NAT rule desync on RouterOS rather than WAN PPPoE line drops.

## 2. MikroTik RouterOS REST API Management (LAN & WAN)
- **Host / Port**: `192.168.110.2:9090` (LAN) or `mirotik1.taadaa.click:9090` (WAN).
- **Credentials**: User `admin`, Password `N0spam@@` (`Authorization: Basic YWRtaW46TjBzcGFtQEA=`).
- **Sing-box Mixed Proxy Container**: IP `172.17.0.2` on MikroTik running ports `20001..20080` mapped 1:1 for 80 farm devices (`20000 + machine_id`).
- **Operational Automation Scripts**:
  - `python D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py --check` (inspect router resources, container, PPPoE status).
  - `python D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py --fix` (clean stale IP aliases, verify Hairpin NAT, restart proxy container).
  - `python D:\Taadaa\AI-Tools\scripts\set_proxy_farm_adb.py --machines <id>` (provision global `http_proxy` on devices via ADB).
