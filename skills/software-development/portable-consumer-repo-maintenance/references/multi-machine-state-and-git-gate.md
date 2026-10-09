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

## 3-Tier Farm Sync Architecture (Kibe vs Admin)

1. **Git Layer (`D:\Taadaa\...` on each host)**: Independent checkouts per host. Code lives on physical drive, NOT in OneDrive. Git's non-fast-forward / fetch-first protection prevents secondary hosts from accidentally overwriting commits pushed by the primary host.
2. **OneDrive Shared Tools Layer (`D:\OneDrive\Taadaa_Sync_Shared\tools\`)**: File-sync across hosts for cross-machine orchestration scripts (e.g. `ensure_row_accounts.py`). Must use dynamic `Path.home()` or host-config discovery to bind tokens/profiles dynamically per host instead of hardcoding Admin or Kibe paths.
3. **Hermes Sync Layer (`apply_sync_admin.py`)**: One-way sync (Kibe ➔ Admin) copying config and skills from OneDrive into Admin, preserving Kibe as the master authoring environment.

## Safe Git Pull Reconciliation for Consumer Hosts with Dirty Overrides

Consumer hosts frequently carry machine-specific runtime state (e.g. swapped device serial mappings in `calibrate.py`/`social_reg_v1.py` or local target selection JSONs). A raw `git pull` will abort with `error: Your local changes to the following files would be overwritten by merge`.

Safe sequence:
```bash
git stash
git pull
git stash pop
# Run focused pytest immediately to verify syntax and regression safety:
pytest tests/<focused_test>.py -v
```
If `git stash pop` auto-merges, verify with `git diff <file>` that local machine serial overrides and upstream logic fixes coexist cleanly without conflict.
