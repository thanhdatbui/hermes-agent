# Canonical Orchestration Policy Promotion & Focused Offline Validation

When promoting a rule tested or introduced in a specific consumer repository (e.g. `tiktok-luot nuoi acc/AGENTS.md` or `PROJECT_RULES.md`) to the canonical all-repo orchestration policy in `D:\Taadaa\HERMES_SUBAGENT_RULES.md`:

## Core Principles

1. **Promote Once, Reference Many (No Fleet Bloat)**:
   - Do not copy large verbatim policy blocks across 30+ consumer repositories.
   - Insert the normative rule into the canonical document (`HERMES_SUBAGENT_RULES.md`).
   - Update canonical contracts (such as `## CANONICAL ORCHESTRATION CONTRACT`) to point to the new rule so all consumer repos inherit the contract by reference.

2. **Clear Precedence & Backward Compatibility**:
   - Multi-target/fleet rules (such as cluster-first canary selection) govern **scoping** and **selection**.
   - Per-machine rules (such as official runner enforcement, strict incident evidence, media capture, device locks, and no-manual-tap) govern **execution** on whichever target is selected.
   - Always include an explicit clause stating that cluster-first scoping does not weaken or bypass existing per-machine runner and evidence standards.

3. **Pure Byte-Level CRLF Integrity**:
   - `HERMES_SUBAGENT_RULES.md` on Windows environments is typically formatted with pure CRLF (`\r\n`).
   - Insertion scripts must format all inserted lines and blank lines with `\r\n`.
   - Validate that `crlf == lf`, `lone_lf == 0`, and `lone_cr == 0`.

4. **Offline Validation Checklist**:
   - **Baseline Backup**: Make a byte-exact backup copy outside the repo fleet (e.g. `C:\Users\Kibe\AppData\Local\Temp\HERMES_SUBAGENT_RULES.md.bak-baseline`).
   - **Anchor Uniqueness**: Prove the anchor where the rule is inserted occurs exactly once before writing.
   - **Marker Count**: Confirm `marker_count == 1` post-patch.
   - **Heading Deduplication**: Parse all `## ` headings and assert `len(headings) == len(set(headings))`.
   - **Clause Assertions**: Check regex matches for all core mandates (e.g. failure signature clustering, representative selection, parallel clusters, failure isolation, fleet reopen requirements).
   - **Contract Pointer**: Verify the canonical orchestration contract line contains the reference.
   - **Scope Lock & Zero Bleed**: Verify `git status` on consumer repos remains unchanged, no live device actions were called, and no commit was made.
