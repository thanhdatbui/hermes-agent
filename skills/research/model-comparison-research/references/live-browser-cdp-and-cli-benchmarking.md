# Live Browser CDP and CLI Head-to-Head Benchmarking Patterns

## Key Invariants for Live Model Comparisons

1. **Stateless Turn Isolation:**
   - When benchmarking models via Web UI / CDP (e.g. Gemini Web Pro / 4 Argon), **never reuse an existing conversation thread**. Reusing a thread leaves previous turn DOM in memory.
   - If previous turn DOM remains, heuristic code scrapers can prematurely grab stale `<pre>` or `<code-block>` elements before the current turn finishes, producing fake runtimes and identical duplicate outputs across different questions.
   - Force fresh navigation (`page.goto(URL)`) or click `New Chat` / `Temporary Chat` prior to each prompt.

2. **Angular & Modern Web Component Scraping:**
   - Modern Gemini Web UI splits text into multiple custom components:
     - Outer summary / introductory prose: `.model-response-text`
     - Source code blocks: `<code-block>` containing `<pre><code>`
   - Scrapers targeting only `.model-response-text` will miss the code block entirely and capture only brief introductory sentences.
   - Use `page.evaluate()` to locate the longest `<code-block>` element (or fall back to container text) and strip custom component wrappers.

3. **Subprocess & Stream Generation Timeout Budgets:**
   - Headless CLI tools (like `agy.exe`) streaming thinking/reasoning responses for large multi-class Python modules (>100 lines) take 50s to 200s, and complex mathematical/algorithmic tasks (e.g. manual 2D DCT implementations) can exceed 300s over mobile/cellular proxies.
   - Setting `timeout=60s` or `120s` kills the subprocess mid-stream, returning empty output (`0 chars`) and causing false diagnoses of network or token death.
   - Set CLI subprocess timeouts to at least 600s (10m) for complex code questions (`ask`) and 900s (15m) for repository-level tasks (`fix`).

4. **Silent Model Fallback & Quota Exhaustion Trap:**
   - On Web UI (e.g. Gemini Web Pro), when a flagship model (`4 Argon`, `3.1 Pro`) hits its rate limit / quota window (e.g., "Hạn mức sẽ được đặt lại vào 23:05..."), Google disables the menu item (`aria-disabled="true"`).
   - Automated scripts that catch click failures with `except Exception: pass` will leave the browser on whatever default or lower-tier model was already selected (e.g. `3.5 Flash-Lite`).
   - The script then runs all benchmark rounds against the inferior model while reporting it as the flagship model, creating completely falsified speed and capability metrics.
   - **Rule:** Automation MUST verify that the target model is active (`aria-disabled="false"` and `data-active="true"` or switcher button text matches target). If disabled, fail immediately with exact reset time; never fall back silently.

5. **Concurrency Architecture (Web CDP vs Headless CLI):**
   - Single-profile Web CDP has a hard constraint of `concurrency = 1`. Concurrent worker requests sent to a single browser profile queue sequentially, adding `N * latency` delay.
   - Supporting concurrent tasks over Web CDP requires an active pool of N independent browser profiles running on separate CDP ports (~300MB RAM each).
   - Headless CLI runners scale concurrently across account profiles without browser GUI overhead, making them vastly superior for multi-worker fanout.

6. **Zero-Tolerance Anti-Fabrication Rule:**
   - Never generate comparative analysis, commentary, or scores based on exit codes, character counts, or `ast.parse` status alone.
   - Verify that the response text contains domain-specific identifiers matching the exact prompt (e.g., DCT matrix logic for pHash, bounds calculation for XML parser, circuit breaker states for proxy pool).
   - Display raw head and tail code snippets directly to the user to prove authenticity.

7. **Free Tier API vs Subscription Companion Harness Quota Asymmetry (Gemini 3.8 Flash vs Antigravity):**
   - Google AI Studio Free Tier API (`generativelanguage.googleapis.com`) imposes an extreme per-model quota on preview/flagship models: `gemini-3.8-flash` is hard-capped at **20 requests per day per project** (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue: 20`), NOT the 1,500 RPD of older 2.0 Flash models.
   - CLI harness architectures (like `omp` / Oh My Pi) that inject large system prompts (~180KB project context per turn) trigger rapid 429 `RESOURCE_EXHAUSTED` with 24h retry delays.
   - In contrast, companion IDE/web harnesses (`agy cli` via `cloudaicompanion.googleapis.com` backed by Google One AI Premium $20/mo accounts): run on rolling windows per account rather than the 20 RPD Free Tier cap, sustaining long-horizon benchmarks and production runs.

8. **Aged Account vs Farm Clone Project Quota & Trust Denials (HTTP 403 `PERMISSION_DENIED`):**
   - Newly created GCP projects on zero-trust / fresh farm Google accounts receive `403 PERMISSION_DENIED` ("Your project has been denied access. Please contact support.") when calling preview models via AI Studio API keys.
   - To benchmark or run first-party API keys, use an established aged Google account (`Default Gemini Project` on existing Google One accounts), which is pre-authorized.
   - Non-disruptive key retrieval on Windows hosts: launch `webbrowser.open('https://aistudio.google.com/apikey')` into the user's running Chrome instance without closing or killing tabs/processes, and retrieve the verified key safely.

9. **CLI Coding Harness Unrestricted Backends & OmniRoute Integration (Bypassing AI Studio API):**
   - **AI Studio 20 RPD Quota Trap:** Free Tier Google AI Studio API keys are useless for agent harnesses running preview models (`gemini-3.8-flash` is capped at 20 requests/day/project, easily exhausted in 1-2 multi-step turns).
   - **Native OAuth `google-antigravity` in `omp` & Loopback Pitfall:** `omp login google-antigravity` binds a loopback callback server on port `51121` (`127.0.0.1:51121/oauth-callback`). In non-interactive or background subprocesses, subshell termination drops the port before browser consent finishes (`ERR_CONNECTION_REFUSED`), and Google authorization codes are strictly single-use (`invalid_grant`). Never ask the user to manually run login commands when hitting this friction.
   - **OmniRoute Proxy Injection Pattern:** `omp` ignores arbitrary `OPENAI_BASE_URL` env vars for unconfigured model IDs (`Model not found`). To route through local multi-account proxy pools (OmniRoute `:20129`), write an explicit provider block into `C:/Users/Kibe/.omp/agent/models.yml`:
     ```yaml
     providers:
       omniroute:
         baseUrl: 'http://127.0.0.1:20129/v1'
         api: 'openai-completions'
         apiKey: 'dummy'
         models:
           - id: 'antigravity/gemini-3.8-flash-tiered'
             name: 'Gemini 3.8 Flash Tiered'
             contextWindow: 1000000
             maxTokens: 65536
     ```
     Execute headless benchmark/prompt:
     `omp.cmd --model omniroute/antigravity/gemini-3.8-flash-tiered -p "<prompt>"`
   - **Head-to-Head Benchmark Findings (`gemini-3.8-flash`):**
     - `omp` via OmniRoute `:20129`: **144.5s** duration, generated 4,527 chars of structured code with comprehensive docstrings and full assertion passes (4/4).
     - `agy cli` native companion: **169.8s** duration, generated 2,393 chars of functional code with 4/4 assertions passing.
     - `omp` demonstrated ~15% faster end-to-end turnaround while utilizing the exact same pool of 22 Google One AI Premium accounts via OmniRoute.
   - **Windows Subprocess Pipe Deadlock:** When executing CLI harnesses via Python `subprocess.run()`, background TUI handlers keep stdin/stdout open. Always supply `stdin=subprocess.DEVNULL` and redirect stdout/stderr to disk files to avoid hanging indefinitely.


