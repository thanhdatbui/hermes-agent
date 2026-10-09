# ChatGPT Linking Failures on Android 8 (Galaxy S7): Post-Noon Chain Watchdog Triage & Runbook (2026-09-24)

## Bối cảnh & Hiện tượng
Trong ca chạy song song `Reg Gmail -> Add 2FA TikTok` (15:15 -> 15:51 ngày 23/09/2026), Phase 1 ghi nhận `ChatGPT linked: 0/8 (8 fail)` mặc dù cả 8 Gmail đều đăng ký thành công và Live 100%.

Qua phân tích và debug bóc tách frame thực tế trên các máy S7 rảnh rỗi (Máy 16, 22, 24), đã phát hiện chuỗi 5 lỗi liên hoàn gây fail 100%.

---

## 1. Các Nguyên Nhân Kỹ Thuật Cốt Lõi

### A. Bẫy Gom Chuỗi Thư (Thread Grouping) của Gmail & `max_check_attempts` của OpenAI
- **Hiện tượng**: Nhập mã OTP vào Chrome báo đỏ `Mã không chính xác`, sau 3 lần thì bị OpenAI khóa:
  `error_code: max_check_attempts` (*Bạn đã thử quá nhiều lần. Vui lòng đợi vài phút rồi thử lại*), làm phiên đăng ký bị đóng băng 15–30 phút.
- **Cơ chế**:
  - Farm tắt Auto-Sync ngầm để tiết kiệm pin/RAM. Khi mở Gmail, thư mới từ OpenAI chưa được kéo về ngay.
  - Gmail tự động gom các email xác nhận OpenAI thành 1 luồng hội thoại (`thread`).
  - Snippet hoặc regex quét thô toàn bộ XML sẽ bắt trúng mã OTP của **thư cũ** nằm trong thread.
- **Khắc phục**:
  - Vuốt kéo làm mới Inbox ở vùng an toàn không vướng banner: `swipe 540 1350 540 1800 400` và chờ 2–3s.
  - Phân tích XML theo thứ tự phân cấp cây DOM (ElementTree): duyệt từ trên xuống dưới, chỉ lấy mã OTP tại node xuất hiện đầu tiên trên đỉnh Inbox.

### B. Chính Sách Mật Khẩu Mới của OpenAI: Bắt Buộc $\ge$ 12 Ký Tự
- **Hiện tượng**: Tại màn hình `Tạo mật khẩu` (`auth.openai.com/create-account/password`), hệ thống báo đỏ:
  `X Ít nhất 12 ký tự` và vô hiệu hóa nút Tiếp tục.
- **Cơ chế**: OpenAI áp dụng chính sách bảo mật mới yêu cầu độ dài tối thiểu 12 ký tự. Các mật khẩu tạo Gmail tự động trên farm trước đây thường dài 10–11 ký tự (vd: `Dao$Zone608` [11 ký tự], `Win44@Tra7` [10 ký tự]).
- **Khắc phục**:
  - Trước khi gửi mật khẩu sang form OpenAI:
    ```python
    pw_to_type = password
    if len(pw_to_type) < 12:
        pw_to_type = f"{pw_to_type}@2026"
    ```
  - Điền vào ô mật khẩu `(540, 1328)`, ẩn bàn phím bằng `keyevent 4` rồi tap `Tiếp tục` tại `(540, 1814)`.

### C. Bàn Phím Ảo Samsung Đẩy Nút Tiếp Tục & Bẫy Chữ `g`
- **Hiện tượng**: Email nhập vào form bị dính đuôi chữ `g` (vd: `letai.top190173@gmail.comg`) hoặc không chuyển trang sau khi submit email.
- **Cơ chế**:
  - Khi focus vào ô nhập email, bàn phím ảo Samsung chiếm 1/2 dưới màn hình, đẩy nút `Tiếp tục` lên tọa độ `(540, 762)`.
  - Code cũ tap tọa độ cố định `(540, 1504)` dẫn tới **tap trúng vào phím chữ `g`** trên bàn phím ảo.
- **Khắc phục**:
  - Khi bàn phím ảo đang mở, tap nút `Tiếp tục` tại `(540, 762)` và gửi phím Enter `keyevent 66`.
  - Tuyệt đối CẤM tap vùng Y > 1000 khi bàn phím ảo đang hiển thị.

### D. Kẹt Màn Hình Tìm Kiếm Thư (Search Mode) trong Gmail
- **Hiện tượng**: Mở app Gmail nhưng bị kẹt ở giao diện tìm kiếm thư có nút `Quay lại`, `Tệp đính kèm`, `Xoá văn bản`. Script timeout 90s không tìm thấy thư OTP.
- **Cơ chế**: Phiên trước đó để lại trạng thái focus ô search. Bấm 1 lần Back chỉ ẩn bàn phím ảo mà chưa thoát về Inbox.
- **Khắc phục**:
  - Gửi 2 lần liên tiếp phím Back (`keyevent 4` cách nhau 0.5s) để vừa đóng bàn phím vừa trở về Inbox chính.

### E. Nút FAB "Soạn Thư" Bị Nhận Nhầm Thành Màn Hình Compose
- **Hiện tượng**: Script vừa mở Gmail là tự bấm Back thoát ngược lại Chrome ngay lập tức.
- **Cơ chế**: Nút tròn tạo thư mới ở góc dưới Inbox có nhãn `Soạn thư`. Điều kiện cũ `if "Soạn thư" in xml: press Back` nhận diện nhầm nút này là đang soạn thư dở.
- **Khắc phục**: Chỉ coi là màn hình Soạn thư khi có các trường nhập liệu cụ thể: `"compose_area" in xml or ("Chủ đề" in xml and "Đến" in xml) or "Soạn email" in xml`.

---

## 2. Quy Trình Chạy Canary Chuẩn Nghiệm Thu
Chạy trực tiếp qua `DeviceContext` với máy rảnh:
```bash
"D:/Taadaa/python-envs/automation/Scripts/python.exe" -c "
import sys, time
sys.path.insert(0, r'D:/Taadaa/automation-core/src')
sys.path.insert(0, r'D:/Taadaa/register gmail')
sys.path.insert(0, r'D:/Taadaa/register gmail/scripts')
from automation_core.device_lock import DeviceContext
from hook_chatgpt_register import register_chatgpt_on_device
from gmail_reg_v10 import shell

serial = '<SERIAL>'
machine_id = <N>

shell(serial, 'am', 'force-stop', 'com.android.chrome')
shell(serial, 'am', 'force-stop', 'com.google.android.gm')
time.sleep(1.0)

with DeviceContext(serial=serial, machine=machine_id, project='canary_chatgpt', user_authorized=True):
    res = register_chatgpt_on_device(
        device_id=serial,
        email='<EMAIL>',
        password='<PASSWORD>',
        dob='<DOB>',
        timeout=240,
        check_live=False
    )
    print('CANARY_RESULT:', res)
"
```
