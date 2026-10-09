# User-authorized reviewer and large-diff closeout

## External-agent authorization

- Treat “kiểm tra/check/review” as read-only unless the user explicitly asks to sửa/làm/triage remediation.
- Never invoke Claude CLI, OpenCode, or another external coding agent merely because a review failed, a gate is blocked, or a terminal command is inconvenient.
- A request for a named reviewer (for example, Codex Terra) authorizes that reviewer call only; it does not authorize Claude CLI or code edits.
- If an external coding agent was accidentally invoked, report the exact process/result and stop further autonomous remediation until the user explicitly authorizes it.

## Large-diff procedure

1. Run focused tests and inspect staged scope before review.
2. Normalize line endings only when evidence shows line-ending churn; re-stage and re-run tests.
3. Use a minimal, semantically coherent scope. The `--files` list must exactly match staged files.
4. Never use `--skip-test`; never treat a score alone as approval; `APPROVED_PARTIAL` is failure.
5. A truncation finding is not automatically a code defect. First remove CRLF churn, unrelated/generated files, and accidental staging; then review the smallest coherent production+test slice.
6. Do not add speculative mock tests merely to chase a score. Tests must exercise actual production functions and address a named finding; integration claims require isolated integration evidence, not a renamed unit mock.
7. Do not declare L3 merely because a reviewer requests more evidence or a dispatch budget is exhausted. Continue with bounded scope reduction, focused verification, or an explicitly authorized reviewer route. Use L3 only after the applicable retry/escalation path is genuinely exhausted.
