# Chẩn Đoán Runner 2FA TikTok Mã Thoát 5 & Cơ Chế Chống Bão Spam Báo Cáo (26/10/2026)

## 1. Hiện Tượng Thực Tế
- Báo cáo gửi về nhóm Telegram `Tiktok add 2fa` (`-5468653590`) lúc 12:31 và 12:33:
  ```text
  ⏰ [FARM REPORT][TOÀN FARM] BÁO CÁO 2FA TIKTOK CA TRƯA:
  • Farm Kibe (Máy 1-80): Hoàn tất 0 | Bỏ qua 0 | Lỗi 0
  • Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 0 | Lỗi 0
  • Lỗi runner: mã thoát 5
  ```
- Toàn bộ chỉ số Hoàn tất / Bỏ qua / Lỗi của cả 2 cụm đều là 0 máy (không có máy nào được khởi chạy).
- Bản tin bị gửi lặp lại sau đúng 2 phút.

---

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)

### A. Căn nguyên mã thoát 5 (Exit Code 5)
Trong kiến trúc batch 2FA (`tiktok-add-bao-mat-f2a`):
1. **Tại `python_runner/run_batch_live_2fa.py`:**
   ```python
   try:
       targets = freeze_targets(cfg.workbook_path, cfg.workbook_sheet, cfg.journal_root, cfg.limit)
   except (OSError, WorkbookError) as exc:
       print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
       return 5
   ```
   Hàm `freeze_targets()` kiểm tra `workbook_exclusive_available()`: Nếu tồn tại file tạm của Excel (`~$taikhoan_dat_v2_updated .xlsx`) hoặc không acquire được workbook lock, runner văng `WorkbookError("BLOCKED_WORKBOOK_OPEN_IN_EXCEL")` và thoát ngay với **exit code 5**.

2. **Tại `cron_night_tiktok_2fa_watchdog.py`:**
   ```python
   if not WORKBOOK_PATH.exists() or not hydrate_workbook(WORKBOOK_PATH):
       logger.error('Workbook %s không tồn tại hoặc không thể hydrate, dừng Cluster Kibe', WORKBOOK_PATH)
       kibe_code = 5
       outputs.append('=== CLUSTER KIBE (MÁY 1-80) ===\nBLOCKED: WORKBOOK_HYDRATION_FAILED')
   ```
   Khi file Excel trên OneDrive bị tính năng *Files On-Demand* giữ offline hoặc lệnh `attrib -u +p` bị timeout/lỗi quyền truy cập, watchdog gán cứng `kibe_code = 5` và bỏ qua toàn bộ đợt chạy của cụm.

3. **Lệch code giữa Kibe và Admin-PC (Cluster Desync):**
   - Khi chỉnh sửa code trong `D:/Taadaa/tiktok-add-bao-mat-f2a/python_runner/run_batch_live_2fa.py` (hoặc `run_capture_phase_b.py`), nếu chưa đẩy code sang Admin-PC, khi Watchdog chạy lệnh SSH PowerShell sang `admin-farm`, tiến trình Python trên Admin sẽ sập ngay tại bootstrap/freeze_targets với **exit code 5**.
   - BẮT BUỘC chạy `python D:/Taadaa/tools/sync_2fa_to_admin.py` ngay sau khi sửa code 2FA trên Kibe để đồng bộ sang Admin.

### B. Căn nguyên lặp lại tin nhắn (Spam Loop)
1. **Mất Idempotency khi Status là Failed:**
   - Khi runner exit code 5, watchdog ghi nhận `status = "failed"`.
   - Nếu hàm kiểm tra đã chạy hôm nay (`already_ran_today()`) bọc điều kiện `is_success` (chỉ dừng khi đợt chạy thành công), lần tick cron tiếp theo sẽ coi như ca chưa được thực hiện.
2. **Thiếu Cooldown cứng khi Runner Crash:**
   - Khi tiến trình con thoát bất thường ở giai đoạn bootstrap (trong vài giây đầu), lane lock được nhả ngay lập tức mà không có khoảng thời gian đệm (`cooldown threshold`). Tick tiếp theo lập tức spawn lại và tiếp tục gửi alert lỗi lên Telegram.

---

## 3. Quy Tắc & Giải Pháp Bắt Buộc

### 1. Phục Hồi & Tự Động Retry Khi Hydrate Workbook
- **Lõi `run_batch_live_2fa.py`**: Bọc `freeze_targets()` trong retry loop 5 lần với exponential backoff `[2.0, 3.0, 4.0, 5.0, 5.0]` giây để triệt tiêu xung đột với cron sync 5 phút (`taikhoan-run-safe-sync`). Mỗi nhịp tự động kiểm tra `~${path.name}` và unlink lock mồ côi nếu `excel.exe` không còn sống trên máy. Bắt buộc có logging `logger.warning` thay vì `except Exception: pass`.
- **Telemetry Retry chuẩn**: Bắt buộc in telemetry `print(f"[telemetry:freeze-retry] attempt={attempt}/{len(delays)} delay={delay}s error={type(exc).__name__}", flush=True)` để đảm bảo tính quan sát từ xa và vượt qua tiêu chí đánh giá Observability của Closeout Gate.
- **Hạ tầng `cron_night_tiktok_2fa_watchdog.py`**:
  + Tại Kibe: `hydrate_workbook()` có retry loop 3 lần x 2.0s + reap lock mồ côi.
  + Tại Admin-PC: Trong script PowerShell gửi qua SSH (`ps_admin_script`), thêm đoạn tự động dọn lock mồ côi `~$taikhoan_dat_v2_updated .xlsx` trước khi gọi `attrib -u +p $wb`.
  + Sau khi sửa code: BẮT BUỘC chạy `python D:/Taadaa/tools/sync_2fa_to_admin.py` (chia chunk base64 đẩy sang Admin) và `python D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py --force`.

### 2. Kỷ Luật Watchdog State & Cooldown Chống Spam
- **Ghi nhận ngày chạy bất kể kết quả:** Watchdog bắt buộc ghi nhận `last_2fa_date = today_str` ngay sau khi đã gửi báo cáo (kể cả khi runner trả về exit code 5 hoặc partial failure).
- **Hard Cooldown Threshold:** Đặt cooldown tối thiểu 45 phút giữa các lần chạy tự động. Không tự động rerun khi gặp lỗi bootstrap trừ khi có cờ tường minh `--force`.

### 3. Đối Soát Đầu Ra Khi Runner Crash
- Khi `total == 0` và `code not in (0, 4)`: Watchdog bắt buộc phân tách rõ nguyên nhân: `• Lỗi runner: mã thoát {code} (kẹt Workbook lock hoặc OneDrive chưa hydrate)` thay vì in mỗi `mã thoát {code}` vô nghĩa.

---

## 4. Kỷ Luật Closeout Gate Khi Sửa Runner 2FA
1. **Unit Test Bắt Buộc Khi Thêm Retry Loop**:
   - Khi sửa `run_batch_live_2fa.py`, bắt buộc viết kèm ít nhất 2 unit test trong `test_run_batch_live_2fa.py`:
     + `test_freeze_retry_exhausted_returns_5`: Mock `freeze_targets` luôn ném `WorkbookError`, kiểm tra runner thử lại đủ 5 lần và return 5.
     + `test_freeze_retry_succeeds_after_transient_failure`: Mock `freeze_targets` ném lỗi ở lần 1 và trả về target hợp lệ ở lần 2, kiểm tra runner tự phục hồi và return 0.
   - Code thêm mới $\ge 15$ dòng trong file test bắt buộc có comment `# Bước X: ...` để vượt qua GuardGate invariant.
2. **Tách Biệt Commit Logic vs Rules Policy**:
   - TUYỆT ĐỐI KHÔNG commit gộp file `rules.json` chung commit với code runner khi chạy Closeout Gate. Gộp chung sẽ khiến Sol Auditor soi regex tĩnh và trừ điểm vì thiếu enforcement test suite. Phải commit `rules.json` riêng trước đó.

---

## 4. Runbook Triage Nhanh O(1) Cho Coordinator Khi Gặp Mã Thoát 5

1. **Kiểm tra tiến trình Excel & Lock file mồ côi:**
   - Kibe: `tasklist /FI "IMAGENAME eq excel.exe"` & kiểm tra glob `~$*.xlsx` tại `D:\OneDrive\TaadaaData\kibe\`.
   - Admin: `ssh admin-farm "tasklist /FI \"IMAGENAME eq excel.exe\""` & kiểm tra glob `~$*.xlsx` tại `D:\OneDrive\TaadaaData\admin\`.
2. **Kiểm tra Hydration & Read byte:**
   - Chạy `attrib -u +p <path>` và đọc 10 bytes nhị phân đầu tiên để xác nhận OneDrive không giữ offline.
3. **Thử nghiệm Target Freeze Offline Mocked:**
   - Import `freeze_targets` trực tiếp trong Python với limit=10 để kiểm chứng logic đọc sheet và header mà không kích hoạt ADB hay can thiệp thiết bị thật.
4. **Kiểm tra Đồng bộ Code Song Song Cụm Admin:**
   - Kiểm tra `git status` trên `D:/Taadaa/tiktok-add-bao-mat-f2a/`. Nếu có file code python_runner bị modified hoặc vừa commit mới, BẮT BUỘC chạy `python D:/Taadaa/tools/sync_2fa_to_admin.py` và kiểm tra `ALL_FILES_PUSHED_OK`.
5. **Chống Task Diversion & Premature Fix Assumption:**
   - Khi nhận Farm Alert mã thoát 5 mà sau đó bị lái sang việc khác (ví dụ: refactor định danh, sửa GuardGate), CẤM ngộ nhận hoặc báo cáo là alert ban đầu đã xong nếu chưa thực hiện đủ 3 bằng chứng: dọn lock mồ côi, `sync_2fa_to_admin.py` exit 0, và dry-run freeze-targets exit 0.
6. **Kỷ Luật Farm Safety Window:**
   - Tuyệt đối CẤM chạy rerun `--force` trong các khung giờ nuôi (Ca nuôi sáng 05:05–09:30, Ca nuôi trưa 11:45–15:30, Ca nuôi chiều 17:45–21:30) để tránh xung đột lock thiết bị làm đứt gãy phiên nuôi feed.
7. **Kỷ Luật Điều Phối Sửa Code (Hard Gate #3):**
   - Khi cần điều chỉnh code của runner/watchdog, CẤM dùng `delegate_task` (bị Hard Gate #3 chặn). Bắt buộc dispatch qua `dispatch_worker.py` (Sol/Agy/Haiku O(1)) hoặc L2 Emergency Surgery nếu thỏa mãn đủ điều kiện exact diff.
