# Quy tắc Kỷ luật Proxy/IP: Phân loại Lỗi Nền Tảng vs Lỗi Script trong Login / Reg / Ver / OAuth

## 1. Bối cảnh & Nguyên lý Cốt lõi
Khi tự động hóa các tác vụ nhạy cảm với nhận diện rủi ro (Fraud / Abuse Detection) như **Login Gmail/TikTok**, **Đăng ký tài khoản (Reg)**, **Xác minh 2FA/OTP (Ver)**, hoặc **Nạp OAuth SSO**:
- Mỗi cổng Proxy / IP cố định trên Farm (MobiProxy 4G hoặc MikroTik) chỉ được phép gán tối đa theo hạn mức an toàn trong ngày (ví dụ: 1 acc/IP/ngày hoặc 2 acc/IP/ngày).
- Tuy nhiên, nếu áp dụng cứng nhắc "cứ fail là trừ quota" hoặc "cứ fail là thử lại bất chấp", hệ thống sẽ rơi vào 2 thảm họa:
  1. **Thảm họa lây nhiễm Checkpoint (Chết chùm)**: IP vừa bị Google / TikTok bật cờ nghi vấn (bắt captcha/SĐT), script lại tiếp tục nhồi nick khác vào IP đó ➔ Tất cả các nick sau đều bị khóa / dính checkpoint.
  2. **Thảm họa lãng phí tài nguyên**: Script bị lỗi nội bộ (thiếu password trong Excel, crash cục bộ trước khi mở web) nhưng lại tính đã dùng IP ➔ Cổng proxy sạch bị vứt bỏ cả ngày vô ích.

---

## 2. Bảng Phân loại Chi tiết: Lỗi Nền Tảng vs Lỗi Script

| Tiêu chí | Lỗi NỀN TẢNG (Platform Error) | Lỗi SCRIPT / MÔI TRƯỜNG (Script Error) |
| :--- | :--- | :--- |
| **Bản chất** | Xảy ra từ phía server nền tảng (Google, TikTok, Hotmail). IP đã bị nền tảng nhận diện và đánh giá rủi ro. | Xảy ra trước khi tương tác trọn vẹn với nền tảng, hoặc do thiếu sót dữ liệu/code nội bộ. IP chưa bị vấy bẩn. |
| **Dấu hiệu nhận biết** | - reCAPTCHA / hCaptcha / Arkose challenge.<br>- Checkpoint yêu cầu SĐT (`challenge/iap`, `selection`).<br>- Thông báo từ chối truy cập / Trình duyệt không an toàn (`rejected`).<br>- Mật khẩu sai hoặc tài khoản bị vô hiệu hóa (`BLOCKED_WRONG_PASSWORD`).<br>- Rate limit / 429 từ phía server nền tảng. | - Thiếu password / 2FA trong Excel/DB (`MISSING_PASSWORD`).<br>- Tự động skip theo rule lọc an toàn nội bộ (như `khoaleemagic`).<br>- GPM API timeout / không start được profile (`START_FAILED`).<br>- Playwright / CDP disconnect trước khi tải trang.<br>- Mất kết nối socket nội bộ tới proxy port. |
| **Xử lý Quota IP** | **TÍNH 1 LƯỢT DÙNG (TƯƠNG ĐƯƠNG SUCCESS)**.<br>👉 **Khóa IP/Port đó ngay lập tức** đến 00:00 hôm sau để cách ly, bảo vệ tuyệt đối cho các nick khác. | **KHÔNG TÍNH VÀO QUOTA IP**.<br>👉 **Giữ nguyên lượt dùng của IP**, cho phép IP đó được thử lại với tài khoản/profile khác trong ngày. |
| **Xử lý Tài khoản** | Đưa vào danh sách chờ cooldown (ví dụ: `cooldown_7days` hoặc `wrong_password_or_checkpoint`). | Đưa vào danh sách `failed_script_emails` trong ngày để không retry lặp vô tận cùng một nick lỗi dữ liệu. |

---

## 3. Pattern triển khai chuẩn (Python Template)

```python
# Phân loại trong worker
if is_success:
    record_result(email, status="SUCCESS", proxy_port=port, fail_type="NONE")
    consume_proxy_quota(port)
elif is_platform_error:
    # Lỗi do nền tảng: reCAPTCHA, Phone Checkpoint, Sai pass...
    record_result(email, status="PLATFORM_FAIL", proxy_port=port, fail_type="PLATFORM", reason=err_msg)
    consume_proxy_quota(port)  # Khóa IP để bảo vệ dàn nick
else:
    # Lỗi do script: Thiếu password trong Excel, GPM API start fail...
    record_result(email, status="SCRIPT_FAIL", proxy_port=port, fail_type="SCRIPT", reason=err_msg)
    mark_email_script_failed_today(email)
    # KHÔNG gọi consume_proxy_quota(port) -> IP vẫn mở cho profile khác
```

---

## 4. Chuẩn mực Báo cáo 6h (Reporting Standard)
Báo cáo định kỳ mỗi 6h về các tác vụ Login / OAuth Pool bắt buộc phải tách biệt minh bạch:
1. **✓ Thành công**: Số lượng acc nạp/login thành công kèm Port.
2. **🛑 Lỗi nền tảng (Đã khóa IP an toàn)**: Số lượng acc + lý do cụ thể (bảo vệ dàn nick).
3. **⚠️ Lỗi script / nội bộ (IP được giữ lại)**: Số lượng acc + lý do (thiếu pass, crash tool, skip khoale).
