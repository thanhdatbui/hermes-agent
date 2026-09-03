# Follow mode 2 (follow followers từ tab Follower) — tiktok-follow repo

Session 2026-08-12, commit chain `9c3465f` → `08fbdf9` → `e9eaef0` (AG APPROVED).
Probe máy thật → implement → 3 vòng audit. Full suite 108 passed.

## Row-scoped verify cho list UI (kỹ thuật chính)

Khi follow TRỰC TIẾP từ list (tab Follower có nhiều row, mỗi row một nút
Follow), **KHÔNG dùng `classify_button` toàn màn hình** — list luôn chứa nút
`Follow lại` của các row khác chưa xử lý, nên classify toàn dump trả
`not_followed` dù row vừa tap đã follow (hoặc ngược lại). Verify phải
**row-scoped**: chỉ xét nút follow trong cùng y-band với row vừa tap.

```python
def _y_overlap(a, b, margin=60):
    a_top, a_bot = a["bounds"][1], a["bounds"][1] + a["bounds"][3]
    b_top, b_bot = b["bounds"][1], b["bounds"][1] + b["bounds"][3]
    return a_top - margin <= b_bot and b_top <= a_bot + margin

def _follow_button_for_row(nodes, row_node):
    for n in nodes:
        if n.get("resource_id") != FOLLOWER_FOLLOW_BUTTON_RESOURCE_ID:  # tcj
            continue
        if _y_overlap(row_node, n):
            return n
    return None

def _classify_row_button(nodes, row_node) -> str:
    btn = _follow_button_for_row(nodes, row_node)
    if btn is None:
        return "unknown"
    text = (btn.get("text") or "").lower()
    if any(m.lower() in text for m in FOLLOWED_TEXT): return "followed"
    if any(m.lower() in text for m in FOLLOW_BUTTON_TEXT + FOLLOW_BACK_TEXT): return "not_followed"
    return "unknown"
```

Verify loop sau tap: dump MỚI → `_classify_row_button` → `followed` = success;
`not_followed` → retry tới `verify_reload_retries` → hết cap = `FOLLOW_BLOCKED`
(`state.set_follow_blocked()`); `unknown` (nút biến mất/layout đổi) →
`MANUAL_REVIEW` — KHÔNG silent-success.

Selectors chốt từ dump thật máy 1 (TikTok 46.3.3, `FollowRelationTabActivity`):
- Tab Follower trên profile: text `Follower`, id `com.ss.android.ugc.trill:id/sdn`
- Row: username `...:id/txt_desc`, display name `...:id/txt_user_name`,
  nút follow `...:id/tcj` (text `Follow`/`Follow lại`/`Đã follow`), menu `...:id/ote`
  (KHÔNG phải follow)
- Header list: `Đã follow N`/`Follower N`/`Bạn bè N`/`Được đề xuất` (android:id/text1)
- PITFALL: header tab `Đã follow` cũng chứa "đã follow" — marker list header
  khác marker nút follow row; không dùng chung set text.

## Launch activity resolution (pitfall)

`am start -n <pkg>/<pkg>.MainActivity` fail `Error type 3` trên máy thật:
launcher activity KHÔNG phải MainActivity. Trước khi launch, resolve activity
thật:
`adb shell cmd package resolve-activity --brief <pkg>` (hoặc dumpsys
`mResumedActivity` sau khi mở bằng tay). TikTok 46.3.3 máy 1 =
`com.ss.android.ugc.aweme.splash.SplashActivity`. Đừng đoán tên activity;
`Error type 3` = class không tồn tại trong package đã cài, không phải lỗi
network/VPN.

## Core `open_profile_root` contract: adapter phải có `back()`

`automation_core.tiktok.account_switcher.open_profile_root(adapter)` gọi
`adapter.back()` (KHÔNG phải `press_back()`) khi cần thoát subpage. Consumer
`FollowAdapter` chỉ có `press_back()` → core fail. Fix: thêm alias

```python
def back(self) -> None:
    """Contract core account_switcher: `adapter.back()` (trả None = OK)."""
    self.press_back()
```

Và FakeAdapter (conftest) cũng phải thêm `back()` nếu test chạm
`_path_b_verify`/`open_profile_root` — AttributeError trong test chính là
bằng chứng contract thiếu. Path B (sample verify) dùng `adapter.back()` cho
nhất quán, không trộn `press_back`.

## Queue-based FakeAdapter: đếm dump consume theo từng bước

Test `run_mode2` dùng queue XML theo thứ tự consume. Mỗi bước trong flow
consume một dump: `_open_follower_tab` (profile wait → list check), loop
collect, `follow_one_follower` parse button, verify sau tap, scroll. Thêm một
bước dump = thêm một phần tử queue; đếm lại mọi test khi đổi flow. Test fail
kiểu "followed == [] nhưng expect f1" thường là thiếu 1 bản list giữa chừng
(queue hết → replay last → row đã Đã follow → skipped). Ghi chú thứ tự
consume ngay trong test:

```python
# 1 profile (open tab wait) -> 2 listA (open check) -> 3 listA (loop collect)
# -> 4 listA (follow parse button) -> 5 listB (verify sau tap)
fake.push_xml(_profile_xml())
fake.push_xml(list_a); fake.push_xml(list_a); fake.push_xml(list_a)
fake.push_xml(list_b)
```

**Wait loop dump consumption**: các hàm `wait_for_node` / `_wait_search_input`
có timeout/interval riêng (mặc định timeout=8, interval=1.5 hoặc timeout=6,
interval=1.0) → mỗi lần chờ tiêu thụ ~5-6 dump. Test queue phải push **generous
counts (30 mỗi phase)** chứ không phải 5-10. Khi hết queue, FakeAdapter replay
last item → row đã Đã follow → skipped/tham số sai.

```python
def _push_phase(fake, xml: str, count: int = 30) -> None:
    """Push generous copies of a phase XML (30 = safe cho wait loop)."""
    for _ in range(count):
        fake.push_xml(xml)

# Search nav phases in exact consumption order:
_push_phase(fake, _search_icon_xml(), 30)      # wait_for_node icon
_push_phase(fake, _search_input_xml(), 30)     # _wait_search_input
_push_phase(fake, _result_xml(uid), 30)        # wait_for_node result
```

## Fail-closed gate test khi feature ĐÃ implement

Khi module mode 2 từ "chưa tồn tại" sang "đã tồn tại", test cũ
`test_mode2_missing_fails_closed` (assert `_mode2_module_available() is False`)
sẽ fail. KHÔNG xóa gate — monkeypatch ngược: `monkeypatch.setattr(fe,
"_mode2_module_available", lambda: False)` rồi assert `STATE_CONFIG_ERROR` +
`details["mode2"] == "NOT_IMPLEMENTED"`. Gate fail-closed phải sống mãi.

```python
def test_mode2_missing_fails_closed(monkeypatch, tmp_path):
    """Fail-closed gate còn nguyên: module mode 2 không available (simulate
    bằng monkeypatch) -> CONFIG_ERROR, không ImportError, không đụng device."""
    from follow_runner.flows import follow_engine as fe
    monkeypatch.setattr(fe, "_mode2_module_available", lambda: False)
    # ... setup engine ...
    res = eng.run_session(1, "2")
    assert res.status == STATE_CONFIG_ERROR
    assert "mode 2" in res.reason
    assert res.details["mode2"] == "NOT_IMPLEMENTED"
```

## AG audit findings (mode 2) — 3 vòng tới APPROVED

1. **Bare `except Exception` nuốt root cause**: bắt exception ghi vào
   `reason_holder` (list) để `run_mode2` đưa vào MANUAL_REVIEW reason. Dùng
   `reason_holder[-1]` (reason LẦN CUỐI, không phải `[0]` — retry lần 2 có thể
   lỗi khác).
2. **Loop exit đừng dựa vào `res.status` mặc định (fragile)**: dùng cờ cục bộ
   `failed = False`, set True tại mọi break lỗi, đưa `not failed` vào điều
   kiện while.
3. **`back()` vs `press_back()` nhất quán** (finding về rename chưa verify
   production adapter — verify bằng `git show <commit>:<file> | grep "def back"`
   trước khi sửa).
4. **Trailing newline**: patch selectors.py để kết thúc bằng `\n` — `git diff
   --check` báo `\ No newline at end of file`.
5. **Test fail-closed gate phải giữ** (mục trên).

## Audit route ghi nhận lại

- `9c3465f` mode2 → AG MINOR_FIXES (5 findings) → fix → `08fbdf9` → AG
  MINOR_FIXES (2 findings: reason_holder[0], back() chưa verify) → fix →
  `e9eaef0` → **APPROVED**. MINOR_FIXES phải re-audit cùng model tới APPROVED
  (khớp `references/taadaa-audit-route-invocation.md`).
- AG audit qua script: `bash /d/Taadaa/reports/ag-audit/run-ag-audit.sh
  <repo> <commit> ag/claude-opus-4-6-thinking 600` — chạy background,
  `AG_AUDIT_VERDICT=` trong output, response file trong
  `D:/Taadaa/reports/ag-audit/audit-<commit>-<ts>-response.txt`.