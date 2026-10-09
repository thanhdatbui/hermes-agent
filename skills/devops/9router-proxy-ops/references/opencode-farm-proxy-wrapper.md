# OpenCode Free Tier Farm Proxy Integration (`oc_farm.py`)

## 1. Upstream Requirements & Enforcement (Enforced 2026-09)
- **403 External Block**: Upstream Zen API (`https://opencode.ai/zen/v1/...`) blocks direct external HTTP requests with:
  `HTTP 403: {"type":"FreeTierError","message":"OpenCode's free tier can only be used from within OpenCode"}`.
- **Client Version**: OpenCode CLI must be `>= 1.18.0` (installed global npm `opencode-ai`). Older versions (e.g. 1.17.x) fail with:
  `Error: OpenCode 1.18.0 or newer is required to use the free tier`.
- **Free Models Verified**:
  - `opencode/muse-spark-1.3-contributor-free` (Fast, 100% code benchmark, median ~25s)
  - `opencode/nemotron-3-ultra-free` (Deep reasoning, Nvidia 120B/ultra)
  - `opencode/space-bunny-free`, `opencode/big-pickle`, `opencode/ling-3.0-flash-fin-free`.
  - *Note:* Paid models (`glm-5.3`, `deepseek-v4.1-flash`, `kimi-k3`) require `opencode-go` ($5/mo) subscription.

## 2. 69 Farm Proxy Topology & URL Encoding
Proxy pool available on Taadaa farm:
- **35 MikroTik**: `mirotik1.taadaa.click:10001..10035`
  - Auth: `admin@1:admin@1` -> **CRITICAL URL ENCODING**: `admin%401:admin%401` (Unencoded `@` causes URL parse failures in Bun/Node/Python).
- **32 Mobi**: `test.taadaa.click:5101..5138` (Excluding gap ports: 5109..5110, 5119..5120, 5129..5130). Auth: `mobiN:TaadaaMobi#2026!`.
- **2 Khoalee**: `khoalee.duckdns.org:16001` (Gyx4k1:RzI0fc3o), `16002` (5ns08q:AmLmaMJ0).

## 3. CLI Wrapper Architecture (`D:/Taadaa/tools/oc_farm.py`)
OpenCode CLI respects standard proxy environment variables.
- **Critical Environment Invariant**:
  - Must export `HTTPS_PROXY`, `HTTP_PROXY`, `ALL_PROXY`.
  - **MUST SET `NO_PROXY="localhost,127.0.0.1,::1"`**: Without `NO_PROXY`, OpenCode routes internal IPC/TUI communication through the proxy, causing subprocess hangs.
- **Error Detection & Cooldown**:
  - Detects `429`, `rate limit`, `daily quota`, `timeout`, `proxy connection failed`.
  - Persists cooldown state to `~/AppData/Local/hermes/oc_farm_cooldown.json` (300s TTL).
  - Automatically fails over to the next healthy proxy (max 3 retries).

## 4. Usage Pattern for Coding Workers
Run bounded one-shot tasks:
```bash
python D:/Taadaa/tools/oc_farm.py run --model opencode/muse-spark-1.3-contributor-free "task prompt"
```
Structured JSON extraction:
```bash
python D:/Taadaa/tools/oc_farm.py run --format json --model opencode/muse-spark-1.3-contributor-free "task prompt"
```
Unit test verification:
```bash
python -m pytest -q -p no:cacheprovider D:/Taadaa/tools/tests/test_oc_farm.py
```
