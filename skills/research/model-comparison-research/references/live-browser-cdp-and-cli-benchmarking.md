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
   - Headless CLI tools (like `agy.exe`) streaming thinking/reasoning responses for large multi-class Python modules (>100 lines) take 50s to 200s.
   - Setting `timeout=60s` or `120s` kills the subprocess mid-stream, returning empty output (`0 chars`) and causing false diagnoses of network or token death.
   - Set CLI subprocess timeouts to at least 300s (5m) for code questions and 600s for repository-level tasks.

4. **Zero-Tolerance Anti-Fabrication Rule:**
   - Never generate comparative analysis, commentary, or scores based on exit codes, character counts, or `ast.parse` status alone.
   - Verify that the response text contains domain-specific identifiers matching the exact prompt (e.g., DCT matrix logic for pHash, bounds calculation for XML parser, circuit breaker states for proxy pool).
   - Display raw head and tail code snippets directly to the user to prove authenticity.
