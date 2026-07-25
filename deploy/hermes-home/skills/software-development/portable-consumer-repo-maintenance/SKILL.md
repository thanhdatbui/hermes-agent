---
name: portable-consumer-repo-maintenance
description: "Implement focused consumer-repository fixes for machine-specific configuration drift with isolated worktrees, override preservation, and evidence-based verification."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [consumer-repo, portability, configuration-drift, worktree, verification]
    related_skills: [systematic-debugging, test-driven-development, requesting-code-review]
---

# Portable Consumer-Repo Maintenance

## Trigger

Use when a consumer repository has machine-specific absolute paths, runtime defaults, scheduler/install wrappers, or configuration drift findings. This applies to Python, PowerShell, shell, and mixed-language workflow entrypoints.

## Workflow

1. **Isolate first.** Locate the consumer repository, read `AGENTS.md`/project rules/runbooks, inspect git status, and create a dedicated worktree and branch from the clean current consumer `main`. Do not edit a shared/core repository for a consumer-only issue.
2. **Trace configuration flow.** Read the flagged scripts, callers, wrappers, and focused tests. Identify default values, CLI flags, environment variables, path normalization, subprocess propagation, and scheduler/task-registration arguments.
3. **Build a tight red check.** Add focused tests that fail before the fix and prove both:
   - defaults do not embed user/machine-specific paths;
   - explicit CLI overrides remain authoritative;
   - environment overrides remain authoritative where supported.
   For non-Python wrappers, assert generated command/path text when invoking registration would be unsafe or unnecessary.
4. **Implement the smallest portable change.** Prefer project-relative paths, standard executable discovery (`PATH`), or explicit configuration. Preserve current behavior, validation, lock semantics, subprocess environment propagation, CLI compatibility, and exact existing asset basenames (including spaces and punctuation). Do not silently rename a workbook/config asset while relocating its directory. Avoid unrelated refactors.
5. **Verify in layers.** Run the focused tests, compile/lint checks, relevant drift/static scans, and `git diff --check`. Then run the broader suite if practical. Distinguish failures caused by missing sibling/reference worktrees or pre-existing fixtures from failures in the changed scope.
6. **Ad-hoc fallback.** If no canonical test/lint command is detected, create a temporary `hermes-verify-*` script in the OS temp directory using a safe `tempfile` path. Run it with the repository import path explicitly configured (for example, `PYTHONPATH=<worktree>`), remove it afterward, and report it explicitly as ad-hoc verification rather than suite-green evidence. Always assert the changed behavior directly, including default resolution and explicit environment/CLI override precedence. Keep assertions exact but simple when checking wrapper text (prefer asserting the required basename and forbidden legacy basename separately); if the verifier itself fails due to quoting/escaping or is launched outside the repository, correct the harness and rerun it before diagnosing repository code. Capture cleanup proof with `test ! -e <temp-script>` and print a concise success marker.
7. **Report precisely.** Include exact worktree path, branch, changed files, commands and real outputs, focused/full-suite status, blockers, and confirmation that no commit or push occurred. Preserve unrelated changes.

## Portability Patterns

- Define project root from the script location (`Path(__file__).resolve().parents[...]` or PowerShell `$PSScriptRoot`), not from the current working directory.
- Use repository-local `data/` or `runtime/` defaults only when that matches the repository’s documented behavior; otherwise make required locations explicit rather than inventing a host path.
- Use environment variables for deployment-specific paths and make CLI arguments take precedence over defaults. Do not silently replace an explicit CLI value with an environment value.
- Use `shutil.which()`/equivalent executable discovery for tools expected on the host PATH. Keep explicit executable overrides available.
- For scheduled tasks, derive project paths at install time and pass resolved values as arguments. Avoid registering stale paths from the development machine.

## Pitfalls

- A Windows absolute path can appear even when it is computed from a portable worktree on Windows; tests should reject known machine-specific fragments (`OneDrive`, `CodexRuntime`, cache roots, user profiles), not reject every drive-letter path.
- A temporary verification script launched from `%TEMP%` may fail to import repository modules. Set `PYTHONPATH` or use an explicit repository import path; this is a harness issue, not evidence that the implementation failed.
- Do not call a full suite green when unrelated baseline tests fail. Record exact failure counts and reasons.
- Do not run live scheduled-task registration, workbook writes, device flows, or external automation just to validate path construction unless explicitly authorized.

## Support Files

Session-specific drift verification notes and commands are in `references/portable-drift-verification.md`.

## Completion Checklist

- [ ] Consumer-only worktree/branch created from current main.
- [ ] Relevant rules, docs, callers, and tests inspected.
- [ ] Regression tests cover portable defaults and CLI/env override precedence.
- [ ] No machine-specific absolute defaults remain in scope.
- [ ] Focused tests and relevant static/diff checks pass.
- [ ] Full-suite failures, if any, are classified and reported.
- [ ] No commit or push was performed unless requested.
