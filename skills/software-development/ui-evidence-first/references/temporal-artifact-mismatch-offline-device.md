# Temporal Artifact Mismatch & Offline Device Diagnostics

## 1. Problem Statement & User Trigger
User queries like:
- *"Có hình mà sao ghi device offline?"*
- *"Sao chụp được ảnh mà lại báo adb/usb disconnected?"*
- Showing an alert or image with a banner stamp `[MAY <N>] - HH:MM:SS DD/MM` alongside an error:
  `device is offline or ADB/USB disconnected for <serial>: device offline or ADB/USB disconnected: adb.exe: device '<serial>' not found`

## 2. Root Cause: Temporal Artifact Mismatch
This confusion arises from a **temporal disconnect** between an earlier successful run and a later failing run:
1. **Earlier Session ($t_{banner}$):** The device was online and functional. A run (e.g., Row 1 canary or regular session) succeeded, and a verified banner artifact (e.g. `m<N>_verified_banner.png`) was rendered and saved with the timestamp stamped on the banner.
2. **Intermediate Event:** Sometime after $t_{banner}$, the device lost connection (loose USB cable, powered-off USB hub port, depleted battery, or hardware crash).
3. **Later Session ($t_{fail}$):** A subsequent run (e.g., Row 2 scheduled batch) started. The runner failed immediately at preflight (`adb.exe: device '<serial>' not found`).
4. **Alert/UI Presentation:** The alert or operator channel surfaced the latest known screenshot/banner artifact from the previous run, misleading the user into thinking the script took a photo and simultaneously claimed the device was offline.

## 3. Investigation Protocol (Turn-1 Verification)
1. **Extract Banner Timestamp ($t_{banner}$):**
   - Read the exact text stamped on the red banner header: `[MAY <N>] - HH:MM:SS DD/MM`.
   - Check the creation/modification time of `D:\Taadaa\m<N>_verified_banner.png`.

2. **Extract Incident Timestamp ($t_{fail}$):**
   - Read `summary.txt` and `log.jsonl` under `runtime/.../machines/machine_<N>/<run_id>/`:
     - `start_time` / `end_time`
     - `stop_reason` / `reason`
     - `cohort_id` / `account_row` (identifies which row was running when it failed).

3. **Check Account Identity Discrepancy:**
   - Look up the account shown in the banner screenshot (e.g., username on screen).
   - Check `taikhoan_run_safe.xlsx` or `taikhoan_dat_v2_updated .xlsx` for Machine `<N>`.
   - If the banner shows Row 1 account (`@userA`) but the failure log is for Row 2 (`@userB`), this confirms beyond doubt that the image is from the earlier Row 1 session.

4. **Verify Current Physical / ADB State:**
   - Run `adb devices`.
   - Check if `<serial>` appears in the device list.
   - If missing from `adb devices`:
     - It is a **physical layer / hardware disconnection** (cáp lỏng, hub USB, nguồn máy), not a script bug or ADB daemon hang.
   - If `<serial>` is present with status `offline`:
     - Transient ADB transport hang; needs ADB server restart (`adb kill-server && adb start-server`).

5. **Reporting to User:**
   - State clearly: The image is from the **earlier session** at $t_{banner}$ (Row X), whereas the failure occurred at $t_{fail}$ (Row Y) — hours apart.
   - Clarify that the device disconnected *between* the two sessions.
   - Conclude whether it is physical hardware (cable/hub/battery) or ADB transport.
