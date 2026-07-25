# Admin bootstrap

This deployment bundle is intentionally private and contains the active Hermes/Codex user setup for the admin workstation, including bootstrap credentials.

From a fresh Windows checkout, open PowerShell in the repository and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\setup-admin.ps1
```

The script installs Hermes editable from this checkout, installs Claude Code and Codex CLI, syncs the repository's canonical skills into the current user's Hermes home, bootstraps missing configuration/credentials, and verifies the installed commands.

The repository root `skills/` directory is the sole canonical shared skill source. `sync-skills.ps1` copies it to `%LOCALAPPDATA%\hermes\skills` with `robocopy /E`; runtime metadata, index caches, lock files, and ticker artifacts are excluded. Existing destination skill files are retained unless the source copy updates them.

## Bundle contents

- `hermes-home/`: bootstrap config, persona, `.env`, and Hermes auth. It does not contain a skill snapshot.
- `codex-home/`: bootstrap Codex CLI state/auth files available on the source workstation.
- `setup-admin.ps1`: Windows bootstrap script.
- `sync-skills.ps1`: syncs the canonical repository skills to the managed Hermes home.

The script targets the current Windows user:

- Hermes: `%LOCALAPPDATA%\hermes`
- Codex: `%USERPROFILE%\.codex`

Run the script from the checked-out repo. Do not use a PyPI/global Hermes executable: the script installs the local checkout with `pip install --editable` and invokes its virtualenv executable for verification.

The setup is safe to rerun: existing Hermes `.env`/`auth.json` and Codex state files are preserved, and bootstrap copies are made only when those destination files do not exist.
