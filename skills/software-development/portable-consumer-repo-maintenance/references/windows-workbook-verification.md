# Windows Workbook Verification

Use this recipe when a consumer-repo change affects `.xlsx` mapping, preflight, or runtime configuration and the task requires focused ad-hoc evidence.

## Recipe

1. Create a verifier under `%TEMP%` with a `hermes-verify-` prefix.
2. Use `tempfile.TemporaryDirectory(prefix="hermes-verify-")` for workbook/config fixtures.
3. Create a minimal workbook with only the relevant schema (for example, `Accounts` with `May`/`Máy`, `So Seri`, and `ID`).
4. Assert the exact contract: machine resolves to serial and ID; serial resolves back to the same row; legacy YAML/profile source is not consulted; configured ADB path is preserved.
5. Close every workbook explicitly:

```python
wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
try:
    # assertions / reads
    ...
finally:
    wb.close()
```

Also close the workbook used to create the fixture before the temporary directory exits. Otherwise Windows may report `WinError 32` while `TemporaryDirectory` removes the `.xlsx`.

6. Run the script with the repository import path explicitly configured (for example, `PYTHONPATH=scripts`).
7. Remove the verifier afterward and report the result as **ad-hoc verification**. It is not equivalent to a canonical test-suite pass.

## Failure interpretation

If the first run fails during temp-directory cleanup while assertions otherwise reached the expected path, inspect open workbook handles first. Fix the harness with `wb.close()`/`finally`, rerun, and only then classify product behavior. Do not claim the initial cleanup exception proves a repository defect.
