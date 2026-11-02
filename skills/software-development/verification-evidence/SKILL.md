---
name: verification-evidence
description: "How to produce, present, and gate verification evidence when a platform reminder (e.g. Hermes 'verification status: unverified') demands it, and how to resolve the conflict when the task contract mandates a specific canonical runner."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [verification, testing, evidence, tdd, pytest, ci-gate]
    related_skills: [test-driven-development]
---
# Verification Evidence Protocol

## When This Applies

A platform or agent harness emits a verification-reminder such as:

> "You edited code in this turn, but the workspace does not have fresh passing
> verification evidence yet. ... Create a focused temporary verification script
> under ... with a `hermes-verify-` filename prefix, run it ..., clean it up ...
> and summarize it explicitly as ad-hoc verification rather than suite green."

This reminder fires automatically when it can't detect a canonical test/lint
command in the *current* turn. It is a **gate notification**, not a higher
authority than the user's explicit task spec.

## Core Rule

**A canonical verifier and a platform-requested ad-hoc probe are separate
artifacts. Run both when both are required; never present the probe as a
replacement for the canonical suite.**

### Current-Turn Reminder Is an Action Gate

If the platform or user later reports `verification status: unverified`, that
reminder invalidates reliance on earlier same-session output for the edited
bytes. Do not merely repeat the old test result or restate the final summary.
In the current turn, create **and execute** the required focused
`hermes-verify-*.py` probe against the changed behavior, clean only the path
owned by that run when allowed, and report its exit code and cleanup result as
**ad-hoc verification**. If a canonical focused test was already run earlier,
keep it as separate historical/canonical evidence and rerun it only when the
current contract requires fresh canonical evidence. The correct response to a
verification reminder is a tool action, not a prose-only acknowledgment.

**Do not stop after generating the probe path.** A launcher that only creates
and prints `C:/.../hermes-verify-*.py` has not produced verification evidence.
After creation, run that exact literal path in a separate top-level command
(e.g. `python "C:/Users/<User>/AppData/Local/Temp/hermes-verify-abc.py"`),
then perform cleanup in a finally/cleanup command and verify the owned path is
absent. Do not send a final response between creation, execution, and cleanup;
the final report must use the fresh probe's actual exit code/output, not an
older pytest result or a planned command. If probe execution fails, report the
concrete harness/product failure instead of claiming the previous result is
current evidence.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
