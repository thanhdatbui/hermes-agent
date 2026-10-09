# Night Chained Reg Gmail ➔ Reg TikTok Pipeline

Tài liệu kỹ thuật và quy trình vận hành chuỗi tự động ban đêm (00:00) kết hợp giữa 2 repo `register gmail` và `Tiktok_Reg`.

## 1. Cấu Trúc Khởi Chạy & Lịch Hermes Cron
- **Cron Job ID:** `38ea60c09825` (`night-chain-reg-pipeline`)
- **Lịch chạy:** `0 1 * * *` (01:00 đêm hàng ngày)
- **Kênh nhận báo cáo (Deliver):** `telegram:-5139245637` (Nhóm **Gmai reg**)
- **Launcher:** `C:\Users\Kibe\AppData\Local\hermes\scripts\night_chain_reg_pipeline_launcher.py`
- **Pipeline Thực Thi:** `D:\Taadaa\Tiktok_Reg\scripts\run_night_chain_pipeline.py`

## 2. Luồng Thực Thi Chi Tiết (Chuỗi Tuần Tự Mới: Ca 4 Feed Row 7/8 -> Reg Gmail -> Add 2FA)
*(Cập nhật 2026-09-11: Loại bỏ hoàn toàn Reg TikTok ban đêm khỏi chuỗi đêm, chuyển sang mô hình tuần tự 100%).*

1. **00:00 - Khởi động Phase 1 (Ca 4 Đêm - Nuôi Feed Row 7/8 theo ngày chẵn/lẻ):**
   - Bắt đầu cố định lúc 00:00.
   - Tính ngày theo giờ HCM (`Asia/Ho_Chi_Minh`): Ngày chẵn -> chạy **Row 8**; Ngày lẻ -> chạy **Row 7** (`8 if day % 2 == 0 else 7`).
   - Gọi canonical launcher: `D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1 -Row <row> -Preset full -LocalRun -RecoveryTestSwipes 2 -MaxWorkers 40 -Run`.
   - Timeout 3600s kèm cơ chế kill tasktree PID an toàn nếu quá giờ; báo alert về `.ai-runs` nếu thất bại.
   - Đợi hàm return hoàn toàn -> ghi nhận thời gian kết thúc Phase 1, nghỉ 10s trước khi sang Phase 2.

2. **Phase 2 (Reg Gmail - Chạy tuần tự NGAY SAU KHI Phase 1 kết thúc):**
   - Bắt buộc đợi Phase 1 return mới khởi chạy, KHÔNG chạy đồng thời.
   - Gọi canonical launcher `D:\Taadaa\register gmail\run_all.ps1 -fullScopeTakeover`.
   - Kế thừa toàn bộ cấu hình: Cooldown 5 ngày, max 15 máy/batch, kiểm tra VPN preflight trên từng máy.
   - Mail tạo thành công được ghi trực tiếp vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
   - Đợi batch Gmail kết thúc (hoặc timeout 90 phút), nghỉ 10s để file Excel flush hoàn toàn.

3. **Phase 3 (Add 2FA TikTok - Chạy tuần tự NGAY SAU KHI Phase 2 kết thúc):**
   - Bắt buộc đợi Phase 2 return mới khởi chạy.
   - Chạy batch bật 2FA bằng `python_runner/run_batch_live_2fa.py --live --max-workers 40`.

4. **Báo cáo tổng kết Telegram:**
   - Khi chuỗi kết thúc, pipeline tổng hợp exit code và trích xuất summary từ output của cả 3 công đoạn tuần tự.
   - Format chuẩn:
     ```
     [BÁO CÁO CHUỖI ĐÊM] Ca 4 Feed Row <X> -> Reg Gmail -> Add 2FA
     - Tổng thời gian: HH:MM -> HH:MM (XX phút)

     - Phase 1 (Ca 4 Nuôi Feed Row <X> [<Ngày chẵn/lẻ>] - Code <C1>):
       + Thời gian: HH:MM -> HH:MM (XX phút)
       + Tổng máy: ...
       + Success (...): ...
       + Fail (...): ...

     - Phase 2 (Reg Gmail - Code <C2>):
       + Thời gian: HH:MM -> HH:MM (XX phút)
       + Tổng máy: ...
       + ...

     - Phase 3 (Add 2FA TikTok - Code <C3>):
       + Thời gian: HH:MM -> HH:MM (XX phút)
       + Tổng máy: ...
       + ...
     ```
   - In ra stdout chuẩn để Hermes Cron đẩy đúng 1 tin nhắn tóm tắt về nhóm Telegram **Gmai reg** (`-5139245637`). Gọt sạch emoji chống vỡ font Telegram.

## 3. Các Pitfalls Đã Giải Quyết (2026-08-19)
1. **Hermes `no_agent: true` output capture:**
   - Trong launcher Python, bắt buộc dùng `subprocess.run(..., capture_output=True)` và `sys.stdout.write(completed.stdout)` để flush output về stdout của tiến trình cha. Nếu không, Hermes sẽ đánh giá là silent/empty và không gửi tin nhắn về Telegram.
2. **PowerShell inline Python quoting:**
   - Trong `run_all.ps1` và `run_parallel.ps1`, tránh dùng multi-line here-string `@' ... '@` cho `python -c` khi có dấu ngoặc kép hoặc `RuntimeError("...")` vì PowerShell phân tích sai cú pháp dấu ngoặc. Chuyển sang chuỗi 1 dòng inline với `sys.exit('...')`.
3. **Lệch cột Serial trên `taikhoan_dat_v2_updated .xlsx`:**
   - Cột 10 (device ID) bị ghi nhầm ngày tạo `2026-08-18 18:27:39` và đẩy serial sang cột 11 (hoặc dòng bị `None`) sẽ khiến `_detect_clean.py` chặn toàn bộ tiến trình với `TARGET_INVENTORY_CONFLICT` hoặc `TARGET_INVENTORY_MISSING_SERIAL`. Luôn kiểm tra và sync lại `taikhoan_run_safe.xlsx` qua `taikhoan_sync_cron_launcher.py`.
4. **Assignment Manifest Roster:**
   - File `C:\Users\Kibe\AppData\Local\automation-core\assignments\register-gmail.json` bắt buộc phải chứa đầy đủ 80 máy (`machine:1` đến `machine:80`). Thiếu máy sẽ bị `assert_assigned` chặn với lỗi `TARGET_OUTSIDE_ASSIGNMENT`.
5. **UnicodeDecodeError khi capture output tiến trình con trên Windows (2026-08-23):**
   - Lỗi: `Exception in thread Thread-1 (_readerthread): UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa0 in position ...: invalid start byte`.
   - Nguyên nhân: `subprocess.run(..., capture_output=True, text=True)` trên Windows mặc định decode UTF-8 thuần. Khi PowerShell/ADB in byte ANSI/CP1258/CP1252/Shift-JIS hoặc non-breaking space (`0xa0`), thread đọc pipe của Python bị crash.
   - Fix: Bắt buộc truyền `encoding="utf-8", errors="replace"` trong `subprocess.run()` (hoặc capture raw bytes và decode với `errors="replace"`) cho mọi script runner bọc PowerShell/ADB.
6. **Quy tắc màn hình khi lỗi:**
   - Chỉ khi SUCCESS mới tự động dọn dẹp về Home. Khi FAIL/Kẹt lỗi, giữ nguyên hiện trường trên thiết bị để người vận hành kiểm tra vào ban ngày.
   - **Tuyệt đối KHÔNG tự động lock máy** khi gặp sự cố, chỉ lock khi có lệnh trực tiếp từ user.
7. **Lỗi `[BLOCKED][PRE_GMAIL][APP_STARTUP]` trên Samsung S7 (2026-08-26 / 2026-08-27):**
   - **Nguyên nhân 1 (Regex focus):** `get_current_focus_package` đọc `dumpsys window windows` thiếu regex khớp với format `mCurrentFocus=Window{...}` và `mFocusedApp=AppWindowToken{...}` của Android 7/8.
   - **Nguyên nhân 2 (Token whitelist):** `prepare_app_for_automation` khi retry 10 lần không thấy focus sẽ trả về stop_reason `"failed to focus target app after launch"`. Nếu whitelist chỉ lọc `verify_app_focus` sẽ bị sót token này, khiến runner không kích hoạt fallback sang `launch_gmail_home` (xác thực qua UI XML thực tế) mà ném `RuntimeError`.
   - **Fix:** Mở rộng regex focus cho Samsung S7 + bổ sung `"failed to focus target app after launch"` vào whitelist fallback.
8. **Date/Time String tràn vào cột Device Serial trong Workbook:**
   - **Hiện tượng:** Trong `taikhoan_run_safe.xlsx` hoặc `taikhoan_dat_v2_updated .xlsx`, người dùng vô tình dán ngày giờ (`23/08/2026`, `2026-08-24 18:27:39`) vào cột `Device ID` $\rightarrow$ loader map tuần tự lấy nhầm giá trị cuối làm serial $\rightarrow$ ADB báo `device '23/08/2026' not found`.
   - **Fix:** Hàm `_normalize_device_serial_cell()` bắt buộc lọc bỏ toàn bộ các ô `date`/`datetime`, dải unformatted Excel serials (35000..60000), định dạng `strptime` ngày tháng (`/`, `-`, `.`, có `T`), đồng thời truyền `cell.number_format` để loại bỏ an toàn mà không làm mất serial số (ví dụ `1234567890123456`) hay serial TCP/IP (`192.168.1.10:5555`).
9. **Timeout Cron dọn cache TikTok cuối ngày (`cron_clear_tiktok_cache.py`):**
   - **Hiện tượng:** Hàng loạt máy báo `[TIMEOUT] Machine XX [...] cache clear timed out after 45s`.
   - **Nguyên nhân:** Khi Deep Link intent không mở được và phải dò 5 vị trí widget trên màn hình chính (mỗi vị trí tap + dump UI XML) kèm xác nhận xóa và verify kích thước cache, tổng thời gian trên S7 vượt 45s.
   - **Fix:** Nâng timeout của từng worker từ 45s lên 120s.
10. **Hermes Cron Runner Timeout 3600s đối với Chained Night Batch (`night-chain-reg-pipeline`):**
   - **Hiện tượng:** Telegram nhận cảnh báo `Cron 'night-chain-reg-pipeline' failed: provider timeout. Fallback chain was exhausted or unavailable` sau đúng 60 phút (02:00).
   - **Nguyên nhân:** Hermes scheduler có hard timeout mặc định 3600s cho script trong chế độ `no_agent: true`. Khi chuỗi ban đêm chạy Phase 1 (Reg Gmail ~12-15m) + Phase 2 (Reg TikTok nhiều batch, ~22 targets, >50m) $\rightarrow$ tổng thời gian thực thi chạm ngưỡng 64 phút > 3600s $\rightarrow$ Hermes Scheduler tự động ngắt và báo lỗi timeout.
   - **Cách Fix vĩnh viễn cấu hình Hermes:**
     Chạy lệnh cấu hình tăng timeout cho script cron của Hermes lên 3 tiếng (10800s):
     ```bash
     hermes config set cron.script_timeout_seconds 10800
     ```
   - **Bản chất thực tế & Xử lý khi bị ngắt:** Các tiến trình con (`_run_all_targets.py`) trên máy vẫn tiếp tục chạy ngầm hoàn tất; tuy nhiên hàm `apply_tiktok_deferred_results()` ở cuối launcher có thể bị ngắt giữa chừng. Khi gặp cảnh báo này, bắt buộc:
     1. Kiểm tra thư mục artifacts `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<run_dir>\` để đối soát danh sách `tracking_result_stt*.json`.
     2. Chạy bù script `apply_deferred_tracking_results.py` với danh sách tracking results để ghi nhận các nick thành công vào `taikhoan_dat_v2_updated .xlsx`.
     3. Kích hoạt sync sang `taikhoan_run_safe.xlsx` qua `sync-safe-workbook.py`.
11. **Quy chuẩn định dạng báo cáo Farm Batch / Cron:**
   - **CẤM:** Spam từng dòng `[OK] Machine XX: ...` hoặc `[WARN] Machine YY: ...` làm tràn màn hình chat.
   - **BẮT BUỘC:** Báo cáo ngắn gọn theo chuẩn Cron TikTok nuôi acc:
     • **Tổng máy:** <Số lượng>
     • **Success (<Số lượng>):** <Danh sách STT máy thành công>
     • **Fail (<Số lượng>):** <Danh sách STT máy thất bại kèm lỗi nếu có>
12. **Excel STT Type Mismatch (String vs Integer) trong `deferred_tracking_writer` & `find_deferred_tracking_slot`:**
   - **Hiện tượng:** Trong `taikhoan_dat_v2_updated .xlsx`, một số dòng có cột `Máy` lưu dạng chuỗi (ví dụ: `'78'`) thay vì số nguyên `78`.
   - **Hậu quả:** `find_deferred_tracking_slot()` so sánh `row_stt == stt` bị `False` $\rightarrow$ trả về `("", "")` $\rightarrow$ `tracking_result_stt78*.json` bị trống `tracking_row`/`tik` $\rightarrow$ `apply_deferred_tracking_results.py` báo `BLOCKED_DATA_CONFLICT: RESULT_MISSING_ROW_OR_TIK` hoặc `EXPECTED_STT_78_GOT_78`.
   - **Fix:** Chuẩn hóa `_int_or_none(ws.cell(row_idx, 1).value)` và `int(row_stt)` trước khi so sánh equality với `stt` ở cả `social_reg_v1.py` và `scripts/deferred_tracking_writer.py`.
13. **Lỗi terminating exception `PathNotFound` trong `Get-RunResultFromLog` (`run_parallel.ps1`, 2026-09-06):**
   - **Hiện tượng:** Khi một worker kết thúc nhưng file log bị thiếu, rỗng hoặc đường dẫn `$LogPath` không hợp lệ, lệnh `Get-Content -LiteralPath $LogPath` trong `run_parallel.ps1` có thể ném terminating exception làm sập logic phân loại kết quả hoặc crash cả batch.
   - **Fix:** Kiểm tra `![string]::IsNullOrWhiteSpace($LogPath)` và bọc `Test-Path -LiteralPath $LogPath -PathType Leaf` cùng `Get-Content -ErrorAction Stop` trong `try/catch` với flag `$hasLog`. Nếu `$hasLog` là `$false`, fallback an toàn sang `reason = "Missing log, exit code $ExitCode"` (hoặc exit code 0) thay vì ném exception.
14. **Hardcoded đường dẫn log ảo khi cảnh báo lỗi Phase 1 (`run_night_chain_pipeline.py`, 2026-09-06):**
   - **Hiện tượng:** Khi Phase 1 (Reg Gmail) thất bại, `_send_night_chain_alert` truyền hardcoded `str(GMAIL_REPO_DIR / "logs" / "reg.log")` — một file không tồn tại do runner song song ghi log vào runtime directory (`D:\CodexRuntime\codex_gmail_debug-register-gmail\logs_parallel_*`). Khi gửi cảnh báo Farm Alert, log đính kèm bị rỗng hoặc lỗi path.
   - **Fix:** Thêm hàm `find_latest_gmail_log_path(gmail_out)` tự động trích xuất `RUN_DIR` / `Log dir` từ output của batch, hoặc quét thư mục `logs_parallel_*` mới nhất dưới `GMAIL_RUNTIME_ROOT` (ưu tiên `summary.txt`), fallback an toàn về repo `logs/` hoặc repo dir để đảm bảo file log gửi đi luôn tồn tại thật trên đĩa.
15. **Tuần tự Phase 2a (Reg TikTok) & Phase 2b (Nuôi feed Row 7/8) và tách riêng báo cáo (2026-09-07):**
   - **Nhu cầu vận hành:** Trong đêm, farm vừa cần đăng ký TikTok mới cho các máy thiếu nick (chưa đủ 8 acc), vừa cần nuôi lướt feed cho các nick đã có ở Row 7 hoặc Row 8.
   - **Giải pháp:** Phase 2 chạy tuần tự cả 2 việc: Phase 2a chạy `_run_all_targets.py`, sau đó Phase 2b chạy `run-feed-session.ps1` với Row 8 (ngày chẵn) hoặc Row 7 (ngày lẻ) theo giờ HCM.
   - **Báo cáo Telegram chuẩn:**
     - Header: `[BÁO CÁO CHUỖI ĐÊM] Gmail -> TikTok (Reg & Feed Row 7/8) -> Add 2FA`
     - Bóc tách đầy đủ cả 2 mục riêng biệt:
       • `- Phase 2a (Reg TikTok - Code X):` (Tổng máy, Success, Fail)
       • `- Phase 2b (Nuôi Feed Row 7/8 [Ngày chẵn/lẻ] - Code Y):` (Tổng máy, Success, Chưa có acc, Fail)
     - Giữ nguyên sanitization loại bỏ emoji chống vỡ font Telegram.
16. **PowerShell 5.1 `NativeCommandError` False Alarm & Batch Summary Parsing trong Night Chain Pipeline (2026-09-08/2026-09-09):**
   - **Hiện tượng:**
     Khi launcher PowerShell (`run_all.ps1`) gọi script con bằng `powershell @parallelArgs` hoặc lệnh bên ngoài, nếu tiến trình con in stderr hoặc kết thúc với exit code != 0, PowerShell 5.1 tự động bọc stderr thành `+ FullyQualifiedErrorId : NativeCommandError`, `CategoryInfo: NotSpecified: ... RemoteException`.
     Ở phía Python orchestrator (`run_night_chain_pipeline.py`), hàm `parse_summary_line()` dùng substring matching `any(marker.casefold() in line.casefold() for marker in ("FAILED", "ERROR", ...))`. Chuỗi `"error"` trong `"NativeCommandError"` bị bắt dính, làm pipeline trích xuất dòng rác PowerShell này thay vì dòng summary thật.
     Đồng thời trong `main()`, `if gmail_code != 0:` vội vã phát `_send_night_chain_alert()` ngay cả khi batch đã hoàn thành bình thường và chỉ có vài máy fail/cooldown (exit code 1 do `$fail > 0`), dù file `summary.json`/`summary.txt` đã được tạo và ghi nhận đầy đủ.
   - **Giải pháp & Khắc phục chuẩn:**
     1. **Trong `parse_summary_line()`:**
        - Bổ sung `"KET QUA:"` vào danh sách `summary_markers`.
        - Lọc bỏ triệt để các dòng rác PowerShell trong output: bỏ qua dòng chứa `'NativeCommandError'`, `'CategoryInfo'`, `'FullyQualifiedErrorId'`, `'RemoteException'`, `'+ CategoryInfo'`, `'+ FullyQualifiedErrorId'`, `'+ ~~~'`, `'At line:'`.
        - Nếu output không còn dòng summary marker trực tiếp (do bị stderr lấn át), chủ động đọc tóm tắt từ file `summary.txt` hoặc `summary.json` tìm được qua `find_latest_gmail_log_path()`.
     2. **Trong `find_latest_gmail_log_path()`:**
        - Mở rộng regex nhận diện cả `Summary TXT:\s*([^\r\n]+)`, `Logs:\s*([^\r\n]+)`, và `Summary JSON:\s*([^\r\n]+)`.
     3. **Trong `main()` Phase 1 Alert Guard:**
        - Khi `gmail_code != 0`, kiểm tra `gmail_details = parse_gmail_details(gmail_out)`. Nếu `gmail_details.get("total", 0) > 0` (đã có kết quả tổng hợp của batch), không coi đây là pipeline crash và không phát `_send_night_chain_alert()`, để dành tổng kết chi tiết cho báo cáo cuối chuỗi. Chỉ alert khi batch thực sự bị sập, crash hoặc không thu được bất kỳ dữ liệu nào.
     4. **Trong PowerShell launcher:**
        - Trong `run_all.ps1`, tránh spawn child `powershell @parallelArgs` làm phát sinh lỗi `NativeCommandError` không đáng có; gọi script trực tiếp trong session qua `& (Join-Path $PSScriptRoot 'run_parallel.ps1') @params`.
        - Trong `run_parallel.ps1`, tại block kết thúc in rõ cả `RUN_DIR` và dòng chuẩn `TOTAL=... SUCCESS=... FAILED=...` đồng bộ với format của `summary.txt`.
     5. **Bộ Test Chống Tái Diễn (Regression Test Suite):**
        - File test: `D:\Taadaa\Tiktok_Reg\tests\test_night_chain_summary.py`
        - Kiểm chứng nhanh qua lệnh:
          ```bash
          "D:/Taadaa/python-envs/automation/Scripts/python.exe" -m pytest D:/Taadaa/Tiktok_Reg/tests/test_night_chain_summary.py -v
          ```
        - Bao phủ các case: bỏ qua `NativeCommandError` khi parse summary line, bắt đúng `KET QUA:`, lọc nhiễu PowerShell khi failure thật, và trích xuất đường dẫn file `summary.txt` từ `Logs: <dir>`.
17. **Chuỗi Tuần Tự Mới & Pitfall Cập Nhật Test Suite `test_night_chain_pipeline.py` (2026-09-11):**
    - **Kiến trúc mới:** Ban đêm không còn chạy batch Reg TikTok độc lập (đã chuyển sang cơ chế on-demand trong feed runner). Chuỗi đêm chạy tuần tự 100%: Phase 1 (Ca 4 Đêm Nuôi Feed Row 7/8 lúc 00:00) ➔ Phase 2 (Reg Gmail) ➔ Phase 3 (Add 2FA TikTok). Phase sau chỉ được chạy sau khi phase trước hoàn tất return.
    - **Chạy Pytest cho `test_night_chain_pipeline.py`:** BẮT BUỘC thiết lập `PYTHONPATH="D:/Taadaa/Tiktok_Reg"`:
      ```bash
      PYTHONPATH="D:/Taadaa/Tiktok_Reg" "D:\Taadaa\python-envs\automation\Scripts\python.exe" -m pytest "D:/Taadaa/Tiktok_Reg/tests/test_night_chain_pipeline.py"
      ```
      Nếu thiếu `PYTHONPATH`, pytest sẽ báo `ImportError: cannot import name 'run_night_chain_pipeline' from 'scripts'`.
    - **Bẫy test case cũ:** Khi xóa bỏ `run_tiktok_reg_batch` và đổi header báo cáo Telegram sang `[BÁO CÁO CHUỖI ĐÊM] Ca 4 Feed Row X -> Reg Gmail -> Add 2FA`, các test trong `tests/test_night_chain_pipeline.py` (`test_main_returns_zero_and_prints_clean_report`, `test_main_handles_fallback_with_parsed_counts_and_emoji_cleaning`, `test_runners_stderr_progress_isolation`, ...) phải được cập nhật đồng bộ để tránh fail do assert header cũ và mock method đã xóa.
    - **Tránh recursive grep toàn farm:** Tránh chạy `grep -rn ... /d/Taadaa/*/` vì farm có các file log 200MB+ (`social_reg_log.txt`) và thư mục `runtime`/`artifacts` khổng lồ gây timeout shell 180s. Luôn dùng `git grep` trong từng repo hoặc chỉ định chính xác thư mục scripts.
