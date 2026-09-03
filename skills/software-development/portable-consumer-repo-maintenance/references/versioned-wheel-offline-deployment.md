# Versioned-Wheel Offline Deployment: Case Study 2026-08-23

ViChanger GET_IP `--receiver-foreground` fix delivered as automation-core 0.4.45 → 0.4.46 wheel + consumer repin. Contract: no install, no live, no commit; preserve unrelated dirty files in both repos.

## Pipeline with real outputs

### 1. Baseline (both repos)

```
cd /d/Taadaa/automation-core && git status --porcelain
 M src/automation_core/preflight.py      # the fix (--receiver-foreground added to am broadcast)
 M tests/test_preflight.py               # regression test for GET_IP flag order
```
Consumer (`/d/Taadaa/tiktok-luot nuoi acc`): 7 dirty files incl. `flows/multi_machine_feed_session.py` (WIP, preserve-only) and the pin file `requirements-automation-core.txt`.

Fix diff was one line in `check_android_vpn`:
```diff
-    ["am", "broadcast", "-a", "vn.vichanger.app.GET_IP", "-n", ...],
+    ["am", "broadcast", "--receiver-foreground", "-a", "vn.vichanger.app.GET_IP", "-n", ...],
```

### 2. Version bump + build

Single-line patch: `version = "0.4.45"` → `"0.4.46"` in pyproject.toml.

```
python -m build --wheel --outdir dist .   # setuptools backend present → no isolation needed
Successfully built automation_core-0.4.46-py3-none-any.whl
```
(`--no-isolation` avoids network; only safe because setuptools>=68 + wheel verified importable first.)

### 3. Wheel verification BEFORE copying

```python
import zipfile
z = zipfile.ZipFile('dist/automation_core-0.4.46-py3-none-any.whl')
meta = z.read('automation_core-0.4.46.dist-info/METADATA').decode()
# Line order: Metadata-Version, Name, Version — version is NOT the first line
'Version: 0.4.46'
'--receiver-foreground' in z.read('automation_core/preflight.py').decode()  # True
```

Copy + hash equality:
```
sha256 dist/...whl == sha256 C:/Users/Kibe/p1-venv-wheels-20260812/...whl
39e0aafc0f2fec46e342257b13e281f64bc492ec992fc0811cc6bba275ba4a85
```

### 4. Repin (consumer)

```
automation-core @ file:///C:/Users/Kibe/p1-venv-wheels-20260812/automation_core-0.4.46-py3-none-any.whl
```
Keep the `# Validated P1 wheel (...)` comment version in sync with the pin.

### 5. Core test

```
pytest -q tests/test_preflight.py → 10 passed in 6.84s
```
Regression test asserts flag order directly: `assert "--receiver-foreground" in call` for every GET_IP broadcast.

### 6. Provenance WITHOUT install (the shadowing trap)

Naive check lies:
```
$ python -c "import automation_core, importlib.metadata as md; ..."
module path: D:\Taadaa\automation-core\src\automation_core\__init__.py   # SOURCE TREE
version: 0.4.45                                                          # STALE
```
Why: `__editable__.automation_core-0.4.45.pth` in site-packages + persisted `PYTHONPATH` entries (`D:/Taadaa/automation-core/src`, `D:/Taadaa/Tiktok-video/scripts`) win over any wheel reasoning.

Correct isolated probe (no install):
```python
tmp = tempfile.mkdtemp()
zipfile.ZipFile(wheel).extractall(tmp)
subprocess.run([sys.executable, '-c',
  'import automation_core, importlib.metadata as md; '
  'print(md.version("automation-core")); print(automation_core.__file__)'],
  env={**os.environ, 'PYTHONPATH': tmp})
# → version: 0.4.46 ; module path: <tmp>\automation_core\__init__.py  ✓
shutil.rmtree(tmp)
```
Wheel had zero `Requires-Dist` lines → import-probe needs nothing else.

### 7. Dual-wheel A/B failure attribution (75 passed / 3 failed)

First combined run: `test_multi_machine_feed_session.py + test_device_prepare.py` → 3 failed, 75 passed. Failures all `'failed' != 'skipped-device-locked'` / `"worker returned unexpected result type: MagicMock"` raised from `flows/multi_machine_feed_session.py:1793` — a preserve-only dirty consumer file.

A/B procedure: extract 0.4.45 and 0.4.46 wheels to two temp dirs, run the SAME 3 nodes with each PYTHONPATH:

| Run | Result |
|---|---|
| PYTHONPATH=extract(0.4.45) | **collection ERROR** — `ImportError: cannot import name 'DeviceLockNeedsUserDecision' from 'automation_core.device_lock'` |
| PYTHONPATH=extract(0.4.46) | 3 failed (identical set) |
| bare session python (=dirty src 0.4.45) | 3 failed (identical set) |

Interpretation:
- Identical failure set under old-src and new-wheel ⇒ **pre-existing**, caused by consumer dirty WIP, not the wheel bump.
- The 0.4.45-wheel ImportError proves the dirty consumer source is AHEAD of the old pin: the new API exists only in the newer core tree. The version bump is the ENABLING change — the focused suite cannot even import against the old wheel, so "did you try the old version?" has no baseline runtime here.
- Per-file with new wheel: `test_device_prepare.py` 23 passed; mmfs 52 passed / 3 failed.

### 8. Scope close-out

`git diff --check` exit=0 both repos. Core final dirty set = original 2 fix files + pyproject.toml (in-scope). Consumer final dirty set shrank mid-session because an EXTERNAL process committed `6dfd722` absorbing 5 previously-dirty popup/feed files — attributed via `git log --oneline -3` + `git show --stat HEAD`; my touched set (`requirements-automation-core.txt`) untouched by it. See `concurrent-workspace-safety` pitfall "A foreign writer can COMMIT the dirty file and move HEAD mid-session".

## Acceptance mapping (contract → evidence)

| Criterion | Evidence |
|---|---|
| pyproject 0.4.46 | `grep '^version' pyproject.toml` → `7:version = "0.4.46"` |
| wheel at exact path, metadata 0.4.46 | ls -la + zipfile METADATA read |
| consumer pin exact 0.4.46 wheel | grep requirements file |
| core pytest passes | 10 passed |
| consumer focused tests pass / failures classified | 75 passed; 3 failed = pre-existing (A/B proof) |
| diff-check + changed paths clean | exit=0 ×2, path sets enumerated |
| provenance | isolated extract-import prints 0.4.46 + tmp path |

## Pitfalls specific to this pipeline

- METADATA version is line 3, not line 1 — printing `splitlines()[0]` shows `Name:` and looks unverified.
- `python -m build` default (isolated) may attempt network installs of build deps; check local setuptools/wheel first.
- Never validate a wheel by importing in the working shell (editable-install + PYTHONPATH shadowing above).
- Clean up BOTH A/B extract dirs before finishing — leftover temp dirs are noise in `%TEMP%` and could silently shadow later probes.
- Consumer suites using `unittest.TestCase` classes need `file.py::ClassName::test_name` node IDs for focused reruns (see Windows space-path section in the parent SKILL.md).
