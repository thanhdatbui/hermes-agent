---
name: audit-plan-revision
description: Revise an existing implementation plan (under .hermes/plans/) for internal consistency and audit readiness — documentation-only, enumeration-scope coherence, static-vs-runtime evidence separation, governance gates. Use when asked to "fix/make consistent/update the plan", add a route/item to an enumerated set, or produce an "audit-revised" plan.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, plan-mode, audit, documentation, consistency, review]
    related_skills: [plan]
---

# Audit Plan Revision

Revise an ALREADY-WRITTEN implementation plan so it is internally consistent and audit-ready. The deliverable is the updated `.md` file only. This is NOT implementation.

> Overlaps with the built-in `plan` skill (which authors plans from scratch). This skill covers the *revision / consistency* pass on an existing plan and the audit-readiness discipline (enumeration scope, static-vs-runtime evidence, governance gates). If `plan` is editable in your environment, prefer folding this content into it; otherwise keep this as the supplementary skill.

## Hard boundary — documentation-only

- Edit ONLY the plan markdown file. Do NOT edit production code, tests, policy/HANDOFF, or any other repo file.
- Do NOT run ADB, live automation, scheduled tasks, process kills, network recovery, commit, push, or deploy.
- Re-read the whole plan at the end and confirm no contradictory statements survive.

## Read source ONLY to ground the plan; cite exact locators

For a discovered route/seam, open the real source file and record `file:symbol/lines`.
- PowerShell: `read_file` the `.ps1`, quote the exact function lines (e.g. `Invoke-HealthCheck` ~L512-534 calling `Write-ResumeRequest` ~L533 then `Start-ScheduledTask` ~L534).
- **Windows path gotcha:** `search_files` mis-translates `D:\...` into MSYS `/d/...` and returns `os error 3` on Windows hosts. Use native Windows paths with `read_file`/`patch`, or fall back to `terminal grep "..." "/d/..."` for bulk scans.

## Enumeration-scope consistency (the #1 source of contradictions)

If the plan enumerates a numbered set (routes R1-R10, steps, tasks), every reference to "all of them" MUST use the same upper bound after you add an item.

- After adding a route/item R11: replace every `R1-R10` / `R5-R10` / `R5–R10` (and any en-dash variants) with `R1-R11` / `R5-R11`. Audit these locations: route table, route verification matrix, scope notes ("may only edit R1-R10"), discovery/acceptance gate, RED/GREEN matrix, Task-N heading ("R5-R10 RED→GREEN"), Task rerun list, acceptance-criteria bullets, and the execution handoff.
- Keep classification distinctions explicit: a classification-only route (e.g. "R9 is scan-only, do NOT disable") must not be silently promoted to a runtime-disabled route; a static-source route must not be conflated with dynamic ones.
- **Prove zero stale references remain:** `grep -nE 'R1-R10|R5-R10' file.md` → expect NONE_FOUND.

## Separate static-source evidence from runtime/installed-task evidence

Plans that hard-stop via PowerShell/scheduler often cannot be runtime-verified offline.

- A "test" that inspects `.ps1`/`.py` text and asserts a disabled branch short-circuits BEFORE a launch call is a **static text/ordering scan**, NOT a runtime mock. Label it: "does NOT execute PowerShell, does NOT mock a process call at runtime — it inspects source text/ordering."
- Mark such a route as a **STATIC/REGRESSION node, not a runtime RED→GREEN node**, so a future executor does not misclassify it as runtime proof.
- Always pair it with a **deployment-gap** statement: actual installed-task / live-runtime behavior remains **NOT PROVEN** by the offline plan; track it as an open risk. Never claim the installed task behavior "passed."

## Governance gates to retain in audit-revised plans

- Implementation stays blocked until an independent plan-audit returns `APPROVED` (a transport failure is NOT a verdict).
- Explicit **implementation authorization** is SEPARATE from **release authorization** — never conflate "may edit code" with "may commit/push/deploy".
- Source-only compatibility / deployment-gap statement wherever PowerShell/runtime cannot be verified.
- Dedicated worktree/branch + rebase/diff/rerun gating for shared core changes.

## Baseline binding

When the plan cites HEAD SHAs, bind consumer+core baselines explicitly and keep the stale-SHA provenance note so a reader cannot mistake an old commit for evidence. Do NOT claim audit approval in the plan text — record status as NOT APPROVED if a re-audit is still required.

## Automated Plan Auditor Expectations & Anti-Rejection Pitfalls

When submitting plans to automated model auditors (e.g. 9Router `plan-review`), prevent recurring rejection patterns:
1. **Reproducible Artifacts over Narrative Claims:** Candidate SHA-256 hashes must be 100% reproducible directly from the plan document or explicit deterministic generator scripts — avoid partial fragments or placeholders for scoped targets.
2. **Calibrated Guarantees & Real Threat Models:** Never claim absolute "100% fail-closed against all local adversaries" when handles are closed before Windows `MoveFileExW`. Accurately scope: "Strong serialization for cooperative subagents; Best-effort checkpoint detection at $T_0..T_3$ for uncoordinated background modifications with acknowledged residual TOCTOU".
3. **Bounded Execution on Every Command:** Every `subprocess.run` must use `[sys.executable, ...]` with an explicit `timeout=` parameter. No unbudgeted socket or filesystem waits.
4. **Universal Hold Guard on Lock Acquisition:** Lock state machines must enforce that EVERY acquisition path (normal run and takeover) verifies metadata and rejects `MANUAL_HOLD_REQUIRED` before mutating lock state.
5. **Review Gate Freshness & Endpoint Binding:** Review receipts must bind `request_hash`, `artifact_sha256`, `model`, `endpoint`, and enforce a strict freshness TTL ($\le 300s$) verified under lock.

## Domain Invariants & Anti-Minefield Gate

Before reporting the revised plan, require:

- [ ] Domain invariants identify a source of truth, verification method, and violation handling.
- [ ] Every mutating or I/O step has explicit Pre-condition, Post-condition, and Side-effects.
- [ ] Every I/O, subprocess, HTTP, socket, ADB, or OCR action has an explicit timeout and bounded retries.
- [ ] Reruns are safe through a receipt, lock, checkpoint, or idempotency guard.
- [ ] Unknown states capture evidence and stop fail-closed; no guessed continuation.
- [ ] Missing evidence is reported as NOT PROVEN, never silently promoted to PASS.

## Consistency checklist (run before reporting done)

- [ ] Every enumerated set uses one consistent upper bound (grep for stale bounds — must be empty).
- [ ] Each new route/item has a table row, a matrix entry, a Task step, a named test, and appears in the rerun/handoff lists.
- [ ] Static-source tests labeled static (not runtime); deployment-gap NOT_PROVEN stated.
- [ ] Governance gates (audit APPROVED gate, impl≠release auth, deployment-gap) preserved.
- [ ] No production code/tests/policy edited; no ADB/commit/push/network actions taken.
- [ ] Full plan re-read; no contradictory "Route Map R1-R10" / "may only edit R1-R10" survivors.

See `references/checklist.md` for a concrete worked example (the R11 health-watcher route addition).
