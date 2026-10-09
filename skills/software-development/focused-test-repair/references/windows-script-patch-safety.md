# Windows Script-Based Patch Safety

## Why this matters

A multiline `python -c` patch can fail in two independent ways:

- Shell/Python quoting can turn an intended source literal such as `\\n` into
  a real newline, producing an unterminated test string during pytest collection.
- A compact read-transform-write expression can truncate the destination before
  the source is read. In Python, expressions are evaluated left-to-right; in a
  form such as `open(dst, 'wb').write(open(src, 'rb').read())`, opening `dst`
  first destroys the source when `dst == src`.

Both failures require fresh verification. A prior passing run is stale after
any subsequent edit.

## Transactional recipe

1. Capture a preimage outside the repository, including raw bytes and EOL style.
2. Read the source once into `original`; never open the destination until the
   replacement and all anchor assertions have succeeded.
3. Build `updated` in memory and assert each anchor count is exactly one.
4. Write `updated` to a same-directory temporary path with the original EOL
   convention, then atomically replace the target after close/flush.
5. Immediately run byte-size/line-count checks, `py_compile`, the exact focused
   pytest command, and scoped `git diff --check`.
6. If the file is unexpectedly empty or malformed, stop. Recover only the owned
   file from the saved preimage in an isolated worktree/temp clone, then rerun
   all checks. Do not use broad checkout/restore/reset in a shared worktree.

## Quoting check

For an inserted Python source literal, construct the expected replacement with a
small external script or `repr()` and inspect its raw representation before
writing. The final source should contain `\\n` characters when the runtime test
needs an escaped newline; it must not contain a physical newline between the
opening quote and closing quote. Use a temporary launcher file instead of deeply
nested Git-Bash `python -c` quoting when the patch contains triple-quoted text.

## Evidence rule

Report each attempt separately: collection failure, repair result, compile result,
pytest result, and diff-check result. Do not report an earlier green run as proof
for bytes changed afterward. If recovery restores the original tree, state that
the requested patch is not present rather than claiming completion.
