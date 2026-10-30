# Mobiproxy vs OpenWrt Cross-Device Triage & API Automated Provisioning

## 1. Context & Motivation
When testing multi-line PPPoE deployments (e.g. Viettel fiber lines) where one line succeeds but another appears stuck or drops packets, cross-referencing against an existing, working proxy hardware box (e.g., Mobiproxy running on `test.taadaa.click`) provides ground truth:
- Is the fiber line/account active on the ISP OLT/BRAS?
- Or is the router firmware (OpenWrt/DSA/Firewall) misconfigured?

## 2. Critical Pitfalls in Cross-Triage

### Pitfall A: "Just plugging a cable into Mobiproxy won't work automatically"
- Mobiproxy does **NOT** auto-discover PPPoE accounts on a freshly plugged physical LAN port.
- Each LAN port (`Lan 1` to `Lan 4`) stores static PPPoE credentials in its database.
- If a new fiber line (e.g. `tamnhb0`) is plugged into `Lan 3`, Mobiproxy will attempt to dial using whatever account was previously assigned to `Lan 3` (e.g. `hyn_gftth_datlp0`).
- **Result:** RADIUS rejection, lockout, or fallback into ISP Walled Garden IP (`172.17.x.x`).
- **Rule:** Before concluding anything from plugging a cable into Mobiproxy, you MUST query and update the port's credentials via the Mobiproxy API!

### Pitfall B: Misidentifying Cable Pulls / User Speech vs Physical Ports
- When a user/assistant reports "unplugged middle cable / outer cable", verify with `cat /sys/class/net/<dev>/carrier` and `dmesg | grep mt7530`.
- Do not argue with the user's physical observation — acknowledge the DSA mapping inversion immediately and verify which device link changed.

---

## 3. Mobiproxy Internal REST API Integration

The Mobiproxy web panel (`http://<host>/`) exposes an internal JSON API protected by CSRF token and cookie session.

### Step 1: Authentication & CSRF Extraction
```python
import urllib.request, urllib.parse, http.cookiejar, re, json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Get login page & CSRF
res = opener.open('http://test.taadaa.click/login.php', timeout=8)
csrf = re.search(r'name="_csrf"\s+value="([^"]+)"', res.read().decode()).group(1)

# 2. Post login
opener.open(
    urllib.request.Request(
        'http://test.taadaa.click/login.php',
        data=urllib.parse.urlencode({'_csrf': csrf, 'password': 'YOUR_PASSWORD'}).encode()
    ),
    timeout=8
)

# 3. Extract dashboard CSRF token from index.php meta tag
idx_html = opener.open('http://test.taadaa.click/index.php', timeout=8).read().decode()
csrf_token = re.search(r'name="csrf-token"\s+content="([^"]+)"', idx_html).group(1)
```

### Step 2: Query Current PPPoE Credentials per LAN
Endpoint: `GET /api.php?action=network.credentials&lan=<1..4>`
Headers required:
- `Accept: application/json`
- `X-CSRF-Token: <token>`
- `X-Requested-With: XMLHttpRequest`

Response shape:
```json
{
  "ok": true,
  "data": {
    "lan": 3,
    "installed": true,
    "proxy": "proxy21",
    "username": "hyn_gftth_datlp0",
    "password": "***"
  }
}
```

### Step 3: Update PPPoE Credentials on LAN Port
Endpoint: `POST /api.php?action=network.install`
Headers:
- `Content-Type: application/json`
- `Accept: application/json`
- `X-CSRF-Token: <token>`
- `X-Requested-With: XMLHttpRequest`

Payload:
```json
{
  "lan": 3,
  "count": 8,
  "username": "hyn_gftth_tamnhb0",
  "password": "PASSWORD_HERE"
}
```
Response:
```json
{"ok": true, "data": {"lan": 3, "count": 8, "deleted": [], "server": null}}
```

### Step 4: Trigger Redial & Rotate
To force immediate PPPoE redial and restart all proxies:
- Single proxy: `POST /api.php?action=proxy.reset` with body `{"index": 21}`
- All proxies: `POST /api.php?action=proxy.reset_all` with body `{"skip_first": false}`
- Check results: `GET /proxy_getlist?token=<token>` to inspect `ip_public`, `uptime`, and `status`.

---

## 4. Ground-Truth Diagnosis Patterns

1. **If Mobiproxy dials the new account and gets public IP (116.x / 171.x):**
   - Fiber physical line + ISP account are 100% operational.
   - Fault is 100% inside the OpenWrt router (VLAN tag, switch DSA port binding, missing `config device '<port>'`, or policy routing).
   - **Crucial OpenWrt Root Cause to Inspect Immediately:**
     - OpenWrt 21.02 DSA switch requires an explicit `config device` entry for physical ports (e.g. `config device` with `option name 'lan1'`). If `lan2` has `config device 'lan2'` while `lan1` is missing, or if stale 802.1q VLAN subdevices (like `lan1.35`) linger in `/etc/config/network`, pppd will silently suffer `Timeout waiting for PADO packets` on `lan1` even though the physical carrier is up!
     - Never falsely accuse the ISP when Mobiproxy proves the line works; immediately audit `/etc/config/network` on OpenWrt.

2. **If Mobiproxy dials the new account and also gets 172.17.x.x (Walled Garden):**
   - Proves 100% indisputably that the ISP (e.g. Viettel BRAS/OLT) has not completed service activation/billing route for that contract.
   - Router hardware is innocent. Provide this concrete evidence to ISP technician.
