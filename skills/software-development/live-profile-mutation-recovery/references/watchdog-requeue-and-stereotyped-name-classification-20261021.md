# Watchdog Re-queue Contract & Natural Display Name Classification (2026-10-21)

## 1. Watchdog Re-queue & State Machine Invariant

When running continuous fleet-wide profile mutations (such as nickname renames, bio updates, avatar changes):

### State Machine as the Single Source of Truth
- The state file (e.g. `rename_natural_state.json`) records ONLY accounts that have reached verifiable completion (`verified = True`, `has_valid_proof = True` with valid PNG magic bytes `\x89PNG\r\n\x1a\n`).
- **Never Record Failed Attempts:** If a worker aborts (`exit_1`, `exit_2`, timeout, unhandled exception, or missing proof file), the failure is logged via telemetry/stdout (`_fail(m, u, reason)`), but **strictly omitted from the state file**.
- **Automatic Re-queueing:** On every scheduled cycle (e.g., every 15 minutes during farm idle windows), candidate accounts are re-loaded from the central spreadsheet and filtered against the state file:
  ```python
  if u in state and (datetime.now() - datetime.fromisoformat(state[u].get("renamed_at", "2000-01-01"))).days < COOLDOWN_DAYS:
      continue
  targets.append(cand)
  ```
- Because failed accounts are not present in `state`, they remain in the eligible candidate pool and are automatically re-queued without manual operator intervention.
- **Production Evidence:** On Machine 31, account `@nana34874` failed at 09:46 (`exit_2` due to cold-boot splash latency), remained unrecorded in state, and was automatically re-queued at 10:04, successfully completing rename to `'Tôn Hải Hoa'` (`m31_nana34874_rename_confirmed.png`).

---

## 2. Natural Display Name vs Stereotyped Name Classification

When classifying existing display names on the farm to identify accounts needing renaming:

### Classification Heuristics
1. **Empty Display Name:** `not d` -> `empty_display` -> STEREOTYPED.
2. **Identical to Username:** `u.casefold() == d.casefold()` -> `same_as_username` -> STEREOTYPED.
3. **Suspicious Numeric Suffix:** `re.search(r"\d{2,}$", d)` -> `numeric_suffix` -> STEREOTYPED (e.g. "hoang96", "anh123").
4. **Username-Like String:** `re.fullmatch(r"[a-z0-9_.]+\d+", d.lower())` -> `username_like` -> STEREOTYPED.
   - **Critical ASCII-only invariant:** Because the character class `[a-z0-9_.]` is ASCII-only, legitimate Vietnamese diacritic names (e.g. "Đỗ Văn Hoàng", "Trần Tiến Nghĩa", "Nguyễn Tuấn") will **never** match this rule and are safely preserved.
   - Single-word legitimate names (e.g. "An", "Phong", "Hà", "Lan") without digits do not match and are not mistakenly discarded.
5. **Relationship Evaluation:** `is_name_related_to_username(d, u)` from `smart_name_generator`. If unrelated, classified as `unrelated_to_username`.
6. **Fail-Closed Safety:** If the generator or checker raises an exception, the classifier must catch `Exception` and return `checker_error:<ExceptionType>` (fail-closed, marking as stereotyped) rather than crashing or failing open.

### Telemetry & Audit Trail
Every classification decision should log structured details to stdout:
```python
reason = _stereotype_reason(u, d)
verdict = f"STEREOTYPED reason={reason}" if reason else "KEEP"
print(f"[ROLLING RENAME CHECK] @{u} display={d!r} -> {verdict}", flush=True)
```
This enables post-incident audits and instant diagnosis if an account is unexpectedly renamed or skipped.
