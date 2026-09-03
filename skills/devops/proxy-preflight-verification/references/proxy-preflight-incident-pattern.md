# Proxy preflight incident pattern

## Evidence matrix

| State | What it proves | What it does not prove |
|---|---|---|
| `tun0` UP | Android tunnel interface exists | Upstream proxy works |
| VPN `CONNECTED` | Android network agent reports connected | Public IP changed |
| `GET_IP result=200` + non-empty IP | ViChanger/proxy answered at probe time | IP differs from direct host unless compared |
| Proxy IP != direct host IP | Egress differs at comparison time | Proxy will remain healthy for the whole run |
| `GET_IP result=0` | Proxy is unverified/dead at that probe | It was dead at an earlier timestamp |

## Reporting template

- Target/serial:
- Preflight timestamp:
- Registration-start timestamp:
- Runtime interpreter/source revision:
- Live-IP flag:
- Tunnel/VPN state:
- GET_IP result/IP/retries:
- Direct host egress IP:
- Second preflight immediately before registration:
- Verdict: `PASS`, `BLOCKED`, or `UNVERIFIED`
- Missing proof / next owner action:

Never report `fake IP confirmed` from `CONNECTED` alone.
