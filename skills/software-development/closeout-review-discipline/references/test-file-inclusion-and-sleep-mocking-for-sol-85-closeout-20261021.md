# Test-File Inclusion, Mock Sleep Fast-Path & Sol 85 Closeout Remediation

## Context & Incident (2026-10-21)
During closeout of follow failure-accounting and IP breaker isolation (`tiktok-follow`), the commit touched `follow_runner/flows/mode2_follow_followers.py`, `follow_runner/flows/verify_follow.py`, `follow_runner/core/follow_state.py`, and `follow_runner/run_follow.py`.

### 1. Test Discovery Scope Omission Trap (Score 70 -> 76 Plateau)
- `closeout_gate.py` discovers focused tests by matching modified files in the diff.
- In Strike 1 & 2, while `mode2_follow_followers.py` was in the diff, its corresponding test file `follow_runner/tests/test_mode2_follow_followers.py` was NOT modified in the commit.
- Consequently, `closeout_gate.py` only ran `test_cli.py`, `test_follow_state.py`, and `test_verify_follow.py` (146 passed).
- Reviewer Sol High flagged this explicitly:
  *"test_mode2_follow_followers.py được liệt kê trong tài liệu là regression test liên quan nhưng không nằm trong lệnh test đã thực thi... Các assertion cụ thể cho nhánh anchor tap, identity uncertainty và identity-bound not_followed chưa được chứng minh bằng bằng chứng hiện trường."*
  and capped score at 76/100 (REJECTED).

### 2. Deep Sleep In Flow -> Pytest 35s Timeout Trap
- When writing focused unit tests exercising `_ensure_anchor_followed`, the flow had multiple live sleeps:
  `time.sleep(random.uniform(2.0, 4.0))`, `time.sleep(1.5)`, `time.sleep(1.2)`.
- Without mocking, pytest hit the 35s subprocess timeout (`exit 124`).
- **Remediation:** In unit tests calling deep flow functions, always monkeypatch `time.sleep`:
  ```python
  monkeypatch.setattr(flow.time, "sleep", lambda *a: None)
  ```
  This reduces execution time from 35s (timeout) to 1.24s clean.

### 3. Direct Test Pairing for Sol 85+ (APPROVED)
- In Strike 2 Remediation, adding focused unit tests directly to `follow_runner/tests/test_mode2_follow_followers.py`:
  - `test_ensure_anchor_followed_uncertainty_returns_manual`: proves that identity mismatch or undelivered tap returns `MANUAL_REVIEW` and never calls `set_follow_failed()`.
  - `test_ensure_anchor_followed_confirmed_drop_sets_follow_failed`: proves that identity OK and delivered tap returns `FOLLOW_FAILED` and calls `set_follow_failed()`.
- Once `test_mode2_follow_followers.py` was included in the commit, `closeout_gate.py` automatically picked it up, ran all 358 tests, and Sol Reviewer awarded **85/100 (APPROVED)** with `CLOSEOUT_TOKEN` issued.

## Key Rules
1. Every modified production flow module MUST have corresponding test assertions committed in its test file (`test_<stem>.py`) so `closeout_gate.py` includes it in the verified execution log.
2. In tests calling multi-step production flows, always monkeypatch `time.sleep` to prevent closeout test timeouts.
3. Assertions must verify both the negative path (uncertainty -> no state mutation, manual review) and positive path (confirmed drop -> state mutation, failure status).
