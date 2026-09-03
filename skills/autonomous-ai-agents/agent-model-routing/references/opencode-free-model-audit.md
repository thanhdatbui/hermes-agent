# OpenCode Free-Model Audit — evaluation matrix & workflow

Session: 2026-08-06, Taadaa. Goal: add a free audit layer BEFORE Gemini in the
audit chain, WITHOUT duplicating the user's primary model family (DeepSeek).

## The user correction (why this reference exists)

Initial choice was `opencode/deepseek-v4-flash-free` (first free model seen in
`opencode models`). User rejected it: "t bảo kiểm tra opencode có những model
nào chưa gì đã lấy deepseek ra chạy r, hiện tại đang dùng deepseek còn gọi
deepseek của nó hơi bị trùng ấy, nó có mấy model free khác nữa mà".

**Lesson: check the full free-model list BEFORE picking, and avoid a model from
the same family as the session's primary model.** `opencode models | grep -i free`.

## Free models available (opencode CLI 1.17.19, 2026-08-06)

```
opencode/deepseek-v4-flash-free   # SAME family as Hermes primary → rejected
opencode/laguna-s-2.1-free
opencode/ling-3.0-flash-free      # ← CHOSEN
opencode/longcat-2.0-free
opencode/mimo-v2.5-free
opencode/nemotron-3-ultra-free
opencode/north-mini-code-free
freemodel/* (gpt-5.6-luna/terra/sol, claude-*, gpt-5.3-codex...)  # 401 Insufficient balance
```

## Test matrix (live results, `opencode run` + `--agent taadaa-review --format json`)

| Model | Smoke (`Reply OK`) | Agent+json audit | Verdict quality | Verdict |
|---|---|---|---|---|
| `deepseek-v4-flash-free` | OK | OK | reads file, findings | APPROVE_WITH_FIXES (6 findings) — but duplicates user's family |
| `nemotron-3-ultra-free` | OK (text mode) | **502 ResourceExhausted** (Nvidia worker limit 32/32) | — | unusable with agent+json |
| `ling-3.0-flash-free` | OK | OK | reads file, line-level findings, real verdict | APPROVE |
| `mimo-v2.5-free` | OK | OK but returns the **VERDICT template itself** (echoes format, no real audit) | fake | reject |
| `laguna-s-2.1-free` | OK | no output / fails | — | reject |
| `longcat-2.0-free`, `north-mini-code-free` | OK | not tested for audit | — | untested |

**Conclusion: `ling-3.0-flash-free`** — stable, real audit behavior, and NOT
DeepSeek-family.

## Reusable evaluation workflow

1. `opencode models 2>&1 | grep -iE '^opencode/.+-free'` — enumerate free models.
2. Smoke each: `opencode run --dir <real-repo> --model <m> "Reply with exactly: OK"`.
   (Note: `/tmp` does NOT exist on Windows git-bash; use a real dir like `D:\Taadaa`.)
3. Audit-test each candidate with the REAL wrapper args:
   `opencode run --dir <repo> --agent taadaa-review --format json --model <m> "<audit prompt>"`
   — this is the load that exposes 502 limits and template-echo behavior.
4. Inspect the JSONL report: it is **UTF-16 encoded**; read with
   `open(..., 'rb').read().decode('utf-16')`, then collect
   `part.type == 'text'` blocks for the verdict.
5. Update the wrapper pin: `$preferredFreeModel = 'opencode/<winner>-free'` in
   `D:\Taadaa\tools\invoke-opencode-audit.ps1`.
6. Verify end-to-end via the wrapper (exit 0 + report contains `VERDICT`).

## Wrapper facts

- `D:\Taadaa\tools\invoke-opencode-audit.ps1` — param `-Prompt` (string) +
  `-OutputDirectory`; uses `opencode run --dir <repo> --agent taadaa-review
  --format json --model <pin> "<auditPrompt>"`.
- **Cascade (UPGRADED 2026-08-06, replaces single-pin):** `$models = @(
  'opencode/nemotron-3-ultra-free',   # strongest, may 502
  'opencode/ling-3.0-flash-free',     # verified stable
  'opencode/longcat-2.0-free',        # verified
  'opencode/north-mini-code-free'     # light fallback
  )` — strong→weak; on classified quota/capacity failure (`quota|429|502|
  ResourceExhausted|...` regex) it logs `OPENCODE_AUDIT_CASCADE_TO=<next>` and
  `continue`s; only when ALL models fail does it throw
  `OPENCODE_AUDIT_MODEL_UNAVAILABLE`. Explicit `-Model` overrides to a single
  pinned model (validated against the allowed list). Live-verified: nemotron
  502 → ling succeeded (exit 0, report with VERDICT).
- On non-quota failure it throws `OPENCODE_AUDIT_FAILED_NON_QUOTA_EXIT_<code>`
  (e.g. exit 1) — that still aborts, it does not cascade (cascade is
  quota/capacity-only by design).
- `--format json` output is UTF-16 JSONL; `--format text` is human-readable.
- **Coverage limitation (2026-08-06):** on a 25-file AGENTS.md workspace,
  nemotron reads only ~4 files before its context fills and it reports
  "BLOCKED / need to read remaining files" — even when everything is clean.
  For bulk policy audits, trust the deterministic scan (grep/script across all
  files) over the model's coverage claim; treat a model "BLOCKED" as
  inconclusive, not as evidence of a real problem.

## Related pitfall

Gemini wrapper `invoke-gemini-9router-audit.ps1` is BROKEN (SHA256.HashData
missing on old PowerShell + 400 Invalid JSON with large context) — Gemini audit
currently works only via direct 9router call (curl/urllib with
`model: gemini/gemini-3.6-flash`, `reasoning_effort: high`). This is why the
OpenCode layer now sits before Gemini in the chain.
