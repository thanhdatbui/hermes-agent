# Multi-machine consumer farm: state partition and Git gate

## Recommended topology

Use one Git remote and one independent local checkout per host. The repository shares code, reviewed skills, tests, and config templates only. Each host keeps its own workbook, runtime/checkpoint/receipt state, locks, logs, ADB mapping, Hermes profile, credentials, and Telegram bot.

Do not place a Git working tree or `.git` directory in OneDrive. OneDrive synchronizes files; it does not semantically merge concurrent Git index/object/worktree changes.

## Workbook rule

A single `.xlsx` written concurrently by two hosts is not a safe database. Even disjoint machine ranges can lose updates because openpyxl commonly rewrites the workbook and OneDrive has stale-sync/conflicted-copy behavior, not row-level ownership transactions.

Preferred order:

1. Separate workbook per host with disjoint account and machine ownership.
2. Read-only master workbook exported into host workbooks.
3. If a shared live account pool is mandatory, use a transactional SQLite/MariaDB ownership table and retain Excel as import/export.

A future merge tool must fail closed on same-account/same-machine conflicts, use file/version hashes, write atomically, preserve backups, and never treat OneDrive's last-writer result as authoritative.

## Host configuration contract

Track `config.example.yaml`; ignore each host's `config.local.yaml`. The config should contain `host_id`, machine range, workbook path, runtime root, ADB executable, and any host-local scheduler paths. Every live launcher prints and validates the effective host, range, workbook, and runtime root; mismatch means no launch.

Changing config resolution should be a shared, config-driven consumer change, not a fork of the workflow. Add fixtures for two hosts and assert that each resolves only its own workbook/runtime/machine range.

## Commit/push gate

1. `git fetch origin && git pull --rebase origin main` before editing.
2. Make the change and run focused tests/preflight.
3. Audit the diff with an independent model. Require a machine-parseable verdict: `APPROVED`, `MINOR_FIXES`, or `REJECT`; unparseable/transport failure is not approval.
4. `MINOR_FIXES`/`REJECT` → fix only findings → re-audit. Do not commit yet.
5. Only `APPROVED` permits commit. Stage explicit source/test/docs paths; never workbook, runtime, secret, or `git add .`.
6. After commit, fetch/rebase again. If rebase changes the diff/base, rerun tests and audit.
7. Push only after the post-commit gate is still `APPROVED`. Rejected push → rebase and repeat; never force-push.

A project `AGENTS.md` or `.hermes.md` should state this gate explicitly. Memory helps recall it but does not enforce Git behavior; enforcement needs the project rule plus a wrapper/dispatcher or pre-push hook that checks the audit artifact.
