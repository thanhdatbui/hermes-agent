# UTF-8 and structured-output boundaries

## Durable pattern

A provider/runtime failure can be introduced before model execution when a Windows parent process encodes Unicode stdin using the locale code page while the child CLI expects UTF-8. The durable fix is to make the subprocess contract explicit:

```python
subprocess.run(
    command,
    input=prompt,
    text=True,
    encoding="utf-8",
    capture_output=True,
    check=False,
)
```

Do not infer success from `returncode` alone. Preserve, and inspect separately:

1. return code;
2. stdout;
3. stderr;
4. provider-produced result file, if the CLI supports one.

## Recovery-runtime regression matrix

Use offline fixtures only; never invoke devices, accounts, workbook operations, locks, or live recovery handlers.

| Boundary | Fixture | Expected assertion |
|---|---|---|
| stdin encoding | Prompt containing Vietnamese/non-ASCII text | capture seam receives `encoding="utf-8"`; child does not report invalid UTF-8 |
| noisy executor output | Human text plus fenced/embedded JSON | canonical patch decision is extracted, then role/schema validation runs |
| advisor output | Equivalent `status`/plan envelope or result wrapper | typed advisor result is ready with a non-empty fingerprint |
| incomplete executor output | Missing target-bound handler, evidence, or tests | `ready_for_live` is false and ladder fails closed |
| provider failure | Non-zero exit with quota/outage markers | typed provider-unavailable result activates only the configured fallback path |

## Safety boundary

Advisor readiness is not executor authorization. Normalize advisor output only into a read-only planner object. Normalize executor output only into a patch-decision object. Preserve the configured attempt/slot cap and do not add retries merely because parsing failed; parsing ambiguity should consume/fail the slot according to the existing ladder.

## Verification commands

Run the smallest affected tests first, then the requested batch, using the repository's pinned interpreter. Also run `py_compile` on modified Python files and inspect `git diff --check` plus a scoped diff summary. Report exact command output and blockers; never fabricate a pass count when the runner output did not include one.
