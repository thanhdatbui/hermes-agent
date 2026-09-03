# Upload hook verification and runtime provenance

## Failure pattern captured

A final feed session can log `upload-hook` with `result: started` while no video is posted. Do not interpret hook invocation, an existing `upload_result.json`, or a successful feed session as upload success.

For each machine, inspect the final `upload_result.json` and the corresponding `log.jsonl`:

- `status: success` is acceptable only with explicit post evidence such as `post verification passed`, `upload video success`, or `upload completed` from the subprocess output.
- `status: failed` with `reason: upload_subprocess_nonzero` means the upload process exited non-zero; read `stderr_tail` and `stdout_tail`.
- `status: timeout` with `reason: upload-timeout` means only `started` evidence exists unless the child process produced a separate verified receipt. It is not success and its exact UI/proxy cause must not be invented.
- A `started` hook event is dispatch evidence, not post evidence.

## Non-interactive CLI gate

The canonical module entrypoint is:

```text
python -m scripts.tiktok_workflow --config <config> --workflow-workbook <TikN.xlsx> --machine <N> --no-dry-run
```

When this runs through a background subprocess, `run_post.py` must not call `input()` for the real-execution confirmation. The safe contract is:

- interactive TTY: ask for `YES`;
- non-interactive stdin: use the non-interactive confirmation path;
- never accept an `EOFError` as a successful upload.

Before a farm batch, verify the exact interpreter/repository revision used by the launcher contains this behavior. A fix committed in the upload repository is not evidence that an already-running feed worker loaded it.

## Runtime provenance gate

Before explaining a farm-wide upload failure, record:

1. upload repository `HEAD` and dirty state;
2. the actual command from `upload-hook`;
3. the interpreter path and working directory;
4. the loaded source/module revision when practical;
5. representative `upload_result.json` and `log.jsonl` evidence.

If the artifact's stderr shows an old prompt implementation while the repository already contains the non-interactive fix, classify it as a deployment/runtime provenance mismatch, not as a workbook or account failure.

## Timeout handling

Keep `timeout` separate from `failed` in reports. A timeout proves the subprocess did not return before the configured deadline; it does not prove TikTok rejected the post, proxy failed, or UI hung. Inspect child logs/receipts and stop at the evidence boundary.

Do not launch a whole-farm retry merely to investigate. First verify the exact runtime revision and run the canonical upload entrypoint on the explicitly authorized target/canary, with the required proxy/device-lock isolation.
