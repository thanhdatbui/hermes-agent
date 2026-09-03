# Windows fresh verifier launcher

Use this when the harness requests fresh evidence and a direct multiline
`python -c` command would require nested quoting through Git Bash.

## Safe sequence

1. Create a small launcher outside the repository, preferably with
   `write_file`, under `C:\Users\Kibe\AppData\Local\Temp`.
2. The launcher creates the actual verifier with:

```python
with tempfile.NamedTemporaryFile(
    prefix="hermes-verify-",
    suffix=".py",
    dir=tempfile.gettempdir(),
    delete=False,
    mode="w",
    encoding="utf-8",
) as handle:
    verifier_path = Path(handle.name)
    handle.write(verifier_source)
```

3. The verifier must use an explicit repository path when it runs outside the
   repo, parse the exact changed files with `ast.parse`, and run the focused
   pytest command with `-B -p no:cacheprovider`.
4. Run the launcher from the repository. In a `finally` block, delete only the
   verifier path it created. Delete the launcher afterward in the same evidence
   window.
5. Separately inspect for leftover `hermes-verify-*` files. Existing files are
   not owned by this run: report them and do not bulk-delete them.
6. Report the result as **Ad-hoc verification: PASS**, separately from the
   pytest count. If the direct inline attempt failed due to quoting, classify
   it as harness setup failure and do not report it as a product regression.

## Minimal assertions

A useful verifier should prove both syntax and the changed contract anchors,
for example canonical-path gates, identity capture/rechecks, mandatory snapshot
fields, and the focused regression test names. Keep fixtures offline and use
`tmp_path`/mock boundaries; never invoke real sync, workbook, journal, lock,
device, credential, or scheduler state.

## Common failure

`SyntaxError: unexpected character after line continuation character` from the
outer `python -c` means the launcher was malformed before the verifier ran. Do
not retry the same quoting shape. Switch to an out-of-repo launcher file and a
real temporary verifier.