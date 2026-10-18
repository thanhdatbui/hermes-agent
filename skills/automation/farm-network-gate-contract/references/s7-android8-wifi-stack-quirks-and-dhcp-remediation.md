# Samsung Galaxy S7 (Android 8) Wi-Fi Stack Quirks & DHCP Remediation

## 1. Incident Overview (Máy 7 Farm Case Study)

During the deployment of `farm_network_gate.py` on Máy 7 (serial `9885f63030454d3055`, Galaxy S7 Android 8), the device initially failed with `L2_AUTH_FAIL`, then progressed to `L3_NO_IP`. Investigation uncovered four specific low-level quirks of the Samsung S7 Android 8 networking stack that cause gate false-positives and connection hangs if not handled mechanically.

---

## 2. Low-Level Quirks & Root Causes

### A. Stale Profile Accumulation & Blacklisted Networks (ID >= 10)
- **Symptom:** Even when supplied with the correct WPA2 passphrase (`23102025` for `kibe 1`), the device immediately returned `DISCONNECTED` or failed association.
- **Root Cause:** In Android 8, networks are assigned incremental integer IDs. Prior ad-hoc join attempts had accumulated network profiles up to `ID: 10` and `ID: 11`. In `dumpsys wifi`:
  ```text
  ID: 10 SSID: "kibe 1"
  NetworkSelectionStatus NETWORK_SELECTION_TEMPORARY_DISABLED
  mNetworkSelectionDisableReason NETWORK_SELECTION_DISABLED_AUTHENTICATION_FAILURE
  blackListed: 1792271717sec  cuid=10179 cname=com.steinwurf.adbjoinwifi
  ```
  The old cleanup logic only swept `STALE_NETWORK_IDS = range(10)`. Network 10 remained untouched and blacklisted by the OS supplicant, preventing new connection attempts to `kibe 1`.
- **Remediation:**
  ```python
  def _forget_all_networks(serial: str):
      text = _adb_shell(serial, "dumpsys wifi").stdout or ""
      ids = {int(x) for x in re.findall(r"ID:\s*(\d+)", text)}
      for i in sorted(set(range(30)) | ids):
          _adb_shell(serial, f"service call wifi 14 i32 {i}")
  ```

---

### B. Non-Root Socket Failure on `ping -I wlan0`
- **Symptom:** L3 gateway verification reported `gateway unreachable` even when the Wi-Fi link was up.
- **Root Cause:** On Samsung Android 8 without root privileges, passing `-I wlan0` to `ping` (`ping -c 1 -W 3 -I wlan0 192.168.110.1`) fails with returncode `2` (`connect: Network is unreachable` or socket `Permission denied`) because binding to a network interface requires `CAP_NET_RAW` / root capabilities.
- **Remediation:**
  1. Attempt standard ICMP ping without `-I`: `ping -c 1 -W 2 <GATEWAY>`.
  2. If ICMP is blocked or returns non-zero, fallback to TCP probe on Gateway port 80:
     `toybox nc -w 3 -W 3 <GATEWAY> 80 < /dev/null`.
  3. If Gateway port 80 is closed to clients, fallback to TCP probe on Sing-box proxy port (`192.168.110.2:200xx`). If any LAN host on the subnet responds to TCP, L3 routing is verified.

---

### C. Incompatible Netcat Flags on Toybox (`-z` Unsupported)
- **Symptom:** Port probe commands crashed or returned syntax errors.
- **Root Cause:** Android 8 uses `toybox` as its shell core utility provider. Unlike BSD netcat, `toybox nc` does NOT support the `-z` flag (zero-I/O scanning).
- **Remediation:** Use standard timeout flags with input redirection:
  ```python
  def _proxy_open(serial: str, host: str, port: int) -> bool:
      r = _adb_shell(serial, f"toybox nc -w 3 -W 3 {host} {port} < /dev/null", timeout=15)
      return r.returncode == 0
  ```

---

### D. Post-WPA2 Association DHCP Stall
- **Symptom:** The WPA2 4-way handshake completes successfully:
  ```text
  14: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 state UP
      link/ether ac:5f:3e:60:59:1b
      inet6 fe80::ae5f:3eff:fe60:591b/64 scope link
  ```
  However, no IPv4 address is assigned (`ip addr show wlan0` shows only link-local IPv6).
- **Root Cause:** Android 8's DHCP client daemon (`DhcpClient`) occasionally stalls or misses the router's DHCP Offer after rapid radio toggling.
- **Remediation Hierarchy:**
  1. Trigger DHCP renewal via ADB:
     ```python
     def _renew_dhcp(serial: str):
         _adb_shell(serial, "dhcpcd -n wlan0")
         _adb_shell(serial, "svc wifi disable")
         _adb_shell(serial, "sleep 1")
         _adb_shell(serial, "svc wifi enable")
     ```
  2. Increase poll budget: `IP_POLL_ATTEMPTS = 10`, `IP_POLL_INTERVAL = 2.0s` (total 20s).
  3. If DHCP server fails to respond, fallback to assigning the known static IP mapped for the machine (e.g. `192.168.110.124/24` with default gateway `192.168.110.1`).

---

### E. Ruijie Static IP Reservation Conflict (`Converted to Static IP` Stalling)
- **Symptom:** In Ruijie Gateway (`EW3200GX-PRO`), the device MAC is visible in "DHCP Clients" marked as `Converted to Static IP` (remaining lease e.g. 23 min), and appears in "Static IP Addresses" table (e.g. `192.168.110.124`), but the phone's `wlan0` interface remains completely devoid of an IPv4 address. Host ARP table reports `192.168.110.124 -> 00:00:00:00:00:00` (Incomplete).
- **Root Cause:** Farm phones (M1–M80) are designed to operate purely on dynamic DHCP. Only the 4 Aruba APs (`.250`–`.253`) and Admin PC (`.119`) belong in the Static IP table. When a farm phone MAC is manually bound in Ruijie's Static IP table, Ruijie locks the lease state. If the phone subsequently forgets the network or resets Wi-Fi, Android's `DhcpClient` sends fresh DHCP Discover broadcasts with new transaction IDs that Ruijie fails to bind dynamically, resulting in an indefinite DHCP starvation loop.
- **Remediation:**
  1. Access Ruijie Gateway via Web UI (`http://192.168.110.1/cgi-bin/luci/`) -> More -> Basics -> LAN -> "Static IP Addresses".
  2. Delete the farm phone's MAC/IP entry from the static table.
  3. Allow Ruijie to manage the device via normal dynamic DHCP pool, matching the rest of the farm fleet (M1, M2, M6, M8...).

---

### F. `adbjoinwifi` Foreground Lifecycle & Pre-Join Proxy Cleansing
- **Symptom:** Immediate association drops, captive portal popup loops, or DHCP negotiation failing before an IP can be assigned.
- **Root Cause:**
  1. If `am start -S` is used, `-S` force-stops `com.steinwurf.adbjoinwifi`, destabilizing the Wi-Fi service.
  2. If `input keyevent 3` (HOME) is sent immediately after association, the join activity is minimized before Android completes DHCP exchange.
  3. If a stale `http_proxy` (`192.168.110.2:200xx`) remains configured on the device, Android attempts to route initial DNS and captive portal checks through the proxy before gaining network connectivity.
- **Remediation:**
  1. Pre-join hygiene: `settings put global http_proxy :0` and disable captive portal detection (`captive_portal_mode 0`, `captive_portal_detection_enabled 0`).
  2. Omit `-S` when launching `com.steinwurf.adbjoinwifi/.MainActivity`.
  3. Defer sending `KEYCODE_HOME` until after L2->L3->L4 verification is fully completed.

---

### G. Default Route Installation Latency (`_wait_for_gateway`)
- **Symptom:** `_gateway_reachable` fails with `Network is unreachable` immediately after `_has_subnet_ip` returns `True`.
- **Root Cause:** Android `ConnectivityService` takes 2–5 seconds after IP lease acquisition to evaluate link properties and install the default route (`default via 192.168.110.1 dev wlan0`).
- **Remediation:** Implement bounded polling:
  ```python
  def _wait_for_gateway(serial: str, net: dict, attempts: int = 6, interval: float = 2.0) -> bool:
      for _ in range(attempts):
          if _gateway_reachable(serial, net):
              return True
          time.sleep(interval)
      return False
  ```

---

### H. `am start -e password` Argument Quoting Trap
- **Symptom:** WPA2 4-way handshake repeatedly fails with `L2_AUTH_FAIL` or `TIMEOUT` even when the plaintext password in config is correct (e.g. `23102025`).
- **Root Cause:** Passing `shlex.quote(password)` to `am start -e password ...` injects literal single quotes (`'23102025'`). Android `Activity` intent parser does NOT strip shell quotes from extra string arguments, passing `'23102025'` as the 10-character Wi-Fi password instead of the actual 8-character numeric string.
- **Remediation:** Pass the raw password string directly without single quotes:
  ```python
  cmd = " ".join([
      "am", "start", "-n", JOIN_ACTIVITY,
      "-e", "ssid", f'"{net["ssid"]}"',
      "-e", "password_type", "WPA",
      "-e", "password", net["password"],
  ])
  ```

---

### I. Waking Android 8 DHCP Client via `WifiSettingsActivity`
- **Symptom:** L2 Wi-Fi associations succeed immediately (`COMPLETED`), but `DhcpClient` stays dormant and fails to obtain an IPv4 address within the poll window (`L3_NO_IP`, `raw_wlan0: `).
- **Root Cause:** On Samsung Galaxy S7 (Android 8), background broadcast receivers occasionally miss the DHCP Offer when joining programmatically via background activity.
- **Remediation:** Launch the native Wi-Fi settings activity during the polling window:
  ```python
  _adb_shell(serial, "am start -a android.settings.WIFI_SETTINGS")
  ```
  Opening the foreground settings UI forces the Samsung framework Wi-Fi state machine to poll and process pending DHCP lease transactions immediately.

---

### J. `/proc/net/arp` Inspection for Non-Root Gateway Verification
- **Symptom:** Non-root Android 8 devices fail ICMP ping (`connect: Network is unreachable` or `socket: Permission denied`), falsely flagging gateway unreachable.
- **Root Cause:** `ping` requires `CAP_NET_RAW` which non-root shells on Samsung stock firmware may lack.
- **Remediation:** Read `/proc/net/arp` directly to verify whether the gateway's MAC address is resolved and valid on `wlan0`:
  ```python
  arp_out = _adb_shell(serial, "cat /proc/net/arp").stdout or ""
  for ln in arp_out.splitlines():
      if GATEWAY in ln and "wlan0" in ln and "00:00:00:00:00:00" not in ln:
          parts = ln.split()
          if len(parts) >= 4 and parts[2] != "0x0":
              return True
  ```

---

### K. Idempotent Join Bypass When Already Associated
- **Symptom:** Gate runs repeatedly reconnect and drop existing IP leases when checking an already-healthy or partially joined device.
- **Root Cause:** Unconditionally invoking `_join_wifi` flushes supplicant networks and resets radio state, destroying an active dynamic DHCP lease.
- **Remediation:** Wrap join invocation with an association check:
  ```python
  if not (_ssid_connected(serial, net["ssid"]) and _has_subnet_ip(serial)):
      outcome, detail = _join_wifi(serial, net)
  ```

---

## 3. Operator Mandate: Anti-Paralysis Protocol (No Passive BLOCKED)

- **User Correction (2026-10-18):** *"TAO CĂM THÙ CHỮ BLOCKED... làm việc mà cứ dừng lại khóc"*.
- **Invariant:** A Coordinator MUST NEVER passively report `BLOCKED` and stop working when encountering a gate failure or network block.
- **Required Behavior:**
  1. Inspect physical device state immediately using $O(1)$ inspect tools (`inspect_machine.py`, `dumpsys wifi`, `ip addr show wlan0`).
  2. Isolate the exact physical layer failure (L2 WPA2 vs L3 DHCP vs L4 Proxy).
  3. Formulate and propose/execute deterministic remediation (e.g. DHCP renewal, static IP fallback, or full network ID flush).
