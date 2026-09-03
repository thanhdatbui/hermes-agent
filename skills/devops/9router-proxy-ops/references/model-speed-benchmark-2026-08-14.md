# Model speed & quality benchmark — automation task (2026-08-14)

4 rounds per model, same real automation task (fix `check_lock`: expiry-missing → STALE,
naive-tz → UTC epoch, aware-tz → epoch), max_tokens 800, non-stream via 9router
`/v1/chat/completions`, prompt in Vietnamese. Machine: kibe.

## Own measurements (4 rounds)

| Model (route) | V1 | V2 | V3 | V4 | TB | finish |
|---|---|---|---|---|---|---|
| deepseek-v4-flash (combo, cmc) | 3.2s | 8.1s | 9.2s | 7.7s | **7.1s** | **length, content EMPTY 4/4** |
| claude-sonnet-4-6 (ag/*) | 5.0s | 5.0s | 5.1s | 5.9s | **5.3s** | stop, full code |
| gpt-5.6-luna (cx/*) | 32.7s | 69.4s | 51.9s | 83.3s | **59.3s** | stop, full code |

- **deepseek-v4-flash: long task via non-stream → `finish_reason:length` + empty content
  EVERY round** (reasoning tokens eat the 800 budget). Fine for short tasks; unusable for
  long-code non-stream requests. Stream or higher max_tokens needed.
- **claude-sonnet-4-6: fastest stable + best semantics** — returned `LOCKED` for an
  unexpired foreign lock; luna returned `OTHER` (vague). Both handled both bug cases correctly.
- **gpt-5.6-luna: ~11× slower than sonnet-4-6** on the same task. Backup-only for automation.

## Published numbers (benchlm.ai, updated 2026-08-14)

Sonnet 4.6 vs DeepSeek V4 Pro 0813 (closest published pair; Pro ≥ Flash so treat as Flash upper bound):

| Benchmark | Claude Sonnet 4.6 | DeepSeek V4 Pro 0813 |
|---|---|---|
| Overall | **64.4/100** | 61.0/100 |
| SWE-bench Verified | 79.6% | 80.6% |
| MMLU-Pro | 79.2% | 87.5% |
| Reasoning (MRCR 1M) | **83.5%** | 67.2% |
| GPQA | 77.0 | ~67.9 |

Mindstudio blog (no numbers): "DeepSeek V4 Flash strong price-performance + coding chops;
Claude Sonnet 4.6 strong agentic reasoning, tool use, instruction fidelity."

## Takeaway for Taadaa automation routing

- Simple/repetitive scripts (reconcile, lock, batch) → deepseek-v4-flash (fast, cheap) but keep
  responses short or stream.
- Logic-heavy fix/review → claude-sonnet-4-6 (5.3s, correct semantics, reasoning 83.5 vs 67.2).
- gpt-5.6-luna → backup only (59s).
- Sonnet 5 (Claude CLI only) costs ~32% more than 4-6 by API estimate; use for tasks beyond 4-6.
