# OpenWrt Multi-WAN, PPPoE Provisioning & Satellite Farm Deployment

Use this guide when configuring OpenWrt routers (e.g. Xiaomi Mi Router 3G V1 / MT7621A) for remote/satellite phone farm deployments (e.g. Thai Binh satellite branch) requiring multi-line PPPoE aggregation, physical port role conversion, and remote management.

---

## 1. Hardware Architecture & Port Mapping (Xiaomi R3G V1)

Xiaomi Mi Router 3G V1 (MT7621A, 256MB RAM DDR3, 128MB SLC NAND):
* **Ports (Left to Right from rear):**
  1. DC 12V Power Jack.
  2. **WAN Port (Blue):** Gigabit (`wan@eth0`).
  3. **LAN 1 Port (White/Grey - Center):** Gigabit (`lan1@eth0`).
  4. **LAN 2 Port (White/Grey - Outer):** Gigabit (`lan2@eth0`).
  5. USB 3.0 Port (Blue rectangle).
  6. Reset pinhole.

### Physical Link Verification via Kernel Read-Back
Do not trust LED lights or user visual impressions alone. Verify via SSH:
```bash
# Check carrier status (1 = Link UP, 0 = No Carrier / Disconnected)
cat /sys/class/net/wan/carrier
cat /sys/class/net/lan1/carrier
cat /sys/class/net/lan2/carrier

# Check link speed and duplex from switch/PHY driver
dmesg | grep -E 'mt7530.*Link is' | tail -n 10
# Example: mt7530 mdio-bus:1f wan: Link is Up - 1Gbps/Full
```

---

## 2. Port Role Mapping: Remote-Hands Ergonomics (Rescue vs PPPoE)

### Intuitive 3-Port Layout for Non-Technical Remote Hands
In a satellite deployment, family members or non-technical on-site contacts physically plug in cables. Avoid confusing layouts (e.g. blue WAN + 1 white LAN for PPPoE, 1 white LAN for rescue).

**Recommended Canonical Layout:**
* **Blue Port (Inscribed WAN on chassis): RESCUE & Tailscale Port (`rescue` in `br-lan`)**
  * Configured as DHCP client (`proto dhcp`, metric 200).
  * **CRITICAL:** Disable router's internal DHCP server (`uci set dhcp.lan.ignore='1'`). Plugging into a family home router will NOT disrupt their existing network or hand out rogue IPs.
  * *Ergonomics:* Remote hands naturally associate the distinct Blue/WAN port with "connect to home internet".
* **Two White Ports (LAN 1 center, LAN 2 outer): Dedicated PPPoE Lines (`wan`, `wan2`)**
  * Symmetrical white ports map directly to ISP Bridge ONT 1 (`hyn_gftth_...0`, metric 10) and ONT 2 (`hyn_gftth_...1`, metric 20).
* **Normal vs Rescue Operating Principle:**
  * **Normal State:** Only the 2 white ports need to be plugged. If either line dials successfully, the router has Internet and Tailscale comes online automatically. The blue port remains empty.
  * **Rescue State:** If both fiber lines are down or pending technician install, plug the blue port into any household router to bring Tailscale online for remote management.

### Safe Live Migration Sequence (Avoiding SSH Lockout)
When modifying ports while connected via SSH over one of the LAN ports:
1. **Step 1 (Add WAN to bridge):** Add the physical blue `wan` port into `br-lan` bridge device. Verify both blue WAN and LAN1 now serve management access (`192.168.5.1`).
2. **Step 2 (Physical swap):** Move the admin PC cable from LAN1 to the Blue WAN port.
3. **Step 3 (Free LAN ports for PPPoE):** Once connected via the blue port, safely remove `lan1` and `lan2` from `br-lan` and reassign them to `wan` and `wan2` PPPoE interfaces.

```bash
# Example: Convert Blue port to Rescue DHCP and White ports to PPPoE
uci set network.@device[0].ports='wan'
uci set network.rescue=interface
uci set network.rescue.device='br-lan'
uci set network.rescue.proto='dhcp'
uci set network.rescue.metric='200'
uci set dhcp.lan.ignore='1'

# Configure White Port 1 (lan1) -> PPPoE Line 1
uci set network.wan=interface
uci set network.wan.device='lan1'
uci set network.wan.proto='pppoe'
uci set network.wan.username='<user_line1>'
uci set network.wan.password='<pass_line1>'
uci set network.wan.metric='10'

# Configure White Port 2 (lan2) -> PPPoE Line 2
uci set network.wan2=interface
uci set network.wan2.device='lan2'
uci set network.wan2.proto='pppoe'
uci set network.wan2.username='<user_line2>'
uci set network.wan2.password='<pass_line2>'
uci set network.wan2.metric='20'

uci commit network
uci commit dhcp
```

---

## 3. Scaling to 3+ Lines on a 3-Port Router

When a farm requires 3 to 6 fiber lines (e.g. 24–48 public IPs) on a router with only 3 physical ports:

### Method 1: Managed Switch 802.1Q VLAN Trunking (Recommended)
* **Hardware:** 5-port Gigabit Smart Managed Switch with 802.1Q VLAN (e.g. TP-Link TL-SG105E, ~250k–300k VND).
* **Topology:**
  * Port 1: ISP Modem 1 (Access VLAN 10).
  * Port 2: ISP Modem 2 (Access VLAN 20).
  * Port 3: ISP Modem 3 (Access VLAN 30).
  * Port 5: Trunk port (Tagged VLAN 10, 20, 30) connected to **WAN Port (Blue)** of Xiaomi R3G.
* **OpenWrt Configuration:**
  Create subinterfaces on the single WAN port:
  - `wan.10` (VLAN 10) $\rightarrow$ Line 1
  - `wan.20` (VLAN 20) $\rightarrow$ Line 2
  - `wan.30` (VLAN 30) $\rightarrow$ Line 3
  Each subinterface can dial 8 MACVLAN PPPoE sessions.

### Method 2: USB 3.0 to Gigabit Ethernet Dongle
* **Hardware:** USB 3.0 to RJ45 Gigabit adapter using Realtek RTL8153 or ASIX AX88179 (~120k–150k VND).
* **Setup:** Plugs into the blue USB 3.0 port on the rear of R3G. Kernel auto-loads `r8152` driver creating `eth1`. Configure `eth1` as `wan3`.

---

## 4. Pre-Shipment Invariants & Hardening for Remote Routers

Before packaging and shipping any configured router to a remote satellite location:

1. **Remote Access Tunnel Pre-requisite (NON-NEGOTIABLE):**
   * **Never ship a router without a pre-configured reverse VPN tunnel (WireGuard client or Tailscale) dialing back to the main controller/MikroTik.**
   * Once installed behind an ISP modem at the remote site without port forwarding or public DDNS, the router is completely inaccessible from the outside. Remote re-configuration would otherwise require on-site personnel with a laptop and TeamViewer.
   * Tailscale: install `tailscale` and `tailscaled` ipk (OpenWrt 21.02, ~9MB total). Open inbound firewall in `/etc/firewall.user`:
     ```bash
     iptables -I INPUT -i tailscale0 -j ACCEPT
     ```
     Enable service on boot: `/etc/init.d/tailscale enable`.

2. **CRITICAL TAILSCALE INVARIANT — KEY EXPIRY DISABLEMENT:**
   * **The 180-Day Trap:** Tailscale node keys expire after 180 days (6 months) by default! When expired, the node drops offline and demands interactive web browser re-authentication, permanently stranding the satellite device.
   * **Remediation:** In Tailscale Admin Console (`console.tailscale.com/admin/machines`), locate the device row $\rightarrow$ click action menu `...` $\rightarrow$ select **Disable key expiry**.
   * **Evidence Gate:** Verify machine detail page displays status badge `Expiry disabled` and `Key expiry: No expiry`.

3. **NTP Time Synchronization (No Hardware RTC):**
   * Router SoCs (MT7621A) have NO battery-backed hardware RTC. If system time boots with an incorrect date (e.g. year 1970 or 2021), TLS handshakes fail and Tailscale cannot connect to control servers.
   * Ensure `/etc/config/system` contains international reliable NTP pools:
     ```bash
     uci add_list system.ntp.server='time.cloudflare.com'
     uci add_list system.ntp.server='time.google.com'
     uci add_list system.ntp.server='pool.ntp.org'
     uci commit system
     ```

4. **Service & Routing Hygiene (Anti-Flapping & Security):**
   * **Disable Unneeded Daemons:** Disable web file managers or scrapers (e.g. `alist`), and remove unnecessary open WAN ports (e.g. 5244, 1194) in `/etc/config/firewall`.
   * **Disable Multi-WAN Balancer (`mwan3`):** When running clean primary/secondary PPPoE with gateway metrics (metric 10 vs metric 20), disable `mwan3` and `mwan3helper` to allow pure kernel metric failover without tracking jitter.
   * **Disable Blind Watchcat:** Turn off `watchcat` reboot ping rules that may cause repetitive reboot loops while the device sits uninstalled prior to fiber turn-up.

5. **Pre-Shipment Configuration Backup:**
   * Generate a full sysupgrade backup archive and copy it off-router:
     ```bash
     sysupgrade -b /tmp/pre-ship-backup.tar.gz
     ```
   * Download to local engineering machine before boxing the hardware.

6. **Persistent Storage Verification:**
   * Run `uci changes`. If non-empty, run `uci commit`.
   * Uncommitted changes reside in volatile `/tmp/.uci/` and are wiped upon power disconnection.

7. **Physical Action Protocol:**
   * Only instruct the user to unplug power/cables when all read-back tests pass and `uci changes` is verified empty.
