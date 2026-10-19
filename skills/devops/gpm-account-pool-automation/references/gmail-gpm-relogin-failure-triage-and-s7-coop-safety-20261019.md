# Gmail GPM Re-Login Failure Triage & S7 Co-op Safety (2026-10-19)

## 1. Bản Chất Vấn Đề
Khi tài khoản Gmail trên GPMLogin bị mất phiên đăng nhập (văng cookie / trạng thái `NEEDS_LOGIN`), cron nuôi định kỳ (`cron_gpm_gmail_nurture.py`) sẽ phát hiện và dừng nuôi để tránh lãng phí.
Tuy nhiên, trong số các tài khoản chờ đăng nhập lại, có những tài khoản script watchdog (`post_evening_gpm_login_watchdog.py` / `run_oauth_s7_pipeline.py`) **KHÔNG THỂ hoặc CHỦ ĐỘNG KHÔNG ĐƯỢC PHÉP tự động login lại**.

---

## 2. Phân Loại 3 Nhóm Nguyên Nhân Không Thể Re-Login Tự Động

### Nhóm 1: Khóa Cứng Do Dữ Liệu & Rủi Ro Checkpoint (`oauth_pipeline_status.json`)
Script chủ động phát hiện và đưa vào danh sách đen / từ chối thử để bảo vệ tài khoản:
1. **Sai Mật Khẩu (`WRONG_PASSWORD`):**
   - Mật khẩu lưu trong Excel (`master_gmail_manager.xlsx`) không khớp với thực tế của Google.
   - Script ghi nhận vào `wrong_password_or_checkpoint` và dừng ngay lập tức; cấm tuyệt đối brute-force thử lại vì Google sẽ khóa tài khoản vĩnh viễn.
2. **Google Đòi SMS Lạ (`SMS_CHECKPOINT`):**
   - Google yêu cầu nhập số điện thoại hoặc OTP SMS từ số lạ không nằm trong hệ thống farm (hoặc farm không có SIM vật lý tương ứng).
   - Script đánh dấu `SMS_CHECKPOINT` và bỏ qua. Cần can thiệp gán SIM hoặc xác minh thủ công.
3. **Email Khôi Phục Loại Trừ (`excluded_khoalee` / Blacklist):**
   - Tài khoản có email hoặc recovery chứa từ khóa bảo vệ (`khoale`, `khoalee`) hoặc nằm trong `antigravity_blacklist` bị chặn 100% không cho script tự động chạm vào.

---

### Nhóm 2: Tạm Khóa An Toàn Theo Cooldown
1. **Google Sensitive Action Cooldown 7 Ngày (`signin/rejected?rrk=77`):**
   - Khi Google phát hiện thao tác nhạy cảm (bật 2SV, đổi thông tin, đổi IP đột ngột), hệ thống bảo mật Google kích hoạt mã lỗi `rrk=77` yêu cầu chờ 7 ngày.
   - Script ghi nhận `cooldown_7days` với trường `retry_after`. Mọi nỗ lực login trước thời điểm này đều bị Google từ chối và làm tăng thêm thời gian phạt.
2. **Hạ Nhiệt IP reCAPTCHA Hình Ảnh (`ip_cooling_recaptcha`):**
   - Proxy bị dính reCAPTCHA hình ảnh phức tạp không giải tự động được bằng audio solver. Script cho IP nghỉ 24h-48h để hạ điểm rủi ro.

---

### Nhóm 3: Rào Cản Phối Hợp Phần Cứng S7 (Hardware Co-op Dependency)
Luồng login Gmail trên GPM Chromium (`run_oauth_s7_pipeline.py`) không chạy đơn lẻ trên PC mà **bắt buộc phải có máy điện thoại Samsung S7 tương ứng online ADB**:
- **Bấm xác nhận Google Prompt ("Yes, it's me"):** Script mở app hoặc bắt notification trên S7 để bấm số xác nhận.
- **Lấy mã bảo mật 10 chữ số (Google Security Code):** Script tự động mở `com.google.android.gms` -> Cài đặt Google -> Mã bảo mật trên S7 qua lệnh ADB và ATX.
- **Hiện tượng S7 Offline:** Nếu máy S7 bị tắt nguồn, lỏng cáp USB, treo ADB hoặc mất kết nối Wi-Fi, watchdog ghi nhận `serial not in online_serials` và buộc phải bỏ qua, chờ máy online trở lại mới thực hiện login.

---

### Nhóm 4: Điều Kiện Vận Hành & Khung Giờ Watchdog
1. **Khung Giờ Rảnh Giữa Các Ca Nuôi:**
   - Watchdog login Gmail (`post_evening_gpm_login_watchdog.py`) chỉ chạy trong 3 khung giờ rảnh:
     - Sáng: 09:30 – 11:20 (sau Ca 1 kết thúc lúc 09:25).
     - Chiều: 15:30 – 17:20 (sau Ca 2 kết thúc lúc 15:25).
     - Tối: 21:30 – 23:45 (sau Ca 3 kết thúc lúc 21:25).
   - Ngoài khung giờ này, watchdog tự động đóng để nhường tài nguyên USB và proxy cho ca nuôi feed TikTok/Gmail.
2. **Quy Tắc Miễn Trừ Proxy Limit Cho Re-Login:**
   - Tài khoản đăng nhập mới tuân thủ trần an toàn `MAX_LOGINS_PER_PROXY = 2` acc/proxy/ngày.
   - Riêng tài khoản bị văng session (`is_relogin = True`), watchdog cấp cờ miễn trừ để ưu tiên cứu sống session trong ca chạy sớm nhất có thể.
