# Device Lock Cadence & Reap Dead Owner Locks Invariants

## 1. Device Lock TTL vs Shift / Session Cadence (Chu kỳ ca & phiên farm)
- **TTL chuẩn tối đa:** `LOCK_TTL_SECONDS = 3600` (60 phút / 1 giờ).
- **Nguyên nhân cốt lõi:** Các ca và phiên nuôi acc TikTok chạy nối tiếp nhau với khoảng cách ~60–75 phút. Nếu đặt TTL 90 phút (5400s) hoặc 2h (7200s), các máy gặp sự cố ở cuối phiên trước (ví dụ 11:34) vẫn còn hiệu lực khóa khi phiên kế tiếp khởi động (12:45, mới trôi qua ~71 phút), dẫn đến việc hàng loạt máy bị bỏ qua oan uổng (`skipped-device-locked`).
- **Chính sách an toàn khi reap:** Toàn bộ lock hết hạn hoặc dead-owner đều được DI CHUYỂN vào thư mục quarantine (`~/.codex/device-locks-reaped/<timestamp>`), tuyệt đối không xóa cứng (hard-delete) để operator có thể truy vết hiện trường khi cần.

## 2. Phòng Chống Nghẽn Timeout Khi Dọn Dẹp ADB (`reap-dead-owner-locks.py`)
- **Di dời ADB cleanup ra ngoài vòng lặp di chuyển file:**
  - Trong vòng lặp quét lock files, CẤM gọi trực tiếp lệnh ADB dọn màn hình thiết bị.
  - Vòng lặp chỉ thu thập `serials_to_clean: set[str] = set()`, việc `shutil.move` sang thư mục quarantine diễn ra tức thì, giải phóng hiện trường lock đĩa ngay lập tức.
- **Song song hóa ADB cleanup bằng `ThreadPoolExecutor`:**
  - Sau khi toàn bộ file lock đã move sang quarantine, dọn dẹp màn hình thiết bị song song:
    ```python
    if serials_to_clean:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=16)
        try:
            futures = [executor.submit(_cleanup_device_screen, s) for s in serials_to_clean]
            concurrent.futures.wait(futures, timeout=15)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
    ```
  - `max_workers=16` kèm `timeout=15` và `shutdown(wait=False, cancel_futures=True)` đảm bảo dù có 60-80 máy chết lock thì bước ADB cleanup tối đa chỉ mất 15 giây và không bao giờ làm treo reaper.
- **Giới hạn timeout lệnh ADB (3s/lệnh) & Wrapper Timeout (180s):**
  - Mỗi lệnh ADB dọn dẹp (`am force-stop`, `input keyevent 3`) đặt `timeout=3`.
  - Trong `reap-dead-owner-locks-wrapper.py`, đặt `timeout=180` (thay vì 120s) để đảm bảo cron runner có đủ biên độ an toàn khi xử lý dọn dẹp farm quy mô lớn.

## 3. Quy Trình Chẩn Đoán Mass-Failure (Bão Fail Hàng Loạt > 40-50 Máy)
- **Bóc tách Fail Thật vs `skipped-device-locked` (O(1)):**
  - Khi người vận hành hỏi "sao fail nhiều thế" hoặc báo cáo tỷ lệ fail tăng đột biến (ví dụ: 53 máy cùng báo fail):
  - **CẤM KẾT LUẬN VỘI:** Tuyệt đối không phán đoán ngay là máy lỗi UI, crash TikTok hay hỏng mạng hàng loạt.
  - **Kiểm tra ngay `log.jsonl` và `run_manifest.json`:** Lọc các dòng `"result": "skipped-device-locked"` ở bước reservation.
  - Nếu phần lớn máy rơi vào nhóm này, nguyên nhân gốc rễ là **phiên trước chạy kéo dài hoặc bị terminate bất thường khi chưa kịp release device-lock**, khiến PID cũ giữ lock làm phiên sau fail-closed skip toàn bộ.
  - Kiểm tra trạng thái PID trong lock (`powershell.exe -Command "Get-Process -Id <pid> -ErrorAction SilentlyContinue"` hoặc `psutil.pid_exists(pid)`):
    + **Cảnh báo Shell MSYS/Git-Bash:** Lệnh `tasklist //FI "PID eq <pid>"` hoặc `taskkill //F //PID <pid>` chạy trực tiếp trong bash MSYS sẽ fail do sai option (`//FI`, `//F`). Bắt buộc dùng PowerShell hoặc `cmd.exe /c "taskkill /F /PID <pid>"`.
    + Nếu PID đã chết: Xóa file stale lock `~/.codex/device-locks/machine_<N>.lock.json` (hoặc chờ cron `reap-dead-owner-locks` tự quét sau 15p).
    + Nếu PID còn sống nhưng treo từ alert cũ: Terminate bằng `cmd.exe /c "taskkill /F /PID <pid>"` hoặc `powershell.exe -Command "Stop-Process -Id <pid> -Force"`, sau đó xóa file lock.
    + Sau khi giải phóng lock, chạy Canary test đơn máy để verify:
      `env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`
- **Phân nhóm các lỗi máy thật còn lại (Rõ ràng - Không báo chung chung):**
  1. `ATX_SESSION_UNAVAILABLE`: ATX daemon trên máy rớt (cần khởi động lại ATX port 7912 qua adb/u2).
  2. `adb command timed out`: Nghẽn USB/Hub điều khiển khi gửi tap/swipe hoặc setting rotation.
  3. `focused package unavailable` / Mất focus: App TikTok bị crash văng ra Launcher hoặc màn hình khóa.
  4. Lỗi code runtime (như `NameError: name 'ADBError' is not defined`): Luôn kiểm tra kỹ các khối `except <Exception>` trong luồng retry swipe/ADB đã import đầy đủ exception class từ `core.adb` chưa.

## 4. Reaper Singleton Concurrency Safety: True Exclusion (`O_EXCL`) & Heartbeat Refresh (`.reaper.lock`)
- **Vấn đề tranh chấp (Race Condition):**
  - Khi `reap-dead-owner-locks.py` được trigger bởi nhiều cron wrapper hoặc manual trigger cùng lúc, 2 tiến trình reaper có thể cùng quét và di chuyển một file lock vào thư mục quarantine riêng biệt, gây lỗi `move-failed` (FileNotFoundError / AccessDenied).
  - Không thể dùng kiểm tra file tồn tại thông thường (`if lock.exists()`) vì không nguyên tử (non-atomic).
- **Cơ chế True Exclusion (`os.O_CREAT | os.O_EXCL | os.O_RDWR`):**
  - Tạo file singleton lock tại `~/.codex/device-locks/.reaper.lock` bằng cờ `os.O_CREAT | os.O_EXCL | os.O_RDWR`.
  - Nếu file đã tồn tại (`FileExistsError`):
    - Kiểm tra `age = time.time() - lock_path.stat().st_mtime`.
    - Nếu `age < 120s` (`REAPER_LOCK_TTL`): In `REAPER_ALREADY_RUNNING` và exit `0` ngay lập tức.
    - Nếu `age >= 120s`: Xác định tiến trình reaper trước bị crash hoặc treo đột ngột, an toàn unlink file stale lock và thử acquire lại một lần.
- **Heartbeat Refresh trong vòng lặp dài (`REAPER_HEARTBEAT_INTERVAL = 30s`):**
  - Khi duyệt danh sách 80 máy và dọn dẹp màn hình thiết bị qua ADB, thời gian chạy có thể kéo dài >30-60s.
  - Cứ sau mỗi 30s (`time.monotonic() - last_heartbeat > 30`):
    - Ghi đè heartbeat: `os.lseek(fd, 0, os.SEEK_SET)`, `os.write(fd, ...)`, `os.ftruncate(fd, ...)`.
    - Cập nhật file mtime qua `os.utime(str(lock_path), None)`.
    - Việc cập nhật mtime ngăn chặn instance reaper khác coi lock là stale trong lúc instance hiện tại vẫn đang tích cực làm việc.
  - Bắt buộc bỏ qua chính file `.reaper.lock` trong vòng lặp quét lock (`p.name == REAPER_LOCK_FILE.name`).
- **Clean-up trong khối `finally:`:**
  - Bọc toàn bộ luồng xử lý chính trong `try ... finally`.
  - Trong `finally:`, luôn đóng file descriptor (`os.close(lock_fd)`) và unlink file lock (`REAPER_LOCK_FILE.unlink(missing_ok=True)`).

## 5. Watchdog Reaper-Awareness & Ngưỡng Cảnh Báo 40 Phút (`watch_device_locks.py`)
- **Nguy cơ race condition giữa Reaper và Watchdog:**
  - Reaper chạy tại phút `:00`, `:15`, `:30`, `:45`. Watchdog chạy tại phút `:01`, `:16`, `:31`, `:46`.
  - Nếu Reaper quét 80-160 máy và thực hiện dọn dẹp ADB mất >60s, Reaper vẫn đang di chuyển lock sang thư mục quarantine khi Watchdog khởi chạy.
  - Hậu quả: Watchdog đọc các lock đang trong quá trình reap và bắn alert sai (false alarm) về nhóm Telegram.
- **Cơ chế Reaper-Awareness:**
  - Tại `scan_active_locks()`, Watchdog kiểm tra sự tồn tại của `~/.codex/device-locks/.reaper.lock`.
  - Nếu file tồn tại và `(now - mtime) < 120s`, Watchdog log `[watchdog] Reaper is currently running, skipping this tick to avoid false alert.` và trả về danh sách rỗng (bỏ qua lượt scan).
- **Hạ ngưỡng Alert xuống 40 phút (`ALERT_THRESHOLD_MINUTES = 40`):**
  - Chu kỳ phiên nuôi thông thường kéo dài 30–40 phút. Đặt ngưỡng 90p hay 120p là quá muộn (đã trôi qua cả một ca nuôi acc).
  - Ngưỡng 40 phút giúp phát hiện sớm và xử lý máy kẹt ngay trong phiên, không để lan sang phiên sau.
- **Tăng Preflight Reap Timeout lên 120s:**
  - Trong `run_watchdog()`, bước dọn dẹp trước khi quét (`subprocess.run([py_bin, "-B", str(reap_script)])`) phải đặt `timeout=120` (không để 60s) để reaper đủ thời gian xử lý khi có nhiều máy.
- **Cảnh Báo Nghẽn Diện Rộng (>= 30 máy):**
  - Khi tổng số máy đang giữ lock `>= 30`, watchdog tự động gắn tiêu đề ưu tiên đỏ ở đầu tin nhắn:
    `⚠️ CẢNH BÁO NGHẼN LOCK DIỆN RỘNG (>= 30 MÁY)`

## 6. Chủ Động Phát Hiện Preemption Bằng `DeviceLockLease.is_still_held()`
- **Vấn đề khi bị cướp quyền (`force_preempt=True`):**
  - Khi một tác vụ ưu tiên cao (GPM 2FA, giải cứu máy lỗi) cướp lock của tiến trình đang chạy, tiến trình cũ không hề biết mình đã mất quyền và tiếp tục gửi lệnh ADB, gây xung đột màn hình.
- **Giải pháp `lease.is_still_held() -> bool`:**
  - Kiểm tra `_released` flag và đọc snapshot file lock trên đĩa (`_read_json_snapshot`).
  - So sánh `lock_id` và `pid` hiện tại với thông tin trong lease.
  - Nếu không khớp hoặc file đã biến mất $\rightarrow$ trả về `False`.
  - Các worker nuôi acc / batch runner gọi `is_still_held()` giữa các bước quan trọng để tự ngắt an toàn (self-abort) ngay khi bị preempt.

## 7. Phân Biệt Rạch Ròi Giữa Device Lock Retention (`status: blocked`) và Worker Thread Timeout
- **Nguyên tắc sống còn (User chốt 2026-09-06):** "Nhưng như v thì k bị lock và t k detect lỗi đc". CẤM tự ý xóa, hạ TTL hoặc giải phóng lock của máy lỗi sớm. Trạng thái `status: 'blocked'` (`FAILED_LOCKED`) BẮT BUỘC giữ nguyên hiện trường trên màn hình máy thật đủ 1h (3600s) để operator kịp nhận alert và inspect hiện trường bằng `python D:/Taadaa/tools/inspect_machine.py <N>`.
- **Phân biệt 2 khái niệm:**
  1. **Device Lock trên điện thoại (`machine_X.lock.json`):** Máy lỗi PHẢI giữ lock chặt để bảo vệ màn hình hiện trường và chặn các cron khác nhảy vào đè.
  2. **Worker Thread trong Python (`ThreadPoolExecutor`):** Worker thread KHÔNG ĐƯỢC ngâm slot. Hiện tại giới hạn `max_workers = 40`, toàn farm 74 máy phải chia 2 đợt. Nếu 1 máy đứt cáp USB / rớt mạng mà worker thread ngồi chờ retry 35 phút, nó sẽ chiếm 1 slot làm 34 máy đợt sau bị nghẽn và kéo dài cả ca tới 2 tiếng.
- **Quy chuẩn Fast Fail-Closed trong Worker:** Khi phát hiện lỗi vật lý/mạng rõ ràng (`device not found`, `offline`, `kill-switch active`, `ATX dead liên tiếp`), worker thread phải:
  1. Lập tức set `status: 'blocked'` cho file lock máy đó để giữ nguyên hiện trường.
  2. Bắn Farm Alert có ảnh ngay lập tức để operator detect lỗi sớm hơn 30 phút.
  3. Return worker thread ngay lập tức để nhả slot trong threadpool cho máy khác chạy tiếp.

## 8. Watchdog Midnight Rollover, Grace Period & Chống Kẹt Báo Cáo Phiên (`feed_session_watchdog.py`)
- **Cơ chế lỗi (Midnight Date Rollover & Kẹt Báo Cáo Do Runner Busy Vô Hạn):**
  - Ca 3 Phiên 3 (21:45 - 23:59) thường chạy tới 00:xx sáng hôm sau. Khi đồng hồ điểm `00:00:00`, `today` chuyển sang ngày mới, khiến phiên của ngày hôm trước bị coi là `is_today = False`.
  - Mặt khác, nếu kiểm tra `runner_busy` một cách vô điều kiện ở đầu hàm `can_report_session()`, khi một runner của phiên kế tiếp hoặc một tiến trình runner bị treo ngầm, toàn bộ các phiên trước đó dù đã hết giờ từ lâu cũng vĩnh viễn không được chốt báo cáo (gây hiện tượng nghẽn 12h không báo cáo).
- **Quy chuẩn 3 trạng thái cho `can_report_session()`:**
  1. **Tất cả máy dự kiến đã hoàn tất thật:**
     Nếu `completed_expected_count >= expected_count and not has_unattempted_locked`: chốt ngay lập tức (`return True`).
  2. **Trong giờ phiên (`is_today and now_hm < window_end_hm`):**
     Nếu `runner_busy` hoặc `has_unattempted_locked`: chờ (`return False`).
     Chỉ chốt khi `completed_expected_count >= expected_count`.
  3. **Đã qua giờ phiên (`now_hm >= window_end_hm`): Grace Period tối đa 20 phút:**
     Tính mốc `grace_end_hm = _add_minutes_to_hm(window_end_hm, 20)`.
     Nếu `runner_busy` và `now_hm < grace_end_hm`: cho phép runner chạy ráng thêm tối đa 20 phút (`return False`).
     Khi **quá grace period 20 phút** hoặc **runner không bận**: BẮT BUỘC chốt báo cáo (`return True`), không bao giờ để kẹt báo cáo qua ca sau.
  4. **Ngày hôm trước (`not is_today`):**
     Chốt nếu `completed_expected_count >= expected_count` hoặc sau 02:00 sáng (`now_hm >= "02:00"`).
  5. **Nhận diện đầy đủ cú pháp cmdline trong `is_feed_runner_active()`:**
     - Phải kiểm tra cả cờ gạch nối `--mode multi-machine-feed-session` (tránh chỉ bắt `multi_machine_feed_session` gạch dưới).
     - Phải kiểm tra các entrypoint runner: `run_tiktok.py`, `hermes_cron_runner.py`, `tiktok_runner.py`.
     - Bỏ qua chính PID của tiến trình watchdog (`p.pid == os.getpid()`).

## 9. Hậu Quả Nghẽn Toàn Farm Do Dead-Owner Locks Tích Tụ (>100 files) & Bẫy Stderr Trong Cron Wrapper (`no_agent: true`)
- **Nguyên nhân cốt lõi gây "treo cả ngày/12h":**
  - Khi runner / batch feed session bị crash hoặc kill đột ngột (ví dụ PID 179800), các lock file của toàn bộ máy (máy 1..80, bao gồm cả `machine_X.lock.json` và `serial_Y.lock.json`, lên tới 116 files) vẫn nằm trong `~/.codex/device-locks/`.
  - Khi batch runner mới khởi chạy hoặc các cronjob (TikTok runner) cố gắng acquire lock, tất cả máy đều bị skip với lý do `skipped-device-locked` (do lock vẫn mang trạng thái `running` hoặc `queued_v2` trỏ tới PID đã chết). Farm bị tê liệt hoàn toàn.
- **Bẫy chết người `sys.stderr` trong cron wrapper `no_agent=True`:**
  - Cronjob `reap-dead-owner-locks` (`no_agent=True`) được thiết kế để tự động dọn dẹp mỗi 15 phút. Tuy nhiên wrapper script `reap-dead-owner-locks-wrapper.py` có bẫy:
    ```python
    # ❌ SAI LẦM: Ghi status vào stderr khi returncode == 0
    elif proc.returncode == 0:
        sys.stderr.write("(no dead-owner locks)\n")
    ```
  - Trong cơ chế Hermes cron scheduler, với `no_agent: true`, **BẤT KỲ ký tự nào xuất hiện trên `stderr`** (kể cả info/status text) đều khiến Hermes đánh dấu `last_status: error` và kích hoạt chuông cảnh báo lỗi, làm hỏng hành vi im lặng (watchdog pattern).
  - **Quy chuẩn chuẩn hóa:**
    ```python
    # ✅ CHUẨN: Khi clean (không có dead-owner lock), bắt buộc im lặng tuyệt đối (pass)
    elif proc.returncode == 0:
        pass
    else:
        sys.stderr.write(err or f"exit code {proc.returncode}")
        sys.exit(proc.returncode if proc.returncode else 1)
    ```

## 10. Triệt Tiêu Tiến Trình Quét Đĩa Ngầm Bị Bỏ Rơi (Orphaned `grep -rn`) Gây Nghẽn I/O Treo Farm
- **Triệu chứng & Hậu quả:**
  - Các subagent / process trước đó chạy lệnh `grep -rn` quét diện rộng trên ổ `D:/Taadaa` (như PID 611155, 704329, 850540...) chạy nền và bị bỏ rơi (orphaned).
  - Các tiến trình này quét đệ quy hàng triệu file trong các thư mục lớn (`BACKUP_ALL`, `python-envs`, `.runtime`, `.codex-work`), ngốn 100% disk I/O và CPU trên Windows host.
  - Hậu quả: Mọi tác vụ đọc/ghi lock JSON, kiểm tra file status, timeout lệnh ADB bị đình trệ nghiêm trọng, làm cả farm bị treo cứng hàng chục tiếng đồng hồ.
- **Quy tắc bất biến:**
  1. CẤM TUYỆT ĐỐI tự viết hoặc chạy lệnh `grep -rn` quét đĩa diện rộng trên `D:/Taadaa` hay root ổ đĩa.
  2. Khi chẩn đoán farm bị đơ/lag/treo phiên kéo dài: BẮT BUỘC kiểm tra tiến trình `grep` và kill sạch bằng PowerShell:
     `powershell.exe -Command "Get-Process grep -ErrorAction SilentlyContinue | Stop-Process -Force"`
  3. Kết hợp chạy reaper `reap-dead-owner-locks.py` bằng Python farm để giải phóng ngay lập tức các dead-owner locks tồn đọng.

## 11. Bẫy Nuốt Cảnh Báo Telegram Do Giới Hạn 4096 Ký Tự (`message is too long`) Trong Watchdog (`watch_device_locks.py`)
- **Triệu chứng & Hậu quả (Sự cố nghẽn 12h ngày 06/09/2026):**
  - Khi farm có số lượng lớn máy giữ lock hoặc kẹt lock hàng loạt (50–80 máy), danh sách máy trong báo cáo của `watch_device_locks.py` vượt quá 4.096 ký tự (trần tối đa của Telegram `sendMessage`).
  - Telegram API trả về lỗi: `HTTP Error 400: Bad Request: message is too long`.
  - Trong code watchdog cũ:
    ```python
    except Exception as e:
        print(f"[watchdog] Failed to send Telegram alert: {e}")
        return False
    ```
    Hàm chỉ in lỗi ra console và trả về `False`, nhưng `run_watchdog()` vẫn `return 0` (exit code 0).
  - Hermes cron scheduler (đặc biệt các job `deliver: local` hoặc `no_agent: true`) ghi nhận tiến trình exit 0 là `last_status: ok`.
  - Hậu quả: Toàn bộ cảnh báo farm bị nghẽn lock bị nuốt im lặng suốt 12 tiếng liên tục mà người vận hành không hề nhận được bất kỳ tin nhắn nào trên nhóm Telegram `-5518578446`.
- **Quy chuẩn sửa đổi bắt buộc cho mọi script Watchdog:**
  1. **Cắt nhỏ message thành các chunk $\le 4000$ ký tự:**
     Trước khi gửi Telegram, bắt buộc duyệt qua từng dòng text, nếu độ dài vượt quá 4000 ký tự thì tách thành chunk riêng và gửi tuần tự:
     ```python
     chunks, current_chunk, current_len = [], [], 0
     for line in text.split("\n"):
         if current_len + len(line) + 1 > 4000:
             if current_chunk:
                 chunks.append("\n".join(current_chunk))
                 current_chunk, current_len = [], 0
         current_chunk.append(line)
         current_len += len(line) + 1
     if current_chunk:
         chunks.append("\n".join(current_chunk))
     ```
  2. **Không nuốt lỗi gửi alert:** Nếu gửi bất kỳ chunk nào thất bại, watchdog phải raise exception hoặc exit code $\ne 0$ để Hermes cron chuyển sang trạng thái `error` và rung chuông cảnh báo.

## 12. Coordinator Cấm Dừng Sau B3: Bắt Buộc Kích Hoạt B4 (Canary Test Live) Nghiệm Thu Trước Khi Báo Cáo
- **Anti-Pattern (Bỏ rơi hiện trường):**
  - Sau khi hoàn thành B3 (Patch Code) và commit git, Coordinator in dòng lệnh PowerShell / Canary command ra văn bản trả về cho user và thông báo xong.
  - Hậu quả: Máy mục tiêu đang ở trạng thái `status: blocked` hoặc hiện trường đang mở không hề được chạy lại để nghiệm thu. File lock tiếp tục tồn tại, app kẹt nguyên vị trí suốt đêm (12 tiếng), gây hiểu lầm là đã xử lý nhưng thực tế farm vẫn bị kẹt cứng.
- **Quy tắc bất biến:**
  - Quy trình 5 bước Recovery (`Inspect` $\rightarrow$ `Root Cause` $\rightarrow$ `Patch Code` $\rightarrow$ `Canary Test` $\rightarrow$ `Closeout`) là một **CHU TRÌNH KHÉP KÍN BẮT BUỘC**.
  - Coordinator sau khi hoàn tất Patch Code (B3) **BẮT BUỘC PHẢI DISPATCH NGAY Worker Subagent chạy lệnh Canary Test live trên máy mục tiêu (B4)** (với `-RecoveryTestSwipes 2` và `-SkipAccountWorkbookSync -Run`).
  - Chỉ được đóng phiên và báo cáo hoàn tất (B5) khi lệnh Canary đã chạy thực tế trên máy, xác nhận số swipe hoàn thành thành công và nhả device lock hoàn toàn. CẤM TUYỆT ĐỐI dừng lại ở dạng "in câu lệnh hướng dẫn user tự chạy".

## 13. Phân Biệt Các Trạng Thái Lock (`queued_v2` vs `running` vs `blocked`) & Nguyên Tắc Xác Minh Kế Thừa Phiên (Session Succession)
- **Bẫy kết luận vội "máy treo" khi thấy lock tồn tại:**
  - Khi user hỏi máy X có bị treo hay không, hoặc kiểm tra file `serial_<serial>.lock.json`:
  - CẤM nhầm lẫn giữa máy bị treo và máy đang xếp hàng chờ slot (`status: queued_v2`).
- **Phân loại 4 trạng thái lock trong scheduler:**
  1. `status: running` (`owner_active: true`): Thiết bị đang được worker thread điều khiển thực thi thao tác thật (swipe, follow, upload).
  2. `status: queued_v2` (`owner_active: true`): Thiết bị đã được tiến trình runner đặt chỗ (reservation) hợp lệ và đang xếp hàng chờ worker thread rảnh (theo cơ chế phân đợt `max_workers = 40` trên 74-80 máy). **Đây là hành vi điều phối hoàn toàn bình thường, không phải treo.**
  3. `status: blocked` (`owner_active: false`, `handoff_at` set): Thiết bị gặp lỗi (vật lý, VPN, UI crash), kích hoạt Fast Fail-Closed giữ nguyên hiện trường 1h cho operator inspect.
  4. `status: skipped-device-locked`: Phiên sau không thể acquire lock do phiên trước còn tồn đọng lock chưa giải phóng.
- **Nguyên tắc Xác Minh Kế Thừa Phiên (Session Succession Audit):**
  - Khi nhận câu hỏi hoặc alert về một máy bị dừng ở ca trước (ví dụ alert lúc 08:15):
  - **CẤM CHỈ ĐỌC LOG CỦA PHIÊN BỊ ALERT:** Phải quét toàn bộ các thư mục phiên theo trục thời gian trong ngày (`D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-*/*/machines/machine_<N>`).
  - Kiểm tra xem sau thời điểm alert đó, máy đã hoàn thành thành công các phiên tiếp theo (`status: success`, `run_manifest.json`, `upload_result.json`) hay chưa.
  - Luôn chụp screencap (`adb exec-out screencap`) và đọc `mCurrentFocus` tại thời điểm điều tra thực tế để đối chiếu với hiện trường cũ trước khi kết luận tình trạng máy.



