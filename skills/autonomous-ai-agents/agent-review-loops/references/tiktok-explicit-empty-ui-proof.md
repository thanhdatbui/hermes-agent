# Explicit-empty Android UI proof for navigation-only consumers

Use this pattern when an Android relation/list screen legitimately renders an empty state without its normal list container.

## Diagnosis

A semantic tap may land correctly while postcondition verification still times out because the empty surface omits the populated RecyclerView. Prove this with a fresh, read-only capture:

- activity/shell marker;
- exactly one selected relation tab;
- selected tab label and count;
- normal list-container presence/absence;
- explicit empty-state illustration, title and non-empty message markers;
- an independent screenshot artifact, not XML/logs alone.

Sanitize account/UID/device text in retained XML. Keep the raw screenshot only as access-controlled diagnostic evidence.

## Classifier contract

Prefer a three-state classifier: `populated | empty | invalid`.

- `populated`: exactly one selected supported relation header plus the canonical list container. Preserve the pre-existing populated contract.
- `empty`: no list container; exactly one selected relation header **in total**; that sole header is an exact supported target label with numeric zero; exactly one expected pager; exactly one known non-clickable semantic empty title; exactly one non-empty known message; exactly one known illustration. Validate expected classes/resource IDs and uniqueness.
- `invalid`: every missing, duplicate, contradictory, unknown-locale, nonzero-without-list, zero-with-list, loading/error or ambiguous state.

Do not count only selected headers that match the target label. A second selected Following/Friends/Suggested header is ambiguity and must reject even when the target `Follower 0` header is present.

## Vertical TDD

1. Add a privacy-safe synthetic XML matching the real empty surface.
2. Before production edit, run one focused test through the real classifier seam and capture a true assertion RED.
3. Patch the classifier minimally.
4. Test `_open_*`: exact target identity -> guarded semantic tab tap -> explicit-empty postcondition succeeds.
5. Test orchestration: explicit-empty exits the seed before scroll/action calls; assert zero scroll and zero Follow/action invocations.
6. Add adversarial one-field mutations: nonzero count; missing/duplicate pager/title/message/illustration; wrong class/clickability; duplicate target headers; target header plus a different selected relation header.
7. Reconstruct the sanitized live XML by restoring only independently hash-proven semantic tokens and confirm it classifies `empty`.
8. Run focused, module, full suite, compile/static, diff/status/cache checks, then independent audit exact final bytes.

## One-shot live retry discipline

A failed one-shot authorization is consumed even when no live input occurred or failure was pre-input. Never reuse its scope/token. After any harness or production byte change, create a fresh scope, rerun exact-byte audit, then mint a new short-lived one-shot authorization only after immediately-before-input device/lock/VPN/foreground/process checks.

Terminal success requires navigation postcondition, zero forbidden action calls/taps, and cleanup proof for authorization, lease/mutex/process, remote dumps and retained raw artifacts.
