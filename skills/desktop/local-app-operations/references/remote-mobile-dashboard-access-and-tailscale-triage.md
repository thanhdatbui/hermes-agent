# Remote Mobile Dashboard Access & Tailscale Triage

## 1. Overview & Problem Pattern
When a user complains that a local web dashboard (e.g., TikTok Farm Dashboard at `kibe:1905` or `100.88.164.111:1905`) cannot be reached from an iPhone / mobile device, do NOT assume the web server is crashed or guess blindly. 

Systematic diagnosis reveals three common failure modes:
1. **iOS Tailscale Network Extension Dormancy (`magicsock-receive-func-error`)**: iOS background memory management and Wi-Fi/Cellular network handoffs frequently drop the UDP socket of Tailscale's WireGuard extension, causing the iPhone to show `Online: False` on the tailnet and drop data plane traffic (`TxBytes: 0, RxBytes: 0`, `LastHandshake: 0001-01-01T00:00:00Z`).
2. **MagicDNS & Safari Automatic HTTPS Upgrade Trap**:
   - Modern iOS Safari (iOS 15+) aggressively performs **Automatic HTTPS Upgrade**. When a user types `kibe:1905` in Safari's address bar without the `http://` scheme, Safari attempts an HTTPS handshake: `https://kibe:1905/`.
   - Because internal servers (like Python `http.server.ThreadingHTTPServer`) speak plain HTTP without TLS/SSL, receiving a binary TLS ClientHello (`\x16\x03...`) causes the socket to terminate abruptly.
   - Safari displays the exact localized error: **"Safari không thể mở trang vì không thể thiết lập kết nối bảo mật với máy chủ"** (*"Safari cannot open the page because it could not establish a secure connection to the server"*).
   - Furthermore, iOS Safari's UI collapses the address bar to display only the bare host **`kibe`** (hiding both protocol and `:1905` port), misleading users into thinking the port was ignored or the service crashed.
   - If Tailscale is disconnected, local Wi-Fi DNS cannot resolve the single-label MagicDNS hostname `kibe`.
3. **Same-Network Bypass Neglect**: Often the user is physically at the farm/office connected to the same Wi-Fi subnet (`192.168.110.x`) as the host PC (`192.168.110.123`). In this scenario, Tailscale is completely unnecessary; accessing via direct LAN IP (`http://192.168.110.123:1905/`) works instantaneously.

---

## 2. Fast Diagnostic Workflow O(1)

### Step 1: Verify Host Service & Port Binding
Confirm the dashboard process is running and bound to `0.0.0.0` (all interfaces):
```python
import psutil
for c in psutil.net_connections(kind='inet'):
    if c.laddr.port == 1905 and c.status == 'LISTEN':
        print(f"Port 1905 bound to {c.laddr.ip} by PID {c.pid}")
```

### Step 2: Verify Inbound LAN Access
Test connectivity from another device on the same subnet (e.g., via an Android farm phone):
```bash
adb -s <serial> shell "echo -e 'GET /health HTTP/1.0\r\n\r\n' | toybox nc -w 3 192.168.110.123 1905"
```
If this returns `HTTP/1.0 200 OK {"status":"ok"}`, Windows Defender Firewall is actively permitting inbound LAN traffic.

### Step 3: Check Tailscale Peer Status & Mobile Presence
Check `tailscale status --json` to inspect the mobile device:
```python
import subprocess, json
out = subprocess.check_output(['tailscale', 'status', '--json'], text=True)
data = json.loads(out)
for k, peer in data.get("Peer", {}).items():
    if "iphone" in peer.get("DNSName", "").lower() or "iphone" in peer.get("HostName", "").lower():
        print("Peer:", peer.get("DNSName"), "Online:", peer.get("Online"), "CurAddr:", peer.get("CurAddr"))
        print("Handshake:", peer.get("LastHandshake"), "Tx/Rx:", peer.get("TxBytes"), peer.get("RxBytes"))
```
- If `Online: False` and `LastHandshake: 0001-01-01`: Mobile Tailscale VPN is dormant or crashed.
- Run `tailscale ping <tailscale_ip>` to check control-plane responsiveness.
- Check if mobile's LAN IP (`CurAddr` or DHCP lease) responds to `ping -n 2 <local_ip>`.

---

## 3. Clear Remediation Guidance for User

Provide two distinct, zero-confusion options:

1. **Immediate Access (LAN / In-Farm Wi-Fi)**:
   - If user is on the farm/home Wi-Fi:
   - Provide direct LAN URL: `http://192.168.110.123:1905/` (explicit `http://` mandatory).
   - Explains that this bypasses VPN overhead and works even if Tailscale is offline.

2. **Remote Access (Outside / 4G via Tailscale)**:
   - Guide user to open Tailscale app on iPhone.
   - Toggle VPN **OFF** then **ON** (Disconnect $\to$ Connect) to reset the iOS MagicSock socket if dormant.
   - Confirm app shows green `Connected` without warning triangle.
   - Access via full Tailscale IP (strongly preferred over bare hostname to completely bypass Safari's HTTPS upgrade):
     - Primary: `http://100.88.164.111:1905/`
     - Fallback: `http://kibe.tail11bc77.ts.net:1905/` (or `http://kibe:1905/` with mandatory `http://`)
3. **Permanent iOS Safari Bypass (Add to Home Screen)**:
   - Advise the user: Once loaded, tap Safari's **Share** button $\to$ **"Add to Home Screen"** ("Thêm vào Màn hình chính").
   - This creates a standalone web app icon that permanently preserves the `http://` scheme, preventing future HTTPS upgrade failures entirely.
