# MikroTik REST API Firewall & PPPoE Configuration Workflow

## Connection & Auth
```python
import urllib.request, json, base64

AUTH = "Basic " + base64.b64encode(b"admin:N0spam@@").decode("ascii")
HOST = "192.168.110.2:9090"

def api_get(path):
    url = f"http://{HOST}/rest{path}"
    req = urllib.request.Request(url, headers={"Authorization": AUTH, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode())

def api_patch(path, data):
    url = f"http://{HOST}/rest{path}"
    payload = json.dumps(data).encode("utf-8")
    headers = {"Authorization": AUTH, "Accept": "application/json", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status
```

## Step 1: Audit Current State
```python
rules = api_get("/ip/firewall/filter")
for r in rules:
    print(r[".id"], "chain=" + r["chain"], "act=" + r["action"],
          "src_list=" + str(r.get("src-address-list")),
          "port=" + str(r.get("dst-port")), "dis=" + r.get("disabled"))

lists = api_get("/ip/firewall/address-list")
for l in lists:
    print("list=" + l["list"], "addr=" + l["address"])

pppoe = api_get("/interface/pppoe-client")
running = [p["name"] for p in pppoe if p.get("running") == "true"]
enabled = [p["name"] for p in pppoe if p.get("disabled") != "true"]
disabled = [p["name"] for p in pppoe if p.get("disabled") == "true"]
print(f"Running: {len(running)}/{len(enabled)} | Disabled: {len(disabled)}")
```

## Step 2: Create Address List (FPT_LAN)
```python
for subnet in ["192.168.110.0/24", "192.168.10.0/24", "127.0.0.1"]:
    existing = api_get("/ip/firewall/address-list")
    already = any(a["list"] == "FPT_LAN" and a["address"] == subnet for a in existing)
    if not already:
        api_patch("/ip/firewall/address-list", {
            "address": subnet, "list": "FPT_LAN",
            "comment": "FPT LAN - allowed to use proxy"
        })
```

## Step 3: Add Firewall Filter Rules
```python
api_patch("/ip/firewall/filter", {
    "chain": "forward", "action": "accept",
    "src-address-list": "FPT_LAN", "protocol": "tcp",
    "dst-port": "10001-10035,20001-20080",
    "comment": "ALLOW_FPT_LAN_PROXY_PORTS"
})
api_patch("/ip/firewall/filter", {
    "chain": "forward", "action": "drop", "protocol": "tcp",
    "dst-port": "10001-10035,20001-20080",
    "comment": "DROP_EXTERNAL_PROXY_PORTS"
})
```

## Step 4: Disable Unrestricted Rules (Critical!)
```python
rules = api_get("/ip/firewall/filter")
for r in rules:
    dp = r.get("dst-port", "")
    if (dp.startswith("1000") or dp.startswith("2000")) and \
       not r.get("src-address-list") and r.get("action") == "accept" and \
       r.get("disabled") != "true":
        api_patch(f"/ip/firewall/filter/{r['.id']}", {"disabled": "true"})
```

## Step 5: Restrict Generic Forward Rules
```python
rules = api_get("/ip/firewall/filter")
for r in rules:
    if "ALLOW_FARM_ADMIN" in (r.get("comment") or ""):
        api_patch(f"/ip/firewall/filter/{r['.id']}", {
            "src-address-list": "FPT_LAN",
            "comment": "ALLOW_FARM_ADMIN_FORWARD_FPT_LAN"
        })
```

## Step 6: Disable Redundant PPPoE Lines
```python
pppoe = api_get("/interface/pppoe-client")
for p in pppoe:
    num = int(p["name"].replace("pppoe-out", ""))
    if num > 35 and p.get("disabled") != "true":
        api_patch(f"/interface/pppoe-client/{p['.id']}", {"disabled": "true"})
```

## Step 7: Export Config to Repo
- MikroTik REST API does not expose /system/save or /export for full config.
- Changes persist in running config and auto-save periodically.
- To persist to repo: read running config via api_get(), format as .rsc text, write to `docs/infrastructure/mikrotik/firewall-<name>-<date>.rsc`, update master handbook, git add + commit + push.

## Step 8: Verify
```python
import socket
for port in [10001, 20033]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.5)
    r = s.connect_ex(("192.168.110.2", port))
    s.close()
    print(f"Port {port}: {'OPEN' if r == 0 else 'CLOSED'}")

proxy = urllib.request.ProxyHandler({"http": "http://192.168.110.2:10001"})
opener = urllib.request.build_opener(proxy)
with opener.open(urllib.request.Request("http://api.ipify.org"), timeout=3) as resp:
    print("Egress IP:", resp.read().decode().strip())
```

## Notes & REST API Pitfalls
- **Field Unsetting / Clearing Pitfall (HTTP 400 Bad Request):** RouterOS REST API does NOT allow unsetting/clearing a string field (like `src-address=0.0.0.0/0`) by sending `PATCH {"src-address": ""}` or `null` — it returns `400 Bad Request`. The correct pattern is to `DELETE /ip/firewall/filter/<id>` and recreate the rule via `PUT /ip/firewall/filter` specifying only the required fields (omitting `src-address` entirely).
- **Rule Ordering via REST (`move` API):** `PUT /ip/firewall/filter` appends the new rule to the END of the chain. To place it immediately before a DROP rule (e.g. `DROP_EXTERNAL_PROXY_PORTS`), call `POST /ip/firewall/filter/move` with data `{".id": "<new_rule_id>", "destination": "<target_rule_id>"}`.
- **NAT Deduplication on PPPoE lines:** If repeated scripts add `dstnat` rules, duplicate rules accumulate on the same `(in-interface, dst-port)` (e.g. 10001-10035 having 61 rules instead of 35). To clean: query `/ip/firewall/nat`, group by `dst-port`, keep the lowest/first `.id`, and delete duplicates via `DELETE /ip/firewall/nat/<id>`.
- Packet vs Request: 1 HTTP request = 10-30+ TCP packets. 57M packets over 29h ~ 2-5M requests.
- Rule order: FIRST match wins. Unrestricted accept above FPT_LAN allow = bypassed whitelist.
- Python f-string pitfall: CANNOT use backslash in f-string expressions in `python -c` inline. Use separate script files or concat variables.
- PPPoE bulk disable: filter by name number, disable in loop, verify count matches target.
