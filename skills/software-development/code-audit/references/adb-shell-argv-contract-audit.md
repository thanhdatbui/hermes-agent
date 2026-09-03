# ADB Shell-Argv Contract Audit (worked 2026-08-15)

Read-only verdict audit of the uncommitted avatar fix in `D:/Taadaa/Tiktok-video`
(4 dirty files: `docs/tiktok-ui-compatibility.md`, `scripts/tiktok_workflow/media_manager.py`,
`scripts/tiktok_workflow/state_machine.py`, `tests/test_tiktok_workflow.py`). Deliverable
was strict JSON `{"passed": bool, ...}` — verdict token + findings only.

## The bug class

`automation-core` `AdbClient.shell(args)` already prepends the device-shell token:

```python
def shell(self, args, *, timeout=None, check=False) -> AdbResult:
    return self.run(["shell", *args], timeout=timeout, check=check)
```

The pre-fix code passed `["shell", "content", "delete", ...]` etc., producing
`adb shell shell content delete ...` — silently broken, but masked because every
call site ran with `check=False` and the results were best-effort (the stale
MediaStore rows/files were never actually cleaned).

## Verification sequence that worked

1. `git status --porcelain` + `git diff > /tmp/avatar_fix.diff`, read the full diff.
2. Located the contract: `grep -rn "def shell" automation-core/src/automation_core/adb.py`
   → confirmed `run(["shell", *args])`.
3. **Verified the PINNED wheel, not the source checkout** — `requirements-automation-core.txt`
   pins `file:///D:/CodexRuntime/automation-core-merge-20260804/wheel-dist-0.4.35/automation_core-0.4.35-py3-none-any.whl`.
   Extraction this time used the **zipfile variant** (the `pip install --target`
   route from `references/pinned-wheel-contract-audit.md` failed silently — empty
   target dir, exit 0 — so `ls` the target before trusting it):
   ```bash
   mkdir -p /tmp/wheelcheck && cd /tmp/wheelcheck
   python -m zipfile -e 'D:\CodexRuntime\...\automation_core-0.4.35-py3-none-any.whl' \
       'C:\Users\<u>\AppData\Local\Temp\wheelcheck'
   grep -n "def shell" automation_core/adb.py   # native Windows paths ONLY, never MSYS /d/ or /tmp
   ```
   Confirmed 0.4.35 has the same contract → the diff's token removal is correct.
4. Grepped `'"shell",'` across `scripts/` and classified every hit:
   - `device_transport.py` raw `[adb_path, "-s", serial, "shell", ...]` for `subprocess` — token CORRECT there.
   - `adb.shell([...])` call sites — token WRONG; diff removed all three (`purge_media_rows`,
     `delete_remote_glob`, `touch_remote_file`). Other call sites (mkdir, ls, df, find,
     content query/insert/delete) already used the correct form.
5. Checked the red-capable regression: asserts exact argv per helper AND
   `all(command[0] != "shell" for command in commands)`.
6. Ran the focused suite read-only, isolated:
   ```bash
   tmpdir=$(mktemp -d)
   env -u PYTHONPATH PYTHONPYCACHEPREFIX="$tmpdir" \
     python -m pytest tests/test_tiktok_workflow.py -k "avatar or media" -q
   rm -rf "$tmpdir"; git status --porcelain   # must be unchanged
   ```
   (73 passed; worktree untouched — no bytecode left because PYTHONPYCACHEPREFIX
   pointed at the disposable temp dir. Note: pytest cache write failed with
   Permission denied on `D:\Taadaa\Tiktok-video\.pytest_cache` — harmless, the run
   itself was clean.)

## Avatar MediaStore ordering pattern (the "canonical behavior" the diff/doc describe)

The avatar fix's ordering, which the COMPAT-AVATAR-007 doc must match exactly:

1. `delete_remote_glob` every stale avatar glob (Download/Pictures/DCIM × avatar_/av_)
2. `purge_media_rows("avatar_")` + `purge_media_rows("av_")` — MediaStore keeps a row
   for a deleted file (grey placeholder tile in picker)
3. `delete_remote_file(remote_avatar)` — MediaStore does NOT rescan a path changed in place
4. `push_video` with a UNIQUE timestamped name (`av_<safe>_<int(time.time())><suffix>`)
5. `touch_remote_file` — force fresh mtime (push preserves source mtime)
6. `purge_media_rows("avatar_")` again — the push-time row keeps the OLD date_modified
7. `refresh_media_library` → `_ensure_image_media_store_row` (query → insert → query loop)
8. picker: album labels `("Pictures", "Camera", "Hình ảnh", "Images", "Ảnh")` — Pictures
   FIRST because the avatar is pushed there; then canonical first-image-tile tap
9. fail-closed `AVATAR_PICKER_NO_MATCH` if no tile; `AVATAR_MEDIASTORE_INDEX_FAILED` if index missing

Audit cross-check: docs claim ↔ code order at `state_machine.py:5534-5576` and the
picker at 6674-6744. The doc is authoritative ("Không được làm: bỏ qua lỗi command
contract, chọn Recent đầu tiên khi grid trống...") and the code matches it.

## Injection checks that passed

- `_safe_avatar_name` sanitizes `folder_video` to `[A-Za-z0-9_-]` before embedding in
  remote paths → glob and `_data LIKE '%frag%'` fragments are safe (fragments are
  literals `"avatar_"/"av_"` or sanitized).
- All device commands are argv lists through `AdbClient.shell` — no string
  concatenation, no shell injection surface.
- `_data LIKE '%{fragment}%'` is substring-based: a future fragment containing SQL
  wildcards `%`/`_` would broaden the match — defensive note only (all current
  callers pass literal safe values).
