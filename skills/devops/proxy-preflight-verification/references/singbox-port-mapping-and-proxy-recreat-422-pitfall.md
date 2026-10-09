# Sing-box Port Mapping & MobiProxy `proxy_recreat` 422 Pitfall

## Architecture Recap
- **Upstream MobiProxy**: `test.taadaa.click:51xx` (32 modem proxy, 4 groups x 8 ports: 5101-5108, 5111-5118, 5121-5128, 5131-5138; skip 09,10)
- **Sing-box forwarder**: `192.168.110.2:20001..20080` (1:1 proxy to upstream, TCP socket always OPEN even when upstream dead)
- **Workbook SSOT mapping** (`PROXYgandienthoai.xlsx`):
  * **M1 – M32** & **M39 – M70**: Upstream là **MobiProxy 4G** (`test.taadaa.click:5101..5138`, chia 2 chu kỳ 32 modem).
  * **M33 – M37** & **M71 – M75**, **M77 – M80**: Upstream là **MikroTik PPPoE** (`mirotik1.taadaa.click:10001..10007`).
  * **M38** & **M76**: Upstream là **KhoaLee proxy riêng** (`khoalee.duckdns.org:16002`).

> **Cảnh báo quan trọng khi đối chiếu sự cố**: Khi các máy Sing-box chết thuộc dải M33–M37 hoặc M71–M80, nguyên nhân xuất phát từ cụm **MikroTik PPPoE**, tuyệt đối không kết luận nhầm là do MobiProxy sập dù MobiProxy có thể đang bị lỗi web/ngắt đồng thời.

## The 422 Pitfall

When calling `proxy_recreat` or `proxy_check` API on `test.taadaa.click`, **you MUST use the upstream MobiProxy port (51xx), NOT the Sing-box port (200xx)**.

```python
# WRONG — returns 422 {"result":"false","content":"invalid_proxy","message":"Proxy port is outside configured ranges"}
url = f'http://test.taadaa.click/proxy_recreat?proxy=test.taadaa.click:20004&token={TOKEN}'

# CORRECT
url = f'http://test.taadaa.click/proxy_recreat?proxy=test.taadaa.click:5104&token={TOKEN}'
```

## Quick Machine→Upstream Port Resolution

```python
def machine_to_upstream_port(machine: int) -> int:
    """Map machine number to upstream MobiProxy port.
    M1-M8 → 5101-5108, M9-M18 → 5111-5118, M19-M28 → 5121-5128, M29-M38 → 5131-5138.
    Machines >38 wrap: M39→5101, etc.
    """
    group = ((machine - 1) // 10)  # 0, 1, 2, 3
    offset = ((machine - 1) % 10)  # 0-9
    # Skip ports ending in 09, 10 (no modem there)
    if offset < 8:
        return 5100 + group * 10 + offset + 1
    # offset 8, 9 map to next group's 1, 2 (M17→5121, M18→5122, etc.)
    return 5100 + (group + 1) * 10 + (offset - 8) + 1
```

## Sing-box TCP Socket Is Always OPEN

A critical gotcha: Sing-box container ports (200xx) remain TCP-OPEN even when upstream is dead (502/RESET/TIMEOUT). So:
- **TCP probe 200xx** tells you nothing about actual proxy health — it only confirms the container is running.
- **HTTP probe 200xx** (via proxy request to api.ipify.org) reveals real status: OK / 502 / RESET / TIMEOUT.
- **For healing**, always call API on 51xx upstream ports, then re-verify via HTTP probe through Sing-box 200xx.

## Heal Retry Pattern

From session 09/09/2026 (23/26 ports dead):
1. First call `proxy_recreat` on all dead ports → ~30% succeed immediately
2. Wait 15s for modem reconnection
3. Retry failed ports (many succeed on 2nd try)
4. Some modems don't recover at all (hardware/SIM issue) — these need physical inspection
5. Total success rate: ~17/18 ports healed after 2-3 retries, 1 stubborn port needed physical check
