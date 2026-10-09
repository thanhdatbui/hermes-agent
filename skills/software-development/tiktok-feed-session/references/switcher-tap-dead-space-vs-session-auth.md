# Account Switcher Tap — Dead-Space vs Session/Auth Root Cause

## Issue Pattern

Lỗi `profile username still mismatched after switch` có 2 root cause có triệu chứng GIỐNG NHAU:

### Root Cause A: Tap Dead-Space (Samsung)
- **Triệu chứng:** Tap center `[540, Y]` (full row Button width=1080) rơi vào khoảng trống giữa TextView (x≈252..596) và badge icon (x≈942..1032). TikTok bỏ qua tap.
- **Fix:** Trong `_find_account_switch_option`, ưu tiên inner TextView bounds thay vì full row → center `[~416, Y]`.
- **File:** `python_runner/flows/feed_swipe_smoke.py`, dòng ~15469-15490.
- **Verify:** Nếu tap center thay đổi từ `[540, Y]` → `[~416, Y]` và canary pass → confirmed.

### Root Cause B: TikTok Session/Auth (Stale Session)
- **Triệu chứng:** Tap center ĐÃ ĐÚNG (inner TextView `[~416, Y]`) nhưng TikTok vẫn KHÔNG chuyển account. 3/3 attempts đều fail.
- **Phân biệt:** Kiểm tra switcher XML:
  - `tienpham7676 selected=true` (active)
  - `doanthu1005 selected=false` (target, visible in list)
  - Sau tap → verify profile vẫn hiện `tienpham7676` → TikTok từ chối chuyển.
- **Root cause:** TikTok session của tài khoản đích expired/stale trên thiết bị. TikTok validation refuse to switch.
- **Fix path:** Auto-login reconcile (`reconcile_tiktok_accounts.py`) hoặc re-login thủ công.
- **CẤM:** Không sửa tap coordinates thêm — đã đúng, vấn đề ở session.

### How to Distinguish (Decision Tree)

```
Switcher tap fails →
  ├─ Check tap center in log.jsonl selector.center
  │   ├─ center x ≈ 540 → Dead-space possible → Fix & canary
  │   └─ center x ≈ 400..450 → Coordinates correct → Session/auth issue
  │
  └─ Check switcher XML before tap
      ├─ Target NOT in list → ACCOUNT_MISSING → reconcile needed
      └─ Target in list, selected=false → Session/auth issue → reconcile
```

## Batch Alert Handling (20260909 Case)

- 21/79 machines (26.6%) fail switcher on Row 3.
- Patch applied: tap coordinates fixed. py_compile passed.
- Canary M28: 3/3 taps correct coordinates → still fails → confirmed session/auth issue.
- **Conclusion:** 21 máy là session/auth issue, không phải code bug. Auto-login reconcile đang xử lý.
- Patch code vẫn giữ (fixes dead-space for marginal cases) nhưng KHÔNG commit vì root cause ở别处.
