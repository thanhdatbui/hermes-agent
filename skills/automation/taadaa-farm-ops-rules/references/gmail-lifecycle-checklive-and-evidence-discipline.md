# Quy trình Quản lý Vòng đời Gmail Mới Reg, Check-Live & Kỷ luật Nghiệm thu Thật

## 1. Vòng đời Tài khoản Gmail Mới Reg (Gmail Lifecycle & Anti-Checkpoint)

### Nguyên tắc Bất biến:
- **Ngâm tự nhiên 24h - 48h trên thiết bị Android S7:**
  - Gmail vừa đăng ký xong chỉ cần duy trì trong `AccountManager` (`dumpsys account` nhận diện tài khoản) và app Gmail trên điện thoại.
  - **TUYỆT ĐỐI KHÔNG** nạp tài khoản mới tạo (< 24h) lên profile trình duyệt máy tính (GPM / Chrome PC) để đăng nhập Google hoặc các dịch vụ bên ngoài. Đăng nhập ngay lập tức từ thiết bị lạ khác fingerprint phần cứng sẽ kích hoạt Google Fraud AI đòi SMS Phone Checkpoint (`challenge/iap`) dẫn đến DIE hàng loạt.
  - **TUYỆT ĐỐI KHÔNG** bật 2FA (Google Authenticator) ngay lúc vừa reg. Cờ chính sách: `ENABLE_POST_REG_2FA=0`. Chỉ bật 2FA sau khi tài khoản đã ngâm đủ >= 24-48h và được thực hiện cuốn chiếu vào ca trưa/tối.
  - **TUYỆT ĐỐI KHÔNG** dùng tài khoản nội bộ (SMTP script từ mail recovery như `thanhdat...`) bắn mail chào hỏi/tương tác chéo sang Gmail mới reg. Hành vi này tạo thành cụm liên kết bất thường (Inter-linking Cluster) khiến Google gắn cờ và quét chết cả chùm.

### Giới hạn Kỹ thuật trên Samsung S7 (Android 8.0 Oreo):
- **Không dùng App ChatGPT:** App ChatGPT chính thức yêu cầu tối thiểu Android 9.0+ (API level 28+). Samsung S7 chạy Android 8.0.0 (API 26) không tương thích.
- **Không dùng Google OAuth ("Continue with Google") trên Chrome S7:** Google Play Services trên Android 8.0 khi xử lý Intent callback từ `auth.openai.com` bị đá văng về `Settings$UserAndAccountDashboardActivity`, làm WebView của Chrome bị kẹt trắng ở URL authorize. Muốn đăng ký dịch vụ bên ngoài phải chờ sau 24-48h rồi thực hiện trên GPM/Chrome PC.

---

## 2. Quy trình Kiểm tra Live/Die qua Checkmail.live

### Cơ chế hoạt động:
- Trang `https://checkmail.live/` bắt buộc phải có phiên đăng nhập (API Key hợp lệ) thì nút `#btn-check` mới hoạt động. Nếu chưa đăng nhập, gọi check sẽ bị chặn âm thầm.
- **Script chuẩn canonical:** `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py`.
  - Tự động kiểm tra API Key hiện hữu; nếu session hết hạn, tự động submit form đăng ký/đăng nhập ephemeral qua proxy Mobi 4G (`http://test.taadaa.click:5101`).
  - Nạp danh sách email vào CodeMirror editor (`window.editor.setValue(payload)`).
  - Bấm `#btn-check` và polling kết quả từ `window.liveResultEditor` / `window.dieResultEditor`.
- **Dọn dẹp kho dữ liệu:**
  - Ngay khi phát hiện tài khoản bị checkpoint đòi số điện thoại hoặc DIE trên checkmail.live, BẮT BUỘC tạo file backup `.xlsx` có timestamp trước khi xóa dòng khỏi `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx`.

---

## 3. Kỷ luật Bằng chứng Nghiệm thu (Anti-Hallucination & Evidence Gate)

### Bài học Xương máu (Subagent Hallucination Trap):
- **CẤM TIN VÀO BÁO CÁO VĂN BẢN (Self-report) CỦA WORKER:** Worker subagent báo "đã click submit thành công", "đã chuyển hướng", "đã hoàn tất" KHÔNG PHẢI là sự thật đã được kiểm chứng.
- **Hiện tượng thực tế:** 
  - Subagent gọi click form submit newsletter hoặc form web nhưng trang thực tế bị Cloudflare Turnstile treo load, trả về màn hình trắng (ảnh chụp kích thước nhỏ, pixel trắng xóa `RGB 255, 255, 255`), hòm thư không hề nhận được thư nào.
  - Script HTTP POST thuần gửi vào form đăng ký nhận `HTTP 200 OK` nhưng thực chất mã 200 đó là trang HTML thử thách bot của Cloudflare chứ không phải form submit thành công (False Positive).

### Quy tắc Điều phối Bắt buộc cho Coordinator:
1. **Kiểm tra Artifact Tận mắt:** Trước khi báo cáo kết quả cho user, Coordinator BẮT BUỘC tự kiểm tra file screencap, kiểm tra nội dung text trong XML dump hoặc kiểm tra inbox thực tế qua ADB.
2. **Kỷ luật Đính kèm Bằng chứng Ảnh:** Mọi tác vụ thao tác UI, chạy batch, kiểm tra hiện trường BẮT BUỘC đính kèm ảnh chụp màn hình nghiệm thu ở dòng riêng dạng `MEDIA:<absolute_path>`. Không có ảnh chứng minh hoặc ảnh chụp màn hình trắng/lỗi = COI NHƯ TASK CHƯA HOÀN THÀNH.
3. **Cài đặt Cron Canh giờ phải kiểm tra Lịch Nuôi Acc (Preflight Schedule):**
   - Trước khi tạo cron hoặc canh giờ chạy task can thiệp thiết bị, BẮT BUỘC kiểm tra bảng mapping tài khoản của máy đó trong `taikhoan_run_safe.xlsx` và `_SCHEDULE` của `tiktok_runner.py`.
   - Nếu máy đó có tài khoản trong Row của ca nuôi, ca nuôi có thể kéo dài do cooldown máy. Không được đoán mò giờ kết thúc. Ưu tiên chọn các máy rảnh hoàn toàn (không có tài khoản trong slot của ca đó) để chạy canary test.
