# Meta / Muse AI Antidetect Registration Governance

## 1. Nguyên tắc cách ly môi trường tuyệt đối (Clean-State Invariant)
- **Cấm tái sử dụng Profile dính vết:** Khi một tài khoản đăng ký thử nghiệm (Meta, Muse AI, Claude, OpenAI) thất bại hoặc chuyển sang thử tài khoản mới, **BẮT BUỘC** phải tạo mới đồng thời cả **Profile GPM mới toanh** và **Proxy mới toanh**. Tuyệt đối không xóa cookie hay dùng lại profile/proxy cũ vì browser fingerprint, WebRTC và canvas hash đã bị server đánh dấu xấu.
- **Bám sát Geolocation người dùng chỉ định:** Nếu User yêu cầu vùng cụ thể (ví dụ: Canada), kiên định tìm và duy trì proxy/môi trường đúng quốc gia đó. Cấm tự ý quay xe về US vì tiện lợi.

## 2. Phòng chống đẩy việc & Tư duy tự động hóa (No-User-Steering)
- **Cấm đẩy việc cho User:** Khi gặp các bước cần tương tác (cài extension, click confirm, nộp selfie, đổi proxy), Coordinator phải chủ động dùng `computer_use` hoặc browser API tự làm trọn gói đến cùng. Tuyệt đối không gọi User vào click hộ ("gọi tao làm đéo gì", "tự làm nốt đi").
- **Bảo vệ tài khoản cá nhân:** Tuyệt đối không xúi User đăng nhập Facebook/Instagram cá nhân hoặc IP mạng gia đình vào các profile gắn proxy ngoại kẻo dính checkpoint khóa tài khoản oan.

## 3. Bản chất các chốt chặn Meta / Muse AI
- **Lỗi Waitlist (`muse.ai/access`):** Do dải IP Datacenter bị chặn early access. Cần dải Residential/Mobile IP hoặc IP sạch chưa bị blacklist.
- **Lỗi từ chối đăng ký (`login_registration_rejected_dialog_impression`):** Do sử dụng đuôi email tạm (`@fextemp.com`, tempmail). Meta chặn tạo user tại bước sinh tài khoản. Cần email thật (Gmail/Hotmail thật).
- **Lỗi xác minh tuổi (Age Verification / Selfie):** Meta dùng AI quét khuôn mặt. Có thể dùng ảnh chân dung người thật rõ ngũ quan, ánh sáng tốt, nhìn trên 18 tuổi trong kho ảnh farm để bypass.
- **Tài khoản clone giá rẻ:** Các nick mua rẻ (1k-2k) thường đã bị Meta quét quét đình chỉ diện rộng (`We suspended your account... associated with another account`). Cần kiểm tra session trước khi nạp vào flow liên kết.
