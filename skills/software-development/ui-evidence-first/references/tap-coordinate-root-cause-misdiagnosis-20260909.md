# Tap Coordinate Root Cause Misdiagnosis — Case 20260909

## Background

21/79 machines (26.6%) dính lỗi `profile username still mismatched after switch` tại ca Row 3 (09/09/2026). Coordinator phát hiện tap center `[540, 816]` (full row Button) rơi vào dead-space trên Samsung → ban đầu concluded root cause là tap coordinates.

## Investigation Flow

1. **Initial hypothesis:** Tap x=540 lands in dead-space between TextView (x=252..596) and badge (x=942..1032). TikTok ignores the tap.
2. **Patch applied:** Removed `if clickable: best_bounds = node.bounds` branch, replaced with inner TextView priority → center changed from `[540, 816]` to `[416, 816]`.
3. **Canary M28 (doanthu1005):** 3/3 switch attempts with CORRECT coordinates `[416, 816]`, TikTok **STILL did NOT switch**. `tienpham7676` remained active throughout.
4. **Post-alert batch confirmed:** Same machine M28 same result — not a timing issue.
5. **Conclusion:** Root cause was NOT tap coordinates. TikTok session/auth validation refused to switch target account (stale/invalid session on device).

## Evidence

```
Switcher 1 before tap: tienpham7676 selected=true, doanthu1005 selected=false
Tap fired at center=[416, 816] (inner TextView) → SUCCESS
Verify 1 after tap: display_name="Thủy Tiên ...." (still tienpham7676!)
Switcher 2 before tap: tienpham7676 still selected=true (DID NOT SWITCH)
```

## Lesson

**Wrong tap coordinates and TikTok session/auth failure produce IDENTICAL symptoms:**
- Both cause `profile username still mismatched after switch`
- Both leave the original account active after tap
- Both require `switch_attempts` max retries before fallback

**How to distinguish:**
1. If tap center is `[540, 816]` (full row) and there's a clickable Button wrapper → tap coordinate issue is plausible → fix and canary.
2. If tap center is already correct (inner TextView `[~400, 816]`) and switch STILL fails → root cause is TikTok session/auth, NOT tap coordinates.
3. Check `switcher_1_guard/attempt_1/ui.xml`: if target account is visible in list but `selected=false` remains after tap → session/auth issue.
4. The auto-login reconcile (fallback) confirms session issue — `reconcile_tiktok_accounts.py` is the correct fix path.

## Anti-Pattern

**Assuming code fix solves it without canary verification:**
- The patch to `_find_account_switch_option` was code-correct (tapping inner TextView instead of dead-space center)
- But canary proved the real issue was elsewhere
- Without canary, we would have committed a code change that doesn't fix the actual problem

**Mandatory:** Always run canary AFTER code fix and BEFORE committing. If canary fails despite correct code, report "root cause is TikTok session/auth, not code" instead of "code fix insufficient."
