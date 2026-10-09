# Offline Git candidate binding recipe

Use this recipe when a closeout gate extracts a candidate from a local Git
repository and binds the review to exact bytes.

## Repository binding

1. Resolve the Git root first:
   `git -C <candidate> rev-parse --show-toplevel`.
2. Preserve unrelated dirty/untracked paths; inspect only the authorized files.
3. Use `tmp_path` and local `git init`, identity config, add, and commit. No
   network, device, or remote ref is needed.

## Non-targeted working-tree parity

- Commit a tracked baseline file.
- Modify it without staging.
- Call the real extractor and the real binding resolver.
- Assert the extracted scope is the modified file, the binding mode is the
  working-tree mode, and `extracted.diff_sha256 == binding["diff_sha256"]`.
- Ensure Git subprocess reads are hermetic (`--no-ext-diff`; disable fsmonitor
  and hooks where the implementation supports those flags). Ambient external
  diff settings can cause `git diff` to fail even in a valid temporary repo.

## Oversized candidate safety

- Use a deliberately small extraction limit against a large unstaged edit.
- Assert extraction emits the explicit truncation marker and hashes the exact
  returned representation.
- Resolve the binding from the raw working-tree diff and assert its SHA differs
  from the truncated extraction SHA.
- The pipeline must treat that mismatch as a pre-review binding failure; never
  accept a truncated candidate as if it were the raw candidate.

## Verification discipline

After editing either the implementation or test, rerun the exact focused test
against the final bytes, then `py_compile` and the required scoped diff check.
A baseline pass before a test edit is historical evidence only. If a bounded
worker budget ends before the final commands, report the work as incomplete and
list each unrun check.
