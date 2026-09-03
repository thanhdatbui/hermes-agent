# Absolute-path worker provenance diagnostics

Use this reference for a **read-only** investigation where a delegated worker claims to have written files but the requested parent target does not show them.

## Evidence recipe

Run commands against the exact native Windows target; do not silently substitute the current shell directory:

```text
pwd
git -C 'D:\Taadaa\target' rev-parse --show-toplevel
git -C 'D:\Taadaa\target' rev-parse HEAD
git -C 'D:\Taadaa\target' branch --show-current
git -C 'D:\Taadaa\target' worktree list --porcelain
git -C 'D:\Taadaa\target' branch -avv
git -C 'D:\Taadaa\target' status --short --untracked-files=all
```

For each requested path, report the exact path, existence, byte size, SHA-256, and mtime. If the path is absent, inspect `git ls-files` and permitted source/test directories for the repository-relative equivalent. A root-level filename and a tracked nested source module are different claims.

For a tracked file on Windows, include:

```text
git -C 'D:\Taadaa\target' ls-files --eol -- path/to/file
git -C 'D:\Taadaa\target' hash-object path/to/file
git -C 'D:\Taadaa\target' diff -- path/to/file
```

Interpret `i/lf w/crlf` as a possible checkout-normalization explanation when the Git object/hash and semantic content agree; do not report it as a worker write without additional evidence.

## Worktree and landing-path search

Enumerate the explicitly named sibling directory, e.g. `D:\Taadaa\target-worktrees`, and the Git-reported worktrees. Also inspect related sibling directories with names indicating a clone/worktree/phase, while excluding secrets, workbooks, `.env`, logs, and generated runtime trees. Hash only allowed source/test artifacts and report exact paths. An empty `*-worktrees` directory is useful evidence: it rules out that directory as the observed landing location, but not other Git worktrees.

## Attribution rules

- `git worktree list` proves checkouts exist, not which worker used one.
- A worker terminal's `pwd`, invocation command, process command line, or completion metadata is required to prove isolation or authorship.
- If the worker has exited and no invocation record exists, report the sibling checkout as a possible isolated location and state that exact attribution is unavailable.
- Separate: current diagnostic terminal location; requested parent repository state; available sibling worktree locations; exact paths containing observable artifacts.
- Never edit, stage, commit, push, delete, or “repair” anything during this investigation.
