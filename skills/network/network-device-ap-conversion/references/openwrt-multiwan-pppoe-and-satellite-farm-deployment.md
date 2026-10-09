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

## 2. Converting LAN Port to WAN2 (Dual-WAN Setup)

### The Problem
ISP fiber lines in regional branches (e.g. VNPT / Viettel Thai Binh) frequently enforce a hard cap of 8 concurrent PPPoE sessions per physical fiber line. To supply 16 concurrent public IPs for an 80-device farm, 2 separate physical fiber lines (2 ONT modems in bridge mode) must be connected to the router.

A 3-port router has only 1 dedicated WAN port. The secondary LAN port (`lan2`) must be detached from the local bridge and converted into `wan2`.

### UCI Configuration Sequence
```bash
# 1. Remove lan2 from br-lan bridge
uci del_list network.@device[0].ports='lan2'

# 2. Create wan2 interface bound directly to lan2 physical device
uci set network.wan2=interface
uci set network.wan2.device='lan2'
uci set network.wan2.proto='dhcp'  # Or 'pppoe' if dialing directly

# 3. Add wan2 to firewall zone 'wan' for NAT Masquerade and forwarding
uci add_list firewall.@zone[1].network='wan2'

# 4. Commit to flash persistent storage
uci commit network
uci commit firewall

# 5. Reload subsystems
/etc/init.d/firewall reload
/etc/init.d/network reload
```

### Read-Back Validation
```bash
# Verify no pending uncommitted changes
uci changes

# Verify bridge configuration
cat /etc/config/network | grep -A 5 'config device'
# Expected: list ports 'lan1' only

# Verify firewall zone
cat /etc/config/firewall | grep -A 6 "option name 'wan'"
# Expected: list network 'wan', 'wan6', 'wan2'

# Verify interface state in netifd
ubus call network.interface.wan2 status
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

## 4. Pre-Shipment Invariants for Remote Routers

Before packaging and shipping any configured router to a remote satellite location:

1. **Remote Access Tunnel Pre-requisite (NON-NEGOTIABLE):**
   * **Never ship a router without a pre-configured reverse VPN tunnel (WireGuard client or Tailscale) dialing back to the main controller/MikroTik.**
   * Once installed behind an ISP modem at the remote site without port forwarding or public DDNS, the router is completely inaccessible from the outside. Remote re-configuration would otherwise require on-site personnel with a laptop and TeamViewer.
   * WireGuard client must have `persistent-keepalive = 25` and autostart enabled so that the tunnel establishes immediately upon receiving an Internet connection.

2. **Persistent Storage Verification:**
   * Run `uci changes`. If non-empty, run `uci commit`.
   * Uncommitted changes reside in volatile `/tmp/.uci/` and are wiped upon power disconnection.

3. **Physical Action Protocol:**
   * Only instruct the user to unplug power/cables when all read-back tests pass and `uci changes` is verified empty.
