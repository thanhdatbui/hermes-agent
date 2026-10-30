# SSOT Proxy Identity Presentation & Remote Proxy Routing Invariants

## 1. Problem & User Correction
- **Confusion Encountered:** Displaying the intermediate bridge/hop (e.g. `192.168.110.2:202xx` or Sing-box internal listener) in SSOT records (`PROXYgandienthoai.xlsx`), master databases (`farm_master.db`), and Web Ledger UI (`kibe:1905`).
- **User Correction:** In SSOT databases, spreadsheets, and Web UI dashboards, the proxy column MUST ALWAYS display the **canonical destination identity** of the proxy assigned to that machine (e.g., `tb.taadaa.click:5141`, `test.taadaa.click:5101:mobi1:...`). It must NOT show raw internal hops or sing-box translation ports.

## 2. Distinction: SSOT Identity vs. Mechanical L3/L4 Hop
1. **SSOT Identity (User-facing & Multi-app integration):**
   - Represents the true exit IP origin (e.g. `tb.taadaa.click:51xx` for Thai Binh Viettel line; `test.taadaa.click:51xx` for MobiProxy).
   - Used by GPM browser profiles when warming Hotmail/Gmail accounts matching S7 phones: GPM profiles run on PC must know the true proxy endpoint to bind the browser profile to the exact same exit IP / Geo-location as the phone.
   - Displayed in `farm_master.db.machines.proxy_endpoint`, `PROXYgandienthoai.xlsx`, and `http://kibe:1905`.

2. **Mechanical Routing Hop (Device-level execution):**
   - Android S7 phones lack built-in proxy auth support and risk leaking farm IP if remote connections drop.
   - Therefore, devices connect via local Wi-Fi to MikroTik Sing-box container (`192.168.110.2:202xx`) or direct LAN listener.
   - Sing-box enforces fail-closed kill-switch and forwards via Windows PortProxy / Tailscale to the destination.
   - The runner script (`set_proxy_farm_admin_adb.py` or watchdog) translates the SSOT target (`tb.taadaa.click:51xx`) into the local forwarder port (`192.168.110.2:202xx`) when issuing `settings put global http_proxy`.

## 3. ISP Carrier Concurrent Session Ceiling (Viettel FTTH)
- **Hard ISP Limit on PPPoE Concurrent Sessions:**
  - Standard FTTH Viettel line caps public IP PPPoE sessions (e.g. exactly 35 concurrent sessions on Da Nang line, 8 sessions per line on Thai Binh R3G).
  - Attempting to dial beyond the ISP ceiling (e.g. session #36 on Da Nang MikroTik) triggers CGNAT fallback (e.g. `172.22.x.x` private subnet) where packets are dropped or fail internet routing.
  - **Rule:** Never keep interfaces enabled beyond the known verified public pool limit. Extra declared interfaces must remain `disabled=true`.
