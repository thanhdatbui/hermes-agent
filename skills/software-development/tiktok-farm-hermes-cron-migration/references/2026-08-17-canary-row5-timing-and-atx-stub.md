# Timing sau dismiss popup + follow hook cross-repo (canary row 5, 17/08 tối)

## _sleep_and_recapture: 0.8s → 2.5s (máy 19)

- Triệu chứng: feed swipe gặp popup contacts permission ("Cho phép TikTok truy cập vào danh bạ?" —
  packageinstaller, XML đủ marker `permission_message`/`permission_allow_button`/
  `permission_deny_button`/`do_not_ask_checkbox`). Flow `dismiss_deny_button` TAP ĐÚNG nút
  TỪ CHỐI (result success) NHƯNG sau deny chỉ chờ 0.8s rồi recapture → popup chưa fade-out
  + TikTok chưa trả foreground → vẫn `com.android.systemui` →
  `swipe_N_after_after_packageinstaller_dismiss observe failed` → "TikTok focus lost"
  (dương tính giả: máy thật đang về feed).
- Fix: `python_runner/flows/benign_popup.py::_sleep_and_recapture` `time.sleep(0.8)` → `2.5`.
  Test `test_benign_popup.py` mock hàm này nên không phụ thuộc giá trị sleep (112 passed).
- Bài học chung: deny/dismiss dialog xong phải chờ ≥2s cho popup animation + host app trả
  foreground TRƯỚC khi verify focus; verify ngay sau dismiss = dương tính giả "focus lost".
- Máy 5 + máy 19 row 5 đều PASS feed+follow sau fix này (mỗi máy follow 2 nick OK).

## Follow hook dùng code TRỰC TIẾP từ repo tiktok-follow (không copy)

- `_run_follow_hook` (multi_machine_feed_session.py) chạy `python -m follow_runner.run_follow`
  với cwd = `D:\Taadaa\tiktok-follow` → bên follow commit gì, bên feed dùng bản đó NGAY.
- Nghi ngờ bản cũ (.pyc): `find . -name "*.pyc" -path "*follow_runner*" -delete` rồi chạy lại
  (Python sẽ recompile từ source mới).
- Khi follow repo đổi behavior: KHÔNG cần redeploy/copy sang feed repo.
- Cẩn thận: file follow_engine.py/test có thể bị sibling subagent ghi đè giữa chừng →
  trước commit đối chiếu `git diff --cached --stat` đủ file, sau commit
  `git show HEAD:file | grep <symbol-mới>` (thiếu = patch chưa lên đĩa).

## ATX stub restart (com.github.uiautomator) — máy có atx-agent nhưng stub chết

- Triệu chứng: `capture_atx_session_ui` → `ATX_SESSION_STUB_NOT_RUNNING` + HTTP 502;
  `ps -A | grep atx-agent` thấy agent nhưng KHÔNG thấy `com.github.uiautomator`.
- `am startservice com.github.uiautomator/.UiAutomatorService` → "Error: Not found; no service
  started" (KHÔNG dùng — service không khai báo startable kiểu đó).
- Đúng: `am force-stop com.github.uiautomator` + `monkey -p com.github.uiautomator 1`
  (open app → stub process chạy) → verify `ps -A | grep uiautomator` có PID + 
  `capture_atx_session_ui` trả XML. Nếu vẫn fail: `pkill -9 -f atx-agent` chạy RIÊNG rồi
  `/data/local/tmp/atx-agent server -d` (mỗi lệnh 1 shell, không chain — race).
- Restart atx-agent KHÔNG tự start stub — stub là app riêng phải launch 1 lần.