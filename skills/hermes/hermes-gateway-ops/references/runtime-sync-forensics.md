# Runtime-sync forensics (Windows Hermes)

## Purpose

Use this reference when a Hermes runtime has mixed core/plugin versions or the user asks what updated Hermes. It records the evidence pattern from the 2026-08-26 Telegram incident without treating the session-specific timestamp as a general rule.

## Evidence pattern

A runtime-sync package backup can establish that a copy/install operation occurred:

- `runtime-sync-package-backups/<timestamp>/manifest.json` records the editable finder, file count/categories, excluded-data policy, and backup hashes.
- `root-sync-manifest.json` can identify the wheel/artifact, its SHA256, source site-package hashes, and root post-copy hashes.
- A post-manifest can identify the source checkout, installed runtime, wheel version, pip command, hash chain, and whether a restart was performed.

Example interpretation:

```text
source root:      D:\Taadaa\Hermes
installed root:   %LOCALAPPDATA%\hermes\hermes-agent
artifact:         hermes_agent-<version>-py3-none-any.whl
operation:        wheel install + root/source sync
```

This proves the **copy mechanism** and affected roots. It does not prove that OmniRoute, Desktop, a Scheduled Task, or a specific chat session invoked it.

## Trigger attribution checklist

1. Read `hermes-update.log` and `update.log`. If the entry ends at “other Hermes processes are running” and recommends rerunning `hermes update`, treat it as a blocked attempt, not a successful install.
2. Query Task Scheduler metadata for Hermes/runtime/update names and check last-run time/result. Do not dump action arguments if they may contain secrets.
3. Inspect Startup-folder launchers and gateway service scripts. A launcher containing `gateway run` is a start mechanism, not an updater unless it invokes update/install/sync commands.
4. Search Desktop, Gateway, agent, and error logs for `hermes update`, `pip install`, `git pull/fetch`, `runtime-sync`, `repair`, and restart markers around the manifest timestamp.
5. Inspect Git reflog and commit times in both the source checkout and installed runtime. A Git commit/reset may explain source changes but does not by itself prove that the runtime was copied.
6. Inspect the live Gateway command line and process tree when deciding whether a restart or update could have happened. Avoid restarting during a live farm batch.

## Attribution language

Use three confidence levels:

- **Confirmed:** the log/scheduler/session explicitly records the invoking command or actor.
- **Confirmed mechanism, unresolved trigger:** manifests prove the runtime-sync copy/install, but no launcher/session log proves who invoked it.
- **Not supported:** no evidence for a proposed actor (for example, OmniRoute) after checking relevant logs/tasks.

Never state “it auto-updated” merely because files changed. Never state “OmniRoute did it” merely because OmniRoute was updated nearby.

## Safety and preservation

- Keep credentials redacted.
- Do not run `git reset`, `git clean`, broad reinstall, or whole-tree copy during forensics.
- Preserve the dirty-tree status before changing anything.
- If repairing an affected file, diff it against the venv copy and available backups first; a direct copy can erase user customizations in that file.
- Report runtime repair separately from source-repository changes.

## Incident-specific lesson

The Telegram outage showed the failure mode: a newer adapter imported a private core helper (`_coerce_allow_set`) while the active core did not provide it. A cold restart exposed the mismatch; a process that had already imported the old adapter could mask it. Any future runtime-sync hardening must validate the core/plugin pair before replacement and perform a cold-import check before restart.
