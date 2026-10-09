# Android Device Emergency Power Off Pattern

## Problem
- Farm operators frequently wonder if toggling the hardware power switch on multi-port phone farm boxes differs from physically unplugging the power cord.
- **Hardware Fact**: Box switches are pure physical cuts to the PSU rail (12V/5V). Mainboards lack battery/ACPI shutdown circuits, so cutting box power drops Android instantly mid-write.
- Consecutive hard power cuts during active automation (feed, login, reg) lead to:
  1. eMMC/UFS flash block corruption (especially fragile Samsung Galaxy S7 / Note 5).
  2. Bootloop / `/data` partition corruption.
  3. Corrupted SQLite databases (Chrome cookies, TikTok account state).

## Solution: 1-Click Multi-Device Soft Shutdown
Instead of expecting the operator to type lengthy commands during power emergencies while UPS is beeping:
1. Provide a synchronized, zero-friction 1-click batch script located in shared storage (`D:\OneDrive\TAT_FARM_KHAN_CAP.bat`) and desktop shortcut.
2. The launcher calls a multithreaded Python script (`ThreadPoolExecutor`) that discovers ADB devices and dispatches parallel `adb -s <serial> shell reboot -p` with a short timeout (~5-8s).
3. The graceful shutdown triggers Linux init/system_server to sync buffers and cleanly dismount filesystems before the box switch is turned off.
