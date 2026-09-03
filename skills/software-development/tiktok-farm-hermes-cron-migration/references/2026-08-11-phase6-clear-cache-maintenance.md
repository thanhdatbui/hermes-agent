# Phase 6 — clear-tiktok-cache maintenance (2026-08-11, commit 33f6c4d)

GREEN: full 6 suite **166 passed** (baseline 162 + 4 test Phase 6). RED evidence: 4 test fail đúng lý do —
thiếu `maintenance` / thiếu `Runner.clear_cache_due` / CLI chưa nhận `--clear-cache` / journal chưa biết event.
py_compile OK, `git diff --check` clean.

## Quyết định kiến trúc (sự thật sau implement, đừng đoán lại)

- **`maintenance` là top-level key BẮT BUỘC** — strict `set(payload) == required` cập nhật CÙNG phase
  (nếu quên: mọi manifest fail `SOURCE_CONFIG_INVALID`). `build_manifest_payload(..., maintenance=None)`
  DEFAULT tự sinh qua `maintenance_for_source(source)` → mọi legacy caller (`test_hermes_cron_p1_r2.py:189`,
  `test_hermes_cron_regressions.py:177`) xanh không cần sửa. Đây là pattern chung: thêm key top-level mới
  bằng DEFAULT param để không phá caller cũ.
- **`maintenance_for_source(source)`**: máy đầu tiên theo `sorted(machines)` (dict machine→serial từ
  feed_accounts) + serial của nó; command cố định:
  `["python", "python_runner/scripts/clear-tiktok-cache.py", "--machine", N, "--serial", S]`.
- **`_validate_maintenance`** (manifest.py:228): shape chính xác `{clear_tiktok_cache: {run_once_per_day,
  due_after_block, command}}`; `run_once_per_day is True` (identity, không truthy); `due_after_block == 3`;
  `len(command) == 6`; `command[0] == "python"`; script path substring; cấm secret/workbook (.xlsx/.csv);
  machine int ≥ 1, serial không whitespace; có source → machine/serial phải khớp source (`MAPPING_CONFLICT`).
- **`Runner.clear_cache_due(as_of)`** (runner.py:409): `is_in_logical_window(current, requested_day)` →
  tìm block_index==3 → `max(slot_end)` của 2 entry trong block → `current >= block_end` → chưa có
  `CLEAR_CACHE_DONE` trong journal. KHÔNG cần `_assert_requested_day` (trả False ngoài window, không raise).
- **CLI `--clear-cache`** (hermes_cron_runner.py): offline-only; đọc command từ `payload["maintenance"]`;
  idempotent — nếu đã có REQUESTED hoặc DONE cho (entry_id, machine, serial) thì KHÔNG append thêm;
  stdout = MỘT JSON object `{"action": "clear_tiktok_cache", "command": [...], "offline": true}` —
  action-level, KHÔNG phải list entry như nhánh dry-run. Không bao giờ gọi subprocess (monkeypatch
  `subprocess.run` ném lỗi trong test để chứng minh).

## Timestamp — resolution cho finding tồn đọng #2 (plan v2)

Plan test assert `"timestamp" in req`; journal append cũ KHÔNG tự thêm timestamp. Resolution KHÔNG phải
"bỏ assert": thêm `timestamp` như common field cho CLEAR_CACHE_* events —
`_append_unlocked` (journal.py:954-955) `value.setdefault("timestamp", value.get("as_of") or datetime.now(TZ).isoformat())`;
`common` allowlist nhận `timestamp`; `_validate_event` `parse_hcm_timestamp(event["timestamp"])`.
Ghi chú cũ trong SKILL.md ("bỏ assert khi làm Phase 6/7") đã hết hiệu lực.

## Checklist 8 chỗ — thêm 1 journal event mới (journal.py)

Event có `entry_id` (không `notification_key`/`failure_signature`) rơi vào stream **"execution"**
(`_stream_kind`: notification_key → DRY_RUN_PREVIEW → failure_signature → else execution; `_stream_events`
nhóm theo entry_id). Phải sửa ĐỦ 8 chỗ, thiếu 1 là ValueError:

1. `models.py` — `JournalEvent` enum member.
2. `TRANSITION_MATRIX["execution"]` — frozenset predecessor (REQUESTED: {None}; DONE: {REQUESTED}).
3. `_validate_event` `allowed` set — key mới (machine, serial, result).
4. `exact_fields` dict — set chính xác per event (REQUESTED: {entry_id, machine, serial, as_of};
   DONE: {entry_id, machine, serial, result}).
5. Value-semantic block — identity vs `_manifest_entry` (machine/serial khớp entry), result non-empty
   không whitespace, terminal flag đúng per event.
6. `required_by` dict — same sets (duplicate của exact_fields, kiểm tra `<=` cho "incomplete journal event").
7. `terminal_by_event` dict — REQUESTED False, DONE True.
8. Auto-populate trong `_append_unlocked` — setdefault timestamp (chỉ event family cần timestamp).

Chú ý: `event_fields == fields` strict của exact_fields — thêm key lạ vào event → "journal event fields are
not canonical"; thêm key vào `allowed` mà không vào exact_fields → pass allowlist nhưng fail canonical.

## Locator (commit 33f6c4d)

- models.py:84-85 — 2 enum member.
- journal.py:61-62 (matrix), 411+414 (common + allowed), 451-452 (exact_fields), 507-508 (timestamp parse),
  509-525 (value-semantic clear-cache), 605-606 (required_by), 623 (terminal_by_event), 954-955 (auto timestamp).
- manifest.py:157 (maintenance_for_source), 211 (return key), 228-252 (_validate_maintenance), 260 (required set), 263 (call).
- picker.py:137 — truyền `maintenance=maintenance_for_source(self.source)`.
- runner.py:409-424 — clear_cache_due; imports thêm is_in_logical_window, parse_hcm_timestamp.
- scripts/hermes_cron_runner.py:26 (--clear-cache), 36-67 (branch offline + idempotent append).
- tests/test_hermes_cron_fleet.py:138-224 — 4 test theo plan dòng 829-927 (đã sửa: `copy.deepcopy` thay
  `from copy import deepcopy`; bỏ dòng `snap = ...` thừa trong test CLI; chạy runner_main 2 lần cùng args list).

## Verify sau commit

Sau khi commit, Hermes yêu cầu fresh evidence: tạo script tạm `tempfile.NamedTemporaryFile(prefix="hermes-verify-",
suffix=".py")` trong `%TEMP%`, chạy 4 check (manifest-maintenance, journal-events, clear-cache-due, cli-offline),
xóa script, báo "AD-HOC VERIFY OK" — không gọi là suite green. Lưu ý: `%TEMP%` có thể chứa `hermes-verify-*.py`
của sibling subagent khác — chỉ xóa file của mình, không dọn chung.
