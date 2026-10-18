# Post-follow verification and reconcile

## Durable lesson

A follow runner can have a real post-tap checker and still produce `script=2, web=0`. The measurements are taken at different layers and times:

1. `tap_attempts`: the runner tapped two target rows.
2. Immediate row verification: the list row changed state.
3. Path-B verification: the runner opened each target profile, classified the action button, refreshed the profile, classified again, and restored the follower list.
4. Web/snapshot reconciliation: a later crawler read the public/account-level following state.

These must not be collapsed into one number.

## Required per-UID evidence

For each UID counted as confirmed, preserve or locate these milestones:

- pre-tap action state;
- post-tap row classification;
- profile navigation and exact target identity;
- pre-refresh profile action classification;
- pull-to-refresh completion;
- post-refresh profile action classification;
- return/list restoration;
- final result and timestamp.

The success counter must be derived from the final Path-B result, not merely from a hook exit code or the first optimistic UI state.

## Diagnostic interpretation

- If Path-B is `not_followed` after refresh, classify as immediate release and do not count it.
- If Path-B is `followed` but later web is zero, investigate delayed server-side release, snapshot timing/cache, or a target/account-level restriction.
- If Path-B milestones are missing, report conservatively: `tap_attempts=N`, `path_b_verified=unknown/incomplete`, `web_delta=M`.
- A self-profile `Following` counter is only an account-level sanity signal. It cannot prove that specific target UIDs were followed.
- Do not state “shadow drop” as fact without timestamped artifacts showing a valid Path-B success followed by a later release or web delta of zero.

## Reporting format

Use a compact evidence table or bullets:

```text
UID | tap | row-check | Path-B pre-refresh | refresh | Path-B final | web/snapshot | conclusion
```

Separate “script attempted”, “runner verified”, and “web reconciled”. This prevents a report from incorrectly implying that a checker was absent when the actual issue is a delayed release or insufficient per-UID observability.
