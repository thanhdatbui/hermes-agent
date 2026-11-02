---
name: high-density-farm-wifi-planning
description: High-density WiFi RF planning, physical layout, AP placement, and cabling for large Android phone farms (160+ devices, multi-tier metal racks, Aruba Instant IAP, PoE cabling).
tags: [wifi, rf-planning, aruba, high-density, phone-farm, poe, cabling]
---
# High-Density WiFi RF Planning for Android Phone Farms

Use this skill when designing, expanding, troubleshooting, or physically laying out WiFi infrastructure for high-density phone farms (e.g. 80–160+ Android devices on metal racks running automation tools).

---

## 1. Physical Placement & RF Architecture (Cross-Illumination)

### The Faraday / Metal Shadowing Problem
* Multi-tier metal racks containing dozens of closely packed smartphones create severe RF shadowing and local Faraday-cage effects (10–20 dB attenuation between tiers).
* **Never place all APs on one side or clustered in one zone.** Clustering APs within <1.5m in the same corner creates severe near-field RF saturation and receiver desensitization.

### Canonical Layout Rules
1. **Cross-Illumination & 3D Diagonal Separation:**
   * **Rack Placement (2x APs on metal rack):** Place APs diagonally opposite across the rack frame (e.g. **Top-Left corner** for upper tiers and **Bottom-Right corner** for lower tiers). This maximizes 3D physical separation ($\sqrt{H^2 + W^2}$), prevents vertical near-field RF coupling, and balances left-to-right horizontal coverage across wide phone trays. Avoid vertical collinear stacking directly above/below each other on the same side.
   * Place at least 1 AP on the **opposite wall / far corner (Line-of-Sight, 2.5m–3m)** aiming directly at the front of the rack.
   * Place remaining APs at cross-angles (e.g. adjacent furniture/wall) to illuminate side angles.
* **Antenna Orientation & Rack Surface Resting:**
  * Aruba APs (AP-325, AP-315) use hemispherical internal antennas radiating outwards from the plastic front dome (Aruba logo).
  * **Top rack mount:** Must point **face DOWN** into the phone trays. Resting the plastic front dome directly face-down on open metal wire mesh shelves is acceptable and highly effective: the open mesh allows 5GHz RF penetration while the rear aluminum heatsink faces upward into ambient air for passive convective cooling.
  * **Bottom rack mount:** Point **face UP** or tilted 45° inward toward bottom phone trays.
  * **Wall/Pole mount:** Must point **face forward** directly at the target phone racks.
  * Do not rely on loose hooks; secure APs with zip ties (cable ties) through the mounting bracket onto metal bars.
3. **Sleeping Space Separation:**
   * Keep high-power APs away from direct head-level sleeping areas. Use far room corners (e.g. entrance door / clothes rack / far foot of bed) for room-spanning cross-illumination.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
