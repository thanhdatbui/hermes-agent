# Kỷ Luật Chống Tê Liệt Điều Phối & Quy Trình Khôi Phục Phiên TikTok

## 1. Hiện Tượng Tê Liệt & Phản Ứng Của User (User Incident 2026-10-04)
- **Tình huống**: Máy M3 báo động P0 `ACCOUNT_SWITCHER_FAILED: expected account was not found (@annhubvqttr)`. Khi User ra lệnh dứt khoát *"Làm đi"*, Agent Coordinator thay vì thực thi ngay lại bị vướng các chốt chặn và quay sang hỏi `clarify` ("Sếp muốn xử lý theo hướng nào?"), khiến User bức xúc: *"Sửa guard ngu lồn cho tao"*.
- **Nguyên tắc tối cao**: 
  - Khi User đã phát lệnh hành động ("Làm đi", "Chạy đi", "Fix đi"), Coordinator BẮT BUỘC tự chủ động xử lý tới cùng (L0 -> L1 -> L2) hoặc báo BLOCKED kèm bằng chứng thật.
  - CẤM TUYỆT ĐỐI dùng `clarify` để hỏi xin phép, hỏi "có nên tiếp tục không", hoặc né tránh rào cản kỹ thuật.

---

## 2. Các Bẫy Lỗi Trong Bộ Lọc An Toàn Điều Phối & Cách Khắc Phục

### Bẫy 1: Regex Missing Colon `:` Chặn Tuyệt Đối Đường Dẫn Windows
- **Triệu chứng**: Chạy `python D:/Taadaa/tools/recover_missing_tiktok_login.py` bị chặn bởi nhánh `DEFAULT-DENY`.
- **Nguyên nhân**: Trong allowlist terminal, regex cho phép file python là `[\w\-/\\]+\.py\b`. Do thiếu dấu `:` (colon) và `.` (dot) trong character class, đường dẫn ổ đĩa tuyệt đối `D:/...` không thể match và bị chặn.
- **Chuẩn hóa Regex**:
  ```python
  r"^(?:python(?:\.exe)?\s+(?:-m\s+pytest\b|[a-zA-Z]:[/\\][\w\-/:\\\.]+\.py\b|[\w\-/:\\\.]+\.py\b)|pytest(?:\.exe)?\b)"
  ```

### Bẫy 2: Chặn Nhầm Mã Phần Cứng `input keyevent` Trong ADB
- **Triệu chứng**: Chạy `adb shell input keyevent 224` (bật sáng màn hình) hoặc `keyevent 82` (mở khóa) bị chặn nhầm.
- **Nguyên nhân**: Regex kiểm tra ADB bị gom nhầm: `re.search(r"\binput\s+(?:tap|swipe|keyevent)\b")`.
- **Khắc phục**: Keyevent là mã điều khiển trạng thái phần cứng (224=Wake, 82=Unlock, 3=Home, 4=Back), an toàn và bắt buộc cho tự động hóa. Bộ lọc CHỈ ĐƯỢC chặn bấm tay bypass:
  ```python
  if re.search(r"\binput\s+(?:tap|swipe)\b", c_strip, re.IGNORECASE):
      return False, "CẤM TUYỆT ĐỐI 'adb shell input tap/swipe' bấm tay thay cho sửa code!"
  ```

### Bẫy 3: Quét Chuỗi Bảo Vệ Quá Đà Gây Liệt Đọc Cache/Logs
- **Triệu chứng**: Thao tác `delegate_task` hoặc `read_file` các file cache kết quả bị chặn vô điều kiện.
- **Khắc phục**:
  1. Loại bỏ kiểm tra bao quát thư mục dữ liệu cục bộ.
  2. Rào chắn bảo vệ chỉ áp dụng cho thao tác GHI (`write_file`, `patch`) hoặc lệnh shell tác động trực tiếp vào file bảo vệ, KHÔNG chặn thao tác ĐỌC cache/logs hoặc tham số ngữ cảnh `delegate_task`.

### Bẫy 4: Worker Bị Khóa Chặt Không Thể Chạy Tool Khôi Phục
- **Khắc phục**: Mở rộng allowlist terminal cho Worker: Cho phép thực thi tất cả các script python hợp lệ nằm trong `D:\Taadaa\tools\` (`expected_dir = r"D:\Taadaa\tools"`).

---

## 3. Quy Trình Khôi Phục Phiên Đăng Nhập TikTok (TikTok Login Recovery)

### Bước 1: Khử Nhiễm Biến Môi Trường `PYTHONPATH`
- Trước khi kích hoạt `tiktok_login_v1.py` từ caller/runner subprocess, bắt buộc loại bỏ `PYTHONPATH` để tránh xung đột thư viện `greenlet`/`playwright` của runtime cha gây lỗi ngộ nhận Gmail `DIE`:
  ```python
  env = os.environ.copy()
  env.pop("PYTHONPATH", None)
  ```

### Bước 2: Thiết Lập Timeout Thích Hợp Cho Thiết Bị Galaxy S7
- Dòng máy Galaxy S7 (2016) có độ trễ phần cứng:
  - Check live Gmail: ~50 giây.
  - Khởi động app TikTok & nạp splash: 30 - 45 giây.
  - UI XML dump & cuộn tìm Account Switcher: 2 - 3 phút.
  - Xử lý xác thực OTP / 2FA TOTP: 1 - 2 phút.
- **Quy chuẩn**: Tổng timeout cho lệnh recovery phải đặt tối thiểu **600 giây (10 phút)**. Dùng `timeout=300s` sẽ bị `TimeoutExpired` khi app đang ở giữa chừng bước xác thực.

### Bước 3: Tận Dụng Cờ `--resume` Khi Màn Hình Đã Mở Sẵn
- Khi app TikTok trên máy đã mở sẵn (Profile hoặc Login modal), luôn truyền cờ `--resume`:
  ```bash
  python D:/Taadaa/tools/recover_missing_tiktok_login.py --machine <N> --account <ID> --resume
  ```
- Script sẽ bỏ qua bước mở app từ đầu, nhận diện ngay form đăng nhập hiện tại và điền credentials, rút ngắn thời gian xử lý xuống dưới 2 phút.
