# Admin bootstrap

This deployment bundle is intentionally private and contains the active Hermes/Codex user setup for the admin workstation, including bootstrap credentials.

From a fresh Windows checkout, open PowerShell in the repository and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\setup-admin.ps1
```

The script installs Hermes editable from this checkout, installs Claude Code and Codex CLI, syncs the repository's canonical skills into the current user's Hermes home, bootstraps missing configuration/credentials, and verifies the installed commands.

The repository root `skills/` directory is the shared Git source for both machines. `sync-skills.ps1` copies it to `%LOCALAPPDATA%\hermes\skills` with additive/update-only `robocopy /E`; runtime metadata, caches, lock files, and ticker artifacts are excluded in both directions. It uses Hermes's `.bundled_manifest` origin hashes: an unchanged local copy is updated when the repository skill changes, while a genuinely locally modified skill is preserved and reported. Repository-only and local-only skills are preserved. Neither script uses `/MIR` or `/PURGE`.

The manifest records the hash of each skill directory at the last successful sync. Keep it with the local Hermes skills directory; it is runtime provenance and is excluded from repository export. If a skill predates the manifest, the sync is conservative and only accepts an exact repository copy; a differing local skill is reported and the sync aborts before `robocopy`. Review, back up, or reset it before retrying rather than risking an overwrite.

To publish skills created or edited in the local Hermes home back into this repository, pull remote changes first, resolve any conflicts, then run:

```powershell
git pull --rebase
.\deploy\sync-skills-to-repo.ps1
git status
git diff --check
```

The export is additive/update-only: it never infers deletions from a missing local skill and never deletes repository-only skills. If a skill deletion is intentional, remove it explicitly with `git rm` after the export and review that deletion. The export fetches the current configured upstream and refuses to run when the branch is behind it, has no tracking branch, or the repository `skills/` tree is dirty. Pull/rebase and resolve conflicts before exporting; fetching does not commit or push anything. The upstream freshness guard remains required because local-to-repo export can update repository files.

```text
pull remote changes -> resolve conflicts -> export local skills -> inspect diff -> git diff --check -> review for secrets -> git add/commit -> git push
```

Before `git add`/commit, inspect the diff for credentials, tokens, private prompts, or other secrets. Do not auto-commit or auto-push the export. This keeps concurrent edits from two machines visible and mergeable.

## Bundle contents

- `hermes-home/`: bootstrap config, persona, `.env`, Hermes auth, Cron config (`cron/jobs.json`), and Cron scripts (`scripts/*.py`). It does not contain a skill snapshot.
- `codex-home/`: bootstrap Codex CLI state/auth files available on the source workstation.
- `setup-admin.ps1`: Windows bootstrap script (tự động sync skills, config, cron, scripts).
- `CRON_DEPLOYMENT_GUIDE.md`: hướng dẫn chi tiết về cơ chế cấu hình và đồng bộ Cron Jobs.
- `sync-skills.ps1`: syncs the canonical repository skills to the managed Hermes home.
- `sync-skills-to-repo.ps1`: exports local Hermes skills back into the repository, excluding runtime metadata.

The script targets the current Windows user:

- Hermes: `%LOCALAPPDATA%\hermes`
- Codex: `%USERPROFILE%\.codex`

Run the script from the checked-out repo. Do not use a PyPI/global Hermes executable: the script installs the local checkout with `pip install --editable` and invokes its virtualenv executable for verification.

The setup is safe to rerun: existing Hermes `.env`/`auth.json` and Codex state files are preserved, and bootstrap copies are made only when those destination files do not exist.
