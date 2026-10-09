# Dual-answer orchestration canary

## Acceptance matrix

| Input | Primary answer | Advisor call | Expected output |
|---|---:|---:|---|
| `Case này nên xử lý thế nào?` | yes | exactly 1 | primary text plus `Advisor (Sol / review)` section |
| `Có nên clear data không?` | yes | exactly 1 | primary text plus structured Advisor advice |
| `Chạy script follow máy 3` | yes | 0 | primary answer only |
| `Kiểm tra log máy 2` | yes | 0 | normal command workflow |
| advice question + Advisor timeout | yes | 1 | primary text plus `Advisor unavailable`; no fabricated recommendation |

## Evidence levels

- **Adapter probe:** calls `advisor_consult` directly and proves only redaction, route, timeout, and response parsing.
- **Dispatcher canary:** invokes the Hermes model-tool dispatch boundary and proves the tool is visible and executable.
- **Orchestration canary:** mocks/controls the primary answer, submits an advice-intent original user message, and proves classifier → one Advisor call → dual composition. This is the required proof for the user's automatic behavior request.
- **Live route probe:** confirms OmniRoute `review` connectivity and latency; report separately from orchestration behavior.

## Failure classification

- Adapter PASS + orchestration not exercised: `INCOMPLETE`, not DONE.
- Advisor timeout with primary preserved: expected degraded success, not a rejection.
- Normal imperative command causing a call: routing bug; fix classifier/guard.
- Advice question with no Advisor section despite successful Advisor response: composition bug.
- More than one call for one user turn: one-call-cap bug.

## Operational constraints

Use synthetic, non-secret evidence. Do not touch ADB, devices, accounts, UI, or production farm state. Keep the Advisor read-only with `tools=[]` and `tool_choice=none`. Preserve unrelated worktree changes and run focused offline tests after the final edit.
