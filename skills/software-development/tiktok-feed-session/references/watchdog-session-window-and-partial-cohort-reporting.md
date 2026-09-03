# Watchdog Session Window & Partial Cohort Reporting Contract

## 1. Cơ chế hoạt động của Watchdog (`feed_session_watchdog.py`)
- Chạy dưới Hermes Cron chế độ `no_agent: true` định kỳ (mỗi 5 phút).
- **Silent Semantics**: Khi chưa đủ điều kiện gửi tin, script không in stdout (empty output) để tránh spam tin rác/tin dở dang lên Telegram.

## 2. Khung giờ các phiên nuôi Feed (SESSION_WINDOWS)
- **Ca 1 (Sáng):**
  - Phiên 1/3: 06:00 – 07:30
  - Phiên 2/3: 07:30 – 09:30
  - Phiên 3/3: 09:30 – 12:00
- **Ca 2 (Chiều):**
  - Phiên 1/3: 12:00 – 13:45
  - Phiên 2/3: 13:45 – 15:30
  - Phiên 3/3: 15:30 – 18:30
- **Ca 3 (Tối):**
  - Phiên 1/3: 18:30 – 20:15
  - Phiên 2/3: 20:15 – 22:00
  - Phiên 3/3: 22:00 – 23:59

## 3. Điều kiện kích hoạt gửi báo cáo Telegram (Gate Conditions)
Báo cáo chỉ được bắn lên Telegram khi thỏa mãn đồng thời:
1. **Có thư mục run artifact**: `D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>\row-<ROW>-<HHMMSS>` phải chứa `summary.txt` / `run_manifest.json` của các máy trong phiên.
2. **Điều kiện hoàn tất (`can_report_session`)**:
   - *Với ngày hiện tại (`is_today == True`)*:
     + *Xong sớm*: Số máy hoàn thành đạt đủ số lượng dự kiến (`completed_count >= expected_count`) VÀ runner của phiên đã dừng hẳn (`not runner_busy`).
     + *Hết giờ phiên*: Thời gian hiện tại đã vượt qua mốc kết thúc phiên (`now_hm >= win["end"]`, ví dụ: sau 13:45 đối với Phiên 1 Ca 2). Chốt báo cáo phiên quá khứ độc lập, không bị block bởi runner đang chạy của phiên tiếp theo.
   - *Với ngày đã qua / rollover (`is_today == False`)*: Luôn chốt báo cáo ngay lập tức (`can_report = True`), không để runner đang chạy hôm nay chặn báo cáo tổng kết của hôm qua.
3. **Tránh trùng lặp**: Mỗi phiên (`<YYYY-MM-DD>_caX_phienY`) chỉ được ghi nhận và báo cáo đúng **1 lần** vào `STATE_FILE`.

## 4. Kiểm tra tiến trình Runner an toàn (Process Probe Safety)
- Hàm `is_feed_runner_active()` BẮT BUỘC lọc theo tên binary thực thi (`python.exe`, `powershell.exe`, `pwsh.exe`).
- Tuyệt đối không match chuỗi thô trên toàn bộ tiến trình hệ điều hành (tránh trường hợp `grep.exe`, `ripgrep`, `bash.exe` đang tìm file chứa từ khóa `run_follow` / `multi_machine_feed_session` bị nhận diện nhầm là runner đang chạy, gây tê liệt watchdog cả ngày).

## 5. Xử lý kịch bản Partial Proxy Alive (vd: Mirotik Live, Mobi Down)
- Khi một số máy có proxy sống (vd: Mirotik `10001-10007`) và một số máy bị chết port proxy server (vd: Mobi `5101-5124`):
  - Máy chết proxy sẽ fail-closed trong ~1.5s tại Preflight socket probe, ghi nhận trạng thái `blocked-vichanger-vpn` / `swipes_completed=0`.
  - Máy có proxy sống sẽ tiếp tục chạy hết luồng feed và follow.
  - Toàn bộ artifact vẫn được gom vào run directory chung của đợt chạy.
  - Watchdog gom kết quả, phân loại rõ: **Feed Success** (danh sách máy Mirotik thành công), **Feed Fail** (danh sách máy Mobi lỗi proxy/lock), và chi tiết **Follow chéo** để gửi 1 tin tổng kết duy nhất khi phiên kết thúc.

## 6. Multi-Run Session Result Merging Rules (Sticky Follow-Failed & Cumulative Followed)
Khi một phiên có nhiều run folder liên tiếp (chạy đợt 1 + chạy vét đợt 2/3):
- **Sticky FOLLOW_FAILED**: Nếu máy bị nhả follow (`status == "FOLLOW_FAILED"` VÀ `follow_failed is True` thỏa mãn strict zero-failed) ở bất kỳ run nào trong phiên, sự kiện này BẮT BUỘC giữ nguyên. Lượt chạy sau khi máy được bỏ qua vì `follow-released-daily-cooldown` hoặc `sensitive-skip` TUYỆT ĐỐI KHÔNG được ghi đè làm mất trạng thái nhả follow thành `SKIPPED`.
- **Cumulative Followed**: Danh sách tài khoản đã follow (`followed`) phải là phép hợp (unique set/list) của tất cả các run trong phiên: `combined_flist = list(dict.fromkeys(prev_flist + new_flist))`.
- **Sticky Success**: Trạng thái `success` của Feed và Upload có độ ưu tiên cao nhất, không bị ghi đè bởi `skipped` hay `fail` của lượt quét sau.

## 7. Strict Contract & Unhashable Type Defense trong Watchdog Parsing
1. **Strict Type Checking cho `follow_failed`**:
   - `follow_failed` chỉ được công nhận là `True` khi `type(raw_ff) is bool and raw_ff is True` và `failed == 0` (hoặc `raw_failed is False`).
   - CẤM dùng ép kiểu lỏng lẻo `bool(raw_ff)` vì chuỗi `"false"` hoặc số nguyên `1` sẽ bị ép thành `True`, gây báo sai “Nhả follow”.
   - `FOLLOW_FAILED` không-clean (thiếu trường `failed` hoặc `failed != 0`) KHÔNG được nâng thành clean `follow_failed` mà phân loại vào `fl_error` / `contract_error`.
2. **Lọc phần tử unhashable trong danh sách `followed`**:
   - Trước khi thực hiện deduplicate `dict.fromkeys(prev_flist + new_flist)`, bắt buộc lọc và chuẩn hóa chuỗi `[str(x) for x in flist_raw if isinstance(x, (str, int, float))]` để loại bỏ dict/list rác lồng nhau, triệt tiêu lỗi `TypeError: unhashable type` làm crash watchdog.
3. **Bọc I/O Reading an toàn**:
   - Mọi thao tác đọc file `summary.txt` / `follow_result.json` phải được bọc trong `try/except` để tránh việc file đang ghi dở hoặc lỗi quyền truy cập làm crash toàn bộ tiến trình cron.
