# Windows git-bash: running the canonical test/verify command

When the repo working directory lives under a path with spaces (e.g.
`D:\Taadaa\tiktok-luot nuoi acc`) and the host shell is MSYS git-bash, the
naive command fails:

```
cd /d/Taadaa/tiktok-luot nuoi acc && git status   # -> cd: too many arguments
```

## Fixes that worked

1. **Quote the path** when it contains spaces:
   ```
   cd '/d/Taadaa/tiktok-luot nuoi acc' && git status --short --untracked-files=all
   ```
   The task may instruct `cd /d/Taadaa/tiktok-luot nuoi acc` literally — that
   form works in `cmd.exe` but NOT in git-bash. In git-bash, always single-quote
   the MSYS-style path. Both `/d/...` (MSYS) and `C:\...` (native) forms are
   accepted by git-bash; `/d/...` is cleaner.

2. **Always pass `workdir='/d/Taadaa/tiktok-luot nuoi acc'`** to the terminal
   tool. The tool's `cd` is handled by the harness; the in-command `cd` is your
   own. Set workdir so each call starts in the right place even if a prior
   `cd` failed.

3. **`search_files` with `target='content'` fails on a path with spaces** with
   `IO error ... The system cannot find the path specified`. Workarounds that
   worked: use the `terminal` tool with `grep -R "<pattern>" -n <path>` (git-bash
   handles the unquoted/quoted path there), or read files directly with
   `read_file`. Don't rely on `search_files` for content search inside a
   space-containing repo path — fall back to grep-in-terminal or read_file.

## PYTHONPATH pollution from the Hermes session (false ImportError)

The Hermes terminal session exports a `PYTHONPATH` that prepends the hermes
venv:

```
PYTHONPATH=C:\Users\Kibe\AppData\Local\hermes\hermes-agent;C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages;...
```

If that venv holds compiled extension modules built for a different CPython
version than the interpreter you invoke, imports fail at runtime. Observed
concretely (2026-08-14, D:\Taadaa\Tiktok-video):

```
$ python -m pytest ... -k avatar_picker
...
E   ImportError: cannot import name '_imaging' from 'PIL'
    (C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\__init__.py)
```

`python` resolved to `C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe`
(Python 3.12), but the hermes venv's `PIL` package contained only
`_imaging.cp311-win_amd64.pyd` — so Pillow's compiled core was unimportable.
Two tests failed with this ImportError; **they were not real failures**.

### Diagnosis

```bash
echo $PYTHONPATH                       # venv paths injected?
which -a python python3                # which interpreter actually runs
python -c "import sys; print(sys.executable)"
python -m pip show Pillow | head -6    # note: may report the VENV's pip/site-packages,
                                       # not the standalone interpreter's — same injection
ls /c/Users/Kibe/AppData/Local/hermes/hermes-agent/venv/Lib/site-packages/PIL/_imaging*.pyd
ls /c/Users/Kibe/AppData/Local/Programs/Python/Python312/Lib/site-packages/PIL/_imaging*.pyd
```

Compare the `.pyd` cp-tags (cp311 vs cp312) against the interpreter version.
A version mismatch under a polluted `PYTHONPATH` is the smoking gun.

### Fix (verified working)

Clear `PYTHONPATH` for the canonical run so the standalone interpreter uses its
own site-packages:

```bash
cd /d/Taadaa/Tiktok-video && \
PYTHONPATH= /c/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe \
  -m pytest -q -p no:cacheprovider tests/test_tiktok_workflow.py -k "avatar_picker"
# -> 7 passed, 351 deselected
```

After clearing, the same interpreter imported its own working Pillow
(`PIL OK 12.3.0`) and all 50 avatar tests passed.

### Rule

- **Never classify a `PIL`/compiled-extension ImportError as a product/test
  defect on this host without first checking `PYTHONPATH`.** The polluting env
  var is a harness condition, not evidence of a broken package or broken code.
- Prefix the canonical verifier with `PYTHONPATH=` (or `env -u PYTHONPATH`)
  when the repo requires compiled extensions.

## Verifier invocation pattern (canonical)

```
cd '/d/Taadaa/tiktok-luot nuoi acc' && \
python -B -m pytest -q -p no:cacheprovider \
  python_runner/tests/test_hermes_cron_phase9_identity.py \
  python_runner/tests/test_hermes_cron_phase9_schema.py \
  python_runner/tests/test_hermes_cron_contract.py \
  python_runner/tests/test_hermes_cron_watcher.py \
  python_runner/tests/test_hermes_cron_regressions.py \
  python_runner/tests/test_hermes_cron_p1_r2.py && \
python -m py_compile python_runner/hermes_cron/state_producer.py && \
git diff --check python_runner/hermes_cron/state_producer.py
```

- `-B` skips `.pyc` writes; `-p no:cacheprovider` avoids `__pycache__` churn
  that would otherwise dirty `git status`.
- Chain `&& echo OK` so a non-zero exit is visible.
- After edits, confirm `git status --short --untracked-files=all` and
  `git diff --name-only` show ONLY the allowlisted paths (untracked new files do
  NOT appear in `git diff --name-only` — check status separately).
