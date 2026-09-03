# Plan-authored baseline drift (plan-MAINTENANCE pitfall)

When you REVISE an existing implementation plan (applying audit findings,
user corrections, or re-grounding), the plan's own stated baseline — HEAD SHA,
file SHAs, "test X is missing", "module Y is new" — may be STALE relative to
the live repo. The repo advances between sessions: commits land, tests get
re-landed via cherry-pick, file bytes change. A plan that says
"test_hermes_cron_phase9_identity.py is missing; 9A.1 adds it" can be flatly
wrong if the repo already shipped that test GREEN.

## Mandatory pre-flight for plan MAINTENANCE (not just authoring)
Before trusting ANY parent-stated baseline inside the plan:
1. `git rev-parse HEAD` + `git branch --show-current`; compare to the plan's
   claimed HEAD. Note divergence: local unpushed vs origin, cherry-picks,
   resets, fast-forwards.
2. `git status --short --untracked-files=all` — snapshot foreign dirt to
   preserve byte-for-byte; confirm the two outcome-unknown untracked drafts'
   preimage SHAs still match the plan's recorded values.
3. SHA-256 the plan's claimed file hashes (e.g. `source_config.py`) and compare
   to live `sha256sum`. A mismatch means the plan's FACT table is stale and must
   be corrected to the CURRENT repo, not the parent's memory.
4. AST-scan `python_runner/tests/*.py` for every `module::test_node` the plan
   references or claims is missing. A plan claim "test X does not exist" MUST be
   verified by scan, not by belief. Use `scripts/scan_plan_test_nodes.py`.
5. `git log --oneline -- <file>` to check whether a claimed "rolled-back /
   non-evidence" commit was later re-landed (cherry-pick). The re-landed version
   IS current evidence even if the original SHA was reset away.

## Canonical example (tiktok-luot nuoi acc, 2026-08-13)
- Plan stated HEAD `910a8add`, `source_config.py` `6d8b16fd`, and "identity
  test missing; 9A.1 adds new nodes; no reference to missing
  test_hermes_cron_phase9_identity.py".
- Live repo: HEAD `9d096c9a…` (local master, unpushed; origin/master
  `1146c20…`), `source_config.py` `3fea1690…`, and
  `test_hermes_cron_phase9_identity.py` EXISTS and is GREEN (re-landed via
  cherry-pick `c69d159`). `cb086680` had been reset, but the identity change
  survived through `c69d159`.
- Fix applied: re-ground the FACT table and 9A.1 to "identity already shipped;
  9A.1 is regression-consolidation on the existing contract + existing modules,
  not new-file creation". Never claim a test is missing when the AST scan shows
  it present. Do not perpetuate a rolled-back SHA as "the only identity commit"
  when a later cherry-pick superseded it.

## Patch-content corruption (separate, easy-to-hit pitfall)
`patch` old_string/new_string MUST be the exact literal text to change. Never
embed your own editorial instructions into new_string (e.g. pasting
"Dòng 69 hiện là: ... đổi thành: ..." as the replacement). That writes the
meta-instruction into the file as content and corrupts it. After every
serialized same-file patch batch, re-read the modified region and re-hash the
file before reporting completion — a stale/corrupted final SHA is worse than no
SHA at all.
