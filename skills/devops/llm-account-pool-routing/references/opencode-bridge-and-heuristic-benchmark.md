# OpenCode Bridge, Native Vision & Daily Heuristic Model Benchmark

## Overview
Hermes uses `custom:opencode` (`http://127.0.0.1:20130/v1`) as the immediate fallback provider after the primary model (`omni-worker`). The bridge connects Hermes to the local OpenCode CLI via `D:/Taadaa/tools/oc_farm.py` across 69 farm proxies (35 MikroTik, 32 Mobi, 2 Khoalee).

## 1. Native Vision Architecture in OpenCode CLI
- **Multimodal Support**: `opencode/muse-spark-1.3-contributor-free` natively supports vision via the `-f <file_path>` CLI parameter.
- **Payload Handling**: Hermes sends multimodal requests formatted with base64 data URIs (`data:image/...;base64,...`) or `file:///` URLs.
- **Bridge Decoding Workflow**:
  1. Detect `image_url` blocks in incoming messages.
  2. Decode base64 payloads to temporary image files (`.jpg`, `.png`, `.webp`) under Windows `%TEMP%`.
  3. Append `-f <temp_path>` arguments to the `oc_farm.py run` execution command.
  4. Always unlink/clean up temporary image files in the `finally` block of the request handler.

## 2. Dynamic Failover Ladder (Thứ tự Fallback)
Instead of failing immediately when a model hits an upstream rate limit or timeout, `opencode_bridge.py` executes an internal failover ladder with per-model timeouts (35s for text, 45s for vision):

### Default Text Fallback Hierarchy:
1. 🥇 `opencode/muse-spark-1.3-contributor-free`: Top reasoning, 100% code benchmark pass rate, median latency 2-3s.
2. 🥈 `opencode/mimo-v2.6-flash-free`: High speed flash tier (~9s), fallback for load shedding.
3. 🥉 `opencode/nemotron-3-ultra-free`: Strong logical reasoning (~17s), tertiary fallback.
4. 🏅 `opencode/big-pickle`: Final safety net.
- *Excluded*: `opencode/nemotron-3.5-lightning-free` (frequent >20s stalls and connection timeouts).

### Default Vision Fallback Hierarchy:
1. 🥇 `opencode/muse-spark-1.3-contributor-free`: Primary vision model, verified accurate on UI screenshots.
2. 🥈 `opencode/mimo-v2.6-flash-free`: Secondary vision fallback.

## 3. Daily Heuristic Benchmark vs LLM Decision
### Why NOT use LLMs in Cron for Model Selection:
- **Token Inefficiency**: Burning LLM inference to parse model strings wastes budget and adds network latency.
- **Lack of Real-world Network Awareness**: Static LLM prompts cannot observe whether upstream provider servers are currently throttled, timing out, or broken.
- **Hallucination Risk**: LLMs may recommend non-existent or deprecated models.

### Heuristic Benchmark Ping Pattern:
- **Schedule**: Once daily at 06:00 AM (`cron_opencode_model_benchmark.py`, Cron ID: `daily-opencode-model-benchmark`, schedule `0 6 * * *`).
- **Execution Mode**: `no_agent=True` (pure Python subprocess, 0 LLM tokens, silent unless reporting).
- **Test Battery**:
  1. *Speed / Arithmetic Test*: `1+1=?` (timeout 15s) measuring latency in seconds.
  2. *Reasoning / Logic Test*: Vietnamese temporal logic puzzle ("Nếu hôm qua là thứ hai thì ngày mai là thứ mấy?", timeout 20s).
  3. *Vision Test*: Sample UI screenshot verification with `-f` (timeout 25s).
- **Composite Scoring Formula**:
  $$\text{Score} = \text{Logic (40 pts)} + \text{Speed (30 pts)} + \max(0, 15 - \text{Latency} \times 0.75) + \text{Vision Bonus (15 pts)}$$
- **Dynamic Loading**:
  - Results exported to `D:\Taadaa\runtime\kibe\cron-state\opencode_ranked_models.json`.
  - `opencode_bridge.py` reads `ranked_text_models` and `ranked_vision_models` dynamically on each request without requiring bridge restarts.

## 4. Service Watchdog & Self-Healing
- Cổng `:20130` được giám sát bởi `hermes_stale_watchdog.py` mỗi 2 phút.
- If `http://127.0.0.1:20130/health` fails or times out (2s), the watchdog automatically respawns `D:/Taadaa/tools/opencode_bridge.py` in the background.
