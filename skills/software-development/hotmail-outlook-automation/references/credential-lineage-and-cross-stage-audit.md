# Credential lineage and cross-stage audit

## Trigger
Use when an account succeeds in TikTok registration or OTP retrieval but later fails Microsoft web login. Do not infer that the marketplace supplied a bad password until the credential path is reconciled.

## Evidence matrix

| Boundary | Verify | Failure classification |
|---|---|---|
| Canonical workbook → loaded account | `PASS MAIL` is present for the exact normalized email; record row and field names, not secrets | `IMPORT_BAD` if absent/wrong |
| Workbook → supervisor state | Compare `mail_password` and other secret-field presence using redacted values or hashes | `STATE_STALE` if state is blank/old |
| Supervisor → login runner | Inspect the exact argv and confirm `--password` receives only `mail_password` | `RUNNER_MAPPED_WRONG_FIELD` if it falls back to TikTok/ChatGPT PASS |
| Login runner → Microsoft page | Preserve the post-submit artifact and exact Microsoft error text | distinguishes wrong input from proxy/UI failure |
| Change-pass history | Check changed tracker and workbook status columns separately | absence means “no recorded automated change,” not supplier proof |
| Purchase provenance | Only after internal boundaries match, inspect source/order logs and warranty window | `SOURCE_BAD` only with direct evidence |

## Critical anti-pattern
A stage runner that loads `mail_password` and then updates an existing state record while excluding `password`, `mail_password`, and `chatgpt_password` can preserve a blank/stale secret indefinitely. If login later constructs:

```python
mail_password or password
```

an empty mail password silently becomes the TikTok password. This is unsafe credential-domain crossover. The correct behavior is fail-closed: refresh the canonical mail field, or stop with `CREDENTIAL_MAPPING_MISSING`.

## Why TikTok success is not proof of Hotmail password correctness
TikTok registration can succeed using mailbox access/OTP or an OAuth token while the TikTok account password is stored separately. Therefore:

```text
TikTok reg OK != Hotmail password login OK
```

The combination “TikTok reg succeeded + Hotmail login says wrong password” is a strong signal to audit field mapping and state freshness before blaming the supplier.

## Reporting rules
- Never print passwords, refresh tokens, API keys, or full order lines.
- Report normalized email, machine/row, field names, presence/absence, secret length or keyed hash if needed, and exact code locations.
- Keep the conclusion calibrated: `confirmed internal mismatch`, `confirmed source mismatch`, or `unresolved`.
- Do not treat tracker absence as proof that a password was never changed by any actor; it proves only no recorded automated change.

## Minimal verification recipe
1. Read the canonical workbook using the explicit sheet name.
2. Read the supervisor state for the exact email.
3. Inspect the stage runner's argument construction.
4. Compare field presence and lengths without printing values.
5. Check the changed-password tracker.
6. Inspect one real login artifact only after the data-path check.
7. Do not retry live login or alter state until the mismatch is classified.
