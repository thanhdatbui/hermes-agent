# OpenCode Bridge: Multimodal Vision, Telegram Sync & Fallback Architecture

## Context & Purpose
OpenCode CLI provides free access to high-tier community models (Muse Spark 1.3, MiMo 2.6 Flash, Nemotron 3 Ultra, Big Pickle, etc.) rotated across 69 farm proxies via `oc_farm.py`.
Because Hermes communicates over OpenAI-compatible HTTP endpoints (`/v1/chat/completions`), `D:/Taadaa/tools/opencode_bridge.py` serves as a multi-threaded local adapter on `http://127.0.0.1:20130/v1`.

---

## 1. Native Multimodal / Vision Support via OpenCode CLI
- **CLI Mechanism**: `opencode run` natively accepts image attachments via the `-f <file_path>` argument.
- **Bridge Translation Pipeline**:
  1. Incoming HTTP requests from Hermes contain multimodal content blocks (`image_url` formatted as `data:image/...;base64,...` or `file:///...`).
  2. `opencode_bridge.py` decodes base64 payload into a temporary image file (`.jpg`, `.png`, `.webp`) in OS temp directory.
  3. Appends `-f <temp_file>` to the `oc_farm.py run` command.
  4. Guarantees temp file deletion in a `finally` block to prevent disk bloat.
- **Model Vision Capability**:
  - `opencode/muse-spark-1.3-contributor-free`: Natively processes images and answers detailed visual queries in ~3–4 seconds.
  - Other models (e.g. `mimo-v2.6-flash-free`, `nemotron-3.5-lightning`): May timeout (>30s) or fail on image processing.

---

## 2. Pinned Fallback Philosophy (Anti-Overengineering)
- **User Correction & Directive**:
  - Do NOT deploy complex LLM-driven daily benchmarks or automated shifting ladders across different models in OpenCode.
  - Do NOT guess or automatically change the user's fallback target.
- **Deterministic Pinning**:
  - Fallback is pinned directly to `muse-spark-1.3`:
    $$\text{Primary (omni-worker)} \longrightarrow \text{Fallback 1: muse-spark-1.3 (custom:opencode)} \longrightarrow \text{Fallback 2: cx/gpt-5.6-luna-high (custom:omni)}$$
  - `opencode_bridge.py` executes the exact requested model directly. If the user wants a different model, they manually switch via Telegram `/model`.

---

## 3. Automated Non-LLM Model Catalog Sync to Telegram
- **Problem**: When OpenCode releases new free models, `config.yaml` of Hermes is not aware of them unless updated, preventing users from seeing or switching to them via `/model`.
- **Solution (`cron_sync_opencode_models_to_hermes.py`)**:
  - **Cron ID**: `sync-opencode-models-to-hermes` (Schedule: `0 */6 * * *`).
  - **Execution Mode**: `no_agent=True` (pure Python script, 0 LLM tokens, executes in <0.3s).
  - **Pipeline**:
    1. Scans `opencode models` CLI.
    2. Strips vendor prefixes and extracts clean model names (`muse-spark-1.3`, `mimo-v2.6-flash`, `nemotron-3-ultra`, `big-pickle`, `space-bunny`, `longcat-2.5-preview`, etc.).
    3. Safely updates `custom_providers.opencode.models` in `C:\Users\Kibe\AppData\Local\hermes\config.yaml` with `context_length: 128000`.
    4. Generates user-friendly short aliases in `model.aliases`:
       * `/model muse` $\rightarrow$ `muse-spark-1.3`
       * `/model mimo` $\rightarrow$ `mimo-v2.6-flash`
       * `/model nemotron` $\rightarrow$ `nemotron-3-ultra`
       * `/model nemotron-3.5` $\rightarrow$ `nemotron-3.5-lightning`
       * `/model pickle` $\rightarrow$ `big-pickle`
       * `/model longcat` $\rightarrow$ `longcat-2.5-preview`
       * `/model bunny` $\rightarrow$ `space-bunny`
       * `/model ling` $\rightarrow$ `ling-3.0-flash-fin`
    5. **Silent Watchdog Discipline**: Produces empty stdout when catalog is unchanged (no Telegram spam). Only delivers a message when a new model is detected.

---

## 4. Bridge Service Watchdog Integration
- `opencode_bridge.py` is monitored by `hermes_stale_watchdog.py` (running every 2 minutes).
- Every tick probes `http://127.0.0.1:20130/health` with a 2s timeout.
- If port 20130 is down (e.g. after Windows reboot or process crash), the watchdog immediately spawns `python D:/Taadaa/tools/opencode_bridge.py` in the background, guaranteeing permanent availability.

---

## 5. Anti-Freeze Discipline for Model Probes
- **User Frustration Incident**: Running sequential blocking benchmark probes in foreground terminal with 30–60s timeouts on slow/unresponsive upstream models freezes the coordinator turn for >90s.
- **Rule**:
  - Any model health check or probe on untrusted/slow remote models MUST use tight timeouts ($\le 15$s) or be dispatched to a background process (`terminal(background=True, notify_on_complete=True)`).
  - Never run multiple sequential blocking probes in the main interaction loop.
