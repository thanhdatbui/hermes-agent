# OmniRoute vs 9Router Proxy Isolation & Direct IP Ban Forensics

## Root Cause of Mass Codex Bans (October 2026)
- **OmniRoute silent fallback**: In OmniRoute (`storage.sqlite`), setting `proxy_enabled = 1` in `provider_connections` without an entry in `proxy_assignments` silently routes all outbound API calls through the host's direct residential IP (`1.53.55.190`).
- **Impact**: 51/65 unassigned connections were permanently banned with `account_deactivated` by OpenAI.
- **9Router Fail-Closed Pattern**: 9Router binds proxies directly inside `providerSpecificData.proxyPoolId`. If the proxy fails, the connection fails closed without leaking host IP.
- **Rotation Configuration**: Use `fallbackStrategy: "round-robin"` with `stickyRoundRobinLimit: 2` to cycle accounts and distribute load across distinct 4G egress IPs.
