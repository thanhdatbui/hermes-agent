# Phone Farm Wi-Fi (Aruba) Tuning & High-Density LAN Scaling Architecture

Knowledge bank and operational rules for deploying, tuning, and scaling network infrastructure for Android phone farms (80 to 1000+ devices).

---

## 1. High-Density Wi-Fi Architecture (Aruba IAP Cluster for 80–160 Phones)

### The "Enterprise Band Steering" Trap on Static Farms
- Enterprise default (`Prefer 5 GHz` + single SSID + `ClientMatch`) is designed for roaming office users.
- On a static metal farm rack, S7/Android phones experience signal bounce and will randomly fallback to 2.4 GHz.
- 2.4 GHz channel saturation (max 3 non-overlapping channels: 1, 6, 11) leads to massive packet loss, latency spikes, and ADB/ATX automation timeouts.
- ClientMatch fails to load-balance static phones evenly (observed real-world skew: 65 clients on AP1 vs 13 clients on AP2).

### Canonical Farm RF & SSID Rules (4x APs: 2x AP-325 + 2x AP-315 for 160 S7s)
1. **Disable 2.4 GHz completely:** Set SSID / Radio to `5 GHz only`.
2. **Channel Width:** Lock to **20 MHz** (never 40/80 MHz to prevent channel overlap).
3. **Static Non-Overlapping 5 GHz Channels:**
   - AP 1 (IAP-325): Channel **36** (UNII-1)
   - AP 2 (IAP-325): Channel **149** (UNII-3)
   - AP 3 (IAP-315): Channel **44** (UNII-1)
   - AP 4 (IAP-315): Channel **157** (UNII-3)
4. **Transmit (TX) Power:**
   - APs mounted 1.5m–3m away from rack: **9 dBm – 12 dBm**.
   - APs placed directly on rack: **3 dBm – 6 dBm** (prevents receiver overload/blinding).
5. **Enforce 40 Phones / AP via Split SSIDs:**
   - Create 4 SSIDs (`FARM_01` to `FARM_04`) mapped to specific AP zones/radios.
   - Phones 1–40 connect to `FARM_01`, 41–80 to `FARM_02`, 81–120 to `FARM_03`, 121–160 to `FARM_04`.
   - Each phone forgets all other SSIDs to guarantee 100% fixed 40-device load per AP.

---

## 2. Scaling Architecture: 160 → 500 – 1000 Phones (USB vs LAN Box)

### Physical & Controller Limits of USB
- xHCI controllers limit endpoints to 64–128 per controller (1 phone consumes 4–6 endpoints).
- Beyond 150–200 phones per PC via USB, ADB daemon crashes, I/O bottlenecks, and OS USB driver instability occur.

### "Legacy USB Preserved + New Batches LAN" Strategy
- **Existing 160 Phones (ID 1–160):** Keep on USB boxes + 4 Aruba APs (no hardware disposal/loss).
- **New Batches (ID 161–1000+):** Purchase **LAN Box Phones only** (20 phones/box, built-in USB-to-ETH chip + internal switch, 1 external RJ45 port).

### 2-Tier Switching Topology for 1000 Phones
```text
                         [Main Router / Gateway]
                                    │
                    ┌───────────────┴───────────────┐
                    │     10G Core Switch (SFP+)    │ (MikroTik CRS305 / TP-Link 10G)
                    └───────┬───────┬───────┬───────┘
          (10G DAC/Fiber)   │       │       │   (10G DAC/Fiber Uplink)
       ┌────────────────────┘       │       └────────────────────┐
       ▼                            ▼                            ▼
 ┌──────────┐                 ┌──────────┐                 ┌──────────┐
 │ Server 1 │                 │ Server 2 │                 │ Access   │ (24/48-port 1G Switch
 │(Dual Xeon│                 │(Dual Xeon│                 │ Switch   │  w/ 2-4x 10G SFP+ Uplinks)
 │ +10G NIC)│                 │ +10G NIC)│                 └────┬─────┘
 └──────────┘                 └──────────┘                      │ (42x 0.5-1m Cat6 RJ45 patch cords)
                                              ┌─────────────────┼─────────────────┐
                                              ▼                 ▼                 ▼
                                         [LAN Box 1]       [LAN Box 2]       [LAN Box 42]
                                         (20 phones)       (20 phones)       (20 phones)
```

### Server & Workload Distribution (Dual Xeon 50/50 Split)
- **Avoid Single Point of Failure:** Split total fleet 50/50 across 2 Dual Xeon servers:
  - **Server 1:** 80 USB phones (1–80) + 420 LAN phones (161–580) = 500 phones.
  - **Server 2:** 80 USB phones (81–160) + 420 LAN phones (581–1000) = 500 phones.
- **Control Mechanism:** ATX-agent HTTP API (`http://<device_ip>:7912`) / ADB over TCP (`adb connect <ip>:5555`).
- **Bot Operations:** 2 independent Hermes bot instances (or 1 Telegram Group with Topics per server).

---

## 3. Power, Heat & Infrastructure Checklist

- **Thermal Load:** 1000 phones + 2 Dual Xeon PCs + 42 power supplies produce ~5.5 kW continuous heat.
- **Cooling Requirement:**
  - Option A: 2x 2HP (18,000 BTU) Inverter Air Conditioners running alternating 12h shifts at 26°C–28°C.
  - Option B: Industrial exhaust ventilation (2-3x 40-50cm extraction fans + filtered air intake).
- **Electrical Circuitry:** Dedicated 32A breakers and separate AC lines for PC servers vs phone box power supplies to prevent voltage drop.
