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
