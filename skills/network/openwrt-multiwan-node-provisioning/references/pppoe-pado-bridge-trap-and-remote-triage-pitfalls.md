# Troubleshooting OpenWrt Multi-WAN, PPPoE PADO Timeout, and Remote Triage Pitfalls

## 1. The DSA Bridge PADO Swallowing Trap (Critical)

### Symptom
When converting switch ports (e.g., `lan1`, `lan2` on MediaTek MT7621 under OpenWrt DSA) to PPPoE WAN interfaces, the router sends PADI discovery frames (`PADI` outgoing broadcast), but incoming PADO response frames from the ISP/modem are never received by `pppd`. The system log continuously repeats:
```text
Timeout waiting for PADO packets
Unable to complete PPPoE Discovery
```
Meanwhile, another commercial router or PC connected to the exact same cable dials PPPoE successfully.

### Root Cause
In OpenWrt DSA architecture, switch ports default to being slave members of `br-lan`. If an interface is set to `proto 'pppoe'` on device `lan1`, but `lan1` was **not explicitly removed from `network.@device[0].ports` (or `br-lan` bridge ports)**, the Linux bridge driver `rx_handler` intercepts incoming Ethernet frames with EtherType `0x8863` (PPPoE Discovery) and forwards them up to `br-lan`. The `pppd` daemon listening on raw socket bound to `lan1` never sees the PADO packet.

### Mechanical Fix (CLI)
Explicitly remove switch ports from the bridge definition:
```sh
uci -q del_list network.@device[0].ports='lan1'
uci -q del_list network.@device[0].ports='lan2'
uci commit network && /etc/init.d/network restart
```
Verify via `ls /sys/class/net/br-lan/brif` — only the management/rescue port (e.g., `wan`) should remain.

---

## 2. Remote Web Terminal / TTYD Clipboard Stripping Trap

### Symptom
When pasting multiline shell blocks into OpenWrt LuCI web terminal (`ttyd`) via remote desktop tools (UltraViewer, AnyDesk, TeamViewer):
- Chained command operators `&&` are stripped or converted to whitespace. Commands like `mkdir -p /root/bak && cp ...` become `mkdir -p /root/bak cp ...`, failing with `unrecognized option`.
- Background operator `&` and redirect `2>&1` are stripped: `/usr/sbin/tailscaled ... >/dev/null 2>&1 &` becomes `... >/dev/null 2> 1` (foreground execution without ampersand), freezing the terminal when subsequent commands are pasted.
- Chained `uci` commands like `uci set ... uci commit ...` fail with `Usage: uci ...`.

### Mechanical Protocol
1. **Never send multiline chained `&&` or background `&` commands to remote web terminal via UltraViewer.**
2. Send strictly **one discrete command per turn**, execute with Enter, and observe output.
3. To run background daemons safely without relying on `&`, use OpenWrt's built-in `start-stop-daemon`:
   ```sh
   start-stop-daemon -S -b -x /usr/sbin/tailscaled -- --state=/tmp/tailscaled.state
   ```

---

## 3. Remote Factory Reset Dead-End Guard

### Safety Invariant
**NEVER execute or advise `firstboot` / `Perform reset` (Factory Reset) on a remotely triaged OpenWrt node connected through host PC UltraViewer.**

### Why It Fails
1. **IP Reversion Collision:** OpenWrt resets its LAN static IP back to default `192.168.1.1`. If the host PC is obtaining internet/WiFi from an ISP home modem already residing on `192.168.1.1`, an IP conflict occurs, breaking the PC's network adapter and immediately terminating the UltraViewer remote session.
2. **Port Role Reversion:** The blue port (configured as `br-lan` management port `192.168.5.1`) reverts back to hardware WAN mode with incoming firewall rules set to REJECT. The PC loses all HTTP/SSH connectivity to the router.
3. **Loss of Tailscale Credentials:** Tailscale state and machine auth keys are wiped, requiring physical console recovery.

---

## 4. Viettel PPPoE: Untagged Bridging vs VLAN 35 vs Walled Garden (172.17.x)

### ISP Behavior
- On Viettel GPON ONTs (e.g., ZTE, Huawei, Dasan), when a LAN port is set to Bridge Mode by the ISP technician, the ONT strips the 802.1Q uplink tag. The Ethernet handoff to customer router is **untagged**.
- Do NOT configure OpenWrt VLAN sub-interfaces (`lan1.35`) unless the ISP technician explicitly confirms that the ONT bridge is operating in 802.1Q trunk/passthrough mode. Tagging VLAN 35 on an untagged bridge causes PADO timeout.
- **Dual-Stack Decoupling:** Viettel BRAS allocates IPv6 via DHCPv6-PD (`2402:800:...`) independently of IPv4 IPCP. Having a public IPv6 prefix does NOT mean IPv4 is open. If IPv4 receives `172.17.x.x` (Walled Garden/internal pool) and drops `8.8.8.8` (100% loss), the ISP subscriber profile has not been activated on the BRAS/RADIUS server for public routing.
