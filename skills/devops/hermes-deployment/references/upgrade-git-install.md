# Upgrading a git-installed Hermes (source tree at %LOCALAPPDATA%\hermes\hermes-agent)

Verified 2026-08-05 on this machine (0.18.2 → 0.20.0, git install, local CRLF
working tree, one carried commit). Follow this exact sequence; it preserves
local custom patches and survives shallow-clone history.

## Check install method first

```bash
hermes --version                      # reports "Install method: git" if git-installed
cd "$HOME/AppData/Local/hermes/hermes-agent"
git rev-parse --short HEAD
git log --oneline -3 HEAD             # is HEAD a lone commit (shallow)?
ls .git/shallow                       # exists => shallow clone
```

A `pip`-installed Hermes is a different upgrade path (reinstall the wheel); this
guide is for the git tree.

## Pre-flight

1. **Stash ALL local modifications** (custom patches, CRLF-converted files):
   ```bash
   git stash push -m "local-custom-patches-$(date +%F)"
   ```
   Untracked files (`??`) are NOT stashed by default — they stay and are fine
   (backups, new plugins). Do not delete them.
2. Fetch and check for a shallow history:
   ```bash
   git fetch origin
   git merge-base HEAD origin/main   # fails ("Not a valid commit name") if shallow
   ```
3. If shallow, deepen it:
   ```bash
   git fetch --unshallow origin
   ```
   (A fresh `git clone --depth 1` gives a shallow repo whose parent commit is
   missing; `merge` then refuses with "refusing to merge unrelated histories"
   until you unshallow. `--unshallow` on an already-complete repo errors
   harmlessly with "does not make sense" — that means you're fine.)

## Merge (not pull)

```bash
git merge origin/main --no-edit
```

Prefer merge over `pull --rebase` here: you have a carried local commit and a
dirty working tree; merge keeps your local commit in place and just brings in
upstream. (For clean multi-machine sync, `pull --rebase` is still the
deployment-skill recommendation — that's a different scenario.)

Upstream merges can be HUGE single commits (e.g. 0.18.2→0.20.0 touched 5888
files including pyproject.toml + uv.lock). After the merge you MUST reinstall
Python deps because the venv still has the old ones:

```bash
./venv/Scripts/python.exe -m pip install -e .   # or follow repo's own install cmd
./venv/Scripts/python.exe -c "import hermes_cli.main; print('import OK')"
```

Skipping this step is what breaks model calls after upgrade (missing new
modules like `agent.errors`).

## Restore local patches

```bash
git stash pop
```

Conflicts are expected on files you patched locally. Resolve per file:

- **Files where local change was only CRLF** (check with
  `git diff --ignore-cr-at-eol -- <file>`; if near-zero real lines, upstream LF
  version is fine) → take upstream: `git checkout --theirs -- <file> && git add <file>`
- **Files with real local logic** (e.g. a desktop model-presets.ts fix that
  upstream hasn't merged) → keep local: `git checkout --ours -- <file> && git add <file>`
- Auto-generated docs (website/i18n, model-catalog, skills docs) → take
  upstream; local copies are stale.

Check CRLF vs logic BEFORE resolving: use
`git diff --ignore-cr-at-eol --stat` and count real `^[+-][^+-]` lines.

The stash entry is kept after a conflicting pop — verify with `git stash list`
and drop it only after everything resolves.

## Post-upgrade verification

```bash
hermes --version          # still reports the OLD version until app restart
./venv/Scripts/python.exe -c "import agent.chat_completion_helpers; import tui_gateway.server; import hermes_state; print('imports OK')"
```

- `hermes --version` reads the installed metadata, not the git HEAD — it lags
  until you restart the app. That is EXPECTED; the running session still uses
  the old in-memory code.
- Restart the desktop app to load the new code.

## Pitfalls

- **"refusing to merge unrelated histories"** = shallow clone missing the
  parent commit. Run `git fetch --unshallow`, NOT `git merge --allow-unrelated-histories`.
- **Model calls fail after upgrade** = venv missing new deps. Reinstall
  (`pip install -e .` or repo's install command), then import-test.
- **`hermes --version` shows old version after upgrade** = normal until app
  restart; do not chase it.
- **Do not `git clean -fdx`** — it deletes untracked backups/plugins.
- **Dist-info mismatch**: site-packages may hold `hermes_agent-0.18.2.dist-info`
  while source is 0.20.0; imports resolve from the source tree (venv has the
  source on path), so the dist-info is cosmetic until reinstall.
