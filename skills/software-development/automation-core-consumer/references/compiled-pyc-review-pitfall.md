# Compiled `.pyc` Review Pitfall

## Session: 2026-07-26 — Codex _soft_reboot_recovery review

### Problem

Codex was asked to add wake+swipe unlock into `_soft_reboot_recovery` — a function that lives between `boot_completed` polling and `force-stop` inside the soft reboot recovery sequence in `social_reg_v1.py`. The review checklist was:

1. Wake uses `KEYCODE_WAKEUP` (input keyevent 224), not `KEYCODE_POWER` toggle
2. Swipe from 95% height → 25% height, 500ms duration
3. Verify unlock via `dumpsys window policy`
4. Consumer retry 3 lần
5. Changes must not modify `automation-core`

### Root cause of blind review

The project has two parallel source trees:

- **`D:\Taadaa\Tiktok_Reg\social_reg_v1.py`** — real source, ~290KB, 6724 lines
- **`D:\OneDrive\Tiktok_Reg\social_reg_v1.py`** — deployed bootstrap, ~600 bytes, loads a compiled `.pyc`

Codex ran on a worktree under `D:\OneDrive\Tiktok_Reg\` and modified the **compiled** `.pyc` (`__pycache__/social_reg_v1.cpython-311.pyc`) directly. The `.py` source file was **not updated**.

This means:
- `grep`, `search_files`, and `git diff` on the `.py` files found **nothing**
- The `_soft_reboot_recovery` function was visible only in the `.pyc` 
- A reviewer who only searches `.py` files would conclude the function doesn't exist and cannot verify the change

### How to find the real source

```bash
# Key command: find where automation-core lives (it's an editable install)
pip show automation-core
# → Editable project location: D:\Taadaa\automation-core

# Sibling consumer projects live under the same parent
ls D:\Taadaa\
# → Tiktok_Reg/  automation-core/  Tiktok-video/
```

### What actually existed in the skill already

The consumer-side unlock recovery parameters (`95%→25%`, 500ms, dumpsys verify, 3 retries) were **already documented** in the `automation-core-consumer` skill's Consumer-Side Unlock Recovery section. The review requirement was a verification checklist against code that may or may not match what was already prescribed.

### Lesson

When Codex modifies a consumer project that uses a `.pyc` bootstrap loader, **do not attempt to review from the deployed `.py` files alone**. Either:

1. Find and read the real source tree under `D:\Taadaa\`
2. Request Codex decompile the `.pyc` back to source before review
3. Compare the `.pyc` timestamp against the `.py` source — if the `.pyc` is newer, the compiled code diverges from source

The review in this session resulted in **REJECT** because the compiled-only change could not be verified.
