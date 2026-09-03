# Mixed PHP/HTML/JS Provider Verification

## Why this reference exists

Provider integrations in legacy PHP views often combine server-side branches, inline JavaScript, persisted configuration, cron code, and checkout code. A concurrent worker may also modify the exact files after the coordinator's baseline. The verification target is therefore the *current* worktree, not an earlier report.

## Reusable sequence

1. Re-read every scoped file after the worker reports completion. Do not patch from a stale snapshot.
2. Inspect `git diff --patience` for cloned supplier/template blocks. Ordinary diff alignment can make an unchanged neighboring provider look modified or hide an indentation accident.
3. Verify the provider path end-to-end:
   - dropdown option;
   - server-side add validation;
   - server-side edit validation;
   - field toggle and hidden/visible fields;
   - persistence of every transport field on add *and* edit (API key, proxy, rate, flags);
   - cron route/registration and fail-closed authentication;
   - catalog sync and cleanup gates;
   - checkout adapter and refund/error behavior.
4. For inline API error messages, test the actual rendered expression. `json_encode($msg)` alone is not sufficient when the result is placed inside an HTML `<script>` element: use `JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT` so `</script>`, quotes, ampersands, and angle brackets remain data.
5. Parse only the changed JavaScript block. A broad `<script>` extractor can hit unrelated vendor snippets or PHP-template fragments that are not standalone browser JavaScript. A failure outside the changed block is not evidence that the provider edit broke the page; identify the block first.
6. If PHP is unavailable, use an AST parser as supplementary syntax evidence and label it honestly. It does not replace `php -l`. Run content invariants and a behavior harness against the real files, not a copied fixture.
7. Keep temporary harnesses outside the repository and remove them. Run `git diff --check`, scoped name/numstat checks, EOL byte counts, and a secret scan before finalizing.
8. An unauthenticated `401` probe verifies that the endpoint and auth gate respond. It does not verify the catalog schema, cron behavior, or purchase flow. Never call a real purchase only to improve the evidence count; leave live-buy verification explicitly unverified when no safe test credential/approval exists.

## Evidence labels

Use precise labels in the report:

- **Implemented by worker; verified by coordinator** when a concurrent worker wrote the code.
- **AST parse PASS** rather than `php -l PASS` when no PHP runtime was installed.
- **Logic harness PASS** when the harness ports decision rules instead of executing PHP.
- **Endpoint auth probe PASS** for a 401/403 gate response; do not call it an end-to-end integration pass.
- **Live catalog/checkout UNVERIFIED** until a real configured environment is exercised safely.

## Common missed details

- A form can display a proxy field but fail to persist it on the add path while edit persists it.
- A supplier option can exist while the auto-show control remains hidden, leaving synced products invisible.
- Plain `json_encode` can still allow a `</script>` breakout; use the JSON_HEX flags.
- A valid empty catalog is not necessarily a safe deletion signal. Gate cleanup on a non-empty validated catalog unless the provider has an explicit, reliable empty-catalog contract.
- A successful HTTP status is not a successful purchase unless the provider's explicit success field and usable credential items are both present.
