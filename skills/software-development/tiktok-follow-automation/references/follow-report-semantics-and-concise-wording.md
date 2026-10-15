# Follow report semantics and concise operator wording

## Trigger
Use when a follow-session report shows `Success (0)` and the operator asks whether any machine actually ran, was released, or caused an IP lock.

## Interpretation
`Success (0 máy)` means zero completed successful cross-follows without release. It does **not** prove zero attempts or zero follows executed:
- `Follow chéo (X lượt follow)`: Tổng số lượt follow tích lũy được trong phiên (ví dụ 14 lượt).
- `Thành công (0 máy)`: Không có máy nào hoàn tất phiên mà giữ sạch cờ — mọi máy đều dứt điểm bằng `FOLLOW_FAILED` (bị nhả ở lượt cuối).
- `Nhả follow` / `Nhả liền`: Machines that attempted and were released before a successful count was recorded, hoặc follow được một số lượt (ví dụ M1 được 2 lượt, M18 được 12 lượt) rồi bị nhả ở lượt kế tiếp và rơi vào diện `Nhả follow`.
- `Bỏ qua`: Safe skips such as cooldown, organic rest, eligibility, circuit-breaker protection (`Khóa IP do máy cùng IP nhả`), hoặc `Feed chưa ổn định` (nguyên bản code là `sensitive-skip-*`: Fail-Closed Sensitive Guard khi phiên Feed trước đó gặp lỗi/chưa đủ warm, hủy follow để bảo vệ nick).
- `Khóa IP`: Proxy/IP circuit-breaker events and protected machines.

### 0. Phân Biệt Các Dạng Bỏ Qua (Safe Skips) & Nhãn "Feed chưa ổn định" (Raw: "sensitive-skip-*")
Khi operator thấy nhãn `Feed chưa ổn định` (hoặc các mã kỹ thuật cũ `sensitive-skip-...`) trên báo cáo Telegram:
- **Bản chất `sensitive-skip`:** Là cơ chế bảo vệ nick (Fail-Closed Sensitive Guard) giữa Feed và Follow trong `multi_machine_feed_session.py`. Nick chỉ được đi follow chéo khi phiên feed trước đó hoàn tất sạch sẽ và đã warm tối thiểu 3 video (`completed_swipes >= 3`).
- **Chuẩn hóa nhãn hiển thị Telegram:** Trong `feed_session_watchdog.py`, toàn bộ lý do chứa `sensitive` được tự động ánh xạ sang nhãn người dùng dễ hiểu: `Feed chưa ổn định (N máy)`.
- **`sensitive-skip-failed`:** Phiên feed kết thúc với trạng thái `failed` (ví dụ: mở app thất bại, không focus được TikTok sau launch). Không thể chạy follow trên app đang lỗi ➔ Hủy an toàn.
- **`sensitive-skip-manual_needed`:** Phiên feed kết thúc với trạng thái `manual-needed` (ví dụ: mất focus app khi vào profile, kẹt splash/ad không thể vuốt thoát, hoặc username trên profile không khớp với tài khoản chỉ định). Hủy follow để tránh thao tác nhầm trên sai tài khoản hoặc bị TikTok gắn cờ bot.

Do not collapse attempted, successful, released, skipped, and protected into one number. If the report lacks an explicit attempt count, say that the attempt count is not directly shown rather than inventing it.

## Compact Telegram Circuit Breaker & Released Formatting (User Correction)
### 1. Cầu Dao Tự Ngắt IP (Ultra-Concise 1 Line)
Operator yêu cầu khóa IP chỉ ghi số lượng kèm máy partner được cứu, tuyệt đối KHÔNG liệt kê danh sách cổng rườm rà:
- Có máy partner được cứu:
  ```text
  ⚡ Cầu dao tự ngắt IP (X proxy đã khóa): Khóa cứu Y máy (M78, M75, M8)
  ```
- Không có máy partner cần cứu:
  ```text
  ⚡ Cầu dao tự ngắt IP (X proxy đã khóa)
  ```

### 2. Định Dạng Máy Nhả Follow Kèm Số Lượt Thực Tế
Khi máy đạt được một số lượt follow thành công rồi mới bị nhả ở lượt cuối (`Nhả ở Hồi phục 1/2`, `Nhả ở Cấp Khỏe`), BẮT BUỘC ghi rõ số lượt đã đạt được cạnh tên máy:
```text
  + Nhả follow (25 máy | 100.0%):
    - Nhả liền (0 lượt | 92.0%): (M3, M4, M9, M16, ...)
    - Nhả ở Hồi phục 1 (1 - 4 lượt | 4.0%): (M1: 2 lượt)
    - Nhả ở Cấp Khỏe (10+ lượt | 4.0%): (M18: 12 lượt)
```
Tuyệt đối không in trơ trọi tên máy `(M1)` hay `(M18)` khiến operator hiểu lầm là máy bị nhả trắng 0 lượt như nhóm `Nhả liền`.

## Compact wording
Preferred shorthand: `Nhả → khóa IP`.

When a little more context is needed:
```text
Follow chéo: 0 lượt thành công
Nhả liền: X máy, 0 lượt thành công
Khóa IP: Y IP
```

## Operator Triage: "Sao report không báo cáo phiên follow?" (Tri-Channel & Forum Topic Pitfall)
Khi operator phản ánh "sao report không báo cáo phiên follow" hoặc "ca trưa không chạy follow à":
1. **Kiểm tra kênh tiếp nhận (Tri-Channel Split):**
   - Báo cáo chính stdout của cron watchdog gửi về `Tiktok Luot Nuoi Acc` (`-5377611430`) **đã bị cắt bỏ hoàn toàn mục Follow chéo** để gửi riêng về nhóm `Tiktok Follow` (`-5127276494`).
   - Nếu operator chỉ xem nhóm Luot Nuoi Acc, họ sẽ thấy hoàn toàn không có dòng nào về follow.
2. **Kiểm tra Forum Topics (General Topic Blackhole):**
   - Nhóm `Tiktok Follow` (`-5127276494`) bật chế độ diễn đàn/topic (`has_topics_enabled: true`).
   - Nếu lệnh dispatch `sendMessage` gửi thiếu `message_thread_id`, tin nhắn báo cáo follow rơi vào topic `General` thay vì topic làm việc của phiên, khiến operator không thấy thông báo.
3. **Phân biệt "Không chạy" với "Dừng an toàn / Nhả liền tại lượt 0":**
   - Ca trưa (Row 4) phần lớn là nick non (Rookie).
   - ~33% nghỉ Dưỡng sinh, proxy bẩn bị Cầu dao IP 48h chặn trước cửa app (`CIRCUIT_BREAKER_SKIPPED`), các nick được vào cày bấm anchor thì bị TikTok nhả ngay tức thì (`FOLLOW_FAILED` sau swipe).
   - Cơ chế Fail-Closed lập tức ngắt phiên tại lượt 0 để bảo vệ nick khỏi bị cấm tính năng vĩnh viễn ➔ Thống kê ghi nhận 0 lượt thành công nhưng toàn bộ hệ thống đã kích hoạt bảo vệ 100%.

### 4. Giải Pháp Kiến Trúc Đã Chốt & Invariant Chống Bất Đối Xứng Giao Vận (Delivery Asymmetry & State Atomicity Invariant)
- **Bản chất bất đối xứng giao vận (Delivery Asymmetry):**
  * Kênh Lướt Feed (`-5377611430`) được gửi bởi daemon **Hermes Cron Scheduler** (hứng `stdout` của script, gateway kết nối bền vững, buffer tin cậy).
  * Kênh Follow (`-5127276494`) và Video (`-5435853713`) lại do tiến trình Python watchdog tự gọi raw HTTP socket (`urllib.request.urlopen`) ngắn hạn.
  * Khi tiến trình con bị đứt socket/DNS tới Telegram, nếu script nuốt lỗi trong `try...except`, nó vẫn in lướt feed ra `stdout` và ghi nhận session đã hoàn tất vào `feed_session_reported.json`.
  * Hậu quả: Nhóm Nuôi Acc nhận tin bình thường, nhưng nhóm Follow bị mất trắng vĩnh viễn và không bao giờ được gửi bù ở các nhịp sau! Người dùng thấy cực kỳ vô lý vì cùng một lần chạy của watchdog mà kênh này có, kênh kia mất.
- **Quy tắc State Atomicity bắt buộc:**
  * Nếu gửi kênh phụ thất bại sau 3 lần retry: **CẤM ghi nhận hoàn tất vào file state**, HOẶC tự động gom block Follow nối ngược vào `stdout` để đẩy chung qua nhóm Nuôi Acc (không để dữ liệu biến mất trong bóng tối).
- **Vòng lặp gửi tin cậy & Cô lập ngoại lệ:** Bọc `try...except` độc lập cho từng kênh (`cid`), retry 3 lần với timeout 15s để chống rớt tin khi Telegram API gặp độ trễ failover mạng. Ghi lỗi ra `sys.stderr` thay vì nuốt âm thầm.
- **Đồng bộ Unit Test Invariant & Coverage cho Dispatch Telegram:**
  Khi sửa đổi hàm `dispatch_split_reports` (hoặc bất kỳ hàm dispatch tin nhắn Telegram nào có chia nhỏ tin nhắn và retry):
  * **Test Chunking (> 4000 chars):** Bắt buộc tạo fixture block dài > 4000 ký tự và assert `urlopen.call_count > 1` để chứng minh thuật toán cắt line-buffer hoạt động thật.
  * **Test Retry Loop (Transient Failure):** Mock `side_effect=[Exception("net"), MagicMock(), MagicMock()]` kết hợp `patch("time.sleep")` để chứng minh vòng lặp retry 3 lần tự hồi phục.
  * **Test Persistent Failure Isolation:** Mock `side_effect=Exception("fail")` để xác nhận ngoại lệ được bắt an toàn tại từng kênh, in ra `sys.stderr`, không làm crash hàm và vẫn trả về nội dung báo cáo feed chính.
  * Việc thiếu 3 bài test này sẽ bị Reviewer của Closeout Gate đánh tụt điểm Test Evidence và REJECT.

### 5. Sanitization & Error Reason Summarization (Chống Tuồn Raw Exception / HTTP Dump / Path Nội Bộ Vào Report)
Khi tổng hợp mục `Lỗi script/xác minh` trong báo cáo Telegram (`feed_session_watchdog.py` / `follow_session_watchdog.py`):
- **User Frustration Signal:** Phản ứng tiêu cực khi thấy báo cáo chứa rác debug: `Host: ifconfig.me`, `GET /ip HTTP/1.1`, `context deadline exceeded`, đường dẫn `C:\Program Files (x86)\xiaowei\tools\adb.exe` hoặc stack trace nhiều dòng.
- **Root Cause:** Script lấy trực tiếp chuỗi `reason` từ execution artifact mà không lọc sạch, chỉ `split(":", 1)` sơ sài rồi ném thẳng chuỗi đa dòng vào tin nhắn.
- **Quy tắc chuẩn hóa bắt buộc:**
  1. **Làm sạch chuỗi (Sanitize):** Loại bỏ hoàn toàn ký tự xuống dòng (`\n`, `\r`), thay bằng dấu cách; cắt bỏ đường dẫn file/thư mục tuyệt đối và mọi header HTTP dump (`Host:`, `GET /`, `curl.go`, `goreq.go`).
  2. **Ánh xạ nhãn 1 dòng (Categorized 1-Line Labels):**
     * Lỗi VPN/Proxy/Egress verification (`vpn`, `proxy`, `ifconfig`, `egress`) ➔ `Lỗi kết nối VPN/Proxy` (ví dụ: `Lỗi kết nối VPN/Proxy (1: M13)`).
     * Lỗi kết nối thiết bị/ADB (`offline`, `timed out`, `adb.exe`, `disconnect`) ➔ `Mất kết nối ADB/USB` (ví dụ: `Mất kết nối ADB/USB (1: M28)`).
     * Lỗi popup cản trở (`dialog`, `popup`, `unexpected marker`) ➔ `Popup/Dialog bất thường`.
     * Các lỗi ngoại lệ khác: Chỉ trích xuất thông điệp ngắn gọn đầu tiên (tối đa 60 ký tự), cấm in stack trace/command line thô.
  3. **Nguyên tắc phân định môi trường:** Báo cáo Telegram chỉ hiển thị chỉ số và phân loại nghiệp vụ cấp cao. Chi tiết command line và stderr thô chỉ được lưu trong runtime log trên máy, tuyệt đối không tuồn lên kênh chat.

### 6. Phân Biệt Số Follow Trên DB/Dashboard (Cộng Dồn Ngày) vs Báo Cáo Phiên Watchdog (Per-Session)
Khi operator thắc mắc: *"Sao trên db báo 1 lượt mà ở đây báo 0?"*:
- **Bản chất lệch số:** 
  * `tiktok_tracker.db` (bảng `daily_account_actions`, `session_action_stats`) và trang Dashboard thống kê lũy kế **TOÀN BỘ NGÀY HÔM NAY** (`target_date`). Nếu Phiên 1 (06:00) có máy bấm được 1 follow, DB sẽ ghi nhận `1 lượt`.
  * Báo cáo Watchdog trên Telegram (`feed_session_watchdog.py`, `follow_session_watchdog.py`) gửi tổng kết **ĐỘC LẬP THEO TỪNG PHIÊN** (Session Window, ví dụ Phiên 2 lúc 07:30–09:30).
  * Trong Phiên 2, nếu các máy đều bị nhả hoặc skip ➔ Báo cáo Phiên 2 ghi `• Follow chéo (0 lượt follow)`. Đây là kết quả chuẩn xác của riêng phiên đó, không phủ nhận lượt follow thành công của Phiên 1 đã lưu trong DB.
- **Cách trả lời Operator:** Khẳng định ngay lượt trên DB là thật (từ Phiên 1), giải thích báo cáo Telegram là của riêng Phiên 2, đối soát rõ số máy và thời điểm bấm.

### 7. Bẫy Báo Động Giả "LỖI SCRIPT FOLLOW HÀNG LOẠT" Khi Thiết Bị Rớt Cáp/Nghẽn USB
- **Hiện tượng:** Watchdog bắn tin cảnh báo đỏ:
  `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT FOLLOW HÀNG LOẠT (10 máy lỗi script Follow)`
  kèm chi tiết: `Lỗi script/xác minh (10): Mất kết nối ADB/USB (10: M12, M27, ...)`.
- **Bản chất kỹ thuật & Sự ngộ nhận:**
  * Script Follow (`run_follow.py`) **HOÀN TOÀN KHÔNG BỊ BUG HAY CRASH**. Khi kiểm tra preflight VPN, script phát hiện thiết bị rớt ADB thì chủ động dừng khẩn cấp (`status: BLOCKED`) để bảo vệ tài khoản khỏi lộ IP direct — đây là cơ chế Fail-Closed chuẩn.
  * Tuy nhiên, hàm `classify_machine_follow_result` trong watchdog gom toàn bộ các ca `BLOCKED` vào danh sách `fl_error`. Khi số máy rớt $\ge 8$ (ngưỡng `DEFAULT_FARM_ALERT_THRESHOLD`), watchdog tự động giật tít `PHÁT HIỆN LỖI SCRIPT FOLLOW HÀNG LOẠT`.
  * Tiêu đề này đánh lừa operator rằng code bot Python bị lỗi, trong khi nguyên nhân thực chất 100% là **nghẽn bus USB 2.0 EHCI (phần cứng main X99)** sau chu kỳ chạy dài (>24–29 tiếng chưa reboot).
- **Kỷ luật xử lý khi nhận lệnh "Fix đi":**
  1. **Không sửa mò script:** Khẳng định script follow không lỗi, giải thích rõ nguyên nhân phần cứng.
  2. **Giải pháp phục hồi:** Kiểm tra TFT Game Guard (`farm_preflight_daily_reset.py --check-only`). Nếu PASS, kích hoạt Reboot BIOS POST qua Task `Taadaa_Farm_Daily_Reboot_1135` lúc 11:35 (hoặc hỏi operator nếu muốn reboot ngay) để reset thanh ghi phần cứng và kéo 80 máy xanh lại trước Ca 2 (12:00).
  3. **Chuẩn hóa Telemetry Watchdog:** Tách riêng nhánh `device_disconnected` / `hardware_offline` khỏi `fl_error` để watchdog chỉ báo "Lỗi script" khi có crash/unhandled exception thực sự.

### 8. Quy Trình Cứu Hộ Nhanh Khi Báo 1-2 Máy "Mất kết nối ADB/USB" (Single-Machine S7 Rescue)
- **Hiện tượng:** Watchdog báo `Lỗi script/xác minh (1): Mất kết nối ADB/USB (1: M<N>)` (ví dụ M38).
- **Cạm bẫy:** Chạy ngay `inspect_machine.py <N>` sẽ bị timeout (>30s) do thiết bị nghẽn ADB transport (ADB pipe treo, các lệnh `shell getprop`, `dumpsys` lần lượt chờ timeout 10s).
- **Quy trình cứu hộ chuẩn O(1):**
  1. **Chạy cứu hộ phân tầng:** `python D:/Taadaa/tools/recover_stuck_s7.py --machine <N>`
     * Script tự động thực thi phân tầng: L1 (soft 3s) -> L2 (reboot 5s) -> L3 (reconnect 5s).
     * Ở L3 (`adb reconnect`), thông thường chỉ mất ~2.2s là transport phục hồi ngay lập tức (`status: 'reconnected'`).
  2. **Nghiệm thu hiện trường:** Chạy lại `python D:/Taadaa/tools/inspect_machine.py <N>` (chỉ mất ~2s) để xác nhận Pin, Màn hình Awake, Current Focus và ROM ONLINE.
  3. **Báo cáo gọn:** Xác nhận phục hồi kết nối và nghiệm thu hiện trường cho Operator.

### 9. Nguyên Lý Vận Hành Silent Trong Hermes Cron Job Của Watchdog
- **Bản chất Cron Runner:** Task scheduled cron chạy định kỳ (ví dụ mỗi 10-15 phút) gọi `follow_session_watchdog.py`.
- **Cơ chế Silent [SILENT]:** 
  * Watchdog sử dụng file state `follow_session_reported.json` để track các phiên đã báo cáo (`<date>_ca<N>_phien<M>`).
  * Khi tất cả các phiên hiện tại trong ngày đã được báo cáo và lưu state thành công (hoặc phiên hiện tại chưa kết thúc / chưa đủ điều kiện xuất tin), watchdog chạy xong và không print gì ra stdout.
  * Trong vai trò Agent chạy cron job, nếu watchdog không in ra báo cáo mới nào (đã claim/report xong trước đó), BẮT BUỘC trả về duy nhất chuỗi `[SILENT]` (theo chỉ thị cron delivery) để triệt tiêu việc gửi tin rác / tin trống về kênh Telegram của User.

## Answer style
Answer the operator's direct question first, in Vietnamese, with no speculative theory. Explain only the distinction needed to prevent the common misread that `Success (0)` equals “no machine ran.”
