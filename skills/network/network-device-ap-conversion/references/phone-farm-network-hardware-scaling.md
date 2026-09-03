# Phone Farm Network Architecture, Aruba RF Tuning & 1000-Device Scaling

Practical engineering guide for high-density Android Phone Farm (Samsung Galaxy S7/Note 8) networking, RF tuning on Aruba Instant APs (315/325), and scaling from USB to LAN architecture up to 1,000 devices.

---

## 1. High-Density Static RF Tuning (Aruba Instant AP-315 / AP-325)

In a static phone farm (e.g. 160 phones on a single metal rack), standard enterprise roaming / auto-steering fails:
- **Sticky Client & Load Imbalance:** With a single SSID + auto-roaming, phones pile up on one AP (observed 65 phones on AP1 vs 13 on AP2). S7 devices do not re-balance dynamically.
- **2.4GHz Trap:** Phones drop to 2.4GHz on minor RSSI dips. 2.4GHz collapses under 20+ concurrent active video/data streams.

### Optimal Farm RF Configuration:
1. **5GHz Only (Mandatory):**
   - Disable 2.4GHz radio completely on all APs (or set SSID to `5 GHz Only`).
2. **Channel Width:**
   - Lock strictly to **20 MHz** (never 40 MHz or 80 MHz in dense RF spaces).
3. **Manual Static Channels (No Auto-Channel / ARM Flapping):**
   - AP 1 (325): Channel **36** (5180 MHz)
   - AP 2 (325): Channel **149** (5745 MHz)
   - AP 3 (315): Channel **44** (5220 MHz)
   - AP 4 (315): Channel **157** (5785 MHz)
4. **Transmit Power (TX Power):**
   - Mounted directly on/near the rack (<1m): **3 dBm – 6 dBm**.
   - Mounted 1.5m – 3m away facing rack: **9 dBm – 12 dBm** (target RSSI: -50 dBm to -58 dBm).
5. **Hard Partitioning via Dedicated SSIDs:**
   - Create 4 distinct SSIDs: `FARM_01` (AP1), `FARM_02` (AP2), `FARM_03` (AP3), `FARM_04` (AP4).
   - Assign exactly 40 phones per SSID. Devices only remember their assigned SSID to eliminate roaming and guarantee a 40/AP split.

---

## 2. Hardware Architecture for Scaling (160 → 1,000 Phones)

### Limitations of USB & Wi-Fi:
- **USB Controller Limit:** xHCI endpoint exhaustion causes ADB driver crashes when exceeding ~150–200 USB devices per PC.
- **Airspace Saturation:** Adding more APs in one room causes co-channel interference regardless of tuning.

### The 1,000-Device Hybrid Architecture (Keep Existing USB, Expand via LAN):

```text
                           [Main Router / Gateway]
                                     │
                     ┌───────────────┴───────────────┐
                     │     10G Core Switch (SFP+)    │ (MikroTik CRS305 / 4-8x 10G)
                     └───────┬───────┬───────┬───────┘
          (10G SFP+/DAC)     │       │       │      (10G SFP+/DAC Uplink)
       ┌─────────────────────┘       │       └─────────────────────┐
       ▼                             ▼                             ▼
 ┌───────────┐                 ┌───────────┐                 ┌───────────┐
 │ SERVER 1  │                 │ SERVER 2  │                 │ ACCESS    │ (24/48-port 1G Switch
 │ Dual Xeon │                 │ Dual Xeon │                 │ SWITCH    │  w/ 10G SFP+ Uplink)
 │(10G PCIe) │                 │(10G PCIe) │                 └─────┬─────┘
 └─────┬─────┘                 └─────┬─────┘                       │ (42x 0.5m-1m Cat6 RJ45 cables)
       │ (USB Cords)                 │ (USB Cords)          ┌──────┴──────┐
       ▼                             ▼                      ▼             ▼
 [80 Phone USB]               [80 Phone USB]           [Box LAN 1]   [Box LAN 42]
 (4x 20-box)                  (4x 20-box)              (20 main/box) (20 main/box)
 (Wi-Fi via 4x Aruba)         (Wi-Fi via 4x Aruba)     (Total: 840 phones over LAN)
```

### Allocation & Redundancy Strategy:
- **50/50 Dual Server Split:**
  - **Server 1:** 80 USB phones (ID 1–80) + 420 LAN phones (ID 161–580).
  - **Server 2:** 80 USB phones (ID 81–160) + 420 LAN phones (ID 581–1000).
  - *Why not 1 server for all LAN?* Prevents single point of failure (reboot/crash won't stop 840 phones) and balances video rendering/FFmpeg disk I/O.
- **Switch Bill of Materials:**
  1. `1x` 10G Core Switch (4–8x SFP+ 10G) ~2.5m VNĐ.
  2. `2x` 10G PCIe NICs (Mellanox ConnectX-3 MCX311A / Intel X520) ~1m VNĐ.
  3. `1x` 48-Port (or `2x` 24-Port) Gigabit Switch with 2–4x 10G SFP+ Uplinks ~2m VNĐ.
  4. `4x` 10G DAC / Fiber patch cables ~500k VNĐ.
  5. `45x` Cat6 short patch cables (0.5m – 1m) ~800k VNĐ.

---

## 3. Box Phone Hardware Forms & Market Pricing

### Standard Phone Farm Form Factor (20 Motherboards / Box):
- **Form:** Horizontal metal/mica chassis with 3x front 80/90mm cooling fans blowing horizontally across 20 vertically mounted bare motherboards (no screens, no batteries).
- **Control Board:** 20-port Hub PCB with centralized 5V 40A–60A power supply and Type-B (USB) or RJ45 (LAN via integrated USB-Ethernet controllers) output.

### Price Comparison (20-Port Box Chassis + PCB + PSU + Fans, excl. phones):
| Source | USB Box Price | LAN Box Price | Notes |
| :--- | :--- | :--- | :--- |
| **Vietnam FB Secondhand / DIY** | 300.000đ – 500.000đ | 700.000đ – 900.000đ | Scrap PSU, laser-cut mica, DIY assembly. Lowest cost for small batches. |
| **China 1688 Direct (New 100%)** | 950.000đ – 1.250.000đ | 1.400.000đ – 1.800.000đ | Industrial steel chassis, new PCB/PSU, factory fresh. Best for 20+ box orders. |
| **Vietnam Commercial Retail** | 1.200.000đ – 1.500.000đ | 1.650.000đ – 1.990.000đ | Packaged retail with markup. |

---

## 4. Power & Thermal Management (1,000 Devices)
- **Continuous Thermal Output:** ~5.5 kW (~4kW phones, 800W servers, 500W PSU dissipation, 200W networking).
- **Cooling Requirement:**
  - *Option A (Sealed Room):* 2x 2HP (18,000 BTU) Inverter Air Conditioners running in rotation, maintaining 26°C – 28°C.
  - *Option B (Exhaust Flow):* 2–3x 40–50cm industrial exhaust fans pulling air directly from behind racks out of the building with filtered intake.
