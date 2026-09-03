# account_switcher `coordinate_fallback` hook — contract + test recipes (2026-08-07)

Task B core automation-core (branch `feat/hermes-cli-fallback`, retry sau 429).
Thay đổi: `src/automation_core/tiktok/account_switcher.py` (docstring contract,
logic hook đã có sẵn) + `tests/test_account_switcher_preconfirmed.py` (2 test).
KHÔNG thêm helper `_coordinate_fallback` — chỉ 1 call site, không lặp thật.

## Hook contract (đã đưa vào docstring open_switcher/open_account_switcher)

- Signature: `coordinate_fallback(action: str) -> tuple[int, int] | None`.
- Core gọi `action="switcher"` CHỈ khi cả semantic anchor lẫn
  `switcher_image_point` đều unavailable (call site trong `open_switcher`):
  ```python
  image_point = getattr(adapter, "switcher_image_point", None)
  point = image_point() if callable(image_point) else None
  if point is None:
      evidence = getattr(adapter, "coordinate_fallback", None)
      point = evidence("switcher") if callable(evidence) else None
  if point is None:
      raise AccountSwitcherError("SWITCHER_ANCHOR_AMBIGUOUS", "semantic/image/coordinate anchor unavailable")
  adapter.tap(*point)
  ```
- Backward-compat: adapter không có hook (hoặc trả None) = hành vi cũ y hệt
  (`SWITCHER_ANCHOR_AMBIGUOUS`), không crash/TypeError. `getattr` + `callable`
  check — KHÔNG `hasattr` riêng.
- Docstring wording dùng được cho mọi hook adapter tương lai: "Adapter hook
  ``<name>(<sig>)``: consumer-supplied ... The core calls it with ``action=...``
  only after ... ; the consumer returns ``None`` for any action it does not
  know. Backward compatible: an adapter without the hook behaves as if it
  returned ``None``, i.e. the previous <CODE> failure path."
- Test assert code qua `exc.code` (AccountSwitcherError có `.code`, str =
  `"CODE: message"` → `pytest.raises(match="CODE")` cũng chạy).

## Test fixtures — XML phải đúng "shape" của is_switcher_open

**No-anchor XML (anchor=None đáng tin cậy):** hierarchy CHỈ root node không
text — mọi nhánh của `find_switcher_anchor` (switcher markers, resource-id,
preferred/identity, @username, generic) đều trượt:
```python
NO_ANCHOR_PROFILE_XML = '<hierarchy><node bounds="[0,0][1080,1920]" /></hierarchy>'
```

**SWITCHER_XML phải là 3-node THẬT** (title + account + "Thêm tài khoản").
`is_switcher_open` trả True chỉ khi có title marker CÙNG add-account/login/
selected-account. XML 1 node chỉ có "Chuyển đổi tài khoản" → is_switcher_open
=False → `open_switcher` load loop dump THÊM lần nữa → `IndexError: pop from
empty list` → UI_DUMP_FAILED. Triệu chứng trông như bug core nhưng là fixture
sai. Dump sequence cho test hook: `[NO_ANCHOR, SWITCHER]` — refresh dump (#1)
rồi post-tap load-loop dump (#2) trả SWITCHER → return ngay.

## Adapter-hook test pattern

- `del adapter.coordinate_fallback` FAIL trên class method (AttributeError:
  'instance has no attribute') — class method không phải instance attribute.
- Đúng: gắn hook có điều kiện trong `__init__`:
  ```python
  if with_fallback:
      self.coordinate_fallback = self._coordinate_fallback  # instance attr
  ```
- Adapter cần `tap(x, y)` (nhánh fallback gọi `adapter.tap(*point)` trực
  tiếp, KHÔNG qua `_tap`/`tap_node`).

## Verify workflow (repo này)

1. `PYTHONPATH=src "<venv>/Scripts/python.exe" -m pytest tests/test_account_switcher_preconfirmed.py -q -p no:cacheprovider`
   (venv: `D:/Taadaa/python-envs/tiktok-reg-recovery/`).
2. Full suite: `PYTHONPATH=src ... -m pytest tests/ -q`.
3. `git diff --check` + byte-count CRLF (bareLF phải = 0).
4. **Chứng minh test fail là pre-existing:** grep file test fail xem có
   reference tới module mình đổi không (`grep -n "account_switcher"
   tests/test_startup.py` → rỗng) + đọc assertion cụ thể. Báo cáo "pre-existing,
   ngoài scope" kèm bằng chứng, KHÔNG stash/chạm file dirty của task khác.
5. Ad-hoc verify (khi hệ thống yêu cầu): script tempfile
   `tempfile.mkstemp(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir())`
   dưới `C:\Users\Kibe\AppData\Local\Temp`, chạy subprocess với venv python +
   `PYTHONPATH=src`, `os.remove` sau khi chạy, báo cáo là ad-hoc chứ không phải
   suite green.
