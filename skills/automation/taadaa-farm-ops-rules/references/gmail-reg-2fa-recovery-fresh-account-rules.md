# Quy trình & Bài học thực tế: Reg Gmail, Bật 2FA & Check Live trên S7 Farm (2026-09-12)

## 1. Cơ chế Check Live Gmail
- **BẮT BUỘC dùng checkmail.live:**
  - Sử dụng Playwright headless với Chrome core 142 + mobile proxy `http://192.168.110.2:20001` (mobi1) theo chuẩn repo `site ban hang clone`.
  - **CẤM dựa vào on-device Google health check:** Ứng dụng Gmail Android không hiện thông báo lỗi khi tài khoản bị khóa ngầm/vô hiệu hóa từ máy chủ Google (vẫn hiển thị avatar và inbox bình thường).
  - Khi phát hiện `[die]` lúc lấy OTP trong flow TikTok Reg (`social_reg_v1.py`):
    1. Tự động xóa dòng mail khỏi `gmail_clean_v2.xlsx` (có backup timestamp).
    2. Đẩy thông tin cách ly vào sheet `Audit Pending`.
    3. Hủy flow ngay để đổi tài khoản khác.

## 2. Kỷ luật Reg Gmail (gmail_reg_v10.py)
- **CẤM đổi IP trước khi Reg:** Giữ nguyên IP proxy đang gán, không reset modem/recreate trước khi vào flow.
- **Quy tắc Pick máy chạy batch:**
  - BẮT BUỘC chọn các máy có **Mobile Proxy gán KHÁC NHAU** (15 máy trên 15 cổng proxy/IP khác nhau), triệt tiêu việc gửi dồn dập request từ cùng 1 IP.
  - **Cooldown tối thiểu 4 ngày (4d cooldown):** Kiểm tra ngày reg gần nhất trong `gmail_clean_v2.xlsx` cho từng máy. Máy vừa reg thành công (trong vòng 4 ngày) CẤM TUYỆT ĐỐI cho reg tiếp ngay trong ngày!
- **Tăng cường Entropy Họ tên & Username:**
  - Kết hợp ngẫu nhiên họ, tên đệm (1-2 chữ), tên chính, từ ngữ tự nhiên, đuôi từ khóa (`top`, `life`, `pro`, `plus`...) kèm salt 3–5 ký tự để tránh pattern bot.
- **Dọn dẹp Gmail DIE trước khi Reg:**
  - Trước khi máy vào flow reg mới, gọi `preflight_s7_rolling_cleanup` (hoặc module xóa tài khoản trên Android OS) để dọn sạch các tài khoản DIE đã đánh dấu trong `gmail_die_by_machine.json`, đảm bảo máy có < 5 tài khoản Google.
- **Lưu trữ Mật khẩu & Kết quả Reg:**
  - CẤM TUYỆT ĐỐI đoán mò hoặc tự tính toán password để điền vào Excel.
  - Phải tích hợp fallback `single_writer_workbook_update` trực tiếp vào `persist_success_result(acc)` trong `gmail_reg_v10.py` để khi chạy canary / lệnh lẻ không có `--result-dir` thì email + password + DOB vẫn được ghi thẳng vào `gmail_clean_v2.xlsx`.

## 3. Bản chất rào cản Bật 2FA / Thêm Email khôi phục trên Fresh Gmail
- **Thực nghiệm trên tài khoản vừa reg (Fresh Account):**
  - **Bật 2FA Google Authenticator:** Khi vào mục *Xác minh 2 bước* trên app Gmail hoặc web, Google yêu cầu xác minh danh tính. Khi nhập đúng mật khẩu vừa tạo, Google xoay 2s rồi **tự động reload lại đúng trang nhập mật khẩu (Loop Verification)** mà không báo lỗi đỏ, không cho qua.
  - **Thêm Email khôi phục:** Khi nhập đúng mật khẩu, Google không cho nhập mail khôi phục mà chuyển sang ép quay video selfie khuôn mặt (*"Lưu video selfie dùng để đăng nhập"*). Nếu bấm *"Để sau"*, Google redirect sang quảng cáo Google One rồi đẩy văng ra ngoài.
- **Nguyên nhân cốt lõi (Root Cause):**
  - Google áp đặt cơ chế phòng thủ **Fresh Account Security Hold / Anti-bot Cooldown** trong 24h–48h đầu sau khi tạo tài khoản trên điện thoại.
  - Mọi thao tác thay đổi cơ chế bảo mật cấp cao (2FA, recovery email) ngay sau khi vừa tạo đều bị xem là hành vi chiếm đoạt/bot automation và bị khóa loop.
- **Giải pháp chuẩn:**
  - Khi reg xong: **Lưu chắc chắn 100% Email + Pass vào Excel**, giữ tài khoản đăng nhập trên Android S7.
  - **Ngâm tài khoản từ 24h – 48h** trên thiết bị để phát sinh lịch sử đồng bộ (sync activity), hết cờ Fresh Account rồi mới kích hoạt luồng Bật 2FA hoặc nạp Recovery Email.
