# Failure Evidence First Protocol & Freeze Screenshot

## 1. Bản chất vấn đề
Trong quá trình chạy automation hoặc xử lý lỗi farm Android:
- Khi một bước gặp lỗi (Timeout, Sai mã PIN, Lỗi OTP, Treo màn hình, Captcha, Webview trắng):
- Lỗi phổ biến nhất của Agent là: Chạy teardown/cleanup/force-stop/bấm HOME trước rồi mới gọi hàm chụp màn hình.
- Hậu quả: Bằng chứng lỗi bị xóa sổ, ảnh gửi qua Telegram trở thành ảnh màn hình HOME (launcher) vô nghĩa, khiến người vận hành không thể đối soát hiện trường.

## 2. Quy tắc bắt buộc: Freeze Before Teardown
1. **Rule #0 - Đóng băng hiện trường ngay lập tức:**
   - Ngay tại thời điểm phát hiện lỗi (hoặc bắt được Exception/False status):
   - **DỪNG NGAY MỌI THAO TÁC ADB KHÁC** (không back, không bấm HOME, không kill app).
   - Gọi `screencap -p` tại chỗ để lưu ảnh freeze screenshot.
   - Gửi ảnh qua `MEDIA:<path>` kèm mô tả chi tiết trạng thái lỗi.
   - **CHỈ SAU ĐÓ** mới được phép thực hiện teardown/cleanup hoặc đưa máy về HOME.

2. **Validation Gate trước khi gửi ảnh:**
   - Kiểm tra `dumpsys window | grep mCurrentFocus` hoặc UI XML.
   - `foreground_package` BẮT BUỘC phải là app xảy ra lỗi (ví dụ: `com.ss.android.ugc.trill`, `com.microsoft.office.outlook`, `com.google.android.gm`).
   - Nếu `foreground_package` là Launcher (`com.sec.android.app.launcher`): **CẤM TUYỆT ĐỐI GỬI LÀM ẢNH BẰNG CHỨNG LỖI**.
   - Ngoại lệ duy nhất: Khi app tự crash văng hoàn toàn khỏi bộ nhớ (`APP_CRASHED_AND_PROCESS_DEAD`), lúc này phải ghi rõ `NO_FOREGROUND_APP_AVAILABLE_AFTER_CRASH`.

## 3. Cú pháp & Format tin nhắn gửi ảnh lỗi
- Dòng đầu tiên BẮT BUỘC: `MEDIA:<đường dẫn tuyệt đối>`
- Dòng 2: `### [MÁY XX] - <Tên màn hình / Nhóm lỗi>`
- Dòng 3+: Stage, Error message, nguyên nhân kỹ thuật và đề xuất hướng giải quyết.
