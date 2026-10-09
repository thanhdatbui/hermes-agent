# ADB Validation Backoff + No Blocked-Lock Retention (2026-09-13)

## 1. ADB `_validate_child_adb` — retry 5 + backoff lũy tiến
- File: `tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py`
- Root cause phiên 2026-09-13 Row 3: 8 worker gọi `adb.list_devices()` trong ~70ms
  làm nghẽn socket adb daemon → danh sách trả về thiếu tức thời → máy online
  bị phán `config-error: Device serial ... was not found in adb devices`.
- Fix đã commit (`f7b2921`):
  - `ADB_ONLINE_ATTEMPTS = 5` (cũ = 2).
  - `except ADBError`: `time.sleep(1.0 * _attempt)` trước `continue`.
  - Serial chưa thấy: `time.sleep(1.0 + 0.5 * _attempt)` (1.5s → 3.0s).
- Pitfall khi delegate: worker đời đầu chỉ chèn `time.sleep(1.0)` mà QUÊN đổi
  `ADB_ONLINE_ATTEMPTS`. Coordinator phải assert cả 2 anchor trong `git diff`
  trước khi commit, không tin self-report của worker.
- Trước khi patch ADB, lục session cũ (`session_search`: adb retry /
  ADB_ONLINE_ATTEMPTS) để tránh fix trùng — phiên 15:13 đã chèn sleep 1.0s,
  phiên này kế thừa nâng lên 5 + backoff.

## 2. Bỏ giữ lock `blocked` khi feed lỗi — luôn release (user chốt 2026-09-13)
- Lý do: teardown luôn chạy `_force_stop_tiktok_and_home()` trước khi xử lý
  lock → màn hình vật lý đã về HOME, giữ lock trên đĩa 60p là giam máy vô nghĩa.
- Hiện trường lỗi (ui.xml / screen.png / log.jsonl / summary.txt) đã lưu vĩnh
  viễn trong artifact `D:/Taadaa/runtime/kibe/live/...` → debug đọc log là đủ,
  không cần giữ scene.
- Fix đã commit (`21e8c0f`): 2 vị trí (`_write_mapping_source_child_artifacts`
  và `_run_child`/`_write_blocked`) đổi `succeeded=False, lock_status="blocked"`
  + `lease.set_status("blocked")` thành `succeeded=True, lock_status="released"`
  + `lease.finish(succeeded=True)`.
- Hệ quả: phiên kế tiếp không còn `skipped-device-locked` do lock mồ côi;
  cron `reap-dead-owner-locks` (TTL 3600s cho `blocked`) không còn là đường
  sống duy nhất.
