# MikroTik REST API Management & Proxy Port Probe Architecture

## 1. Fast Socket Probe vs Authenticated Proxy Verification
- A raw TCP socket probe (`socket.connect_ex`) on a router proxy port checks whether the listener port is open.
- When proxy ports require authentication (`--proxy-user admin@1:admin@1`), testing HTTP egress via `urllib.request.ProxyHandler` or `curl -x` confirms both the socket listener and upstream routing are operational.
- When an upstream port cluster (e.g. ports 10001-10007) is refused while other ports (10008, 10010-10035) work, it indicates listener or NAT rule desync on RouterOS rather than WAN PPPoE line drops.

## 2. DNS Resolution Failure — OmniRoute Proxy ERR Pattern (2026-09-09)
When OmniRoute proxy logs show high ERROR rate (e.g. 130/200) on `mikrotik1.taadaa.click:XXXX` ports while the MikroTik RouterOS shows all PPPoE interfaces CONNECTED, the root cause is often **DNS hostname non-existence** — not a router/port failure.

**Diagnosis (O(1)):**
1. Check DNS: `nslookup mikrotik1.taadaa.click 8.8.8.8` → if `Non-existent domain` → DNS record missing/expired.
2. Check DNS on Cloudflare: `nslookup mikrotik1.taadaa.click 1.1.1.1` → confirm.
3. Test working proxy: `curl -x http://test.taadaa.click:<PORT> http://httpbin.org/ip` → if OK → upstream proxy infrastructure is fine, only the hostname is broken.
4. Confirm PPPoE: MikroTik Proxy Manager (`mikrotik-tool.pages.dev`) shows all interfaces CONNECTED → router hardware/WAN is fine.

**Key distinction:** PPPoE CONNECTED ≠ proxy ports reachable. The PPPoE interface shows L2/L3 connectivity to ISP, but DNS resolution of the domain pointing to the router's WAN IP is a separate DNS-layer concern. OmniRoute can't connect because it resolves `mikrotik1.taadaa.click` → NXDOMAIN → connection fails at DNS lookup, never reaching the TCP/proxy layer.

**Fix:** Add/recreate A record for `mikrotik1.taadaa.click` in DNS management panel (Cloudflare or DNS provider), pointing to the MikroTik router's current public IP (check via MikroTik Proxy Manager public IP column or `curl` through any working port).

**How to read OmniRoute Proxy Logs (dashboard at `192.168.110.123:20129/dashboard/logs/proxy`):**
- Columns: STATUS | PROXY | TLS | TYPE | LEVEL | PROVIDER | TARGET | LATENCY | CLIENT IP | TIME
- Filter buttons: All / Errors / Success / Timeout / AG / OPENCODE / OPENROUTER
- Click a row to see error detail. Error rows show status ERROR with latency (high latency = timeout trying to reach DNS-resolved address or upstream).
- Summary bar: Total / OK / ERR / TMO counts give quick health overview.

## 3. MikroTik RouterOS REST API Management (LAN & WAN)
- **Host / Port**: `192.168.110.2:9090` (LAN) or `mirotik1.taadaa.click:9090` (WAN).
- **Credentials**: User `admin`, Password `N0spam@@` (`Authorization: Basic YWRtaW46TjBzcGFtQEA=`).
- **Sing-box Mixed Proxy Container**: IP `172.17.0.2` on MikroTik running ports `20001..20080` mapped 1:1 for 80 farm devices (`20000 + machine_id`).
- **Operational Automation Scripts**:
  - `python D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py --check` (inspect router resources, container, PPPoE status).
  - `python D:\Taadaa\AI-Tools\scripts\mikrotik_manager.py --fix` (clean stale IP aliases, verify Hairpin NAT, restart proxy container).
  - `python D:\Taadaa\AI-Tools\scripts\set_proxy_farm_adb.py --machines <id>` (provision global `http_proxy` on devices via ADB).
