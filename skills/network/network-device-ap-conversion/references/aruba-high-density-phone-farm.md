# Aruba Instant AP Configuration for High-Density Static Phone Farm

Field-tested RF optimization and infrastructure scaling guidelines for operating 80–160+ Android devices (e.g., Samsung Galaxy S7 / Note 8) on a compact rack using Aruba Instant APs (IAP-315 / IAP-325), and scaling roadmap to 500–1,000 devices.

---

## 1. High-Density Static Phone Farm RF Pitfalls

Enterprise Wi-Fi features (ClientMatch, Band Steering, ARM Auto Channel) are designed for mobile users in office environments. In static phone farms, they frequently cause severe operational issues:

1. **Load Imbalance (Sticky Clients):**
   - Phones do not move. If one AP reboots or drops briefly, clients roam to the remaining AP and **never balance back**.
   - Observed real-world failure: AP1 taking 65 clients while AP2 takes only 13 clients on the same rack.
2. **2.4GHz Drop Trap:**
   - Under minor signal fluctuations, Android devices fall back to 2.4GHz.
   - 2.4GHz has only 3 non-overlapping channels (1, 6, 11). Once >15–20 devices actively stream/download video, airtime collapses, causing packet drops and automation script timeouts.
3. **ARM Channel Flapping:**
   - With auto-channel enabled, close-proximity APs interpret neighboring APs as interference and frequently change channels, dropping connected phones for 2–5 seconds per hop.
4. **Receiver Overload (De-sensing):**
   - Placing high-power APs directly touching the metal rack/phones blinds the receivers.

---

## 2. Proven RF & System Tuning Parameters

### A. Radio & Channel Setup
- **Band:** Disable 2.4GHz entirely (`5 GHz only` or `Force 5 GHz`).
- **Channel Width:** Lock strictly to **20 MHz** (never 40 MHz or 80 MHz in dense multi-AP environments).
- **Channel Assignment:** Manually assign fixed non-overlapping channels:
  - AP 1 (325 #1): Channel **36** (UNII-1)
  - AP 2 (325 #2): Channel **149** (UNII-3)
  - AP 3 (315 #1): Channel **44** (UNII-1)
  - AP 4 (315 #2): Channel **157** (UNII-3)
- **Airtime Fairness:** Enable `Fair Access`.

### B. Transmit (TX) Power Sizing & Physical Distance Rules
- **Physical Standoff / Separation:**
  - Minimum distance between any two APs: **1.2m – 1.5m** (safe in small rooms/compact setups; ideal is 1.5m - 2m).
  - Do NOT place APs < 1m next to each other to avoid receiver desensitization.
  - Alternating frequency band pairing: Place high-band UNII-3 APs (Ch 149/157) next to low-band UNII-1 APs (Ch 36/44) to maximize isolation.
- **Mounted on/inside the phone rack (< 1m):**
  - Set TX Power to **Min 3 dBm / Max 6 dBm** (lowest tier). Prevents signal saturation while maintaining -40 to -50 dBm RSSI on phones.
- **Standoff positioning (Trellis / Wall / Ceiling / Desk / Cabinet 1.2m – 3m away):**
  - Set TX Power to **Min 9 dBm / Max 12 dBm** (target RSSI: -50 dBm to -58 dBm).

---

## 3. SSID & Client Partition Strategies

| Strategy | Setup | Pros & Cons |
| :--- | :--- | :--- |
| **Strategy A: Single Cluster SSID** *(Convenience)* | 1 SSID across all APs, `Force 5 GHz` enabled, ClientMatch enabled. | **Pros:** Easy initial Wi-Fi setup on devices.<br>**Cons:** Prone to client distribution skew (e.g. 65 vs 13). Must monitor distribution regularly. |
| **Strategy B: Dedicated SSIDs per AP** *(Recommended for High Density)* | 4 SSIDs (`FARM_01` to `04`), each assigned to a specific physical AP. 40 phones per AP strictly provisioned. | **Pros:** 100% deterministic load isolation (exactly 40 devices/AP). No roaming flapping.<br>**Cons:** Requires setting specific Wi-Fi SSIDs per batch of phones. |

---

## 4. Workstation Host & Network Architecture

- **Host Hardware for 24/7 ADB / Automation:**
  - Prefer OEM Workstations (e.g. Dell Precision T5810, HP Z440) with ECC RAM and 80 Plus certified PSUs.
  - Avoid cheap/recycled Chinese X99 motherboards for continuous 24/7 multi-device USB loads due to poor VRM power delivery and high failure rates.
- **Network Topology:**
  - Connect APs directly to a Central Gigabit/PoE Switch or separate LAN ports on the main router (Star Topology).
  - Avoid daisy-chaining multiple 5-port switches in series to eliminate backhaul bottlenecks.
- **Server Load Profile:**
  - Script-only background automation (ADB TCP / ATX-agent XML inspection) consumes minimal CPU/RAM (~20–50MB RAM/device). A dual Xeon host can handle 500–1000 headless automation clients.
  - Avoid concurrent full-fleet screen streaming (`scrcpy` live view), which causes severe GPU/CPU decoding exhaustion.

---

## 5. Scaling Roadmap: 160 Devices (Current) → 500–1,000 Devices (Target)

When expanding past 160 devices, Wi-Fi and USB cabling reach physical limits (endpoint exhaustion, RF saturation). Transition to cabled Box Phone LAN architecture:

| Infrastructure Component | 160 Devices (Current Cụm USB/Wi-Fi) | 500–1,000 Devices (Cụm LAN Mở Rộng) |
|---|---|---|
| **Box Phone Units** | 8x Box USB (20 phones/box, Type-B USB to PC) | 42x Box LAN (20 phones/box, internal USB-LAN switch + RJ45 port) |
| **Network Uplink** | 4x Aruba APs (5GHz only, 40 phones/AP) | Cabled Cat6 (0.5m–1m patch cords from Box LAN to Access Switch) |
| **Server Topology** | 2x Dual Xeon Servers (1 PC / 80 phones USB) | 2x Dual Xeon Servers (500 phones/Server: 80 USB + 420 LAN) |
| **Core Switch** | Main Router LAN / Gigabit Switch | 1x 10G SFP+ Core Switch (e.g., MikroTik CRS305) connecting Servers |
| **Access Switch** | N/A | 1x 48-port (or 2x 24-port) Gigabit Switch with 10G SFP+ Uplinks |
| **Thermal / Cooling** | 1.5 HP AC or ambient room airflow | 2x 2 HP (18,000 BTU) Inverter AC running 24/7 (~5.5kW heat load) |
| **Control Mechanism** | ADB over USB (`adb -s <serial>`) | ATX-agent HTTP API (`:7912`) / ADB over TCP (`adb connect <ip>`) |
