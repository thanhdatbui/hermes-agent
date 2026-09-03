# AI Auto-Recovery "commit thất bại" — full diagnosis (2026-08-20, MÁY 35 + MÁY 38)

## Symptom (Telegram Farm Alerts)

```
🛠️ [AI AUTO-RECOVERY - MÁY 35]
• Hướng sửa: Bổ sung handler dismiss_recommendation_or_brand_profile_popup trong benign_popup.py ...
• Kết quả: 🟢 THÀNH CÔNG — ... Đã thực thi lệnh Back (ADB keyevent 4) ...
• Code patch: ⚠️ Patch áp dụng nhưng commit thất bại — pyte
```

The "— pyte" truncation = `pytest_failed_rolled_back` (error string starts with "pytest...", agent message cut it).
User phrasing: "Là bị lỗi gì áp dụng mà commit thất bại hoài thế" (repeats on MÁY 38 same morning).

## Root cause chain (verified against real code)

1. `automation-core/src/automation_core/alerts.py::send_farm_machine_alert` spawns
   `python_runner/ai_recovery/agent.py` via `subprocess.Popen([sys.executable, str(_AGENT_SCRIPT), ...])`.
   `sys.executable` = the Hermes gateway venv python (host PATH exports
   `PYTHONPATH=...hermes-agent;...hermes-agent\venv\Lib\site-packages`).
2. `python_runner/ai_recovery/code_patcher.py::_run_pytest` builds `_PYTEST_CMDS[target]` from
   `sys.executable` too — same broken venv.
3. Gateway venv PIL is broken: `import PIL` works, `from PIL import Image` fails
   `ImportError: cannot import name '_imaging' from 'PIL'` (binary module missing/mismatched).
4. `test_benign_popup.py` imports `flows.benign_popup` → `core.image_navigation` →
   `automation_core.tiktok.image_navigation` → `from PIL import Image` → collection ERROR →
   pytest exits non-zero BEFORE any test runs.
5. `apply_and_commit` sees `passed=False` → restores original file verbatim →
   `result["error"] = "pytest_failed_rolled_back"` → agent.py reports
   `Patch áp dụng nhưng commit thất bại — pytest_failed_rolled_back` → truncated "— pyte".

## Confirmation evidence

- Repo git-CLEAN; `git log --oneline -8 --all` shows no ai-recovery commit;
  `git reflog` no sign of the patch.
- `grep -rn "dismiss_recommendation_or_brand_profile_popup" python_runner/` → 0 hits
  (handler never existed; also no `detect_quick_security_prompt` for MÁY 38).
- `"D:/Taadaa/python-envs/automation/Scripts/python.exe" -B -m pytest -q --tb=short --no-header
  python_runner/tests/test_benign_popup.py` → reproduces the collection ImportError
  (because that env ALSO resolves to the hermes venv site-packages via PYTHONPATH).
- `python -c "import PIL; print(PIL.__version__, PIL.__file__)"` → 12.2.0 from
  `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL` (broken `_imaging`).
- Git mutex + patch counter files (`D:\Taadaa\runtime\kibe\git_patch.lock`,
  `recovery_patch_counter.json`) were empty/absent — lock was NOT the blocker.
- Machine-side: feed-session log showed `manual-needed / unexpected popup/dialog marker detected`
  at `D:\Taadaa\runtime\kibe\live\2026-08-20\row-2-071501\...\machine_35\...` — the alert's origin;
  artifact dir `baseline_after_contact_follow_suggestion_dismiss` etc. confirm the machine
  was un-stuck by ADB (green result) while the code patch was discarded.

## Why it keeps repeating

Each new alert → Gemini writes a NEW handler for the same popup class → pytest collection
crash (interpreter issue, not handler logic) → silent rollback → machine un-stuck via ADB only →
codebase unchanged → next machine hits the same popup → same alert → repeat. The farm never
learns the popup, so "commit thất bại hoài".

## Durable fix (STOP GATE — ask user before applying)

1. In `code_patcher.py::_PYTEST_CMDS`, replace `sys.executable` with the repo's pinned
   interpreter, exactly like the manual working invocation:
   `env -u PYTHONPATH "D:\Taadaa\python-envs\automation\Scripts\python.exe" -B -m pytest -q --tb=short --no-header <testfile>`
   (run with cwd=python_runner so `core.*`/`flows.*` resolve). Optionally also fix the
   gateway venv: `pip install --force-reinstall pillow` (hermes venv).
2. Re-run the suite to confirm collection green, then a future AI-recovery patch should
   commit + push normally.
3. Consider also hardening `agent.py`: log `patch_result["error"]` fully (no truncation) so
   the Telegram message shows `pytest_failed_rolled_back` instead of "— pyte".

## Related known pitfalls (same class)

- PYTHONPATH env poison (hermes venv) defeats even absolute machine Pythons — see
  "Target-machine Python and render-worker provenance" in SKILL.md; the working test
  invocation pattern is `env -u PYTHONPATH "/c/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe" -m pytest ...`.
- `pytest_failed_rolled_back` is a code_patcher failure MODE, not an error message from
  pytest itself; check `code_patcher.py::apply_and_commit` result keys
  (`patched/tested/committed/error`) before blaming git.
- Git-related failures in the same pipeline surface as `commit_failed: ...` / `push_failed: ...`
  (from `_git_commit_push`), which are distinct strings — don't conflate.
