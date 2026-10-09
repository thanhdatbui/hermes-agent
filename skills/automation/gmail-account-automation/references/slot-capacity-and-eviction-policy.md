# S7 Slot Capacity vs Rolling Eviction

## Trigger
Use when a Gmail registration report says `SKIPPED_FULL` / `FULL_NO_ELIGIBLE_CLEANUP`, or when the operator asks to increase the maximum Gmail accounts per S7.

## Distinguish two policies
- **Eviction policy:** decides whether an existing account may be removed. Preserve the TikTok Binding Gate absolutely: never remove an email currently bound to TikTok on that machine. Missing metadata is never eligibility. A non-bound account is removable only when the configured GPM-live proof is present, or the configured soak/2FA rule is satisfied.
- **Capacity policy:** decides when registration must stop because the device has reached its configured account cap. Changing capacity is a business/device-policy change, not an eviction-gate bypass.

## Investigation evidence
Before changing either policy, collect:
1. The exact configured cap in the preflight code and any duplicated cap/report text in the Gmail runner.
2. `dumpsys account` for the affected device(s), via the farm inspection workflow when an alert identifies a machine.
3. TikTok-bound emails for each machine.
4. Per-account GPM-live proof, 2FA state, creation date, and whether metadata is missing or merely misparsed.

A report may say “5 accounts” while the implementation blocks at `count >= 5`, meaning the machine can run only while `count < 5` (four accounts). Do not infer the intended cap from prose; trace the predicate and all duplicated report strings.

## Safe capacity-change workflow
- Ask for the exact new cap if the operator says only “increase the maximum”; this is a business/device-capacity parameter and must not be guessed.
- After the cap is specified, patch the smallest shared policy anchor plus any misleading fixed-number report text. Keep TikTok Binding and eviction predicates unchanged.
- Check all downstream consumers that assume five: preflight predicate, returned messages/count defaults, runner classification reason, and focused tests.
- Test offline/mocked first. Do not use a higher cap as permission to delete accounts or to bypass GPM/2FA/age safety gates.
- A higher cap must be validated against the S7 operational limit and the user’s stated farm convention (for example, an eight-account target), then canary only if the user explicitly requests live execution.

## Known bottleneck pattern
When all non-bound accounts are young and not GPM-live, `FULL_NO_ELIGIBLE_CLEANUP` is expected under the eviction policy. Increasing capacity can let registration continue without deleting those accounts, but it does not solve GPM onboarding; schedule or repair the S7→GPM login lane separately.

## Reporting
Report separately:
- current device count and configured cap;
- TikTok-protected count;
- eligible eviction candidates;
- capacity change requested/applied;
- whether GPM onboarding remains a bottleneck.

Never describe a capacity increase as “fixing” an eviction failure unless the eviction logic itself was changed and verified.
