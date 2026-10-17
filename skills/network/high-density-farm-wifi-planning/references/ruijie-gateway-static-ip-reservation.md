# Ruijie Reyee Gateway & Aruba AP Static IP Mapping

## 1. Ruijie EW3200GX-PRO Admin Architecture
* **Default IP / Gateway:** `192.168.110.1` (Port 80/443).
* **Web Interface:** ReyeeOS / LuCI eWeb (`/cgi-bin/luci`).
* **Static IP Reservation Path:**
  * WebUI Navigation: `Khác` ➔ `LAN` ➔ Tab `Địa chỉ IP tĩnh` (`/admin/alone/network/network_lan`).
  * Add Modal: Popup Element UI dialog có 2 trường:
    * IP Address: `placeholder="Ví dụ: 1.1.1.1"`
    * MAC Address: `placeholder="Ví dụ: 00:11:22:33:44:55"`

## 2. 4-AP Dual-Tier Static IP Architecture
To prevent DHCP collision, IP pool overlap, and rogue lease timeouts on the phone farm, all 4 Aruba Access Points must be anchored on both tiers:
1. **Tier 1 (AP Hardware Flash / ap-env):** Configured directly on Aruba Instant OS via `ap-env` (`ipaddr`, `netmask`, `gatewayip`, `dnsip`, `iap_zone`).
2. **Tier 2 (Gateway DHCP Reservation):** Bound in Ruijie `Địa chỉ IP tĩnh` table to reserve the IP and guarantee no other dynamic client is assigned an AP IP.

| AP Unit | Model | Farm Zone | Target SSID | MAC Address | Static IP | Flash `ap-env` | Ruijie Reservation |
|---|---|---|---|---|---|---|---|
| **AP 4** | AP-315 | `zone4` | `admin 2` (5GHz) | `20:a6:c0:c6:6d:1a` | `192.168.110.250` | `ipaddr: 192.168.110.250` | Bound |
| **AP 1** | AP-315 | `zone3` | `admin 1` (5GHz) | `20:a6:c0:c7:6b:58` | `192.168.110.251` | `ipaddr: 192.168.110.251` | Bound (Master VC) |
| **AP 2** | AP-325 | `zone2` | `kibe 2` (5GHz) | `34:fc:b9:cf:5a:bc` | `192.168.110.252` | DHCP via Ruijie | Bound |
| **AP 3** | AP-325 | `zone1` | `kibe 1` (5GHz) | `b0:b8:67:cd:bf:8a` | `192.168.110.253` | DHCP via Ruijie | Bound |

## 3. Pitfalls & Invariants
* **DHCP Pool Exhaustion & 120-Min Lease Trap:**
  * Ruijie EW3200GX-PRO defaults to a 120-minute lease time. In high-churn phone farm environments (reboots, auto-healer radio cycles), stale dynamic leases exhaust the 254-IP pool.
  * When the pool hits 250+ allocated entries, newly joined phones (like M7) obtain an IP temporarily, then fail ARP/ACK or lose the lease within minutes.
  * **Remediation:** Lower `Lease Time(Min)` to `30` in `Basics` ➔ `LAN` ➔ `LAN Settings`. Flush stale/failed ARP table entries on the upstream L2 switch/MikroTik.
* **Troubleshooting Escalation Order (Gateway First, RF After):**
  * When user directs "xử lý ở rujie trc đã xem đỡ k r ms xử lý aruba tính sau", prioritize verifying and stabilizing Layer 3 IP assignment / DHCP reservation / ARP clean-up before adjusting physical AP RF, transmit power, or antenna orientation.
* **Local Wi-Fi IP (Ruijie DHCP) vs Global HTTP Proxy Independence:**
  * Setting a static IP reservation on Ruijie (`Basics` ➔ `LAN` ➔ `Static IP Addresses`, e.g. `192.168.110.124` for M7) only anchors the Layer 3 interface IP on `wlan0`.
  * It is completely decoupled from the Android Global HTTP Proxy (`settings put global http_proxy 192.168.110.2:2000N`).
  * Assigning a static IP does NOT alter or break device proxy functionality or proxy egress IP; on the contrary, it eliminates DHCP renewal stalls and stabilizes the TCP transport route to the local proxy host (`192.168.110.2`).
  * When operators ask whether static IP assignment breaks proxy: confirm that local IP and proxy port are separate network layers, and verify proxy socket liveness across ports (`20001..20080` and `10008..10035`) and outbound public IP immediately.
* **AP-315 vs AP-325 Hardware IP Behavior:**
  * AP-315 units often have `ipaddr` hard-stored in `ap-env`, causing them to come up on static IP immediately without waiting for DHCP. If Ruijie has not registered these MACs in the Static IP table, dynamic DHCP pool leases could clash if the pool reaches high octets (`.250`+).
  * Always bind all 4 AP MACs into Ruijie's `Địa chỉ IP tĩnh` table.
* **SSID Multi-Zone Spillover (The "Dat" Trap):**
  * If a utility or guest SSID (e.g. `Dat`) is configured with `zone zone1,zone2,zone3,zone4` and `rf-band all`, it will be broadcast by all 4 APs simultaneously on both 2.4GHz and 5GHz.
  * For phone farm stability, farm phones (Samsung S7) must only have profiles for their assigned rack SSID (`kibe 1`, `kibe 2`, `admin 1`, `admin 2`). Never configure the utility SSID `Dat` on farm phones to avoid rogue client roaming.
