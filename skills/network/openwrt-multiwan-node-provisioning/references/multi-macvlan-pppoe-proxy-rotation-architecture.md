# Production Architecture: Multi-MACVLAN PPPoE & Isolated Proxy Rotation with Tailscale

## 1. Problem Statement
When turning a single OpenWrt gigabit line into a multi-port rotating proxy farm (e.g. 8 independent rotating IP ports like MobiProxy):
- Dialing multiple PPPoE sessions on the physical interface without separate virtual MACs will either fail at BRAS or overwrite routing.
- If sub-interfaces alter the main routing table (`0.0.0.0/0`), the default gateway flutters or drops, instantly killing the Tailscale out-of-band management tunnel.
- Upstream proxy software like `3proxy` may be unavailable in lightweight firmware; `tinyproxy` is pre-installed (`1.10.0`) but requires per-instance configuration and explicit `Bind <local_ip>` binding to route traffic through the correct sub-interface.

## 2. Kernel & Routing Architecture
To isolate each proxy port cleanly:
1. **MACVLAN Creation on Base Physical Port (`lan2`):**
   Each sub-interface gets an independent, randomized or sequential MAC (`02:11:22:33:44:01..08`) in `bridge` mode:
   ```sh
   uci set network.dev_mvl1=device
   uci set network.dev_mvl1.name="mvl1"
   uci set network.dev_mvl1.type='macvlan'
   uci set network.dev_mvl1.ifname='lan2'
   uci set network.dev_mvl1.macaddr="02:11:22:33:44:01"
   ```
2. **PPPoE Multi-Session Dialing:**
   Each sub-interface dials using the same or assigned ISP account with:
   - `defaultroute='0'`: **CRITICAL**. Never allow sub-interfaces to install default routes into the `main` table. The main table `0.0.0.0/0` belongs strictly to the primary WAN (`WAN2`) where Tailscale resides.
   - `peerdns='0'`: Do not let sub-interfaces overwrite `/tmp/resolv.conf.auto`.
   - Distinct metric: `metric=$((100 + i))`.
3. **Policy Routing (`ip rule` + Policy Tables):**
   Direct traffic originating from the sub-interface's IP into its dedicated table:
   ```sh
   ip rule add from $new_ip table $((100 + i))
   ip route replace default dev pppoe-wan_sub$i table $((100 + i))
   ```
4. **Proxy Layer (Per-Port Tinyproxy Instance):**
   Spawn separate `tinyproxy` instances for each port (`5101..5108`):
   - Set `Port 510x`
   - Set `Bind $new_ip` (matches the local IP assigned to `pppoe-wan_subX`).
   - Allow incoming connections from Tailscale subnet: `Allow 0.0.0.0/0` (secured via firewall zone `tailscale`).

## 3. End-to-End Verification Recipe
To verify without relying on LLM guesses or local pings:
1. From remote management PC, send HTTPS requests through the remote proxy via Tailscale:
   ```python
   import urllib.request
   req = urllib.request.Request('https://ipinfo.io/json')
   handler = urllib.request.ProxyHandler({'https': 'http://100.115.94.49:5102'})
   opener = urllib.request.build_opener(handler)
   print(opener.open(req).read().decode())
   ```
2. Verify distinct egress IPs: Each port (5102, 5104, 5106) must return different public IPs under the target ISP ASN (`AS7552 Viettel Group`, `City: Thái Bình`).
3. Tailscale tunnel stability check: Ensure `ping -c 2 8.8.8.8` on router returns 0% packet loss and Tailscale remains connected continuously throughout rotation.
