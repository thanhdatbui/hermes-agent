# Post-Evening GPM Login Watchdog Operations & Report Semantics

Tài liệu vận hành và giải mã báo cáo của Watchdog tự động login Gmail lên GPMLogin ca đêm (`post-evening-gpm-login-watchdog`).

---

## 1. Thông tin Job & Lịch trình
- **Cronjob Name**: `post-evening-gpm-login-watchdog` (Job ID: `30ffbf1672e7`)
- **Lịch chạy**: `*/5 20,21,22,23 * * *` (mỗi 5 phút, mở từ 20:15 – 23:45 HCM sau khi ca 3 / avatar hoàn tất).
- **Script**: `C:/Users/Kibe/AppData/Local/hermes/scripts/post_evening_gpm_login_watchdog.py`
- **Target Pipeline**: Mở GPM Profile -> `run_oauth_s7_pipeline.py` -> Duyệt OTP/Security code trên S7 -> Nạp OmniRoute `20129`.
- **Concurrency**: 5 workers song song (stagger 5s).
- **Kênh thông báo**: Telegram Farm Alert (`-5373649734`).

---

## 2. Giải mã cú pháp Báo cáo Watchdog
Chuỗi báo cáo tiêu chuẩn:
```text
[LOGIN GPM ĐÊM - TỔNG KẾT] ✓ {success} | ✗ {fail} | proxy_limit 2/port/ngày | Hoàn tất ca tối
```
- **`✓ {success}`**: Số profile đăng nhập Google + lấy OAuth OmniRoute thành công.
- **`✗ {fail}`**: Số profile gặp lỗi (checkpoint, Google đổi pass, reCAPTCHA dính IP, v.v.). Hệ thống tự động ghi nhận vào `oauth_pipeline_status.json` để cooldown hoặc xử lý sau.
- **`proxy_limit 2/port/ngày`**: Rào chắn an toàn bảo vệ IP proxy 4G — mỗi port chỉ login tối đa 2 lần/ngày.
- **`Hoàn tất ca tối`**: Báo hiệu watchdog đã duyệt hết candidates hợp lệ hoặc đã chạm mốc kết thúc ca tối (23:30+). Watchdog chỉ báo đúng 1 lần duy nhất khi kết thúc ca, không spam từng đợt chạy lẻ.

---

## 3. Tiêu chí chọn Candidate (Watchdog Quét Vét, không phải Full Batch)
Watchdog này là tiến trình **quét vét** (idle scavenging), chỉ chọn các tài khoản thỏa mãn:
1. **Đã có profile GPM**: Đã tồn tại trong `profile_data.db` của GPMLogin (tránh lỗi `PROFILE_NOT_FOUND`).
2. **Chưa có trong `omniroute_success`**: Tránh trùng lặp tài khoản đã live.
3. **Thứ tự ưu tiên**:
   - Acc trong `cooldown_7days` đã hết hạn cooldown tính đến ngày hiện tại.
   - Acc LIVE trong `master_gmail_manager.xlsx` (Sheet `Kibe_Farm_S7`).
4. **Loại trừ tuyệt đối**:
   - Thuộc `excluded_khoalee` hoặc mail khôi phục chứa `khoale`.
   - Thuộc `wrong_password_or_checkpoint` hoặc `ip_cooling_recaptcha` chưa hết hạn.

---

## 4. Tại sao số lượng acc xử lý mỗi đêm thường ít (3 - 5 acc)?
Khi người dùng thắc mắc tại sao chỉ xử lý 5 acc hay vài acc:
- **Watchdog quét vét**: Không phải batch tạo mới toàn farm, chỉ xử lý những acc rớt lại / vừa hết cooldown.
- **Chạm trần Proxy (`MAX_LOGINS_PER_PROXY = 2`)**: Các phiên login ban ngày hoặc ca trước đã dùng hết quota 2 acc/port trên phần lớn các port proxy MobiProxy. Các acc còn lại thuộc các port này sẽ bị hoãn sang ngày hôm sau để bảo vệ proxy.
- **Giới hạn máy**: Mỗi máy S7 chỉ login tối đa 1 lần/ngày. Concurrency 5 workers song song.

---

## 5. Chẩn đoán khi kết quả [✓ 0 | ✗ N] (Tất cả Candidate đều Fail)
- **Triệu chứng**: Watchdog báo `[LOGIN GPM ĐÊM - TỔNG KẾT] ✓ 0 | ✗ N | proxy_limit 2/port/ngày | Hoàn tất ca tối`.
- **Nguyên nhân phổ biến nhất**:
  1. Hầu hết các tài khoản Gmail LIVE mới ngâm trên S7 chưa được cấp `2FA_Secret` (TOTP). Khi mở trên môi trường Chromium GPM (PC) mới toanh, Google đánh giá rủi ro và kích hoạt `challenge/iap` (đòi xác minh SMS SĐT).
  2. Fail-Safe ngắt ngay để tránh làm hỏng tài khoản Google, ghi nhận fail và chuyển sang candidate tiếp theo cho đến khi chạm hạn ngạch `proxy_limit 2/port/ngày`.
- **Hành động điều phối chuẩn (Không can thiệp bừa bãi)**:
  1. **Đêm hiện tại**: Giữ nguyên trạng thái `finished: true`, không cố tình retry làm hao tổn IP proxy.
  2. **Chu trình cuốn chiếu sáng hôm sau**: Chờ `post-morning-gmail-2fa-watchdog` (08:30 - 11:30) chạy `add-gmail-2fa` trên S7 (ADB mã bảo mật 10 số) để kích hoạt Google Authenticator và ghi TOTP Secret vào `master_gmail_manager.xlsx`.
  3. **Ca tối tiếp theo**: Các acc đã có TOTP Secret sẽ tự động điền mã 6 số qua `pyotp` để pass challenge trên PC một cách trơn tru.
