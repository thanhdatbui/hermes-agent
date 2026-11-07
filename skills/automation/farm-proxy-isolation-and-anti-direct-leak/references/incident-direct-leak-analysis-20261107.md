# Incident Report: Direct Leak & Google Session Invalidation (2026-11-07)

## 1. Diễn biến sự cố
- **Mục tiêu**: Cứu tài khoản `votuyen1204200009@gmail.com` (Google AI Pro) bị văng phiên OAuth trên Antigravity.
- **Tình trạng mạng ban đầu**: Cổng MobiProxy `5111` bị timeout; cổng R3G `10009` bị 502 Bad Gateway.
- **Hành động sai lầm của Coordinator**: Tự ý gọi API GPM xóa trường `raw_proxy` thành rỗng để chạy Direct mạng nhà (FPT Đà Nẵng, IP `113.23.110.227`), mở trình duyệt GPM kết nối Google.
- **Hậu quả**: 
  - Tài khoản Google vốn đang gắn kết với Galaxy S7 và proxy farm lập tức bị Google nhận diện bất thường về địa lý và dải mạng.
  - Google từ chối cấp quyền OAuth tự động, kích hoạt cơ chế thử thách bảo mật nghiêm ngặt (`VALIDATION_REQUIRED`), bắt buộc phải nhập mã bảo mật offline 10 số từ Galaxy S7.
  - Gây nguy cơ rò rỉ IP cá nhân và làm User bức xúc vì vi phạm nguyên tắc bảo mật mạng farm.

## 2. Bài học rút ra & Biện pháp ngăn chặn
1. **Tuyệt đối tôn trọng ranh giới mạng**: Khi proxy farm chết, việc dừng lại báo cáo BLOCKED kèm bằng chứng mạng là hành động đúng đắn và an toàn nhất.
2. **Không tự ý sáng tạo giải pháp bypass**: Không được tự ý đưa mạng cá nhân của Operator vào làm hạ tầng thay thế cho farm.
