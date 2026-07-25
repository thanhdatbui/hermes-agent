# Admin bootstrap

This deployment bundle is intentionally private and contains the active Hermes/Codex user setup for the admin workstation, including credentials.

From a fresh Windows checkout, open PowerShell in the repository and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\setup-admin.ps1
```

The script installs Hermes editable from this checkout, installs Claude Code and Codex CLI, copies the bundled Hermes home and Codex state into the current user's profile, and verifies the installed commands.

## Bundle contents

- `hermes-home/`: config, persona, skills, plugins, cron/scripts, `.env`, and Hermes auth.
- `codex-home/`: Codex CLI state/auth snapshot available on the source workstation.
- `setup-admin.ps1`: Windows bootstrap script.

The script targets the current Windows user:

- Hermes: `%LOCALAPPDATA%\hermes`
- Codex: `%USERPROFILE%\.codex`

Run the script from the checked-out repo. Do not use a PyPI/global Hermes executable: the script installs the local checkout with `pip install --editable` and invokes its virtualenv executable for verification.
