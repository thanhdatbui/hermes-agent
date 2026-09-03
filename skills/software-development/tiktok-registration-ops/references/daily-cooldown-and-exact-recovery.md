# Daily registration cooldown and exact-scope recovery

## Rules

- One machine may register at most once per calendar day.
- Record cooldown only after verified success: `SUCCESS` plus final TikTok/profile proof and a valid result artifact. Do not cooldown `PENDING`, timeout, UI error, rate-limit, or handoff.
- Store local state atomically with `reg_success_date`, `cooldown_until`, and `reason`; detector skips active cooldown before batch construction.
- Recovery is exact-scope. Read failed STTs from the specified run's `all_results.json`; build a dedicated recovery manifest. Never call the full pending detector as a recovery substitute.
- Verify the entrypoint's actual manifest path. A similarly named `_clean_targets.json` is not evidence that the runner will use it.
- Before launching devices, print and compare `target_stts` with the approved failed list. If scope differs, stop.
- Reports must separate `started`, `skipped_daily_cooldown`, `skipped_locked`, `success`, `failed`, and `blocked`.
- User escalation is for unfamiliar UI, rate-limit/captcha, ADB/proxy blockers, or exhausted meaningful attempts. Known recoverable errors should use a tested handler while preserving lock and artifacts.

## Incident lesson

A run with 19 failures was accidentally rerun as a 71-target pending batch because the runner regenerated and consumed `runtime/artifacts/pending/tiktok_reg_clean_targets.json`; editing a similarly named root manifest did not constrain it. Always inspect `_run_all_targets.py` and assert the actual manifest before any recovery launch.
