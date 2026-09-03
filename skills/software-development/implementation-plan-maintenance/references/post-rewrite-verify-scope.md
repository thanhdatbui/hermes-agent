# Post-rewrite verification: exclusive write-scope + stale sweep

Use after a wholesale `write_file` rewrite of **exactly one** plan file on a PLAN-ONLY task with an exclusive write allowlist (e.g. "sửa DUY NHẤT candidate plan X thành bản Y"). The deliverable is one rewritten file; proving you changed *nothing else* and the content is internally clean is part of the deliverable, not optional.

## Why a separate protocol

`write_file` overwrites the whole file in one shot (correct for a full rewrite). But it emits a warning when the target was read earlier in the session:

> `_warning: <path> was modified since you last read it on disk (external edit or unrecorded writer). Re-read the file before writing.`

This is not an error, but it is a signal: **after `write_file`, independently re-read/hash the file via terminal before reporting.** Do not trust the in-tool `bytes_written` as the final artifact hash — a concurrent writer (or your own earlier read) could mean the on-disk bytes differ from what you assumed. Recompute SHA-256 / byte count / newline count from a fresh terminal read and use those numbers in the report.

## Commands (from repo root; every terminal cmd prefixed with `cd '/d/Taadaa/...'` per repo rule)

```bash
cd '/d/Taadaa/tiktok-luot nuoi acc'

# 1) Artifact hash / bytes / newlines (recompute independently — do NOT reuse write_file's byte count)
sha256sum .hermes/plans/<ts>-<slug>.md
wc -c     .hermes/plans/<ts>-<slug>.md
python - <<'PY'
p=".hermes/plans/<ts>-<slug>.md"
s=open(p,encoding="utf-8").read()
print("bytes", len(s.encode("utf-8")))
print("newlines", s.count("\n"))
print("splitlines", len(s.splitlines()))
PY

# 2) Stale-token sweep — should print nothing (list the patterns the task told you to remove)
grep -nE 'HEAD `9d096c9|editor note|meta-edit|test_hermes_cron_contract.py::test_source_config_80|py_compile.*\.ps1' \
  .hermes/plans/<ts>-<slug>.md || echo 'NO_STALE_TOKENS'

# 3) Exclusive write scope — prove ONLY the planned file is new/changed
#    Pre-existing dirty/untracked files (not created by you) must be EXCLUDED from the "did I touch
#    anything" verdict; they were already dirty before this task.
git status --short --untracked-files=all | grep -vE '^\?\? (scripts/generate_cron_source_config.py|python_runner/tests/test_generate_cron_source_config.py)$'
echo '--- tracked diff (should list only the plan, if tracked) ---'
git diff --name-only | grep -vE '^\.hermes/plans/' || echo 'ONLY_PLAN_MODIFIED'

# 4) Self-hash MUST be 0 — a plan cannot contain its own final SHA-256 (writing it would change the bytes)
grep -c '<JUST_COMPUTED_SHA256>' .hermes/plans/<ts>-<slug>.md   # expect 0

# 5) Required anchors present (adjust tokens to the task)
grep -nE '910a8add3b86960d1b64702c379c7fced8963168|quarantine/phase9-out-of-gate-20260813-b772b76' .hermes/plans/<ts>-<slug>.md | head
grep -nE 'PENDING_AG_OPUS_REAUDIT|NO-LIVE' .hermes/plans/<ts>-<slug>.md | head
```

## Interpretation rules

- **Step 3 is the real proof of exclusive scope.** `git diff --name-only` does NOT list untracked files, so for an *untracked* plan it returns nothing and you must rely on `git status --short --untracked-files=all`. The plan file will appear as `??` (new untracked). Pre-existing modified files (` M HANDOFF.md`, ` M scripts/...`) and pre-existing untracked drafts will also appear — those are NOT your changes; exclude them by pattern and note they were already dirty. The verdict "only the planned file is new" holds when every other listed path is pre-existing dirt you did not write.
- **Do NOT run `git add` / `git commit`.** Plan-only. The `git diff --check` no-side-effect recipe (intent-to-add then `git reset -q`) from the main skill still applies if you want a whitespace/conflict-marker gate; for an untracked plan use `git add -N` so `diff --check` can see it, then `git reset -q`.
- **Step 4 (self-hash = 0)** confirms the plan did not embed its own final hash. If it is >0, the file is self-corrupting and must be fixed — the external audit prompt, not the plan body, binds path+SHA+bytes+line count.
- **Step 5** confirms the corrected baseline (HEAD SHA), the NON-EVIDENCE quarantine ref, and the mandatory footer (`PENDING_AG_OPUS_REAUDIT` / `NO-LIVE`) survived the rewrite.

## Checklist
- [ ] SHA-256 / bytes / newlines recomputed via terminal (not from write_file's byte count)
- [ ] Stale-token sweep returns empty
- [ ] `git status` shows only the planned file as new; pre-existing dirt excluded by pattern
- [ ] `git diff --name-only` (tracked) lists only the plan, if tracked
- [ ] Self-hash count == 0
- [ ] Baseline HEAD + quarantine ref anchors present
- [ ] Footer `PENDING_AG_OPUS_REAUDIT` / `NO-LIVE` present
- [ ] No `git add`/commit performed
