# User-authorized canonical fix and rule-update pattern

## Trigger
The user explicitly orders a fix in a shared/canonical repository after a consumer rule says cross-repo edits are forbidden.

## Correct response
1. Acknowledge the explicit instruction; do not argue or invent a stronger blocker.
2. Separate two scopes:
   - **Rule scope:** update only the narrow local governance clause to permit this explicit shared fix. Preserve destructive-action, evidence, worker, test, scope, and closeout gates. Do not weaken unrelated rules.
   - **Code scope:** patch the canonical/shared implementation in its own repository with an exact contract.
3. Inspect repository status and exact anchors before writing. Preserve unrelated dirty hunks.
4. Run one focused offline/mocked test and record `git diff --numstat` plus `git diff --check`.
5. Remove redundant consumer shims after canonical behavior is fixed; verify the consumer wrapper is clean without reverting unrelated dirty files.
6. Keep evidence classes separate:
   - Offline test = code-path proof only.
   - Fresh device `inspect_machine.py`, UI XML, screenshot, and target canary = live-incident proof.

## Example pattern
`ATX_SESSION_UNAVAILABLE` was omitted from both the canonical transient UI-dump set and the recovery-handler set. Adding it to both exact sets, then running the focused account-switcher test, fixed the code-level gap. A consumer wrapper was redundant and was removed afterward.

## Pitfalls
- Do not treat a consumer-only cross-repo prohibition as higher authority than an explicit user instruction when the user has authorized the rule change.
- Do not edit broad rule files or weaken safety invariants.
- Do not report a device incident fixed from offline tests alone.
- Do not keep a duplicate consumer retry shim after the canonical fix.
