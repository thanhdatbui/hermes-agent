# Claude Audit & Field Triage Case Study: Xiaomi R3G Multi-WAN Deploy

Case study and operational notes from deploying the Xiaomi Mi Router 3G v1 (`r3g-thaibinh`) with 2 PPPoE lines + 1 rescue port over Tailscale.

## 1. Claude CLI Independent Audit Findings

During pre-shipout review, Claude CLI identified critical production hazards on headless OpenWrt nodes:

1. **mwan3 vs Kernel Metric Route Conflict:**
   - *Finding:* When interfaces have distinct metrics (Line 1 = 10, Line 2 = 20, Rescue = 200), `mwan3` rules still intercept routing unless explicitly configured for failover policies.
   - *Remediation:* If relying purely on Linux kernel metric-based default routing, disable `mwan3` completely:
     ```sh
     /etc/init.d/mwan3 disable
     /etc/init.d/mwan3 stop
     rm -f /etc/rc.d/*mwan3*
     ```

2. **Dormant Daemon Port Exposure & Resource Leaks:**
   - *Finding:* Default ROM images often package `alist` (listening on TCP 5244) and `openvpn` (UDP 1194) with inbound firewall accept rules. On public IP lines, these expose files and services to the public internet.
   - *Finding:* `watchcat` configured to reboot on ping failure will cause infinite reboot loops when upstream ISP fiber is disconnected during transit or installation.
   - *Remediation:*
     ```sh
     /etc/init.d/alist disable && /etc/init.d/alist stop
     /etc/init.d/watchcat disable && /etc/init.d/watchcat stop
     uci -q delete firewall.alist
     uci -q delete firewall.openvpn
     uci commit firewall
     ```

3. **NTP Server Redundancy (No-RTC Clock Desync):**
   - *Finding:* MT7621 routers have no battery-backed RTC. Default NTP lists often contain regional Chinese servers (Aliyun, Tencent) that may fail or time out, leaving system time at 1970. Tailscale cannot validate TLS certificates with desynchronized clocks.
   - *Remediation:*
     ```sh
     uci add_list system.ntp.server='time.cloudflare.com'
     uci add_list system.ntp.server='time.google.com'
     uci add_list system.ntp.server='pool.ntp.org'
     uci add_list system.ntp.server='vn.pool.ntp.org'
     uci commit system
     /etc/init.d/sysntpd restart
     ```

4. **Pre-Shipout Sysupgrade Archive:**
   - *Command:* `sysupgrade -b /tmp/pre-ship-backup.tar.gz`
   - *Verification:* Pull archive back to coordinator PC (`C:/Users/Kibe/pre-ship-backup.tar.gz`) and verify `etc/config/network`, `etc/config/firewall`, `etc/firewall.user` inside before packing hardware.

---

## 2. Field Triage & Flapping Lifeline (Real-World Incident)

### Incident Symptom
- Node appears `Connected` (green dot) in Tailscale Admin Console at `14:10:00`.
- At `14:11:00` (after ~1 minute), node state drops to `Offline (last seen 2:11 PM GMT+7)` with `RxBytes: 0`.

### Root Cause Analysis & Forensic Breakdown
1. **Initial Boot & Primary Line Success:** 
   - At 14:04, instructions were given to plug the 2 white cables (Line 1 and Line 2) and leave the blue port empty.
   - At 14:08, helper plugged the 2 white cables.
   - At 14:10, PPPoE dialed successfully on the primary line, and Tailscale came online (`Connected` at 14:10).
2. **False Diagnostic & Premature Line Severing:**
   - Because of polling lag and impatience, coordinator assumed the primary lines failed and prematurely instructed the helper: *"Unplug the 2 white cables immediately, plug only the blue cable"*.
   - At 14:11:00, helper unplugged the white cables, immediately killing the working PPPoE session.
   - The blue cable, plugged in hurriedly, either had a bad link or was plugged into an IPTV/MyTV port without DHCP. The node remained offline.
3. **Coordinator Denial Bias:**
   - When user presented screenshots showing the node was connected at 2:10 and disconnected at 2:11, coordinator initially dismissed the evidence, assuming the node had never connected.

### Agent Behavioral Correction (Critical Discipline)
- **Do NOT Argue Against Timestamp Evidence:** When the user provides a screenshot showing a recent `Last Seen` timestamp (e.g. `2:11 PM`), never claim "the device never came online".
- **Cross-Check Intervention Timeline Before Ordering Unplugs:** 
  If `LastSeen` matches 1–2 minutes after helper plugged the primary cables, the PRIMARY lines were working. Ordering an unplug destroys the established connection.
- **Default to "Plug All 3 Lines" Rather Than Cable Musical Chairs:** 
  Leave Line 1, Line 2, and Rescue all connected. OpenWrt's metric hierarchy (10 -> 20 -> 200) will automatically select the best active route without human error.
