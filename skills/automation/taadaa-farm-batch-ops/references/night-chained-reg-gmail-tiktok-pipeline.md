# Night Chained Reg Gmail ➔ Reg TikTok Pipeline

Tài liệu kỹ thuật và quy trình vận hành chuỗi tự động ban đêm (00:00) kết hợp giữa 2 repo `register gmail` và `Tiktok_Reg`.

## 1. Cấu Trúc Khởi Chạy & Lịch Hermes Cron
- **Cron Job ID:** `38ea60c09825` (`night-chain-reg-pipeline`)
- **Lịch chạy:** `0 1 * * *` (01:00 đêm hàng ngày)
- **Kênh nhận báo cáo (Deliver):** `telegram:-5139245637` (Nhóm **Gmai reg**)
- **Launcher:** `C:\Users\Kibe\AppData\Local\hermes\scripts\night_chain_reg_pipeline_launcher.py`
- **Pipeline Thực Thi:** `D:\Taadaa\Tiktok_Reg\scripts\run_night_chain_pipeline.py`

## 2. Luồng Thực Thi Chi Tiết
1. **00:00 - Khởi động Phase 1 (Reg Gmail):**
   - Gọi canonical launcher `D:\Taadaa\register gmail\run_all.ps1 -fullScopeTakeover`.
   - Kế thừa toàn bộ cấu hình: Cooldown 5 ngày, max 15 máy/batch, kiểm tra VPN preflight trên từng máy.
   - Mail tạo thành công được ghi trực tiếp vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
2. **Phase 2 (Bridge & Reg TikTok):**
   - Sau khi batch Gmail kết thúc (hoặc timeout 90 phút), nghỉ 10s để file Excel flush hoàn toàn.
   - Gọi canonical launcher `D:\Taadaa\Tiktok_Reg\_run_all_targets.py --full-scope-takeover`.
   - `_detect_clean.py` tự động so khớp `gmail_clean_v2.xlsx` với `taikhoan_dat_v2_updated .xlsx` để lọc ra danh sách máy còn thiếu nick (< 6 acc) và gán mail mới.
   - Chạy đăng ký TikTok, bắt OTP qua Graph API/Gmail và ghi nhận vào workbook.
3. **Báo cáo tổng kết:**
   - Khi chuỗi kết thúc, pipeline tổng hợp exit code và trích xuất summary từ stdout của cả 2 batch.
   - In ra stdout chuẩn để Hermes Cron đẩy đúng 1 tin nhắn tóm tắt về nhóm Telegram **Gmai reg**.

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
