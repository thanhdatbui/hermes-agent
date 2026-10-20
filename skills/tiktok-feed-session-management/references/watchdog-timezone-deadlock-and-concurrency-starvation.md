# Watchdog Timezone Deadlock & Concurrency Starvation Post-Mortem

## 1. Watchdog Delivery Deadlock (UTC Manifest vs Local HCMC Timezone)

### Triệu chứng & Hiện tượng
- Đã quá giờ kết thúc phiên (ví dụ 09:24 sáng) nhưng Telegram không nhận được bất kỳ báo cáo nào của Phiên 1 (06:00 - 08:00) hoặc Phiên 2 (08:00 - 12:00).
- Cronjob watchdog (`feed_session_watchdog.py` / `follow_session_watchdog.py`) vẫn chạy đều đặn mỗi 5 phút với exit code 0 nhưng hoàn toàn im lặng.

### Cơ chế & Nguyên nhân gốc rễ
1. **Manifest ghi chuẩn UTC:** Runner (`run_tiktok.py` / `multi_machine_feed_session.py`) lưu `start_time` và `end_time` vào `run_manifest.json` theo định dạng chuẩn ISO 8601 UTC:
   `"end_time": "2026-10-13T01:02:39.217492+00:00"` (tương đương 08:02:39 sáng theo múi giờ `Asia/Ho_Chi_Minh` GMT+7).
2. **Bẫy String Slicing ngây thơ:** Hàm `_is_session_manifest_completed(date_live, run_name, win_end_hm)` trước đây cắt chuỗi trực tiếp:
   `end_hm = end_time.replace("T", " ").split(" ", 1)[-1][:5]` -> lấy ra `"01:02"`.
3. **So sánh sai lệch múi giờ:**
   - Đối soát với mốc kết thúc phiên `win_end_hm = "08:00"`:
   - Phép so sánh `"01:02" >= "08:00"` trả về `False`!
4. **Kích hoạt Deadlock khi 2 phiên chạy gối đầu:**
   - Mọi hôm, Phiên 1 kết thúc trước 08:00 (lúc 06:45 - 07:35), khoảng nghỉ giữa 2 phiên không có runner nào chạy (`runner_busy = False`), watchdog gửi báo cáo ngay mà không cần check manifest.
   - Khi Phiên 1 chạy vượt mốc 08:00 (kết thúc lúc 08:02) trong khi Phiên 2 đã được scheduler kích hoạt lúc 08:00 (`runner_busy = True` liên tục), watchdog kích hoạt hàm `is_cluster_session_busy()`.
   - Do so sánh UTC sai, `_is_session_manifest_completed` trả về `False` -> watchdog tưởng nhầm Phiên 1 chưa xong -> giữ nguyên cờ `busy = True` -> **chặn đứng báo cáo Phiên 1 vĩnh viễn suốt nhiều giờ**.

### Giải pháp chuẩn hóa (Fix Pattern)
Bắt buộc parse ISO string và convert sang timezone địa phương (`HCMC`) trước khi trích xuất HH:MM:
```python
if win_end_hm in {"24:00", "00:00"}:
    return True
try:
    dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.astimezone(HCMC)
    end_hm = dt.strftime("%H:%M")
except Exception:
    end_hm = end_time.replace("T", " ").split(" ", 1)[-1][:5]
if end_hm >= win_end_hm:
    return True
```

### Pitfall kiểm tra Watchdog qua CLI / Terminal
- Khi chạy trực tiếp `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/follow_session_watchdog.py"` hoặc test lệnh Python một dòng qua `terminal`, script chạy trong môi trường Git-Bash / MSYS trên Windows:
  - Phải luôn chỉ định `timeout` (ví dụ `timeout: 60`) để vượt qua rule guard terminal.
  - Khi import `watchdog` từ script inline Python, cần `sys.path.insert(0, r"D:/Taadaa/tiktok-luot nuoi acc/scripts")` vì các submodule watchdog nằm trực tiếp trong thư mục `scripts/watchdog` (import `from watchdog.lock ...` thay vì `from scripts.watchdog.lock ...`).
  - Nếu phiên hiện tại chưa đến giờ kết thúc hoặc runner đang chạy (`is_feed_runner_active() == True`), watchdog sẽ exit 0 âm thầm mà không in ra báo cáo nào (đúng thiết kế để cronjob chạy nền êm đềm).
  - **Cơ chế Early-Finish Session Window Gating & Multi-Cluster Asymmetry:** Khi một phiên kết thúc sớm hơn giờ đóng khung trên một trong các cụm (ví dụ Phiên 1 khung 06:00 - 08:00, cụm Admin xong lúc 07:51 trong khi cụm Kibe xong lúc 08:03):
    - Hàm `_is_session_manifest_completed` kiểm tra `end_hm >= win_end_hm` (07:51 >= 08:00 -> `False`).
    - Do đó, cụm Admin bị coi là chưa hoàn tất (`completed_after_window = False`), và `is_cluster_session_busy` giữ cờ `busy = True` khi Phiên 2 (08:00:10) đã kích hoạt (`global_runner_busy = True`).
    - Vì `can_report_all` đòi hỏi mọi cụm đều sẵn sàng (`can_rep == True`), chỉ cần 1 cụm kết thúc sớm trước mốc đóng khung là Phiên 1 bị giữ nghẽn (hold) toàn bộ, không thể chốt trong suốt thời gian Phiên 2 đang chạy.
  - **Hiện tượng trả 2 báo cáo dồn toa cách nhau đúng 5 phút (Back-to-back 5-minute delivery):**
    - Khi Phiên 2 hoàn tất (ví dụ 09:26), `global_runner_busy` trở về `False`. Lúc này cả Phiên 1 (bị nghẽn từ trước) và Phiên 2 đều đồng thời đủ điều kiện chốt báo cáo.
    - Script watchdog có cơ chế **One-message-per-tick** (`messages.append(msg); break; print(messages[0])`) nhằm tránh flood tin nhắn Telegram dài trong cùng 1 tick cron.
    - Hệ quả:
      + Tick N (09:30): Watchdog quét thấy Phiên 1 chưa gửi -> gửi report Phiên 1 -> ghi nhận state `ca1_phien1` -> thoát.
      + Tick N+1 (09:35 - cách 5 phút): Watchdog chạy tick kế tiếp, thấy Phiên 1 đã gửi, thấy Phiên 2 chưa gửi -> gửi report Phiên 2 -> ghi nhận state `ca1_phien2`.
    - User sẽ thấy 2 phiên được báo cáo cách nhau đúng 5 phút. Khi điều tra, kiểm tra `feed_session_reported.json` (mtime) và `run_manifest.json` trên từng cụm (`end_time` UTC vs `win_end_hm`).
  - Khi watchdog trả về rỗng (silent) trong cronjob Hermes, agent tuân thủ trả về `[SILENT]` duy nhất để triệt tiêu thông báo rác lên Telegram. Không tự ý bịa đặt nội dung báo cáo khi runner chưa kết thúc và chưa có output từ watchdog.
  - **Nhận diện các tiến trình runner patterns của Farm:** Hàm `is_feed_runner_active()` kiểm tra các pattern: `multi_machine_feed_session`, `multi-machine-feed-session`, `run-feed-session.ps1`, `run_follow`, `run_tiktok.py`, `hermes_cron_runner.py`, `tiktok_runner.py`, `run_post.py`, `tiktok_workflow`, `tiktok_upload`. Khi các tiến trình này (ví dụ `tiktok_workflow` upload video hoặc `run_tiktok.py` feed session) đang chạy thì `is_feed_runner_active()` trả về `True`.
  - **Khác biệt quan trọng giữa `scripts` và `scripts/watchdog` khi test CLI:** Khi chạy inline Python test trực tiếp, nếu script `feed_session_watchdog.py` nạp từ `D:/Taadaa/tiktok-luot nuoi acc/scripts`, `sys.path` cần trỏ đến thư mục `scripts` để các import `from watchdog.lock ...` hoạt động trơn tru.

---

## 2. Nghẽn Concurrency Pool & Chạm Trần Watchdog 2 Giờ (Threadpool Starvation)

### Triệu chứng & Hiện tượng
- Một ca chạy (ví dụ Row 7) kéo dài đúng 2 tiếng 0 phút 1 giây và dừng với lỗi `multi-machine-feed-session/watchdog_budget` (`hard outer watchdog deadline expired`).
- Hàng loạt máy ở cuối danh sách (ví dụ 9 máy M18, M32, M44, M55, M60, M65, M68, M72, M78) có `total_swipes_completed = 0`, bị dừng vì `hard outer watchdog deadline expired` mà **chưa từng được khởi chạy (0 giây execution time)**.

### Cơ chế & Nguyên nhân gốc rễ
1. **Quỹ thời gian cứng:** `worker_hard_timeout` được tính một lần tại thời điểm submit toàn bộ 80 máy (`hard_deadline = time.monotonic() + 7200s`).
2. **Khống chế Worker Concurrency:** `MaxWorkers = 25` (hạ tải để bảo vệ USB 2.0 EHCI). 80 máy phải xếp hàng chạy luân phiên qua 25 worker threads.
3. **Bẫy Retry Dismiss Popup trên máy văng/lag:**
   - Trong `core_prepare_app_for_automation`, khi TikTok không lên được foreground (`focused_package is None` hoặc màn hình Launcher):
   - Script chạy vòng lặp `for attempt in range(1, 11)` (10 lần).
   - Ở mỗi lần focus thất bại, script gọi `popup_dismisser()` -> gọi `capture_required_ui(timeout=60)`.
   - Trên các máy bị treo ADB hoặc rớt kết nối, mỗi lần dump XML mất 60s (kèm 3 lần ATX dump + reset ATX agent).
   - Hệ quả: 10 lần retry x 60s-90s = **10 đến 76 phút bị chiếm giữ bởi 1 máy lỗi**!
4. **Hiệu ứng Dồn toa (Threadpool Starvation):**
   - Chỉ cần 10-11 máy bị lỗi khởi động TikTok chiếm giữ 10-11 worker threads trong 40-75 phút, pool chỉ còn ~14 worker threads để gánh 50+ máy còn lại (mỗi máy lướt 15-20 phút + upload hook 3-5 phút).
   - 9 máy cuối cùng bị kẹt cứng trong hàng đợi của `ThreadPoolExecutor` mà không bao giờ có slot trống cho tới khi đồng hồ chạm mốc 7.200 giây (2 giờ) và kích hoạt hạ màn toàn bộ.
5. **Upload Hook chạy mù quáng:**
   - Khi `prepare_tiktok` đã thất bại (TikTok không thể mở), máy vẫn tiếp tục được đẩy sang `_run_upload_hook`, khởi chạy tiến trình con `tiktok_workflow` vô ích và ngâm thêm 45-60s cho mỗi máy hỏng.

### Giải pháp chuẩn hóa (Remediation Architecture)
1. **Fast-Skip Popup Dismiss khi không có TikTok:**
   - Trong `device_prepare.py`, preflight kiểm tra `focused_package`: nếu là `None` (unresponsive) hoặc các Launcher hệ thống (`com.sec.android.app.launcher`, `nexuslauncher`, `launcher3`), `dismiss_popup()` **trả về `False` ngay lập tức**, không gọi lệnh dump XML nặng 60 giây.
   - Giảm thời gian fail của máy đơ từ 76 phút xuống dưới 15 giây.
2. **Fast Fail-Closed ở cấp Flow:**
   - Đưa `"failed to focus tiktok after launch"` vào danh sách `_FATAL_DEVICE_ERROR_PATTERNS`.
   - Tuyệt đối cấm chạy `upload-hook` khi `child_result.final_status` không phải `success` hoặc `degraded`.
