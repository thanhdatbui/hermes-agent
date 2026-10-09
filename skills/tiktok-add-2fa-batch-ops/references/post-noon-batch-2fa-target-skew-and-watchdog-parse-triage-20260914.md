# Post-Noon Batch 2FA: Target Skew, Time Budget, and Watchdog Parsing Triage (14/09/2026)

## Hiện tượng thực tế
- Watchdog chuỗi sau ca trưa (`post_noon_chain_watchdog.py`) chạy trong 22 phút (15:06 -> 15:28) nhưng gửi báo cáo Telegram:
  `Phase 1 (Reg Gmail - Code 1): Tổng máy: 0, Success (0), Fail (0)`
  `Phase 2 (Add 2FA TikTok - Code 4): Tổng máy: 0, Success (0), Fail (0)`
- User thắc mắc: *"Lại lỗi hoài thế"*, *"Mà sao bật 2fa 40 máy mà thành công có 1"*.
- Dữ liệu thực tế đối soát từ Excel và runtime logs:
  + Reg Gmail: **13/15 máy SUCCESS** (`M7, M8, M9, M10, M17, M23, M28, M42, M44, M48, M55, M64, M68`), 2 máy fail (M03, M69). Đã lưu vào `gmail_clean_v2.xlsx` lúc 15:20.
  + TikTok 2FA: Đã bật 2FA thành công và ghi mã secret cho **Máy 18 (Row 139)** vào `taikhoan_dat_v2_updated .xlsx` lúc 15:26.

---

## 1. Root Cause 1: Bug Regex Parse Trong Watchdog (False Zero Reporting)
- **Cơ chế lỗi:** `parse_summary_counts(output)` tìm cứng regex `TOTAL=(\d+)\s+SUCCESS=(\d+)\s+FAILED=(\d+)` hoặc pattern `Machine\s+\d+.*(?:SUCCESS|OK)`.
- **Thực tế output của 2 runner:**
  1. `run_batch_live_2fa.py`: In bảng stdout dạng:
     `{machine} | {source_row} | {username} | {status} | {reason}`
     Trạng thái là chữ thường (`success`, `skipped`, `failed`), không có từ "Machine" và không có chuỗi "TOTAL=". Regex trượt 100% về `(0, 0, 0)`.
  2. `run_all.ps1` (Reg Gmail): Khi có 2 máy fail, script PowerShell thoát với exit code 1 (`if ($fail -gt 0) exit 1`). File `summary.json` do PowerShell ghi ra chứa ký tự UTF-8 BOM (`\xef\xbb\xbf`), nếu hàm đọc dùng `utf-8` thông thường sẽ văng `json.decoder.JSONDecodeError`.
- **Bản vá đã triển khai:**
  - Nâng cấp `parse_summary_counts` bóc tách trực tiếp bảng `{machine} | {source_row} | {username} | {status} | {reason}` của TikTok 2FA, bắt chữ thường `success`/`skipped`/`failed` và tính `tot = succs + fails + skips`.
  - Bổ sung fallback đọc `summary.json` với encoding `utf-8-sig` từ thư mục runtime `D:/CodexRuntime/codex_gmail_debug-register-gmail/logs_parallel_*/`.

---

## 2. Root Cause 2: Vì Sao 40 Máy 2FA Chỉ Có 1 Máy Thành Công?
- **Độ lệch mục tiêu (Target Skew - 30/40 máy đã có 2FA):**
  + Trong logic `freeze_targets()`:
    ```python
    has_2fa = bool(_clean(values[two_fa_col - 1]))
    needs_pwd = password_needs_rotation(pwd_val)
    if has_2fa and not needs_pwd:
        continue
    pw_only = has_2fa and needs_pwd
    ```
  + Trong 40 máy được chọn: **30 máy đã có sẵn 2FA từ trước**, script kéo vào chỉ để chạy luồng phụ `--password-only` (kiểm tra xoay mật khẩu legacy sang mật khẩu mạnh). **Chỉ có 10 máy là nick mới thực sự chưa có 2FA!**
- **Nghẽn khung giờ & Concurrency:**
  + Tổng chuỗi watchdog chạy 22 phút (15:06 -> 15:28).
  + Phase 1 (Reg Gmail) đã ngốn 14 phút (15:06 -> 15:20).
  + Phase 2 (TikTok 2FA) chỉ bắt đầu lúc 15:21 và kết thúc lúc 15:28 ➔ **Chỉ có đúng ~7 phút thực tế**.
  + Mỗi máy chạy 2FA (mở TikTok, switch nick, vào Cài đặt, đọc OTP qua app Gmail/Outlook trên máy, nhập OTP, lưu Excel) mất từ 3 đến 5 phút.
  + Với `--max-workers 10` kèm delay ngắt quãng 2-8s giữa các máy, trong 7 phút hệ thống chỉ kịp xử lý dứt điểm 1-2 máy trước khi timeout ca trưa.
- **Kẹt OTP mail & Captcha:**
  + Một số máy gặp tình trạng app Gmail/Outlook trên thiết bị lag chưa đồng bộ thư mới kịp thời.
  + Một số nick bị TikTok văng puzzle captcha hoặc yêu cầu xác nhận mật khẩu cũ trước khi mở màn hình cấp khóa Authenticator.

---

## 3. Quy Tắc Vận Hành Đề Xuất
1. **Tách riêng batch 2FA mới khỏi batch rotate pass:** Khi chạy chuỗi sau ca trưa, ưu tiên cờ lọc các nick `has_2fa == False`, không để 30 nick `--password-only` chiếm hết quota 40 slot và tranh chấp worker pool với các nick mới.
2. **Co hẹp batch size theo khung giờ:** Với khung giờ nghỉ trưa (~20-30 phút), chỉ nên gom từ 10 đến 15 target thực sự cần 2FA để 10 workers tập trung hoàn thành dứt điểm, tránh dàn trải 40 máy gây dồn toa.
