# MikroTik Sing-Box Transparent Proxy & Tailscale PortProxy Bridge Architecture

## 1. Architectural Invariant: Never Point Phones to Remote WAN Proxies
- **The Pitfall**: An agent might propose setting Android S7 Wi-Fi HTTP proxy directly to a remote WAN domain (e.g. `tb.taadaa.click:51xx` or a remote IP).
- **Why This Is Strictly Prohibited**:
  1. **Direct-IP Leakage Risk**: Android 7/8 Wi-Fi proxy stack lacks a native kill-switch. When a remote proxy drops, native apps (TikTok Cronet/gRPC) bypass HTTP proxy and fall back to direct Wi-Fi IP, causing account bans/shadowbans.
  2. **Credential & DNS Fragility**: Android Wi-Fi proxy cannot store credentials and relies on external DNS lookups over mobile Wi-Fi.
- **The Farm Standard**: All S7 devices MUST ALWAYS point to the local MikroTik gateway proxy port:
  - Farm Kibe (M1–M80): `192.168.110.2:20001..20080`
  - Farm Admin (M201–M280): `192.168.110.2:20201..20280`

## 2. MikroTik Sing-Box Fail-Closed Role
- MikroTik RouterOS v7 runs a Sing-Box Docker container (`veth-singbox` at `172.17.0.2`, mounted at `/docker/config/config.json`).
- MikroTik DST-NAT rule redirects all TCP `20001-20280` to `172.17.0.2`.
- Sing-Box routes each inbound `mixed-m<ID>` to a specific outbound `proxy_m<ID>`.
- If the upstream proxy dies or disconnects, Sing-Box immediately resets the TCP connection, providing a 100% mechanical kill-switch that prevents leakage to the local gateway IP.

## 3. The Tailscale Routing Gap & Windows PortProxy Bridge Pattern
- **The Problem**: Remote multi-WAN nodes (such as Xiaomi R3G at a remote site) connect via Tailscale (`100.115.94.49`). MikroTik RouterOS v7 does NOT run Tailscale and has no route to `100.64.0.0/10` (Tailscale CGNAT). If Sing-Box attempts to reach a Tailscale IP directly, MikroTik routes packets out via default PPPoE interfaces where ISP BRAS drops them.
- **The Solution (LAN PortProxy Bridge)**:
  - Farm hosts (PC Admin `192.168.110.119` or PC Kibe `192.168.110.123`) sit on the exact same 1Gbps LAN switch as MikroTik (0.2ms latency) AND have active Tailscale connections.
  - Windows built-in kernel PortProxy (`netsh interface portproxy`) bridges incoming LAN requests to the Tailscale destination:
    ```cmd
    netsh interface portproxy add v4tov4 listenport=5141 listenaddress=192.168.110.119 connectport=5141 connectaddress=100.115.94.49
    netsh advfirewall firewall add rule name="PortProxy_5141_5158" dir=in action=allow protocol=TCP localport=5141-5158
    ```
  - `netsh interface portproxy` persists across Windows reboots automatically in the Windows Registry (`HKLM\SYSTEM\CurrentControlSet\Services\PortProxy`).
- **End-to-End Chain**:
  `Phone (192.168.110.2:202xx)` ➔ `MikroTik Sing-Box (172.17.0.2)` ➔ `PC Admin LAN (192.168.110.119:51xx)` ➔ `Tailscale Tunnel` ➔ `R3G Thái Bình (100.115.94.49:51xx)` ➔ `Clean Viettel FTTH IP`.

## 4. Cross-Host Excel Sync Delay Pitfall & Direct Remote Update Pattern
- **The Pitfall**: When the Coordinator updates `PROXYgandienthoai.xlsx` on the controller (PC Kibe) and immediately invokes remote ADB configuration scripts (`set_proxy_farm_admin_adb.py`) on Admin PC via SSH, OneDrive sync has a multi-second or multi-minute propagation delay. Admin PC reads the *stale cached Excel file* and applies the old proxy ports (e.g. `:100xx` instead of `:202xx`).
- **The Solution (Direct Remote Mutation via Base64 Script)**:
  1. Do not rely on OneDrive real-time sync for immediate batch application.
  2. Deliver an atomic Python updater script directly to Admin PC via SSH/PowerShell using Base64 encoding (`[System.Convert]::FromBase64String`) to bypass shell quote/newline mangling.
  3. Execute the local Excel mutation on Admin PC *first*, then immediately execute `set_proxy_farm_admin_adb.py --machines ...`.
  4. Both controller and target host workbooks are guaranteed to be in sync without race conditions.

## 5. Cloudflare DNS & Account Identity Rule
- Domain `taadaa.click` belongs to Cloudflare account `thanhdatbui1995@gmail.com` (Account ID `e5b3266fa0ffe7d721901c78839a732b`).
- **Strict Invariant**: NEVER confuse with or log into `thanhdatbui19951@gmail.com` (which is an empty account without domain records).
- All DNS records pointing to Tailscale IPs (e.g. `tb.taadaa.click` ➔ `100.115.94.49`) MUST be set to **DNS Only** (grey cloud), as Cloudflare CDN proxying cannot handle private CGNAT IP ranges or raw non-HTTP proxy ports.
