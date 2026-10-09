# Follower-count load failure as a follow-action-block signal

## Scope

Use this heuristic when a farm nick opens another TikTok profile during a follow workflow and the target profile's **Followers/Follower value fails to load** (blank, placeholder, or otherwise visibly unavailable).

## Interpretation

- Treat the symptom as a **nick-level suspected action block / silent follow-release condition on the currently used nick**.
- Do **not** attribute it immediately to the target profile, device, proxy, or farm-wide outage.
- Do **not** claim confirmed release from a single ambiguous screenshot. Confirm with fresh live evidence (screenshot and, where available, UI XML) and correlate with a follow verification result or a second target profile.
- A normal low follower count or a genuine numeric `0` is not this signal; the distinction is “value failed to load,” not “value is small.”

## Safe operational response

1. Preserve the evidence: fresh screenshot, timestamp, machine, slot/row, and the currently active `@username`.
2. Stop additional follow attempts for that nick and place it in cooldown/manual review according to the runner's existing state machine. Do not perform ad-hoc logout, `pm clear`, or account deletion.
3. Report by asset identity: `@username (M<number>)`, with the observed UI symptom and evidence path. Never report only a machine number.
4. If the evidence is unreadable or OCR is inconclusive, report `UNPROVEN` rather than upgrading the heuristic to a confirmed failure.
5. Re-enable the nick only after the canonical follow verification/re-entry path shows the target profile's relationship state and follower data loading normally.

## Evidence wording

Prefer:

> `[OBSERVED]` Target profile's Followers value did not load while active as `@username (M<number>)`; `[HYPOTHESIS]` active nick may be action-blocked/being released; `[NEXT]` cooldown and canonical recheck.

Avoid:

> “The target account is broken” or “the proxy is bad” without fresh evidence proving that dependency.
