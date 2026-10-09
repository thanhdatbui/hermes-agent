# Giải thích chi tiết cơ chế reCAPTCHA Fail-Fast trong đăng ký Gmail và liên kết ChatGPT

## 1. Bản chất & Định nghĩa
reCAPTCHA Fail-Fast là cơ chế phòng thủ chủ động của hệ thống automation trên Phone Farm Taadaa:
- Ngay khi phát hiện các dấu hiệu Google reCAPTCHA hoặc thử thách xác minh danh tính người máy trên thiết bị Android S7, hệ thống lập tức **dừng khẩn cấp trong <= 0.5 giây**, chụp ảnh màn hình lưu vết hiện trường và trả về trạng thái thất bại được phân loại rõ ràng (`FAILED_AT_GOOGLE_RECAPTCHA`), đóng trình duyệt và đưa thiết bị về màn hình chính (HOME).
- **Nguyên tắc cốt lõi**: "Thấy captcha là dừng ngay, tuyệt đối không cố đấm ăn xôi, không thử lại liên tục".

## 2. Nguy cơ khi không có Fail-Fast (Fail-Slow & Blind Retries)
- **Tài khoản bị gắn cờ bot dẫn đến DIE vĩnh viễn**:
  - Khi Google đưa ra reCAPTCHA, nếu script tự động không nhận biết mà tiếp tục chờ hết timeout (3-5 phút) hoặc tiếp tục gửi lệnh tap mù quáng vào các tọa độ cố định, hệ thống AI chống gian lận của Google sẽ ghi nhận đây là hành vi spam bot thô bạo.
  - Hậu quả: Tài khoản Gmail non trẻ vừa đăng ký sẽ bị Google nâng cấp mức phạt từ "Yêu cầu xác minh danh tính" lên thẳng "Tài khoản bị vô hiệu hóa" (DISABLED / DIE 100%).
- **Làm kẹt nghẽn tài nguyên Phone Farm**:
  - Nếu mỗi máy dính captcha phải chờ timeout 3-5 phút, một batch 15-40 máy sẽ bị kéo dài thêm hàng giờ đồng hồ, làm trễ toàn bộ chuỗi công việc kế tiếp (nuôi feed, đăng video, bật 2FA).

## 3. Các từ khóa nhận diện reCAPTCHA (Song ngữ)
Trong mã nguồn `scripts/hook_chatgpt_register.py`, bộ lọc phát hiện reCAPTCHA quét cả hai ngôn ngữ tiếng Việt và tiếng Anh:
- `"Xác minh danh tính"`
- `"reCAPTCHA"`
- `"Tôi không phải là người máy"`
- `"Verify it's you"`
- `"Xác nhận bạn không phải là rô-bốt"`
- `"I'm not a robot"`

## 4. Contract trả về chuẩn
```python
{
    "success": False,
    "status": "FAILED_AT_GOOGLE_RECAPTCHA",
    "reason_code": "RECAPTCHA_TRIGGERED",
    "email": email_clean,
    "step_timings": step_timings,
    "trace_id": trace_id,
    "message": "Google yêu cầu reCAPTCHA danh tính"
}
```

## 5. Giá trị vận hành thực tế
1. **Bảo vệ mạng sống cho Gmail (Save Account Life)**: Dừng ngay khi dính captcha giúp tài khoản giữ nguyên trạng thái LIVE trên máy S7. Khi đổi dải IP 4G sạch hoặc để tài khoản ngâm tĩnh 24h-48h, tài khoản vẫn sử dụng bình thường mà không bị xóa sổ.
2. **Nhả slot tức thì cho batch runner**: Chuỗi đăng ký giải phóng thiết bị ngay sau vài giây, cho phép các máy tiếp theo tiếp tục chạy mà không gây nghẽn hàng đợi farm.
