# Bio uniqueness and deployment audit

## Failure pattern

A runner can rename accounts successfully while writing the same bio to every account. The dangerous version is a module-level constant such as `BIO_B64`, or a pool helper that calls `random.choice()` independently for each account without a uniqueness contract. A successful rename/OCR result does not prove that the bio was changed or was unique.

## Required contract

1. Treat display-name and bio as separate acceptance items. A `RENAMED` result must not imply `BIO_SAVED`.
2. Never hardcode a single bio payload in the runner. Generate the bio from a pool using an account-scoped seed (`username`, slot, or stable account id plus batch/date salt).
3. Enforce uniqueness within the active batch. A random pool is not sufficient: maintain a `used_bios` set or deterministic permutation and select a new candidate when a collision occurs.
4. Persist the selected bio in the per-account result/state record before the UI action, then verify the final profile OCR contains the selected bio (allowing known OCR accent distortion).
5. When replacing a hardcoded implementation, audit every executable copy and launcher/runtime mirror before restarting cron. A fixed source file does not fix a stale deployed runner.
6. If duplicate output is discovered, pause the producer watchdog first, preserve the affected reports, and repair the source/deployment path before resuming. Do not rerun a broad rename batch merely to repair bios.
7. A focused offline test must prove: same account seed is stable, two different account identities in one batch do not collide for the tested pool, and a duplicate candidate is rejected/reselected. A real-device canary is still required before claiming farm-wide completion.

## Evidence language

Report name, bio, and avatar as independent statuses. Use `BLOCKED/UNPROVEN` when OCR or the final screenshot does not verify the bio. Do not call a pool "100% unique" unless the implementation enforces and tests uniqueness for the actual batch scope.

## Session reproduction clues

When two fresh profiles show the exact same sentence, inspect the runner's bio-generation lines, deployed copies, and per-account reports. The presence of `BIO_EDIT` followed by the identical final OCR text is proof of a bio-generation/deployment defect, not proof that TikTok ignored input. A later module timestamp does not establish that the earlier batch used that module.
