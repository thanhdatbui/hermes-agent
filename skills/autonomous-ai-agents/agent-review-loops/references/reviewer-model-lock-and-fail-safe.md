# Strict Model Locking & Fail-Safe Architecture for Review Gates

## 1. Context & Incident Anatomy
During automated closeout review loops, subagents or automated runners may attempt to inspect model endpoints (e.g. via `GET /v1/models` on OmniRoute `:20129`) and encounter bare model IDs such as:
- `chatgpt-web/gpt-5.6-sol-pro`
- `chatgpt-web/gpt-5.6-sol-instant`

### The Failure Cascade
1. **Agent Over-Engineering:** The subagent assumes that `sol-pro` provides stricter or higher quality audit criteria and explicitly overrides `--model chatgpt-web/gpt-5.6-sol-pro`.
2. **Quota Exhaustion:** ChatGPT Web Plus accounts allocate a very narrow quota window for `pro` lanes (often single-digit requests per 3–5 hour window). Requesting `sol-pro` on web pool connections immediately triggers `[502]: You've hit your limit. Please try again later.`.
3. **Improper Fallback / Downgrade:** After receiving a 502 error, the agent attempts to "firefight" by dynamically downgrading to `chatgpt-web/gpt-5.6-sol-instant` (zero-thinking lane), undermining review rigor and producing inconsistent scorecards.

---

## 2. The 3-Tier Defense-in-Depth Principle ("Strip & Freeze")

Reviewer model selection MUST NOT be driven by dynamic agent discretion. It must be locked and enforced across three distinct boundaries:

### Tier 1: CLI Script Boundary (`closeout_gate.py`)
- **Default Freeze:** The default model MUST be `"review"`.
- **Strict Whitelist & Rejection:**
  - Whitelist allowed values: `{"review", "chatgpt-web/gpt-5.6-sol-high"}`.
  - If any forbidden model flag is passed (matching `sol-pro`, `sol-instant`, `pro`, `instant`), immediately abort with exit code `2` (Config Violation):
    ```python
    FORBIDDEN_MODELS = {"chatgpt-web/gpt-5.6-sol-pro", "chatgpt-web/gpt-5.6-sol-instant"}
    if args.model in FORBIDDEN_MODELS or ("sol-pro" in args.model) or ("sol-instant" in args.model):
        print(f"[FATAL] Model drift detected: {args.model}. Review gate requires combo 'review' or 'sol-high'.", file=sys.stderr)
        sys.exit(2)
    ```
- **Fail-Closed Retry Discipline:** When encountering HTTP 502 / Rate Limit errors, the script must retry the **same model** after a backoff (`sleep 30-60s`) across the pool. It must NEVER downgrade to a lower-tier thinking model.

### Tier 2: Shell Hook Boundary (`guard_model_drift.py`)
- In Hermes Pre-Tool Execution (`pre_tool_call`), intercept commands calling `closeout_gate.py`:
  ```python
  FORBIDDEN_PATTERNS = [
      r"closeout_gate\.py.*--model.*(sol-pro|sol-instant|pro|instant)",
  ]
  ```
- Reject forbidden execution patterns before the shell process even spawns.

### Tier 3: OmniRoute Proxy Boundary (`:20129`)
- Configure combo `review` as the sole canonical entry point for automated closeout audits.
- Map combo `review` to the 16-account round-robin pool with `chatgpt-web/gpt-5.6-sol-high` as Tier 0.
- Rewrite or block incoming bare `sol-pro` requests originating from audit callers to prevent accidental quota burn on web pool accounts.
