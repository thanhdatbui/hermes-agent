# Reviewer verdict integrity and Claude CLI evidence

Use this reference whenever a coding or enforcement task is described as “until Claude approves”.

## Non-negotiable completion rule

A passing test suite, a normal Claude CLI exit code, a self-authored review prompt, or a worker’s summary is not approval. Completion requires fresh reviewer output that explicitly contains `Verdict: APPROVED` and a score of at least 85/100. Read the output artifact after the process exits; never infer approval from absence of errors.

## Evidence sequence

1. Record the exact review artifact path and round number.
2. Inspect the submitted source tree again after each remediation. Confirm syntax (`py_compile` where applicable), focused tests, and that repo/deploy/live copies are the same files the reviewer will read.
3. Launch a fresh Claude review with read-only permissions and a bounded turn/time budget.
4. If the output contains `unrecognized_model`, advisor-disabled warnings, timeout, incomplete transcript, syntax error, path mismatch, or no explicit verdict, classify the round as UNKNOWN/REJECTED. Do not report success.
5. Read the final artifact and extract the literal verdict and score. Only `APPROVED` plus score >= 85 closes the loop.
6. On rejection, preserve the reviewer’s concrete blockers as the next patch contract. Do not broaden scope or keep repeating an unchanged prompt.

## Production-shaped review pitfalls

- Test mocks must match actual tool result envelopes. For terminal tools, test JSON/dict results with `output`, `exit_code`, and `error`; a raw marker string can produce a false pass.
- Allowlist executable paths with `realpath`, not only a basename. Parse command arguments with `shlex`/argv and reject chaining, substitution, redirection, unknown flags, positional extras, and abbreviated argparse flags.
- Deadline claims must be measured wall-clock. `ThreadPoolExecutor` used in a `with` block can wait during `__exit__` after `future.result(timeout)` raises; if immediate return is required, use explicit shutdown with `wait=False` and test elapsed time.
- A reviewer can catch drift between the live Hermes skill, deploy tree, and git repository. Synchronize the actual reviewed artifact before claiming the fix is reproducible.
- If a concurrent edit leaves syntax broken, stop the review loop, repair the file, compile it, and submit a new round. Never summarize an earlier passing snapshot as the current verdict.

## Round ledger format

```text
Round N — Verdict: REJECTED/UNKNOWN/APPROVED — Score: NN/100
Evidence: <absolute artifact path>
Blockers: <short concrete list>
Verification: <focused test/compile output>
Next contract: <exact bounded remediation>
```
