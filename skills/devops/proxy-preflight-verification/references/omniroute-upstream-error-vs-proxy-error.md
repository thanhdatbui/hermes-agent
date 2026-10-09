# OmniRoute Upstream Error vs Proxy Error — Quick Reference

## Session context (2026-09-09)
User asked why MikroTik proxy ports show ERROR in OmniRoute logs. Initial diagnosis was wrong (claimed DNS failure → proxy broken). Actual root cause: Antigravity upstream provider returning 403 on certain exit IPs.

## Key facts discovered
- DNS record on Cloudflare for Taadaa: `mirotik1.taadaa.click` (NO 'k' — not a typo, this is the actual record)
- `nslookup mikrotik1.taadaa.click` → Non-existent (because spelling is `mirotik1`, not `mikrotik1`)
- `nslookup mirotik1.taadaa.click` → resolves to 171.231.176.248 ✅
- MikroTik Proxy Manager: all 35 PPPoE interfaces CONNECTED, uptime ~4h+
- Proxy TCP probe: all ports respond 407 (Proxy Authentication Required = proxy alive, needs auth)
- OmniRoute error modals: `[403]: Antigravity upstream error (403)` and `[429]: Antigravity upstream error (429)`

## Error pattern analysis
| Port | Public IP range | Typical result | Notes |
|------|----------------|----------------|-------|
| 10005 | 171.231.179.44 | SUCCESS | Clean IP, no flag |
| 10022 | varies | SUCCESS | Clean IP |
| 10001 | varies | ERROR 403 | Google flagged this exit IP |
| 10004 | varies | ERROR 403 | Google flagged this exit IP |

Root cause: each PPPoE port exits through a different public IP. Google Antigravity (OAuth-based free tier) detects abuse/rate-limit per IP. Some IPs are flagged → 403. Others are clean → 200.

## OmniRoute API endpoints used during diagnosis
- `GET http://127.0.0.1:20129/api/health` → `{"status":"ok"}`
- `GET http://127.0.0.1:20129/api/settings` → full settings JSON (proxyEnabled, resilience, etc.)
- `GET http://127.0.0.1:20129/api/providers` → connections list with fingerprints and accountProxies

## OmniRoute proxy log modal fields
| Field | Example |
|-------|---------|
| THỜI GIAN | 09/09/2026, 21:25:08 |
| ĐỘ TRỄ | 9.6s |
| IP CLIENT | 127.0.0.1 |
| PROXY | http://mirotik1.taadaa.click:10001 |
| LOẠI | HTTP |
| MỨC | DIRECT or PROVIDER |
| NHÀ CUNG CẤP | AG |
| DẤU VÂN TAY TLS | Trực tiếp (native) |
| URL ĐÍCH | antigravity/claude-sonnet-4-6 |
| LỖI | [403]: Antigravity upstream error (403) |

## Fix actions
1. **IP-based 403**: Bấm "Đổi IP" trên MikroTik Proxy Manager cho port bị flag → PPPoE reconnect → IP mới → Antigravity không recognize → request pass.
2. **Remove fingerprint**: Xóa fingerprint bị 403 khỏi OmniRoute pool config → request不会再 routed qua port đó.
3. **Token refresh**: Nếu lỗi 403 trên TẤT CẢ ports → Antigravity OAuth token expired → cần refresh/re-auth.

## Anti-pattern: jumping to DNS/conclusion
When proxy logs show errors:
- ❌ DON'T assume proxy is broken from DNS lookup alone
- ❌ DON'T skip the error modal — the actual error code is INSIDE it
- ✅ DO click the ERROR row → read the modal → identify error code → trace to root cause
- ✅ DO compare which ports succeed vs fail → pattern reveals IP-based vs infrastructure issue
