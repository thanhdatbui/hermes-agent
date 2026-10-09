# Phân Tích & Invariant Protocols Xử Lý Lỗi Báo Cáo Sai Lệch So Với Bằng Chứng Hiện Trường

## 1. Bản Chất Kỹ Thuật Khiến AI Agent "Báo Cáo Láo" Dù Ảnh Thể Hiện Khác
- **Prior Probability Override (Thiên lệch dữ liệu mẫu có sẵn)**: Trong bài toán browser automation, các sự cố kẹt thường gặp nhất là timeout proxy, rớt mạng, Chromium treo. Model có xu hướng tự động kích hoạt lời giải thích này mà bỏ qua việc trích xuất chữ thực tế trên ảnh.
- **Lazy Vision / Plausibility Bias**: Model chọn giải thích "nghe có vẻ hợp lý và chuyên nghiệp" (như *nghẽn kết nối do nhiều worker chạy cùng lúc*) thay vì đọc chi tiết các dòng chữ tiếng Việt trên màn hình xác minh của Google.
- **Thiếu Invariant Evidence Chain**: Báo cáo không có bước bắt buộc trích xuất OCR nguyên văn (verbatim quote) dẫn tới việc kết luận tách rời hoàn toàn khỏi bằng chứng.

## 2. Invariant Evidence Protocol (Kỷ Luật Thép Khi Báo Cáo Lỗi UI)
Mọi báo cáo chẩn đoán sự cố dựa trên ảnh chụp màn hình BẮT BUỘC tuân thủ:

1. **Zero Assumption**: CẤM đưa ra giả định nguyên nhân (mạng, proxy, CPU, timeout...) khi chưa hoàn thành bước trích xuất text OCR từ ảnh.
2. **Mandatory OCR / Verbatim Extraction**:
   - Sử dụng tool OCR native (`windows-native-ocr` qua script `winrt_ocr.py`).
   - Báo cáo bắt buộc có block trích dẫn:
     ```
     [EVIDENCE – OCR EXTRACT]
     - Nguồn: <path screenshot>
     - Nội dung thực: "<trích dẫn nguyên văn ≥1 dòng text từ OCR>"
     - UI State: <mô tả nút/input chính>
     ```
3. **Contradiction Circuit Breaker**: Tự đối chiếu kết luận với text OCR. Nếu kết luận mâu thuẫn với nội dung thực tế (ví dụ: ảnh thể hiện đòi SĐT mà báo cáo là rớt mạng), lập tức hủy bỏ kết luận cũ, kích hoạt Circuit Breaker và viết lại trung thực theo chữ trên ảnh.

## 3. Quy Tắc Xử Lý Xác Minh Google SĐT Đuôi 24 Của Tad (0906746624)
- **Định danh**: SĐT đuôi `24` là số cá nhân của **Tad** (user): `0906746624`.
- **Quy trình xác nhận & lấy OTP**:
  1. Khi Google yêu cầu xác nhận số điện thoại trước khi gửi mã: script điền `0906746624` vào `input#phoneNumberId, input[name="phoneNumber"]` và bấm "Gửi".
  2. Sau khi gửi: **DỪNG automation, gửi thông báo gọi Tad để lấy mã OTP 6 số**, CẤM cố chạy lại tự động.
  3. Ghi trạng thái chờ vào `C:\Users\Kibe\waiting_otp.json` và polling nhận mã từ `C:\Users\Kibe\otp_code.txt`.
- **Selector Collision Trap**:
  - TUYỆT ĐỐI KHÔNG dùng `input[type="tel"]` cho ô xác nhận số điện thoại, vì màn hình kế tiếp nhập mã OTP 6 số cũng có thể là `type="tel"`, dẫn đến script lặp vô tận việc điền số điện thoại vào ô OTP và kích hoạt Rate-Limit.
- **Xử lý khi bị Rate-Limit**:
  - Nếu OCR phát hiện: *"Không khả dụng vì bạn đã thử quá nhiều lần. Vui lòng thử lại sau"*, Google đã rate-limit SMS/Call của số này.
  - BẮT BUỘC đưa tài khoản vào `cooldown_7days` để ngâm hạ nhiệt 24-48h, CẤM cố retry tự động.
- **Đường dẫn ảnh nghiệm thu gửi Telegram**:
  - Khi gửi ảnh qua cú pháp `MEDIA:<path>`, luôn copy ảnh ra thư mục phẳng không chứa khoảng trắng (ví dụ `C:/Users/Kibe/<name>.png`), tránh dùng đường dẫn chứa space như `D:/Taadaa/GPM auto/...` khiến Telegram client không parse và tải được ảnh.
