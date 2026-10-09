# MikroTik REST API — PPPoE Interface Management

## Connection & Auth

```
Host: 192.168.110.2:9090
Protocol: HTTP REST API (NOT HTTPS, NOT APIv2 protocol)
Auth: Basic Auth — admin:N0spam@@
```

All requests require `Authorization: Basic <base64(user:pass)>` header.
Endpoints are prefixed with `/rest/` and return JSON.

## Key Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/rest/system/resource` | GET | RouterOS version, CPU load, free memory, uptime |
| `/rest/interface/pppoe-client` | GET | List ALL PPPoE client interfaces |
| `/rest/interface/pppoe-client?name=pppoe-outN` | GET | Filter single interface by name |
| `/rest/interface/pppoe-client/{.id}` | PATCH | Update interface (enable/disable/modify) |
| `/rest/ip/address` | GET | List all IP address assignments |
| `/rest/ip/address?interface=pppoe-outN` | GET | Filter IPs for specific interface |
| `/rest/container` | GET | List containers (3proxy, etc.) |
| `/rest/container/{.id}/stop` | POST | Stop container |
| `/rest/container/{.id}/start` | POST | Start container |
| `/rest/ip/firewall/nat` | GET | List NAT rules |
| `/rest/ip/firewall/nat` | PUT | Create NAT rule (body: chain, action, out-interface, comment) |
| `/rest/ping` | POST | Ping from router (body: address, interface, count) |

## PPPoE Reconnect Workflow (1-click IP change)

The standard pattern to get a new public IP on a PPPoE interface:

```python
# 1. Find interface .id
pppoe = api_call(host, f"/interface/pppoe-client?name={iface_name}")
pid = pppoe[0].get(".id")

# 2. Disable
api_call(host, f"/interface/pppoe-client/{pid}", method="PATCH", data={"disabled": True})
time.sleep(2)

# 3. Enable (triggers new PPPoE session)
api_call(host, f"/interface/pppoe-client/{pid}", method="PATCH", data={"disabled": False})

# 4. Poll for new IP assignment
for _ in range(30):  # max 60s
    time.sleep(2)
    addrs = api_call(host, f"/ip/address?interface={iface_name}")
    if addrs and addrs[0].get("address"):
        new_ip = addrs[0]["address"]
        break
```

**Timing:** Disable → 2s → Enable → 15-30s for new IP. Total typical: 20-35s.

## Response Format

- `GET` returns a JSON **array** of objects (even single items)
- `PATCH`/`PUT` with empty response → HTTP 204
- `.id` field format: `*XX` (e.g. `*1A`)
- Status fields are **strings**: `"true"` / `"false"` (not booleans)

## PPPoE Interface Status Semantics

| `running` | `disabled` | Meaning |
|---|---|---|
| `"true"` | `"false"` | Session active, assigned IP |
| `"false"` | `"false"` | Session down, no IP |
| `"false"` | `"true"` | Manually disabled |

## IP Format Quirk

IPs are returned as `1.2.3.4/32` (CIDR notation with host mask), not just `1.2.3.4`. Client code must handle this.

## Farm Architecture Context

- MikroTik 192.168.110.2 hosts 60+ PPPoE lines (pppoe-out1 through pppoe-out60)
- Each PPPoE maps to a Singbox proxy port at 192.168.110.2:10000+N
- Container `3proxy` on interface `3proxy` provides the proxy service
- `dockers_proxy` interface is the proxy bridge
- PPPoE reconnection is used when an IP gets blocked by platforms

## Pitfalls

1. **No HTTPS** — REST API runs plain HTTP on port 9090, never 443
2. **Timeout sensitivity** — Default API timeout should be 10s; ping can hang longer
3. **Concurrent access** — API is thread-safe; multiple clients can query simultaneously
4. **Container restart** — Stopping/starting container takes 3-5s; check `status` field after
5. **String booleans** — `disabled: "true"` is a string, not `disabled: True`
6. **No ID auto-increment** — IDs are `*XX` hex, not sequential numbers
