# Case M43 (2026-09-04) — Location-permission dialog miss vì gate EditText toàn cục

Alert: `[MÁY 43]` kẹt popup vị trí ("Chưa có gì thu hút sự chú ý của bạn sao?" /
"Hãy cho phép truy cập vị trí…" / nút "Hủy"–"Mở cài đặt"), log
`popup is not in the shared TikTok allowlist; manual review required` + swipe-recovery 2 swipes vẫn kẹt.

## Root cause
- `detect_location_permission_dialog` (`automation-core/src/automation_core/tiktok/benign_popup.py`)
  bail `None` khi **bất kỳ** node `android.widget.EditText` nào tồn tại trên màn hình.
- Tab vị trí ("Thái Bình") luôn có ô search `EditText` nằm sau modal → detector miss đúng
  trong trường hợp cần nó nhất. Text popup đã có trong allowlist từ trước nên đây là lỗi
  gate, không phải thiếu từ khóa.

## Fix chuẩn (evidence-first, giữ fail-closed cho input nhạy cảm)
- Bỏ gate EditText toàn cục; yêu cầu evidence trước (3-marker: title + settings + deny),
  rồi mới quyết định.
- Chỉ fail-closed khi EditText là password/secret input (`password="true"` hoặc
  content-desc password/mật khẩu). Ô search thường không veto.
- Test đối chứng: `test_location_permission_dialog_matches_with_location_tab_search_edittext`
  (tab Thái Bình + search EditText + modal + Hủy/Mở cài đặt → MATCH, close "Hủy");
  test password EditText cũ vẫn `None`; dialog thường không EditText vẫn MATCH.
- Verify: `tests/test_tiktok_benign_popup.py` + `test_tiktok_popup.py` xanh;
  consumer `test_benign_popup_registry.py` 154 passed.
- Canary M43 (`run-feed-session.ps1 -Machines 43 -Row 1 -RecoveryTestSwipes 2`):
  success 2/2 swipes, `manual-needed popup: 0`. Lưu ý trung thực: popup không xuất hiện
  trong cửa sổ canary nên chưa có evidence live tap "Hủy" — evidence dismiss là unit test
  XML tổng hợp hiện trường.

## Pitfalls kèm (tái sử dụng cho mọi fix automation-core)
1. **venv farm cài COPY, không editable**: sau mỗi sửa core phải
   `cp -f src/automation_core/.../benign_popup.py` sang
   `/d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/...` rồi
   `diff -q` verify IN_SYNC trước khi chạy test/canary. Chạy test với
   `env -u PYTHONPATH PYTHONPATH="D:\Taadaa\automation-core\src"` để không dính
   automation_core cũ từ hermes venv.
2. **`AdbClient(adb_path, serial)` — thứ tự ngược直觉**: signature là
   `(adb_path="adb", serial=None, ...)` nên `AdbClient(serial, adb_path=...)` ném
   `TypeError: got multiple values for argument 'adb_path'`. Luôn truyền positional
   `(ADB_EXE, serial)`.
3. **CWD làm lạc file output**: terminal Hermes CWD là `C:\Users\Kibe`, không phải repo —
   ghi screencap/XML phải dùng absolute path (`C:\Users\Kibe\m43_...`), không tìm bằng
   `find /d/Taadaa` (timeout vì cây farm quá lớn).
4. **Không commit chồng WIP subagent khác**: kiểm tra `git status`/`git diff --stat` ở cả
   `automation-core` và consumer trước khi commit; patch M43 để uncommitted khi đã có
   WIP (profile-photo viewer, Case 92/93) và báo parent quyết định.
