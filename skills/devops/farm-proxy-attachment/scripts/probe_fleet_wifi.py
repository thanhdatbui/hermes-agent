#!/usr/bin/env python3
"""
probe_fleet_wifi.py - Rapid inspection of Wi-Fi interface and DHCP status across all connected ADB devices.

Usage:
    python probe_fleet_wifi.py [--adb PATH]
"""

import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

DEFAULT_ADB = os.environ.get("ADB_PATH", r"C:\Program Files (x86)\xiaowei\tools\adb.exe")

def inspect_device_wifi(adb_path: str, serial: str) -> dict:
    info = {"serial": serial, "has_ip": False, "ip": None, "state": "unknown", "ssid": None, "bssid": None, "error": None}
    try:
        r = subprocess.run([adb_path, "-s", serial, "shell", "ip", "addr", "show", "wlan0"], capture_output=True, text=True, timeout=6)
        out = r.stdout
        if "inet " in out:
            m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out)
            if m:
                info["has_ip"] = True
                info["ip"] = m.group(1)
        if "NO-CARRIER" in out:
            info["state"] = "NO-CARRIER"
        elif "DORMANT" in out:
            info["state"] = "DORMANT"
        elif "UP" in out:
            info["state"] = "UP"

        # Check dumpsys wifi for SSID / DHCP error
        r2 = subprocess.run([adb_path, "-s", serial, "shell", "dumpsys", "wifi"], capture_output=True, text=True, timeout=6)
        wout = r2.stdout
        m_ssid = re.search(r'SSID:\s*"?([^",\n]+)"?', wout)
        if m_ssid:
            info["ssid"] = m_ssid.group(1).strip()
        m_bssid = re.search(r'BSSID:\s*([0-9a-fA-F:]{17})', wout)
        if m_bssid:
            info["bssid"] = m_bssid.group(1)
        if "level2FailureCode=DHCPUNKNOWN" in wout or "level2FailureCode=DHCP" in wout:
            info["error"] = "DHCP_FAILURE"
    except subprocess.TimeoutExpired:
        info["error"] = "ADB_TIMEOUT"
    except Exception as exc:
        info["error"] = str(exc)
    return info

def main():
    parser = argparse.ArgumentParser(description="Probe Wi-Fi status across Android phone fleet")
    parser.add_argument("--adb", default=DEFAULT_ADB, help="Path to adb binary")
    parser.add_argument("--workers", type=int, default=20, help="Parallel worker threads")
    args = parser.parse_args()

    res = subprocess.run([args.adb, "devices"], capture_output=True, text=True)
    serials = [line.split()[0] for line in res.stdout.splitlines() if "\tdevice" in line]

    if not serials:
        print("No online ADB devices found.")
        return 0

    print(f"=== PROBING WI-FI ON {len(serials)} DEVICES ===")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(executor.map(lambda s: inspect_device_wifi(args.adb, s), serials))

    connected = [r for r in results if r["has_ip"]]
    disconnected = [r for r in results if not r["has_ip"]]
    dhcp_fails = [r for r in results if r.get("error") == "DHCP_FAILURE"]

    print(f"Total Attached Devices: {len(serials)}")
    print(f"Wi-Fi Connected (Valid IP): {len(connected)}")
    print(f"Wi-Fi Disconnected / No IP: {len(disconnected)}")
    if dhcp_fails:
        print(f"DHCP Failures Detected: {len(dhcp_fails)}")

    if disconnected:
        print("\n--- SAMPLE DISCONNECTED DEVICES ---")
        for r in disconnected[:10]:
            print(f"  Serial {r['serial']}: state={r['state']}, ssid={r['ssid']}, bssid={r['bssid']}, err={r['error']}")

    if len(disconnected) > len(connected) and len(serials) > 5:
        print("\n[ALERT] Mass Wi-Fi disconnection detected. Check Access Point / Router DHCP pool at 192.168.110.1.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
