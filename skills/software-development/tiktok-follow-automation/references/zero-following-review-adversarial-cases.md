# Zero-Following review adversarial cases

## Why this reference exists

The `plan-review-hard` review rejected a candidate that used broad proximity and resource-ID checks to classify an anchor as empty. This reference captures the durable review/test requirements for Mode 2 anchor skipping.

## Required positive proof

Accept `zero_following` only when all of these hold:

1. The current screen is the exact target profile; the header handle matches the requested UID exactly.
2. The Following label is an exact supported variant (`Đang follow`, `Đã follow`, `Following`, `Đang theo dõi`, including approved case variants).
3. The zero value and label belong to the same profile-stat cell. Prefer a shared parent/container or an exact known stat-node relationship. If the layout exposes one combined value, its semantic text must be an exact zero-Following form and its resource ID must be a known profile-stat ID.
4. If the layout splits count and label into separate nodes, their relationship must be unambiguous: same cell/parent when available, tight aligned geometry, and no competing statistic can match the same rule.
5. Only after proof is recorded may the runner avoid tapping/following the anchor, back to proven Feed, and continue to the next anchor.

## Required negative cases

The test suite must reject or remain manual for:

- bare `0` with no Following label;
- `0 Followers`, `0 Friends`, `0 Likes`, or another non-Following counter when Following is nonzero;
- a Following label near an unrelated zero counter without shared parent or unambiguous stat-cell geometry;
- `0 Following` text inside a suggested-account card, bio, or lower profile content;
- a generic `Follow` button in suggested accounts interpreted as anchor release;
- duplicate/ambiguous target handles in header and suggestions;
- stale profile dump or identity mismatch after retry;
- a retry branch that loses the zero classification and turns a proven empty anchor into `MANUAL_REVIEW`.

## Retry and runtime boundaries

Both the first open attempt and the retry must carry an explicit outcome (`zero_following`, `followed`, `failed`, or `manual`). Do not infer `zero_following` from a human-readable reason string alone; a mocked or stale reason is not structural proof. If proof disappears after retry, preserve fail-closed behavior.

A module path, source hash, build marker, or `FOLLOW_RESULT.details` marker proves import provenance only. It does not prove that a physical machine ran the new code or that the UI behavior succeeded. Report source verification, runtime loading, and live behavior as separate facts.

## Review checklist

- Inspect the exact staged bytes/tree, not a mixed working-tree diff.
- Include the production delta and unchanged baseline context in the review prompt.
- Bind the verdict to the staged tree/hash.
- If the reviewer rejects on ambiguity, add the adversarial fixture before requesting a fresh verdict. Do not commit, rebase, or push a rejected candidate.
