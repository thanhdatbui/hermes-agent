# Admin Cluster Machine Range & Decoupled Multi-Cluster 2FA Watchdogs (2026-10-06)

## 1. Bối cảnh & Sự cố thực tế
- Khi mở rộng quy trình Add 2FA TikTok sang Farm Admin (Máy 201–280), lệnh `run_batch_live_2fa.py` trả về `{"status": "validated", "reason": "NO_ELIGIBLE_TARGETS"}` dù trong workbook `admin/taikhoan_dat_v2_updated .xlsx` có tới 614 nick chưa có 2FA.
- Đồng thời, User phát hiện sự cố: chuỗi sau ca trưa (`post_noon_chain_watchdog.py`) không bao giờ chạy Add 2FA TikTok khi Phase 1 (Reg Gmail) bị kẹt hoặc thất bại (*"kẹt phase reg gmail thì kệ con mẹ nó chứ mắc gì k chạy phase add 2fa đéo hiểu"*).

---

## 2. Root Causes & Các bản vá cốt lõi

### A. Lỗ hổng hardcode dải máy trong `_machine()` (2026-10-06)
- **Vị trí:** `python_runner/run_batch_live_2fa.py` dòng 126.
- **Root Cause:**
  ```python
  def _machine(value: object) -> str:
      ...
      return str(number) if 1 <= number <= 80 else ""
  ```
  Code cũ chỉ chấp nhận máy từ 1 đến 80. Khi nạp workbook Farm Admin (Máy 201–280), `_machine(204)` trả về chuỗi rỗng `""`. Điều kiện `if not machine or not serial or not username: continue` trong `freeze_targets()` loại bỏ 100% dòng của Farm Admin.
- **Khắc phục:** Mở rộng dải máy hợp lệ lên 999:
  ```python
  return str(number) if 1 <= number <= 999 else ""
  ```

### B. Lỗi ghép nối phụ thuộc (Coupled Lane Starvation) trong Watchdog
- **Vị trí:** `AppData/Local/hermes/scripts/post_noon_chain_watchdog.py`.
- **Root Cause:**
  1. Tham số `--lane` mặc định là `"gmail"`. Cronjob gọi script không truyền cờ nên chỉ chạy mỗi Reg Gmail.
  2. Khi `--lane all`, script cũ in dòng cảnh báo rồi không gọi `run_tiktok_2fa_batch()`.
  3. Khi Reg Gmail lỗi (exit code != 0), toàn bộ chuỗi bị ngắt, Phase 2 Add 2FA TikTok bị bỏ rơi hoàn toàn.
- **Khắc phục (Decoupled Architecture):**
  - Đổi default lane sang `"all"`.
  - Tách thành 2 khối `if` độc lập:
    ```python
    if args.lane in ("gmail", "all"):
        g_code, g_out = run_gmail_batch(dry_run=args.dry_run)
    if args.lane in ("tiktok", "all"):
        # Luôn chạy độc lập, không bị block kể cả khi Gmail lỗi
        t2fa_code, t2fa_out = run_tiktok_2fa_batch(dry_run=args.dry_run)
    ```

### C. Bẫy đầu độc State File (`last_success_date` Poisoning)
- **Vị trí:** `save_state()` trong watchdog chuỗi.
- **Root Cause:** Ghi đè `last_success_date = today_str` vô điều kiện sau mỗi lần chạy, kể cả khi `lane_status == "failed"`. Khi chạy lại ở tick cron tiếp theo, hàm `already_ran_today()` đọc thấy `last_success_date == today` nên chặn đứng toàn bộ các lần thử tiếp theo trong ngày.
- **Khắc phục:** Chỉ gán `last_success_date = today_str` khi tiến trình thực sự thành công (`lane_status == "success"` hoặc `2fa_status == "success"`). Nếu thất bại, giữ nguyên `last_success_date` cũ để cron tiếp tục retry trong khung giờ.

### D. Tách biệt nguồn dữ liệu Multi-Cluster (Kibe vs Admin)
- **Dàn Kibe (1–80):**
  - Workbook: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`
  - ADB: `C:\Program Files (x86)\xiaowei\tools\adb.exe`
  - Config: `D:\Taadaa\machine-config\kibe.yaml`
  - Thực thi: Local subprocess trên Kibe controller.
- **Dàn Admin (201–280):**
  - Workbook: `D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx`
  - Config: `D:\Taadaa\machine-config\admin.yaml`
  - Thực thi: Remote dispatch qua `ssh admin-farm` với `D:/Taadaa/python-envs/automation/Scripts/python.exe`.
  - Mỗi cụm đọc/ghi độc lập vào workbook riêng của cụm đó, có backup và single-writer lock riêng.

---

## 3. Khung giờ vận hành 2FA cuốn chiếu 24h toàn Farm

| Khung giờ | Watchdog Script | Cơ chế |
| :--- | :--- | :--- |
| **14:30 - 18:30** | `post_noon_chain_watchdog.py` | Cuốn chiếu sau Ca trưa: Phase 1 Reg Gmail -> Phase 2 Add 2FA TikTok (40 workers song song Kibe + Admin). |
| **01:00 - 02:50** | `cron_night_tiktok_2fa_watchdog.py` | Quét dọn ban đêm: Phủ sạch toàn bộ nick mới sinh trong ngày chưa có 2FA hoặc mật khẩu yếu trước ca dọn cache 03:00. |

---

## 4. Kỷ luật Thẩm định Closeout Gate cho Thay đổi Machine Range
- **Sự cố Reviewer:** Lần review 1 bị từ chối 82/100 (dưới ngưỡng 85) do `_machine` mở rộng từ 80 lên 999 nhưng thiếu unit test trực tiếp cho các giá trị biên.
- **Tiêu chuẩn kiểm chứng bắt buộc:**
  + Bắt buộc có test boundary trong `test_run_batch_live_2fa.py` xác minh:
    - Giá trị hợp lệ: `1, 80, 81, 201, 280, 999` $\rightarrow$ trả về string số tương ứng.
    - Giá trị ngoài dải / không hợp lệ: `0, 1000, "nonnumeric", None` $\rightarrow$ trả về `""`.
  + Sau khi bổ sung test biên đầy đủ (12/12 passed), reviewer chấm đạt **86/100 APPROVED**.

