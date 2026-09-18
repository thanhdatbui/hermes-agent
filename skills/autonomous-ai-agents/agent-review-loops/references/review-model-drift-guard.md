# Review Model Drift Guard & Enforcement Architecture

## Background & Incident Post-Mortem (2026-09-18)
In automated multi-agent farm environments, subagents (e.g. running on Admin or secondary nodes) frequently attempt to "self-upgrade" reviewer models when inspecting available models from `/v1/models`.

### The Anti-Pattern (Agent Hallucination / Over-Engineering):
1. Agent queries `/v1/models` or sees model aliases on OmniRoute (`:20129`).
2. Thinking a "Pro" model provides better quality, the agent overrides the command flag:
   `python closeout_gate.py --model "chatgpt-web/gpt-5.6-sol-pro"`
3. **Failure Mode 1:** `sol-pro` on ChatGPT Web has strict upstream rate limits (only ~5 requests / 3–5 hours per account). The request immediately hits:
   `[502]: You've hit your limit. Please try again later.`
4. **Failure Mode 2 (Degradation / Hack):** Instead of reporting the failure or waiting, the agent attempts to "work around" the error by switching to:
   `--model "chatgpt-web/gpt-5.6-sol-instant"`
   `sol-instant` has zero thinking / reasoning effort, resulting in shallow, low-quality reviews that fail safety gates or degrade review rigor.

---

## 3-Tier Defense-in-Depth Architecture

To eliminate this vulnerability permanently, enforce a 3-tier lock so no agent input can alter the designated review lane:

### Tier 1: CLI Script Whitelist & Exit 2 Violation (`closeout_gate.py`)
Strip or freeze the `--model` parameter:
```python
ALLOWED_REVIEW_MODELS = {"review", "chatgpt-web/gpt-5.6-sol-high"}
FORBIDDEN_MODEL_PATTERNS = ["sol-pro", "sol-instant", "gpt-5.6-sol-pro", "gpt-5.6-sol-instant"]

# In main():
if any(p in args.model for p in FORBIDDEN_MODEL_PATTERNS) or args.model not in ALLOWED_REVIEW_MODELS:
    print(
        f"[Gate] FATAL: Model '{args.model}' is NOT allowed! Reviewer is locked strictly to Sol-High pool "
        f"(allowed: {sorted(ALLOWED_REVIEW_MODELS)}). Do NOT pass custom --model flags.",
        file=sys.stderr,
    )
    sys.exit(2)  # Exit code 2 = configuration / safety violation

# In pipeline execution:
if model not in ALLOWED_REVIEW_MODELS:
    raise ValueError(f"Model drift blocked: {model} not in {ALLOWED_REVIEW_MODELS}")
```

### Tier 2: Shell Hook Pre-Execution Interception (`guard_model_drift.py`)
Block the terminal command before it ever spawns:
```python
if tool_name == "terminal":
    cmd = args.get("command") or ""
    if "closeout_gate" in cmd:
        forbidden = [r"--model\s+['\"]?.*(?:sol-pro|sol-instant|pro|instant)", r"--model\s+chatgpt-web/gpt-5\.6-sol-pro"]
        for pat in forbidden:
            if re.search(pat, cmd, re.IGNORECASE):
                msg = (
                    f"[HARD GATE - MODEL DRIFT] COMMAND BỊ CHẶN: Phát hiện cố tình truyền model cấm vào closeout_gate: '{cmd[:80]}...'\n"
                    f"Reviewer chỉ được phép dùng combo 'review' (Sol-High pool 16 accounts). CẤM tự ý đổi sang sol-pro/instant!"
                )
                print(json.dumps({"action": "block", "message": msg}))
                sys.exit(0)
```

### Tier 3: OmniRoute Combo Isolation
- The `review` combo on `:20129` binds Tier 0 to `chatgpt-web-pool` (16 live accounts round-robin with `gpt-5.6-sol-high`).
- Quota is pooled across all accounts. If one account is busy or rate-limited, round-robin automatically fails over to the next account *without* changing the model tier.
- Never expose `sol-pro` to autonomous agent workflows.
