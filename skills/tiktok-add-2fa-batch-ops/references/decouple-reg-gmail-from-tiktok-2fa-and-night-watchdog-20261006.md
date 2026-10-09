# Tách Rời (Decouple) Chuỗi Reg Gmail và Add 2FA TikTok & Watchdog 2FA Ban Đêm (2026-10-06)

## 1. Bối cảnh Sự Cố & Phản Hồi Operator
- **Hiện tượng:** Operator phát hiện màn hình xác minh 2 bước (2FA) trên thiết bị nhưng không thấy báo cáo chạy Add 2FA TikTok. Khi kiểm tra lịch sử, phát hiện ngày hôm trước tiến trình Reg Gmail bị lỗi (`lane_status: failed`, exit code 1) $\rightarrow$ Phase Add 2FA TikTok không hề được gọi.
- **Phản ứng gay gắt của Operator:**
  > *"kẹt phase reg gmail thì kệ con mẹ nó chứ mắc gì k chạy phase add 2fa đéo hiểu"*
  > *"tao cần thiết kế phase add 2fa nhiều hơn để phủ all nick kiểm tra lại các cron hiện tại r thiết kế cho tao"*

---

## 2. Phân Tích Điểm Nghẽn Cốt Lõi (Root Cause)
1. **Khóa cứng lane mặc định & Nuốt lỗi trong caller cha:**
   - Trong `post_noon_chain_watchdog.py`: Tham số `--lane` để giá trị mặc định là `"gmail"` (`default="gmail"`). Khi cronjob chạy không truyền cờ, chỉ có hàm `run_gmail_batch()` được kích hoạt, Phase 2 TikTok bị bỏ qua hoàn toàn.
   - Nhánh `--lane all` cũ in dòng chú thích *"NOTE: --lane all backward-compatible chỉ chạy lane Gmail; TikTok cần trigger riêng"* rồi bỏ rơi TikTok 2FA.
2. **Coupling sai quy trình nghiệp vụ:**
   - Reg Gmail và Add 2FA TikTok phục vụ hai mục đích khác nhau trên tài sản: Reg Gmail tạo tài nguyên mới, còn Add 2FA TikTok bảo vệ các nick TikTok đã đăng ký sẵn.
   - Việc buộc Phase 2FA phải đợi Phase Reg Gmail thành công khiến một lỗi nhỏ (hết SIM, Captcha, proxy) của Reg Gmail làm toàn bộ hàng chục nick TikTok đang chờ bật 2FA bị bỏ đói (starvation).
3. **Thiếu khung giờ chạy chuyên biệt ban đêm:**
   - Trước đây farm chỉ trông chờ vào chuỗi chiều (14:30 - 17:30 / 18:30). Farm có tới 185 nick thiếu 2FA trải trên 68 máy; một khung giờ chiều không đủ để phủ sạch do vướng lịch nuôi feed Ca 2 và Ca 3.

---

## 3. Kiến Trúc Sửa Đổi Độc Lập (Decoupled Architecture)

### 3.1. Sửa `post_noon_chain_watchdog.py`
- Đổi `--lane` mặc định thành `"all"` (`choices=("gmail", "tiktok", "all")`).
- Tách rời hoàn toàn lệnh gọi subprocess:
  ```python
  if args.lane in ("gmail", "all"):
      g_code, g_out = run_gmail_batch(dry_run=args.dry_run)

  # Phase 2 KHÔNG BAO GIỜ bị chặn kể cả khi Phase 1 g_code != 0:
  if args.lane in ("tiktok", "all"):
      t2fa_code, t2fa_out = run_tiktok_2fa_batch(dry_run=args.dry_run)
  ```
- Nạp đầy đủ cờ CLI chuẩn cho `run_batch_live_2fa.py`:
  - `--workbook-path "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx"`
  - `--workbook-sheet "Tài Khoản"`
  - `--adb-path "C:\Program Files (x86)\xiaowei\tools\adb.exe"`
  - `--live --max-workers 40`
  - Đặt `env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\kibe.yaml"`.
- Lưu state chi tiết: Lưu độc lập `gmail_status` và `2fa_status`; chỉ đánh dấu `last_success_date` khi 2FA hoàn tất hoặc toàn chuỗi thành công.

### 3.2. Triển khai Watchdog 2FA Ban Đêm Chuyên Biệt
- Tạo script: `C:\Users\Kibe\AppData\Local\hermes\scripts\cron_night_tiktok_2fa_watchdog.py`.
- Khung giờ hoạt động: **01:00 - 02:50** (trước ca dọn cache 03:00).
- Lên lịch cronjob: `night-tiktok-2fa-watchdog` với chu kỳ `*/10 1,2 * * *`.
- Tự động skip khi có feed runner hoặc máy có lock bận; tự động nhặt các nick trống pass / thiếu 2FA lên xử lý song song 40 workers.

---

## 4. Checklist Kiểm Chứng Định Kỳ
1. Chạy dry-run kiểm tra cả hai phase:
   `python C:\Users\Kibe\AppData\Local\hermes\scripts\post_noon_chain_watchdog.py --dry-run`
   -> Xác nhận stdout xuất hiện cả `Phase 1 (Reg Gmail)` và `Phase 2 (Add 2FA TikTok)`.
2. Kiểm tra độc lập Phase 2FA ban đêm:
   `python C:\Users\Kibe\AppData\Local\hermes\scripts\cron_night_tiktok_2fa_watchdog.py --dry-run`
   -> Xác nhận báo cáo `[BÁO CÁO 2FA TIKTOK BAN ĐÊM]`.
3. Kiểm tra unit test parser báo cáo:
   `pytest C:\Users\Kibe\AppData\Local\hermes\scripts\test_post_noon_watchdog_summary.py`
   -> 3 passed (100%).
