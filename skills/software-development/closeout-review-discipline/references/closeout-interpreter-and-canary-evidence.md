# Closeout interpreter and canary evidence

## Gate/test interpreter binding

A focused pytest run can pass while `closeout_gate.py` fails because the gate selects a different Python executable or import root. Never compare counts without comparing the command. From the gate output, capture:

- exact pytest executable and arguments;
- repository working directory;
- `sys.executable`, `sys.prefix`, and `PYTHONPATH`;
- imported production module paths (`module.__file__`).

Reproduce the gate command with its exact interpreter. If the gate's interpreter is broken or belongs to another project, classify it as gate preflight/environment evidence rather than a product regression; repair the invocation/setup, then rerun the gate. Do not claim approval from a focused run made by a different interpreter.

Namespace-sensitive mocks must patch the object actually imported by the production call path. If production uses a fallback import (`python_runner.flows...` versus `flows...`), make fixtures explicit about early gates and patch the live module namespace, not merely the source module guessed from the import statement. A test that passes only under one `PYTHONPATH` is not valid closeout evidence.

## Remote farm canary evidence

For controller-to-remote-host routing changes, keep three evidence classes separate:

1. **Offline regression:** mocked command argv/env proves serial, video, workbook, config, source root, and no controller-only `ADB_SERVER_SOCKET` leakage.
2. **Remote preflight:** the remote host confirms the expected source file and target binding without UI/upload side effects.
3. **Live canary:** one bounded real-device workflow produces its own execution log, report JSON, and verification image before teardown.

A live canary is accepted only when the same run proves the expected device/account/video and includes `status=SUCCESS`, `post_verified=true`, and `post_submission_state=ACCEPTED` (or the workflow's equivalent), plus a published/profile artifact. Exit code 0 alone is not proof. If teardown returns the device to Launcher, do not use an external post-teardown screenshot as publication evidence; retrieve the in-run `post-published-surface` or profile-grid artifact from the run directory.

## Failure-after-side-effect safety

A subprocess nonzero after the workflow was invoked is ambiguous: the post may have succeeded before the process failed. Do not automatically release a durable upload reservation for retry. Retain the reservation until a report/ledger reconciliation proves the attempt did not publish; add a regression that calls the hook twice and asserts the second call is blocked. Release reservations only for pre-invocation/spawn failures where no workflow side effect could have occurred.

## Reviewer remediation discipline

When the reviewer asks for broader evidence, convert each request into a concrete offline regression at the real production seam: corrupt state must fail closed; row-level and machine-level cooldown sources must use OR semantics; date/streak boundaries must be explicit; remote command quoting and environment isolation must be asserted. Keep farm canary evidence separate from pytest and closeout evidence. Do not weaken production behavior merely to make a stale test pass; first identify whether the test contract, import namespace, early gate, or production logic is wrong.
