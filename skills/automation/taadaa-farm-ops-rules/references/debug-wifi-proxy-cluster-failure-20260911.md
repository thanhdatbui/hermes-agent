# Debug Session: 2 System Error Clusters in Batch Alert (11/09/2026)

## Alert Summary
- **Batch size**: 80 machines
- **Failed**: 26 machines (32.5%)
- **System error clusters**: 2 (each ≥ 10% & ≥ 3 machines)

| Cluster | Signature | Rate | Machines |
|---------|-----------|------|----------|
| 1 | `script-blocker:profile username still mismatched after switch` | 12.5% (10/80) | M33, M34, M35, M36, M37, M71, M73, M77, M78, M80 |
| 2 | `proxy-vpn:required router proxy unreachable... Wi-Fi not connected` | 12.5% (10/80) | M38, M61, M62, M63, M64, M67, M68, M70, M72, M74 |

---

## Cluster 1: Profile Switch Mismatch (10 machines)

### Root Cause
TikTok app shows **"Đã xảy ra lỗi / Thử lại sau"** overlay with retry button (`com.ss.android.ugc.trill:id/dcj`, tap ~540,1436) after profile switch. The profile doesn't load new account data → verification sees old username → `profile username still mismatched after switch`.

### Evidence (M33 canary)
```bash
# OCR screencap showed:
"Đã xảy ra lỗi - Thử lại sau"
Nút "Thử lại" tại vị trí 540,1436
Profile hiển thị nick cũ @lebaothao8787
```

### Fix Applied
Added retry logic in `python_runner/flows/feed_swipe_smoke.py` function `verify_and_switch_profile`:
```python
if not verified and selected_account_by_exact_switcher:
    recaptured_xml_lower = (recaptured_xml or "").lower()
    if "com.ss.android.ugc.trill:id/dcj" in (recaptured_xml or "") \
       or "thử lại" in recaptured_xml_lower \
       or "đã xảy ra lỗi" in recaptured_xml_lower:
        ctx.adb.shell(["input", "tap", "540", "1436"], timeout=...)
        time.sleep(3.0)
    else:
        time.sleep(2.0)
    # Re-read identity and re-verify
    latest_identity = _read_profile_identity_with_add_phone_guard(...)
    # recalc verified...
```
**Commit**: `1623c41` — `fix(switcher): add retry and tap dcj on error screen after profile switch`
**Test**: `pytest python_runner/tests/test_profile_switcher_retry.py` → 3 passed

---

## Cluster 2: Wi-Fi / Proxy Failure (10 machines)

### Root Cause
**Two APs lost power/LAN at ~08:57** (7.1-7.2h before inspection):
- **BOX 1.1** → M38, M62, M63, M74
- **BOX 2** → M61, M64, M67, M68, M70, M72

All 10 machines:
- `wlan0: DOWN`, `ip route` empty, no IP
- `mWifiInfo: DISCONNECTED/UNINITIALIZED, RSSI -127, Net ID -1`
- `lastConnected: ~25000-26000 sec ago` (matches 08:57)
- **Cannot auto-reconnect** — AP is dead, `autoReconnect=1` only works when AP broadcasts

### ADB Diagnostic Commands Used
```bash
# Check Wi-Fi state
adb -s <serial> shell dumpsys wifi | grep -E "mWifiInfo SSID:|lastConnected:|level2FailureCode="

# Verify interface
adb -s <serial> shell ip addr show wlan0
adb -s <serial> shell ip route

# Scan visibility
adb -s <serial> shell cmd wifi start-scan && sleep 3 && adb -s <serial> shell cmd wifi list-scan-results

# Proxy connectivity
python -c "import socket; socket.create_connection(('mirotik1.taadaa.click', 10018), 3)"
```

### Key Findings from `dumpsys wifi`
| Machine | Last Connected | Failure Code | Last SSID |
|---------|---------------|--------------|-----------|
| M38 | 25132s | `ASSOCIATION_REJECTION`, `trackBssid disable reason 1` | BOX 1.1 → kibe 2 |
| M61 | 26048s | — | BOX 2 |
| M62 | 26039s | — | BOX 1.1 |
| M72 | 25914s | `AUTHENTICATION_FAILURE` | Dinh Khoi (not kibe) |

### Resolution
**Physical action required:**
1. Reboot AP **BOX 1.1** and **BOX 2** (power cycle / check LAN cable)
2. Machines will auto-reconnect (`autoReconnect=1`)
3. Verify: `ip addr show wlan0` → `state UP` + `inet 192.168.110.x`

---

## Additional Finding: Serial Mismatch Between Workbooks

| Workbook | Machine | Serial | Proxy |
|----------|---------|--------|-------|
| Admin (`PROXYgandienthoai.xlsx`) | 233 | `ce0616060c76453001` | 10018 |
| Kibe (`taikhoan_run_safe.xlsx`) | 33 | `ce0616061a74682305` | 10001 |

**Both proxies CLOSED** (MikroTik 10001-10035 all timeout). ADB `devices` empty → USB hub/power also lost for M30-M80 range.

---

## Debugging Checklist for Future Wi-Fi/Proxy Cluster Alerts

1. **Pick 1 representative machine** from cluster → `dumpsys wifi`
2. **Check `lastConnected` seconds** → calculate downtime start
3. **Check `mWifiInfo`** → `DISCONNECTED/UNINITIALIZED` = no AP association
4. **Check `ip route` / `ip addr show wlan0`** → `DOWN` + no IP = interface down
3. **Scan cache** → is target SSID (kibe 1/2) visible?
4. **Check `level2FailureCode`** → `ASSOCIATION_REJECTION` / `AUTHENTICATION_FAILURE` = AP rejected
5. **Test proxy port** → MikroTik / MobiProxy connectivity
6. **Correlate machines by AP** (BOX 1.1 vs BOX 2 vs kibe 1/2) → physical AP mapping

---

## Canary Policy Applied
- Cluster 1 (code bug): Fixed + unit test → commit → canary pass
- Cluster 2 (infra): Physical AP reboot required → no code change → wait for infra fix → re-run batch