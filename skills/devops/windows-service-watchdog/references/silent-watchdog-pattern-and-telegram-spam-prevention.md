# Silent Watchdog Pattern & Telegram Spam Prevention

## 1. Bối Cảnh & Triệu Chứng
- User phản ánh: *"Gì thế báo liên tục v"*
- Telegram liên tục nhận thông báo từ bot mỗi 5-10 phút (ví dụ: `[LOGIN GPM ĐÊM] ✓ 0 | ✗ 7 | proxy_limit 2/port/ngày áp dụng`).

## 2. Nguyên Nhân Kỹ Thuật (Hermes Cron Semantics)
Hermes cron runner khi cấu hình:
```yaml
no_agent: true
deliver: telegram:-5373649734  # hoặc deliver: origin
```
Áp dụng semantic phân phối output:
- **Non-empty stdout:** Bất kỳ chuỗi ký tự nào được in ra `stdout` (qua `print()`, `echo`, v.v.) đều được scheduler bắt lại và chuyển phát trực tiếp thành một tin nhắn Telegram mới.
- **Empty stdout:** Nếu `stdout` hoàn toàn rỗng (`""`), scheduler coi đây là **SILENT TICK** — không có gì gửi đi, không spam user.

## 3. Lỗi Thiết Kế Thường Gặp Trong Batch Watchdog
Một tác vụ cuốn chiếu (ví dụ: upload avatar, login GPM, check 2FA) thường:
1. Chạy định kỳ nhiều lần trong khung giờ nhất định (ví dụ: mỗi 10 phút từ 21:30 đến 23:45).
2. Mỗi lần tick chỉ xử lý 1 mẻ nhỏ (batch 5-10 tài khoản) do giới hạn máy rảnh hoặc giới hạn proxy.
3. **Anti-pattern:** Cuối mỗi tick, script gọi `print(...)` để log số lượng thành công / thất bại của mẻ vừa chạy.
4. **Hậu quả:** Scheduler kích hoạt liên tục, gửi tin nhắn rác từng đợt lẻ tẻ thay vì gom lại một lần.

## 4. Quy Tắc Khắc Phục (Best Practice)
1. **Tuyệt đối không in log trung gian ra stdout:**
   - Điều hướng toàn bộ log debug, log quá trình, log lỗi của từng worker sang `sys.stderr` hoặc file log trên đĩa (`D:\Taadaa\runtime\...\*.log`).
2. **Chỉ print stdout 1 lần duy nhất khi kết thúc:**
   - Xác định biến `all_done` (đã duyệt hết toàn bộ danh sách candidates trong ngày) hoặc đã chạm giờ chốt ca (ví dụ `now.hour == 23 and now.minute >= 30`).
   - Kiểm tra cờ trạng thái trong file state JSON (ví dụ `state.get("reported_final")`).
   - Nếu chưa hoàn tất toàn bộ ca: Giữ `stdout` hoàn toàn rỗng (không `print()` gì cả).
   - Khi hoàn tất: `print(...)` báo cáo tổng kết duy nhất một lần và cập nhật `state["reported_final"] = True`.

## 5. Mẫu Code Python Chuẩn

```python
# Ghi nhận log tiến trình vào stderr (không bị Hermes cron bắt thành message)
def log(msg: str):
    sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    sys.stderr.flush()

# Cuối main():
all_done = len(processed) >= total_candidates
already_reported = state.get("reported_final", False)

if all_done and not already_reported:
    total_ok = state.get("total_success", 0)
    total_fail = state.get("total_fail", 0)
    # DÒNG NÀY SẼ LÀ TIN NHẮN DUY NHẤT GỬI VỀ TELEGRAM:
    print(f"[{JOB_NAME} TỔNG KẾT] ✓ {total_ok} | ✗ {total_fail} | Hoàn tất toàn ca.")
    state["reported_final"] = True
    save_state(state)
# Ngược lại: Không print gì ra stdout để giữ yên lặng (Silent watchdog).
```

## 6. Anti-Pattern: In Báo Cáo Rỗng Khi Không Có Việc Hoặc Rớt Phụ Thuộc (Zero-Work Empty Report)
Một biến thể spam nguy hiểm khác là khi watchdog không có việc để làm (ví dụ `len(eligible_devices) == 0` do chưa có máy rảnh, hoặc `adb devices` gặp lỗi timeout/nghẽn server tạm thời):
```python
# LỖI: In template rỗng dù không xử lý máy nào
report = f"""
[BÁO CÁO 2FA GMAIL SAU CA SÁNG]
- Tổng máy đủ điều kiện: 0
- Success (S): []
- Fail (F): []
"""
print(report)  # <- PHÁ VỠ SILENT WATCHDOG! Hermes cron sẽ gửi tin nhắn rỗng này mỗi 5 phút!
```
**Khắc phục**:
- Nếu `not eligible_devices` hoặc không có tác vụ nào được thực thi: `return 0` ngay mà **KHÔNG in bất kỳ nội dung nào ra stdout**.
- Luôn kiểm tra `len(success_list) + len(fail_list) > 0` trước khi `print()` báo cáo.

## 7. Kỷ Luật Phản Hồi Của Agent: Cấm Tự Tiện Xóa / Pause Cron Khi User Gửi Lại Báo Cáo
- Khi user forward hoặc reply tin nhắn báo cáo từ cron (ví dụ: `[BÁO CÁO ...] - Tổng máy đủ điều kiện: 0`), mục đích của user là **thắc mắc nguyên nhân kỹ thuật hoặc kiểm tra hiện trường** (tại sao 0 máy, tại sao fail).
- **CẤM TUYỆT ĐỐI** Coordinator tự ý suy diễn user than phiền spam rồi tự gọi `cronjob(action='remove')` hay `action='pause'` để xóa/dừng job.
- Chỉ được phép xóa hoặc pause khi user ra lệnh rõ ràng bằng văn bản (*"xóa cron X"*, *"tắt job Y"*).

## 8. Anti-Pattern: Race Condition Chốt Sớm Báo Cáo Phiên Đa Khâu (Multi-Stage Session Aggregation Race)
- **Hiện tượng**: Báo cáo tổng kết phiên (ví dụ Feed Session Watchdog) hiển thị: `Success: 70 máy lướt feed`, nhưng `Follow chéo (0 lượt follow), Lỗi script/xác minh (70 máy)`.
- **Nguyên nhân kỹ thuật**:
  1. Phiên nuôi acc gồm 2 khâu liên hoàn: Lướt Feed trước → Follow hook cuốn chiếu ngay sau khi từng máy xong Feed.
  2. Watchdog kiểm tra điều kiện chốt: nếu `completed_machines >= expected_machines (80 máy)` thì chốt ngay lập tức.
  3. Khi 80 máy vừa lướt xong Feed, watchdog tưởng toàn bộ phiên đã kết thúc và phát ngay báo cáo, trong khi Follow runner vẫn đang xử lý hoặc chưa kịp flush file kết quả `follow_result.json`.
  4. Watchdog đọc thiếu file kết quả và đánh đồng toàn bộ các máy vừa lướt Feed thành lỗi script.
- **Biện pháp xử lý**:
  - Không chốt báo cáo sớm chỉ dựa trên số lượng hoàn thành của khâu đầu tiên (Feed).
  - Bắt buộc kiểm tra trạng thái bận của runner (`runner_busy is False`) hoặc đã hết grace period sau khung giờ phiên (`now >= window_end + grace_period`) trước khi chốt phát báo cáo.
  - Kiểm tra tính đầy đủ của các artifact đi kèm (`follow_result.json`, `upload_result.json`) tương ứng với số máy pass feed.

## 9. Anti-Pattern: Lọt Log Trung Gian Ra stdout Do Gọi Trực Tiếp Sub-Module / Hàm Tiện Ích
- **Hiện tượng**: Dù watchdog không chủ động gọi `print()`, Telegram vẫn bị spam các dòng log chi tiết hoặc debug lắt nhắt trong suốt 30-60+ phút chạy của batch.
- **Nguyên nhân kỹ thuật**: Watchdog import trực tiếp hàm từ repo công cụ (ví dụ: `from enable_gmail_2fa_device import enable_2fa_device`). Bên trong hàm con có sẵn nhiều lệnh `print()`. Khi watchdog chạy trong tiến trình Python chính, toàn bộ lệnh `print()` nội bộ của hàm con đổ thẳng ra `sys.stdout` của watchdog.
- **Biện pháp xử lý**:
  Bắt buộc bọc mọi lệnh gọi sub-module hoặc hàm phụ trợ tiềm ẩn print vào `contextlib.redirect_stdout`:
  ```python
  import contextlib
  import io

  with contextlib.redirect_stdout(io.StringIO()):
      res = enable_2fa_device(serial, email)
  ```
  Nếu cần ghi nhận lại log của sub-module để debug sự cố, ghi nội dung của buffer vào file log chuyên biệt trên đĩa (`D:\Taadaa\runtime\...\debug.log`), tuyệt đối không để rò rỉ ra `sys.stdout`.

## 10. Cơ Chế Singleton Lock Bằng PID Lock File Chống Chạy Đè Cho Batch Dài
- **Hiện tượng**: Cron tick định kỳ (ví dụ mỗi 5-15 phút), trong khi một lượt chạy batch của watchdog tốn 30-60 phút. Các lượt tick tiếp theo tiếp tục khởi động tiến trình mới, gây tranh chấp thiết bị (ADB locks, proxy), xung đột tài nguyên hoặc chạy lặp lại cùng một tập tài khoản.
- **Quy tắc triển khai Singleton Lock chuẩn**:
  1. Sử dụng file lock lưu PID (ví dụ: `D:\Taadaa\runtime\kibe\cron-state\<job_name>.lock`).
  2. Kiểm tra tồn tại và liveness:
     ```python
     def is_pid_alive(pid: int) -> bool:
         if pid <= 0:
             return False
         try:
             import psutil
             return psutil.pid_exists(pid)
         except Exception:
             pass
         try:
             os.kill(pid, 0)
             return True
         except OSError:
             return False

     if LOCK_FILE.exists():
         try:
             content = LOCK_FILE.read_text(encoding="utf-8").strip()
             old_pid = int(content) if content.isdigit() else -1
             if old_pid > 0 and is_pid_alive(old_pid):
                 log(f"Watchdog đang chạy bởi PID {old_pid}. Bỏ qua lượt này.")
                 return 0
             else:
                 log(f"Lock cũ (PID {old_pid}) đã chết. Dọn dẹp lock cũ.")
                 LOCK_FILE.unlink(missing_ok=True)
         except Exception as e:
             log(f"Lỗi kiểm tra lock cũ: {e}. Xóa lock.")
             LOCK_FILE.unlink(missing_ok=True)
     ```
  3. Ghi PID và luôn giải phóng lock trong khối `try...finally`:
     ```python
     LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
     LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
     try:
         # Thực thi toàn bộ tác vụ batch / watchdog
         ...
     finally:
         LOCK_FILE.unlink(missing_ok=True)
     ```

## 11. Anti-Pattern: In Danh Sách Dữ Liệu Thô (Raw List Dumps) Trong Báo Cáo Tổng Kết
- **Hiện tượng**: Báo cáo tổng kết in nguyên cấu trúc Python thô `Success (86): ['M1 (a@gmail.com)', 'M2 (b@gmail.com)', ...]` khiến tin nhắn Telegram dài hàng trang, khó đọc trên điện thoại và dễ chạm giới hạn ký tự.
- **Biện pháp xử lý**:
  - Không bao giờ in danh sách chi tiết các item thành công nếu số lượng lớn.
  - Định dạng chuẩn cô đọng, chỉ liệt kê định danh ngắn gọn của các item thất bại để phục vụ điều tra nhanh:
    ```python
    fail_summary = f" ({', '.join([f.split()[0] for f in fail_list])})" if fail_list else ""
    report = (
        f"[{JOB_NAME} TỔNG KẾT]\n"
        f"- Thời gian: {start_time.strftime('%H:%M')} -> {end_time.strftime('%H:%M')} ({duration_min} phút)\n"
        f"- Tổng máy xử lý: {len(eligible)}\n"
        f"- Thành công: {len(success_list)}/{len(eligible)} máy\n"
        f"- Thất bại: {len(fail_list)} máy{fail_summary}"
    )
    print(report)
    ```

## 12. Cạm Bẫy Path Escape `\r` Trên Windows Khi Viết Code Watchdog
- **Hiện tượng**: Viết `r"D:\Taadaa\runtime\..."` trong tool patch hoặc write_file.
- **Cạm bẫy**: Chuỗi `\runtime` có chứa `\r`. Khi truyền qua JSON payload hoặc text replacement parser, `\r` bị diễn dịch thành ký tự Carriage Return (ASCII 0x0D), cắt cụt chuỗi tại `\r` và làm dòng code tiếp theo vỡ thành `unterminated string literal` (`SyntaxError`).
- **Quy tắc bất biến**: Trong mọi code Python sinh ra trên Windows, **BẮT BUỘC dùng dấu gạch xuôi (`/`)**:
  ```python
  STATE_DIR = Path("D:/Taadaa/runtime/kibe/cron-state")
  LOCK_FILE = STATE_DIR / "my_watchdog.lock"
  ```

## 13. Kỷ Luật Phản Hồi Khi User Báo Lỗi / Báo Spam (Action-First, Cấm Xin Lỗi Đãi Bôi)
- **Hiện tượng & Phản hồi sai**: Khi user phản ánh bot spam hoặc lỗi kỹ thuật (*"Tao đã dặn chỉ đc báo cáo khi làm xong r mà cái gì spam lắm v"*), agent lập tức xin lỗi rỗng tuếch (*"Dạ em nhận lỗi. Em đã ghi nhớ kỷ luật..."*). User bức xúc phản ứng gay gắt: *"Sửa cron báo cáo lại, nhận lỗi cái lồn à đợi mày nhớ"*.
- **Quy tắc ứng xử Action-First bắt buộc**:
  1. **CẤM TUYỆT ĐỐI**: Xin lỗi đãi bôi, nói suông, hoặc nhắc lại quy chế khi chưa có hành động sửa chữa thực tế.
  2. **BẮT BUỘC**: Đi thẳng vào hành động kỹ thuật O(1) ngay lập tức:
     - Định vị chính xác cron job / script gây lỗi và giải thích rõ nguyên nhân kỹ thuật (do đâu rò rỉ stdout, do đâu chạy đè).
     - Liệt kê các hành động cụ thể đang triển khai để khắc phục (chuyển delivery về local, bọc redirect_stdout, thêm singleton PID lock, rút gọn format).
     - Dispatch worker thực thi ngay và chỉ báo cáo khi đã có bằng chứng nghiệm thu (compile thành công, test pass).

## 14. Anti-Pattern: Rò Rỉ Log Lỗi Từ Python `logging` (Root StreamHandler) Gây Spam Cron Liên Tục Khi Dịch Vụ Ngoài Bị Lỗi (Upstream Dependency Blip)
- **Hiện tượng**: User gắt: *"đừng có spam thông báo như thế"*. Bot liên tục bắn tin nhắn Telegram cứ mỗi 5 phút chứa các dòng log:
  ```text
  [ERROR] GPM Start API thất bại: Yêu cầu cập trình duyệt [Chromium] [142]
  ```
- **Nguyên nhân kỹ thuật**:
  1. Watchdog import hàm từ repo con (ví dụ `setup_authenticator_for_profile` từ GPM auto).
  2. Repo con cấu hình `logging.basicConfig(level=logging.INFO)` hoặc dùng root logger với `StreamHandler(sys.stdout)` mặc định.
  3. Khi dịch vụ bên ngoài (GPM, Chromium, ADB, Proxy) gặp lỗi (ví dụ Chromium lệch version cần update), hàm con ghi `logger.error(...)`.
  4. Lỗi này đổ thẳng ra `sys.stdout` của watchdog tiến trình chính.
  5. Hermes `no_agent: true` cron thấy `stdout` có text → chuyển phát nguyên văn (verbatim) vào Telegram mỗi 5 phút!
- **Biện pháp xử lý triệt để**:
  1. **Ép StreamHandler của logging về `sys.stderr` hoặc file log**:
     ```python
     import logging
     logging.basicConfig(
         level=logging.INFO,
         stream=sys.stderr,  # BẮT BUỘC: không để logging đổ ra sys.stdout
         format="%(asctime)s [%(levelname)s] %(message)s"
     )
     ```
  2. **Bọc lệnh gọi sub-module bằng `contextlib.redirect_stdout`, `redirect_stderr` và `logging.disable(logging.CRITICAL)`**:
     ```python
     import contextlib
     import io
     import logging

     sink = io.StringIO()
     prev_disable = logging.root.manager.disable
     logging.disable(logging.CRITICAL)
     try:
         with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
             res = setup_authenticator_for_profile(c)
     finally:
         logging.disable(prev_disable)
     ```
  3. **Quy tắc Silent On Failure trong Silent Watchdog**:
     - Nếu không có bất kỳ kết quả thành công nào (`not success_list`): **TUYỆT ĐỐI KHÔNG print ra stdout**, chỉ ghi log lỗi vào stderr hoặc file state JSON và `return 0`.
     - Chỉ in ra stdout khi có **kết quả thành công thực tế** hoặc tổng kết hoàn tất ca.
  4. **Circuit Breaker / Backoff cho Upstream Error**:
     - Nếu upstream service (GPM, ADB) báo lỗi cấu hình liên tục (như lệch Chromium version), ghi nhận cờ tạm dừng trong file state để dừng thử lại mỗi 5 phút, tránh đốt tài nguyên và tránh rủi ro rò rỉ log spam.

## 15. Kỷ Luật Phản Ứng Khi User Phản Ánh Spam: CẤM Tự Ý Tắt Delivery Sang Local Khi User Vẫn Cần Nhận Alert
- **Hiện tượng**: Khi user bức xúc vì bot spam log rác (*"đừng có spam thông báo như thế"*), agent vội vàng chuyển job sang `deliver: local` để tắt ngấm thông báo. Ngay sau đó user phải sửa sai: *"ủa vẫn gửi về nhóm farm alert chứ nhưng k spam tiến trình như v gửi ngắn gọn thôi"*.
- **Bài học cốt lõi**:
  1. Khi user than phiền spam, vấn đề nằm ở **nội dung rác và tần suất vụn vặt** (spam tiến trình, spam log lỗi), **KHÔNG PHẢI** user muốn cắt đứt kênh thông tin.
  2. **CẤM TUYỆT ĐỐI**: Tự ý hạ `deliver` về `local` hoặc `pause` job vĩnh viễn khi user không yêu cầu dẹp job.
  3. **Hành động chuẩn**:
     - Giữ nguyên target gửi về nhóm Farm Alert (`telegram:-5373649734`).
     - Sửa triệt để code watchdog: bọc kín `stdout` để các tick lỗi/tiến trình trở về **0 bytes (Silent Tick)**.
     - Định dạng báo cáo đầu ra cực kỳ ngắn gọn (chỉ gửi 1 tin tóm tắt kết quả thành công khi có phát sinh thực tế).

## 16. Pattern Cho Pool Healer / Account Watchdog: Silent Mode Khi Toàn Bộ Active & Gom Nhóm Lỗi (Compact Cap)
- **Bối cảnh**: Watchdog kiểm tra và tự động hồi sinh pool tài khoản (ChatGPT-Web, Antigravity OAuth, proxy pool) chạy định kỳ qua Hermes cron.
- **Yêu cầu Silent Mode**:
  - Khi toàn bộ tài khoản đều ACTIVE và không có lỗi (`len(all_failed) == 0 and active_cnt == total_cnt`): Watchdog bắt buộc **im lặng hoàn toàn** (`return` trực tiếp, không `print()` bất kỳ ký tự nào ra stdout). Không phát sinh tin nhắn Telegram định kỳ khi hệ thống đang hoạt động bình thường.
  - Loại bỏ hoặc vô hiệu hóa toàn bộ log trung gian lúc đang mở profile/quét tài khoản (ví dụ `log("Đang mở GPM...")`, `log("Phát hiện X tài khoản...")`), tránh việc stdout đã bị rò rỉ trước khi kiểm tra trạng thái cuối.
- **Yêu cầu Format Rút Gọn (Compact Error Cap)**:
  - Khi có tài khoản lỗi cần chú ý, format báo cáo ngắn gọn, gom nhóm:
    ```python
    report_lines = [
        "🤖 <b>[POOL HEALER] BÁO CÁO SỨC KHỎE</b>",
        f"• <b>ChatGPT-Web:</b> {chatgpt_active_cnt}/{len(chatgpt_after)} ACTIVE",
        f"• <b>Antigravity:</b> {ag_active_cnt}/{len(ag_after)} ACTIVE",
    ]
    if recovered:
        report_lines.append(f"• <b>Đã hồi sinh ({len(recovered)} acc):</b> {', '.join([a.split('@')[0] for a in recovered])}")
    if all_failed:
        report_lines.append(f"• <b>Cần chú ý ({len(all_failed)} acc):</b>")
        for a, err in all_failed[:5]:
            report_lines.append(f"  - <code>{a}</code>: {err[:60]}")
        if len(all_failed) > 5:
            report_lines.append(f"  - <i>... và {len(all_failed) - 5} tài khoản khác</i>")
    print("\n".join(report_lines))
    ```

## 17. Kỷ Luật Nuôi Trình Duyệt / Browser Automation Trên Cron (`no_agent=True`): Tách Log File Khỏi stdout & Báo Cáo Ngắn Gọn Khi Xong
- **Hiện tượng**: User phản ánh: *"spam quá chạy xong r báo cáo ngắn gọn thôi"*. Bot liên tục gửi tin nhắn dài hàng chục dòng log chi tiết từng giây của quá trình duyệt web (kết nối CDP, mở tab YouTube, thời gian xem 73s, chụp ảnh nghiệm thu, mở tab Google News, click bài báo, mở Google Search, tắt profile...).
- **Nguyên nhân kỹ thuật**:
  - Script tự động hoá trình duyệt (Playwright/CDP/Selenium) thường cấu hình `logging.basicConfig(..., handlers=[logging.StreamHandler(sys.stdout)])` ở level `INFO`.
  - Trong quá trình chạy, mỗi bước thao tác trình duyệt (chờ trang load, cuộn trang, đổi tab, đếm giây) đều gọi `logger.info()`.
  - Với Hermes cronjob cấu hình `no_agent: true`, mọi dòng text in ra `sys.stdout` đều được gom thành message chuyển phát trực tiếp tới user qua Telegram.
- **Biện pháp xử lý triệt để**:
  1. **Tuyệt đối không dùng `StreamHandler(sys.stdout)` cho log tiến trình**:
     - Điều hướng toàn bộ log chi tiết sang file log chuyên biệt trên đĩa (`D:/Taadaa/GPM auto/logs/<script_name>.log`) bằng `FileHandler` hoặc `RotatingFileHandler`.
     - Nếu cần log console cho debug cục bộ, dùng `sys.stderr`, không dùng `sys.stdout`.
  2. **Khi không có việc (tick rỗng)**:
     - Giữ `stdout` hoàn toàn rỗng (`0 bytes`) để cronjob hoàn toàn im lặng (`Silent Tick`).
  3. **Khi chạy xong mẻ nuôi**:
     - Thu thập danh sách kết quả (email, trạng thái `OK`/`FAIL`, đường dẫn screenshot).
     - Chỉ in đúng 1 báo cáo cô đọng 2-4 dòng ra `sys.stdout` kèm dòng `MEDIA:` nghiệm thu:
     ```python
     summary = [
         f"✓ [GPM Nurture] Hoàn tất nuôi {success_count}/{total_count} profile Gmail:",
     ]
     for r in results:
         summary.append(f"- {r['email']}: {'OK' if r['ok'] else 'FAIL'}")
     if last_screenshot and os.path.exists(last_screenshot):
         summary.append(f"MEDIA:{last_screenshot}")
     print("\n".join(summary))
     ```

## 18. Anti-Pattern: Retry Tick Lặp Lại In Báo Cáo "Đã Dọn Đợt Này: 0 Máy" & Hammering Máy Lỗi Không Giới Hạn
- **Hiện tượng thực tế**: User bức xúc: *"Spam lắm thế"* kèm ảnh chụp nhóm Telegram Farm Alerts liên tục nhận tin nhắn từ bot mỗi 15 phút:
  ```text
  Cronjob Response: end-of-day-clear-tiktok-cache (job_id: 79021fa79d8b)
  ----------
  [BÁO CÁO DỌN DẸP CACHE TIKTOK]
  • Đã dọn đợt này: 0 máy (None)
  • Lũy kế hôm nay: 74 máy
  • Fail (4): 15, 43, 60, 74
    - Máy 15: Timeout
    - Máy 43: could not confirm cache size after clear
    - Máy 60: could not confirm cache size after clear
    - Máy 74: Timeout
  ```
  Và 15 phút sau lại bắn tiếp tin tương tự với `Đã dọn đợt này: 1 máy (60) ... Fail (3): 15, 43, 74`.
- **Nguyên nhân kỹ thuật**:
  1. Cronjob cấu hình lặp ngắn (ví dụ `*/15 3,4,5 * * *`) với `no_agent: true`.
  2. Đợt 1 quét toàn farm (78 máy): 74 máy pass, 4 máy fail. Script đã in báo cáo 1 lần lên Telegram.
  3. Ở các tick 15 phút tiếp theo: Script lấy danh sách các máy chưa dọn (`m not in cleared_today`) để thử lại.
  4. **Lỗ hổng cốt lõi**: Khi các máy lỗi tiếp tục fail, số máy mới dọn được = 0 (`s_count == 0`), nhưng do `f_count > 0`, script VẪN in ra stdout toàn bộ khối `[BÁO CÁO DỌN DẸP CACHE TIKTOK]`. Hermes cronjob bắt stdout và bắn thẳng vào Telegram.
  5. **Hammering vô tận**: Không có giới hạn số lần thử lại (`machine_retries`) cho mỗi máy. Các máy kẹt ADB/UI bị đè ra chạy lại suốt 3 tiếng (tới 12 lần), vừa vô ích vừa làm nghẽn thiết bị.
- **Biện pháp khắc phục triệt để (3 Invariants Bắt Buộc)**:
  1. **Khóa Dedup Báo Cáo Toàn Farm Theo Ngày (`reported_date == today_str`)**:
     - Báo cáo chi tiết `[BÁO CÁO DỌN DẸP ...]` CHỈ ĐƯỢC PHÉP in ra stdout đúng **1 lần duy nhất trong ngày** ở đợt chạy đầu tiên (`reported_date != today_str`).
     - Sau khi in xong, lưu ngay `state["reported_date"] = today_str` vào file state JSON.
  2. **Quy tắc Silent Watchdog khi `s_count == 0`**:
     - Ở mọi đợt tick tiếp theo (retry tick), nếu `s_count == 0`: BẮT BUỘC `return 0` ngay lập tức, `stdout` rỗng 100% (0 bytes).
     - CẤM TUYỆT ĐỐI in chuỗi *"Đã dọn đợt này: 0 máy"* hay danh sách lỗi lặp lại ra stdout!
     - Nếu retry thành công một phần: chỉ log vào `sys.stderr`. Khi và chỉ khi toàn bộ farm đã hoàn tất 100%, mới in đúng 1 dòng vắn tắt ra stdout: `[DỌN CACHE TIKTOK] Đã dọn bù thành công: {s_list}. Hoàn tất {len(cleared_today)} máy toàn farm.`
  3. **Giới Hạn Retry Tối Đa 2 Lần/Máy/Ngày (Circuit Breaker)**:
     - Trong file state, lưu `machine_retries: {str(m): count}` theo ngày.
     - Trước khi đưa máy vào `target_machines`, kiểm tra: nếu `machine_retries.get(str(m), 0) >= 2` thì bỏ qua, không thử lại nữa để tránh lặp vô tận.
  4. **Xử lý khẩn cấp khi user kêu spam**:
     - Gọi ngay `cronjob(action='pause', job_id=...)` trong turn đầu tiên để dập tắt ngay nhịp bắn spam, ngăn Telegram nhận thêm tin rác trong lúc đang điều tra và vá lỗi.

## 19. Anti-Pattern: ThreadPoolExecutor + logging.basicConfig(StreamHandler(sys.stdout)) Bypass redirect_stdout — Gây 35KB-38KB Cron Spam Mỗi Tick
- **Hiện tượng thực tế (2026-09-23)**: Cronjob `post-morning-gmail-2fa-watchdog` bắn cụm tin nhắn 35KB-38KB chi tiết lên Telegram mỗi tick (chứa "Bắt đầu xử lý 2FA: Máy 04...", "Profile started. CDP: 127.0.0.1:53556...", "Đã đóng profile... và dọn sạch tiến trình Chrome port...") khiến user gắt: **"Clgt"** và **"Đkm lại spam alert"**.
- **Nguyên nhân kỹ thuật (chuỗi 3 lỗi)**:
  1. **logging.basicConfig với StreamHandler(sys.stdout)** trong module con (`run_add_2fa_remaining.py`) cấu hình `logging.basicConfig(handlers=[StreamHandler(sys.stdout)])` ở level INFO. Khi watchdog import `setup_authenticator_for_profile`, Python root logger đã bị attach handler stdout ngay lúc import.
  2. **ThreadPoolExecutor + contextlib.redirect_stdout KHÔNG thread-safe**: `contextlib.redirect_stdout(io.StringIO())` chỉ thay `sys.stdout` trong thread gọi nó (main thread), nhưng mỗi worker trong `ThreadPoolExecutor` chia sẻ cùng `sys.stdout` ban đầu. Khi worker thread gọi `logger.info()`, handler stdout gốc (bị attach từ bước 1) vẫn ghi trực tiếp ra `sys.stdout` thật, bypass hoàn toàn redirect.
  3. **Điều kiện báo cáo sai** `if success_list or fail_list: print(...)` — khi mọi máy đều fail (GPM profile chưa login Google), `fail_list` có nội dung → script vẫn in báo cáo và danh sách lỗi 35KB dù `len(success_list) == 0`.
- **Bộ 3 Fix Bắt Buộc**:
  ```python
  import logging, sys, io, contextlib

  # FIX 1: Ngay sau import sub-module, xóa sạch root logger handlers và vô hiệu hóa
  root_logger = logging.getLogger()
  for h in list(root_logger.handlers):
      root_logger.removeHandler(h)
  root_logger.addHandler(logging.NullHandler())

  # Và vô hiệu hóa logger cụ thể của sub-module
  for logger_name in ['Add2FA', 'run_add_2fa_remaining']:
      sub_log = logging.getLogger(logger_name)
      sub_log.handlers = [logging.NullHandler()]
      sub_log.propagate = False

  # FIX 2: Trong _process_single, bọc cả redirect_stdout VÀ redirect_stderr
  _stdout_sink = io.StringIO()
  _stderr_sink = io.StringIO()
  with contextlib.redirect_stdout(_stdout_sink), contextlib.redirect_stderr(_stderr_sink):
      res = setup_authenticator_for_profile(profile_info)
  # (Handler đã bị xóa ở bước 1 nên không còn ghi ra stdout thật nữa)

  # FIX 3: Điều kiện báo cáo ĐÚNG — chỉ in khi CÓ thành công thực tế
  if len(success_list) > 0:  # CẤM dùng 'if success_list or fail_list:'
      report_lines = [
          "[BÁO CÁO 2FA GMAIL SAU CA SÁNG]",
          f"- Thành công: {len(success_list)}/{len(eligible)} máy",
          f"- Thất bại: {len(fail_list)} máy",
      ]
      print("\n".join(report_lines))
  # else: return 0, stdout hoàn toàn rỗng (Silent Watchdog)
  ```
- **Nguyên tắc tổng quát rút ra**:
  - Khi watchdog dùng `ThreadPoolExecutor`, **KHÔNG bao giờ dựa vào `contextlib.redirect_stdout` để bịt logging từ sub-module**. Phải xóa handler ở cấp Python root logger ngay khi khởi động.
  - Invariant báo cáo: `if len(success_list) == 0: return 0` với zero stdout bytes — bất kể có bao nhiêu fail.

## 20. Template Khởi Động An Toàn Cho Watchdog Import Sub-Module Có Logging
Khi watchdog cần gọi hàm từ sub-module có thể có `logging.basicConfig(StreamHandler(sys.stdout))`, áp dụng template sau ngay đầu `main()`:

```python
import logging, sys

def _silence_imported_loggers():
    """Bịt kín mọi root/sub-logger trước khi import module có thể attach StreamHandler(stdout)."""
    root = logging.getLogger()
    # Xóa mọi handler hiện có trên root logger
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(logging.NullHandler())
    root.setLevel(logging.CRITICAL)  # Chặn cả propagate của sub-loggers

    # Ghi log của watchdog ra stderr (không bị Hermes cron bắt)
    watchdog_log = logging.getLogger("watchdog_safe")
    watchdog_log.handlers = [logging.StreamHandler(sys.stderr)]
    watchdog_log.propagate = False
    watchdog_log.setLevel(logging.INFO)
    return watchdog_log

# Gọi trước khi import các module có logging:
logger = _silence_imported_loggers()
from run_add_2fa_remaining import setup_authenticator_for_profile  # safe now
```

## 21. Anti-Pattern: Rò Rỉ Stdout Từ CLI / Subprocess Rescan Cục Bộ Gây Nhầm Lẫn Thu Hẹp Toàn Farm ("Gì v sao có 16 máy")
- **Hiện tượng thực tế (2026-09-23)**: User thắc mắc: *"Gì v sao có 16 máy"* khi nhận được tin nhắn từ cronjob `post-evening-avatar-watchdog`:
  ```text
  [TRACKER RESCAN] Hoàn tất cập nhật DB cho 16 máy (exit: 0, duration: 95.78s).
  [TRACKER RESCAN stdout]:
  ========================================
  📊 [FARM ALERT] BÁO CÁO TRẠNG THÁI TIKTOK (23/09/2026 21:26)
  ========================================
  • Tổng số nick quét: 126
  • Số nick LIVE: 125
  • Số nick chưa có avatar: 40
  ...
  ```
- **Nguyên nhân kỹ thuật**:
  1. Trong watchdog cuốn chiếu (ví dụ upload avatar theo từng Tik), sau khi mỗi mẻ batch chạy xong, script gọi CLI tool phụ trợ `tiktok_account_tracker.py --machines <m_list>` để cập nhật nhanh DB cho tập máy vừa hoàn tất.
  2. CLI tracker tự động format output ra stdout thành template `[FARM ALERT] BÁO CÁO TRẠNG THÁI TIKTOK`.
  3. Hàm wrapper trong watchdog (`rescan_completed_machines`) lại dùng `print(...)` in nguyên văn `res.stdout` của CLI ra `sys.stdout` của watchdog.
  4. Vì cronjob chạy `no_agent: true`, bất kỳ chuỗi text nào ở stdout đều được Hermes chuyển phát về Telegram.
  5. Người dùng thấy tiêu đề `[FARM ALERT]` nhưng chỉ có 16 máy / 126 nick (thay vì 160 máy / 1,024 nick), gây hoang mang tưởng farm bị rớt máy hàng loạt hoặc DB bị mất dữ liệu.
- **Biện pháp khắc phục triệt để**:
  1. **Tuyệt đối không in stdout của subprocess ra `sys.stdout` trong bước trung gian**:
     - Toàn bộ kết quả chạy CLI rescan/sync phải ghi vào `sys.stderr` hoặc file log:
       ```python
       # SAI:
       print(f"[TRACKER RESCAN] Hoàn tất cập nhật DB cho {target_desc}")
       if stdout_clean:
           print(f"[TRACKER RESCAN stdout]:\n{stdout_clean}")

       # ĐÚNG:
       sys.stderr.write(f"[TRACKER RESCAN] Cập nhật DB xong cho {target_desc} ({elapsed:.1f}s)\n")
       # Giữ sys.stdout rỗng 100% để Hermes cron không bắt thành tin nhắn Telegram
       ```
  2. **Phân biệt rạch ròi giữa Batch Rescan (Cục bộ) vs Full Farm Audit**:
     - Các CLI quét cục bộ theo danh sách máy con (`--machines`) không được mang tiêu đề `[FARM ALERT] TOÀN FARM` nếu output có nguy cơ lọt ra kênh công cộng.
  3. **Quy chuẩn Silent Subprocess Execution**:
     - Mọi bước phụ trợ chạy ngầm trong watchdog (rescan, sync DB, clear cache, ping) phải hoàn toàn vô hình đối với `sys.stdout`. Chỉ có báo cáo tổng kết cuối ca (khi đạt điều kiện chốt) mới được phép dùng `print()` duy nhất 1 lần.

## 22. Anti-Pattern: Chromium Multi-Process Quét psutil Gây Duplicate PID Spam (Ví dụ: 1 Profile Báo 8-13 Dòng PID)
- **Hiện tượng thực tế**: User bức xúc: *"Clgt cùng 1 profile mà gửi lắm thế"* khi watchdog dọn profile trình duyệt (GPM/Chrome) in ra hàng loạt dòng PID trùng tên tài khoản:
  ```text
  [GPM-WATCHDOG] ĐÃ PHÁT HIỆN & DỌN DẸP 8 PROFILE TREO > 1h:
  • 39 - tachau17042004@gmail.com - 20039 (PID: 69264) | Treo: 1:06:49 | Port: 59769
  • 39 - tachau17042004@gmail.com - 20039 (PID: 82452) | Treo: 1:07:09
  • 39 - tachau17042004@gmail.com - 20039 (PID: 154240) | Treo: 1:06:46
  • 39 - tachau17042004@gmail.com - 20039 (PID: 192732) | Treo: 1:06:46
  • ...
  ```
- **Nguyên nhân kỹ thuật**:
  1. Chromium trên Windows chạy theo mô hình multi-process: 1 Browser Process mẹ đi kèm 5–10 helper processes con (`--type=renderer`, `--type=gpu-process`, `--type=utility`, `crashpad`).
  2. Tất cả tiến trình con này đều kế thừa cùng tham số `--user-data-dir` trỏ vào profile thư mục đó.
  3. Khi watchdog lặp qua `psutil.process_iter()` và match `is_gpm_chrome_process(cmdline)`, nếu không lọc cờ `--type=`, mỗi tiến trình con đều bị nhận diện là 1 profile độc lập bị treo.
  4. Script in ra N dòng cho cùng 1 tài khoản, gây spam tin nhắn Telegram và làm sai lệch thống kê số lượng profile thực tế.
- **Biện pháp khắc phục triệt để (Bộ 3 Quy Chuẩn)**:
  1. **Bỏ qua tiến trình con Chrome**:
     ```python
     # Chỉ xử lý tiến trình Chrome gốc (browser process)
     if any(arg.startswith("--type=") for arg in cmdline):
         continue
     ```
  2. **Khử trùng lặp theo Profile ID / Path (`seen_profiles`)**:
     ```python
     seen_profiles: set[str] = set()
     ...
     prof_key = prof_id or p_path or str(pid)
     if prof_key in seen_profiles:
         continue
     seen_profiles.add(prof_key)
     ```
  3. **Cấu hình cron delivery phù hợp**:
     - Các watchdog bảo trì / dọn dẹp nội bộ tần suất cao (5–10 phút) phải cấu hình `deliver: local`. Không để `deliver: origin` hay gửi về chat cá nhân gây phiền toái.
- **Kỷ luật đối soát khi user hỏi về thông báo cron cũ**:
  - Khi user phản ánh về một thông báo ("Clgt cùng 1 profile mà gửi lắm thế"): Kiểm tra ngay lịch sử chạy trong `~/.hermes/cron/output/<job_id>/*.md` và thời gian sửa đổi của script (`mtime`).
  - Phân định rõ thông báo user nhận được là từ tick chạy cũ trước khi deploy bản vá, tránh nhầm lẫn rằng hệ thống đang bị lỗi hồi quy (regression) ở thời điểm hiện tại.

## 23. Anti-Pattern: Auto-Healer In Báo Cáo Phục Hồi Thường Quy Ra Stdout & Tần Suất Lặp Dày Quá Mức Trên Fleet Lớn
- **Hiện tượng thực tế (2026-10-01)**: User giận dữ: *"Clgt sao lần nào tạo cron watchdog mày cx tạo spam alert v"* kèm tin nhắn:
  ```text
  Cronjob Response: farm-app-provision-watchdog (job_id: a78be2b1f517)
  -------------
  === Farm App Provision Watchdog Report ===
  Completed Provision Actions (2):
    - [Local (Kibe)] M47 (ce11160bd0119a1203): Installed TikTok
    - [Local (Kibe)] M47 (ce11160bd0119a1203): Applied 5 post-config settings
  ```
- **Nguyên nhân kỹ thuật (3 điểm sai sót)**:
  1. **Nhầm lẫn giữa Auto-Heal thường quy và Báo động lỗi**:
     - Khi một watchdog auto-healer (cài bù app, khôi phục timeout màn hình, auto-reconnect ADB, toggle Wi-Fi) phát hiện bất thường và TỰ PHỤC HỒI THÀNH CÔNG, đây là **nhiệm vụ ngầm định kỳ**, hoàn toàn bình thường của hệ thống.
     - Việc in danh sách `Completed Provision Actions` ra stdout khiến Hermes cron `no_agent: true` coi đó là message cần gửi đi, bắn liên tục về Telegram Farm Alert hoặc DM mỗi khi có máy được sửa xong.
  2. **Cấu hình `deliver` bị hướng về Telegram thay vì `local`**:
     - Các auto-healer và janitor chạy tần suất cao hoặc quét fleet phần cứng lớn phải mặc định cấu hình `deliver: "local"`. Nếu muốn gửi alert cho con người, chỉ gửi khi có **LỖI THẬT SỰ KHÔNG THỂ TỰ PHỤC HỒI** (`errors`).
  3. **Tần suất quét quá dày (`*/5 * * * *`) cho tác vụ quét nặng toàn fleet**:
     - Việc quét 150+ máy qua ADB kiểm tra package list mà chạy 5 phút/lần gây nghẽn ADB bus USB/LAN và liên tục kích hoạt auto-heal lắt nhắt. Các tác vụ audit/provisioning app chỉ cần chạy 1 lần/ngày ngoài giờ cao điểm (ví dụ `0 4 * * *`) hoặc hourly.
- **Biện pháp khắc phục triệt để**:
  1. **Quy tắc Silent on Success cho Auto-Healer**:
     - Ghi toàn bộ thao tác phục hồi thành công vào file log cục bộ (`D:\Taadaa\runtime\<job_name>.log`).
     - Giữ `sys.stdout` hoàn toàn rỗng 100% (`sys.exit(0)`).
     - Chỉ in ra stdout khi danh sách `errors` có nội dung (lỗi không cài được, thiết bị hỏng cần người can thiệp).
  2. **Cấu hình Cron Delivery & Cadence Chuẩn**:
     - Đặt `deliver: "local"` cho các auto-healer.
     - Giãn lịch chạy fleet audit về 04:00 sáng (`0 4 * * *`) hoặc 1-2 lần/ngày.

