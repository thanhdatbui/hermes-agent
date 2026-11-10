"""
Auto-update MobiProxy Scan Guard IPs when MikroTik WAN IP changes.

Logic:
1. Get current MikroTik WAN IP (pppoe-out1)
2. Get current PC Kibe public IP
3. Compare with last-known IPs in state file
4. If changed → POST scan_guard.save to MobiProxy → silent update
5. Silent if nothing changed

Run via cron every 5 minutes with no_agent=True.
"""

import base64
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

# --- Config ---
MIKROTIK_IP = "192.168.110.2"
MIKROTIK_PORT = 9090
MIKROTIK_AUTH = base64.b64encode(b"admin:N0spam@@").decode("ascii")

BOX_URL = "http://test.taadaa.click"
BOX_PASS = "N0spam@23102025"

STATE_FILE = os.path.join(
    os.environ.get("TEMP", "/tmp"),
    "mobiproxy_scan_guard_ips.json",
)

PC_KIBE_URL = "https://api.ipify.org"

# --- R3G (Xiaomi) Tinyproxy sync ---
R3G_TAILSCALE_IP = "100.115.94.49"
R3G_TINYPROXY_CONF = "/data/data/com.termux/files/usr/etc/tinyproxy/tinyproxy.conf"


def update_r3g_tinyproxy(mikrotik_ip, pc_ip):
    """SSH into R3G over Tailscale and sync Allow IPs in tinyproxy.conf, then reload."""
    allow_ips = [ip for ip in (mikrotik_ip, pc_ip) if ip]
    if not allow_ips:
        return
    remote_cmds = [
        f"sed -i '/^Allow /d' {R3G_TINYPROXY_CONF}",
    ]
    for ip in allow_ips:
        remote_cmds.append(f"echo 'Allow {ip}' >> {R3G_TINYPROXY_CONF}")
    remote_cmds.append("killall -HUP tinyproxy")
    remote_script = " && ".join(remote_cmds)
    try:
        subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", f"{R3G_TAILSCALE_IP}", remote_script],
            timeout=15,
            check=True,
            capture_output=True,
            creationflags=0x08000000 if sys.platform == 'win32' else 0,
        )
    except Exception as e:
        print(f"[WARN] R3G tinyproxy sync failed: {e}", file=sys.stderr)


def get_mikrotik_wan_ip():
    """Query MikroTik REST API for pppoe-out1 address."""
    try:
        url = f"http://{MIKROTIK_IP}:{MIKROTIK_PORT}/rest/ip/address?interface=pppoe-out1"
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {MIKROTIK_AUTH}"})
        data = json.loads(urllib.request.urlopen(req, timeout=5).read())
        if data:
            return data[0]["address"].split("/")[0]
    except Exception as e:
        print(f"[WARN] MikroTik query failed: {e}", file=sys.stderr)
    return None


def get_pc_kibe_ip():
    """Get PC Kibe public IP via ipify."""
    try:
        return urllib.request.urlopen(PC_KIBE_URL, timeout=5).read().decode().strip()
    except Exception as e:
        print(f"[WARN] ipify query failed: {e}", file=sys.stderr)
    return None


def load_state():
    """Load last-known IPs from state file."""
    if os.path.isfile(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(state):
    """Save current IPs to state file."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def get_box_scan_guard():
    """Login to MobiProxy and get current scan_guard IPs."""
    try:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

        # Login
        with opener.open(f"{BOX_URL}/login.php", timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            csrf = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
            if not csrf:
                return None
            csrf = csrf.group(1)

        login_data = urllib.parse.urlencode({"_csrf": csrf, "password": BOX_PASS}).encode("utf-8")
        with opener.open(f"{BOX_URL}/login.php", data=login_data, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            csrf2_match = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
            if not csrf2_match:
                return None
            csrf2 = csrf2_match.group(1)

        # Get scan_guard
        req = urllib.request.Request(f"{BOX_URL}/api.php?action=proxy.scan_guard.get")
        with opener.open(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            return data, csrf2, opener
    except Exception as e:
        print(f"[WARN] MobiProxy box unreachable (get_box_scan_guard): {e}", file=sys.stderr)
        return None


def update_box_scan_guard(ips_text, csrf2, opener, enabled=True):
    """POST scan_guard.save to MobiProxy."""
    try:
        payload = json.dumps({"_csrf": csrf2, "enabled": enabled, "allowed_ips": ips_text}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf2,
            "X-Requested-With": "XMLHttpRequest",
        }
        req = urllib.request.Request(f"{BOX_URL}/api.php?action=proxy.scan_guard.save", data=payload, headers=headers)
        with opener.open(req, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[WARN] MobiProxy box unreachable (update_box_scan_guard): {e}", file=sys.stderr)
        return None


def main():
    mikrotik_ip = get_mikrotik_wan_ip()
    pc_ip = get_pc_kibe_ip()

    if not mikrotik_ip and not pc_ip:
        print("[SILENT] Both IPs unreachable, skipping.")
        return

    state = load_state()
    new_state = {
        "mikrotik_ip": mikrotik_ip or state.get("mikrotik_ip"),
        "pc_ip": pc_ip or state.get("pc_ip"),
    }

    # Compare with last known
    if (
        new_state["mikrotik_ip"] == state.get("mikrotik_ip")
        and new_state["pc_ip"] == state.get("pc_ip")
        and state.get("updated")
    ):
        # No change
        return

    # IPs changed or first run — update box
    ips_text = ""
    if new_state["mikrotik_ip"]:
        ips_text += new_state["mikrotik_ip"] + "\n"
    if new_state["pc_ip"]:
        ips_text += new_state["pc_ip"] + "\n"

    result = get_box_scan_guard()
    if not result:
        print("[WARN] Failed to login to MobiProxy box.", file=sys.stderr)
        return

    scan_data, csrf2, opener = result
    resp = update_box_scan_guard(ips_text, csrf2, opener)

    update_r3g_tinyproxy(new_state["mikrotik_ip"], new_state["pc_ip"])

    new_state["updated"] = True
    save_state(new_state)

    print(f"[OK] Scan Guard updated: MikroTik={new_state['mikrotik_ip']}, PC={new_state['pc_ip']}")


if __name__ == "__main__":
    main()
