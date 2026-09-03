# Offline-Tested Read-Only ADB Probe Tool (verified 2026-08-12, tiktok-follow)

Pattern for building a **new-file-scope** tool + offline test in a consumer repo
(`tools/<name>.py` + `follow_runner/tests/test_<name>.py`) without touching
production files, docs registry, or automation-core. Concrete instance:
`tools/dump_selectors.py` (UI probe cho phase mode 2) — read AGENTS.md /
PROJECT_RULES.md / docs/ai/*guide* / HANDOFF.md / docs/ui-compatibility.md
first, per repo rule.

## Loading repo `tools/` modules in tests — non-package dir shadow trap

`from tools import dump_selectors` FAILS when the repo's `tools/` has no
`__init__.py`: Python resolves `tools` to site-packages
(`tools/__init__.py` from some installed package) → `ImportError: cannot
import name 'dump_selectors'`. Do NOT make `tools/` a package (that edits the
repo's import surface). Load by path instead:

```python
def _load_module():
    repo_root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("dump_selectors_under_test",
                                                  repo_root / "tools" / "dump_selectors.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
```

Tests then monkeypatch `m.subprocess.run` (module attr, not `sys.modules` —
the module holds a direct `subprocess` reference).

## Test design that proved itself (3 tests, 0.1s)

- **Exact command-list assertion**: `fake_run` appends every cmd; assert the
  full list equals the 3 expected read-only commands
  (`exec-out screencap -p`, `shell uiautomator dump /sdcard/window.xml`,
  `exec-out cat /sdcard/window.xml`) AND assert no destructive token
  (`tap|keyevent|swipe|force-stop|launch|reboot|clear`) appears in any cmd.
  Scripts stay honest: `workbook`/`credentials` also forbidden in cmd parts.
- **Deterministic filenames**: `monkeypatch.setattr(m, "utc_timestamp",
  lambda: "20260812T010203Z")` → assert every artifact name contains the
  ts and `sha256(serial).hexdigest()[:12]`. Summary JSON asserts
  `serial_hash` == full hex, label, ISO `timestamp_utc` derived from the
  compact ts, `foreground_package` from the hierarchy root's `package` attr
  (no extra dumpsys command), markers `selector_inference=false` +
  `ui_compatibility_update=deferred_until_coordinator_review`.
- **Sanitized summary keeps structural fields**: nodes carry exactly
  `text/content_desc/resource_id/class/bounds/index` (bounds = raw block
  string `[x1,y1][x2,y2]`, index kept as string) — enough for a future
  selector writer, no `password` attr, no serial raw.
- **Failure = zero partial artifacts**: mkdir happens before probe, but
  assert `list(out_dir.iterdir()) == []` on ADB rc!=0 + `BLOCKER` +
  failing command name on stderr. Never fake a PASS.
- **CLI**: `--serial` required → `SystemExit` code 2; default out-dir
  repo-local computed inside `parse_args` from a `repo_root()` helper.

## Windows path-case pitfall (dính thật in the ad-hoc verifier)

The real repo path is `D:\Taadaa\...` (capital T). Terminal/FS ops succeed
with any casing (case-insensitive FS) but **string equality in assertions
fails on case mismatch**: the ad-hoc verifier hardcoded
`REPO = Path(r"D:\taadaa\tiktok-follow")` and one check FAILED while the
pytest (which compared `args.out_dir == module.repo_root() / "runs" /
"probes"`) PASSED. Lesson: in tests AND ad-hoc verifiers, compare paths
against the module's own resolved path (`m.repo_root()`, derived from
`Path(__file__).resolve()`), never a hardcoded string you typed. This
doubles as the cross-drive safety pattern (see
`hermes-verify-script-pitfalls.md`).

## Coordinator handoff contract

Tool must NOT infer selectors — summary writes markers so the coordinator
reviews the real dump and updates `docs/ui-compatibility.md` + regression
tests later. Deterministic output naming (`capture_<tsUTC>_<hash12>_<label>`)
lets a coordinator glob by label (`seed-profile`/`follower-tab`/
`follower-item`) without parsing serials.

## Verification gate run that passed

`py_compile` both files → focused `pytest follow_runner/tests/test_dump_selectors.py`
(3 passed) → full `follow_runner/tests/` (85 passed; baseline 60 + worker + 3
new — attribute deltas) → `git diff --check` (warnings about LF/CRLF on OTHER
workers' files are not yours) → fresh `hermes-verify-*` tempfile script with
21 behavioral checks (fix harness bugs like the path-case one, rerun, then
`rm` + prove deletion). No commit/push.