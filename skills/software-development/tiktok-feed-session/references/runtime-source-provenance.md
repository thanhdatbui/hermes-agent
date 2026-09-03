# Runtime source provenance for feed incidents

Use this reference before claiming a feed-session fix was loaded by a live run.

## Why Git presence is insufficient

A committed fix, an edited working tree, and code already imported by a running Python process are three different states. Python does not automatically reload an imported module after the file changes. A live alert can therefore be produced by:

- the prior committed version;
- the current checkout but before a newer edit;
- a long-lived process that imported an older module before the edit; or
- a different checkout/interpreter than the one being inspected.

## Required evidence

For the exact target run, capture and compare:

1. launcher command line and working directory;
2. interpreter executable path;
3. imported module `__file__` for the affected flow;
4. source byte hash or commit/tree identity;
5. process start time and source-edit/commit time;
6. target machine/row/serial and its own run artifact root.

Use labels:

- `COMMITTED_SOURCE_PRESENT`: fix exists in the inspected Git tree;
- `WORKTREE_SOURCE_PRESENT`: newer uncommitted fix exists locally;
- `PROCESS_SOURCE_CONFIRMED`: running process identity and module bytes match the candidate;
- `RUNTIME_LOADING_UNPROVEN`: any required identity is missing or mismatched.

Do not turn `COMMITTED_SOURCE_PRESENT` into `PROCESS_SOURCE_CONFIRMED` from a passing unit test or from the repository name.

## Incident interpretation

For a camera/profile incident, first determine whether the message is:

- a deliberate fail-closed result from the newer guard (for example, BACK was sent but a fresh recapture still showed Camera); or
- evidence that the intended newer bounded-retry logic was not active.

The exact log, matching XML, and screenshot decide the first question. The process/source provenance evidence decides the second. Keep both conclusions separate.

## Safe canary gate

Before a target canary:

- resolve machine → row → serial from the canonical source;
- detect an existing batch/process that already includes the target and do not launch a duplicate;
- run import/entrypoint preflight with the same interpreter used by production;
- if preflight fails, classify `BLOCKED_AT_GATE_0_PREFLIGHT` and state that no device action occurred;
- after any source/test edit, rerun focused verification and use a fresh canary from the final tree.

A successful run from another machine, a historical artifact, or a generic batch exit is not proof for the incident target.

## Reporting format

Report concisely:

- `Code`: committed/worktree state;
- `Runtime`: process/module provenance confirmed or unproven;
- `Live`: target resolution, duplicate-run status, and canary result;
- `Blocker`: exact gate and evidence path.
