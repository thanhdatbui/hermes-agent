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

### B. Căn nguyên lặp lại tin nhắn (Spam Loop)
1. **Mất Idempotency khi Status là Failed:**
   - Khi runner exit code 5, watchdog ghi nhận `status = "failed"`.
   - Nếu hàm kiểm tra đã chạy hôm nay (`already_ran_today()`) bọc điều kiện `is_success` (chỉ dừng khi đợt chạy thành công), lần tick cron tiếp theo sẽ coi như ca chưa được thực hiện.
2. **Thiếu Cooldown cứng khi Runner Crash:**
   - Khi tiến trình con thoát bất thường ở giai đoạn bootstrap (trong vài giây đầu), lane lock được nhả ngay lập tức mà không có khoảng thời gian đệm (`cooldown threshold`). Tick tiếp theo lập tức spawn lại và tiếp tục gửi alert lỗi lên Telegram.

---

## 3. Quy Tắc & Giải Pháp Bắt Buộc

### 1. Phục Hồi & Tự Động Retry Khi Hydrate Workbook
- Hàm `hydrate_workbook()` phải có vòng lặp retry 3 lần kèm backoff ngắn (2-5 giây) để đợi OneDrive nhả file trước khi kết luận `kibe_code = 5`.
- Kiểm tra và tự động dọn dẹp file lock mồ côi `~$*.xlsx` nếu tiến trình Excel sở hữu đã tắt (`reap-dead-owner`).

### 2. Kỷ Luật Watchdog State & Cooldown Chống Spam
- **Ghi nhận ngày chạy bất kể kết quả:** Watchdog bắt buộc ghi nhận `last_2fa_date = today_str` ngay sau khi đã gửi báo cáo (kể cả khi runner trả về exit code 5 hoặc partial failure).
- **Hard Cooldown Threshold:** Đặt cooldown tối thiểu 45 phút giữa các lần chạy tự động. Không tự động rerun khi gặp lỗi bootstrap trừ khi có cờ tường minh `--force`.

### 3. Đối Soát Đầu Ra Khi Runner Crash
- Khi `total == 0` và `code not in (0, 4)`: Watchdog bắt buộc bổ sung dòng chẩn đoán chi tiết (`WORKBOOK_BLOCKED` hoặc `HYDRATION_FAILED`) thay vì chỉ in mỗi `mã thoát 5` vô nghĩa để người vận hành nhận diện chính xác nguyên nhân từ xa.
