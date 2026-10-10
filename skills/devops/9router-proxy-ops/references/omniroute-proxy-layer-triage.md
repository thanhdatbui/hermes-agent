# OmniRoute / Farm Proxy Layer Triage

Use this read-only sequence when the report is vague (for example, “proxy configuration error”) and the symptom may be coming from either the phone-farm proxy path or the local LLM gateway.

## Evidence matrix

| Layer | Probe | Healthy evidence | Failure meaning |
|---|---|---|---|
| MikroTik control plane | `python D:/Taadaa/AI-Tools/scripts/mikrotik_manager.py --check` | RouterOS responds; `3proxy`, `api`, and `sing-box` are `running` | Router/container/control-plane issue |
| Sing-box local proxy | TCP + HTTPS request via representative `192.168.110.2:200xx` ports | TCP open, HTTPS returns `200`, public egress IP is non-empty | Local inbound or upstream egress issue |
| 9Router | `http://127.0.0.1:20128/api/health` | HTTP `200` / `{"ok":true}` | 9Router runtime issue |
| OmniRoute | `http://127.0.0.1:20129/api/health` | HTTP `200` / status `ok` | OmniRoute runtime issue |
| Model catalog/API route | `http://127.0.0.1:20129/v1/models` with a bounded timeout | Prompt response / valid JSON (401 is an auth-path result, not a socket failure) | If health is 200 but this hangs, isolate model-catalog/auth/runtime path; do not blame farm proxy automatically |

## Representative farm probe

Probe a small, fixed sample such as ports `20001`, `20008`, `20035`, and `20080`. Use both a TCP connect and an HTTPS egress request. Distinct public IPs across ports are expected and are stronger evidence than a dashboard “active” flag.

## Provider/account separation

After the layer split, inspect the known OmniRoute SQLite state and watchdog log read-only. Report provider failures separately: `403 forbidden`, `429 rate limit`, `502 provider/server error`, quota exhaustion, Sentinel/Turnstile, and revoked tokens are account/upstream conditions. `Connection refused`, socket timeout, `407`, and empty egress are proxy-path conditions.

## Safety and redaction

Do not edit `proxy_registry`, restart 9Router/OmniRoute, rotate PPPoE IPs, recreate MobiProxy ports, or change OAuth/account flags during the first diagnostic pass. Redact proxy credentials, access tokens, refresh tokens, API keys, email passwords, and OTPs from reports. A healthy `/api/health` does not prove every API route is healthy, and a failing model request does not prove the farm proxy is misconfigured.
