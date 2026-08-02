# Cross-Machine Skill Sync Reference

## Evidence checklist

Record these facts before reporting success:

1. Repository commit on the target machine: `git status --short --branch` and `git log -1 --oneline`.
2. Runtime operation result: whether the skill was `copied`, `updated`, `user_modified`, `skipped`, or restored explicitly.
3. Active content: `skill_view` shows the expected version and distinctive new section.
4. Reference files: every linked `references/` file exists in the active profile.
5. Session state: a fresh Hermes session or `/reset` happened after the file update.

## Two-machine pattern

Before editing on either machine:

```text
cd <path-to-Hermes>
git fetch origin --prune
git pull --rebase origin main
```

After local skill creation or edits:

```text
# Windows PowerShell
.\deploy\sync-skills-to-repo.ps1

git status
git diff
git diff --check
git add skills
git commit -m "sync skills from local Hermes"
git fetch origin --prune
git pull --rebase origin main
git diff --check
git push origin main
```

On the receiving machine:

```text
git pull --rebase origin main
.\deploy\sync-skills.ps1
```

Use the platform-equivalent export/forward-sync commands on Linux/macOS. Preserve unrelated working-tree modifications and resolve conflicts deliberately. Do not use a hard reset, `/MIR`, automatic commit, or automatic push as a substitute for review.

## Export protection

The local-to-repo export is additive/update-only: it must preserve repository-only skills and exclude runtime metadata such as manifests, usage/curator state, caches, locks, hub/archive data, credentials, and session state. `hermes skills reset` is an explicit one-skill replacement tool, not the normal cross-machine synchronization step.

## Profile isolation

Run the procedure separately for each profile that should receive the update. `$HERMES_HOME/skills/` is profile-scoped; updating the default profile does not update named profiles.

## Never synchronize

Do not copy `.env`, OAuth/auth files, session databases, logs containing sensitive data, or arbitrary profile state between machines as part of a skill update.
