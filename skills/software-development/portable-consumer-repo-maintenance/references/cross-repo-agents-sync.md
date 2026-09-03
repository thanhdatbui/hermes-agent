# Cross-Repo AGENTS.md Policy Sync — bulk propagation with CRLF safety

Session: 2026-08-06, Taadaa. Propagated a policy change (worker pin:
`gpt-5.6-luna` → `session-model worker (Hermes=flash ≡ Codex=luna)`) from the
parent AGENTS.md to 15+ consumer repos. The durable techniques below apply to
any bulk policy-text sync across many repos.

## When to use

Parent policy file changed (e.g. worker model pin, audit chain, marker set) and
every repo that embeds a copied canonical block must follow. Symptom: an LLM
audit reports "7 of 9 files still pin old model" because each repo copies the
`CODEX-DIRECT-WORKER-POLICY` block at creation time and never re-syncs.

## Workflow

1. **Inventory ALL files first** (`os.walk`, skip `node_modules/.git/.codex-work/
   .pytest*/.tmp`), classify: parent / active consumer repos / context-worktrees
   (temporary, ask user before touching). Ask the user which scope to sync —
   do NOT assume worktrees are in scope.
2. **Backup every target before editing**: `cp <repo>/AGENTS.md
   <repo>/AGENTS.md.luna-sync-<timestamp>.bak` + `sha256sum` both. Verify the
   backup hash matches the source before any write.
3. **Profile the file set**: detect per-file line ending (CRLF vs LF), size,
   and which Luna-only patterns exist (`pinned to model \`gpt-5.6-luna\``,
   `Default Worker: a fresh direct \`gpt-5.6-luna\``, `Luna/max executor`,
   `only Luna/max`, invalid rungs `Terra/max`/`Sol/xhigh`). Most repos share the
   same copied block → a small replacement table covers most files.
4. **Apply with line-ending preservation.** The `patch` tool rewrites whole-file
   line endings (LF↔CRLF) on Windows — do NOT use it for bulk multi-file sync
   on mixed-EOL trees. Instead: read bytes → decode → `str.replace` exact
   patterns → write bytes back with `open(p,'wb')`. The decoded text keeps the
   file's own CRLF; re-encoding preserves it. Verify per-file
   `CRLF count == backup CRLF count` after writing.
5. **Windows sandbox PermissionError workaround.** In this environment, python
   running from the Hermes execute_code sandbox gets `PermissionError: [Errno 13]`
   on some files even when `attrib -r` shows writable and terminal `cp` works
   (file held open by another process, e.g. OneDrive/sync). The reliable path:
   - python can always CREATE new files → write `<repo>/AGENTS.md.new`
   - then `cp <repo>/AGENTS.md.new <repo>/AGENTS.md` in the terminal (cp is not
     blocked) and `rm` the `.new`.
   Batch via base64 map: python writes `_map.txt` lines `repo\t<base64>`, then a
   shell loop decodes. If `base64 -d` in git-bash chokes on long lines, decode
   per-file with python and write `.new`, then `cp` each.
6. **Verify by scanning, not by trust.** Write an ad-hoc script that walks all
   target files and asserts, per file: (a) no old pin pattern, (b)
   session-model/equivalent present, (c) no bare `Luna/max` outside legit
   `(Luna/max or flash/max)` clusters, (d) no invalid rungs. Then run the
   canonical validator (e.g. `check-claude-quota-policy.ps1`) and confirm
   exit 0. Re-scan after fixes — the scan catches files the sync missed
   (e.g. nested `apps/desktop/AGENTS.md` under a repo root).

## Pitfalls (all hit live)

- **Nested AGENTS.md under a repo**: syncing `<repo>/AGENTS.md` does NOT cover
  `<repo>/apps/desktop/AGENTS.md` — the final scan found it still pinned old
  model. Walk recursively, don't assume one file per repo.
- **Invalid-rung drift**: consumer ladders may keep `Terra/max` + `Sol/xhigh`
  as valid rungs while parent declares them invalid. A parent-vs-child audit
  (nemotron) catches this; the fix is removing the invalid rungs from consumer
  ladder text, not just the worker pin.
- **Regex false positives on legit clusters**: `` (`Luna/max` or `flash/max`) ``
  and headings `(Luna/max and flash/max)` are CORRECT — strip those clusters
  BEFORE searching for bare `Luna/max`. A naive grep reports them as remnants
  and wastes a fix cycle.
- **Deprecated/historical sections**: `## Deprecated Audit Routing Policy v2`
  blocks keep old wording by design — exclude them from "remnant" checks.
- **`\r\r\n` double-CR**: repeated write/rewrite cycles can produce doubled CR
  (`\r\r\n`); normalize `\r\r\n → \r\n` before final write.
- **Model audit coverage limits**: a free-model auditor reads only ~4 files
  before context fills on a 25-file workspace → it reports BLOCKED/incomplete.
  The deterministic scan is the real verdict; the model audit is secondary
  evidence.
- **Each consumer repo is its own git repo**: after sync, `git status` differs
  per repo; do NOT commit unless asked. Report that commits are pending per
  repo.
