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
- Immediately at `14:10:00`, node state drops to `Offline (last seen 1m ago)` with `RxBytes: 0`.

### Root Cause Analysis
1. Helper plugged in the blue rescue cable; router obtained a DHCP lease from the home network; Tailscale contacted the coordination server (green dot).
2. Helper saw LED light up or heard from the user that it was "working", and immediately unplugged the blue cable to plug in the white cables (or to relocate the router).
3. The newly pulled fiber lines were not yet in Bridge mode on the ISP ONT, so PPPoE failed, leaving the router with zero default routes once the rescue cable was pulled.

### Prevention Protocol
- Always instruct remote helpers:
  > *"Cứ cắm GIỮ NGUYÊN sợi dây ở CỔNG XANH DƯƠNG, TUYỆT ĐỐI ĐỪNG RÚT RA cho đến khi kỹ thuật viên báo đã cấu hình xong từ xa!"*
