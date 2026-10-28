# Dual-Cluster Wi-Fi Preflight Recovery & Vision Gate False-Positive Demarcation

## 1. Dual-Cluster Wi-Fi Auto-Join Fallback (`vpn_preflight.py`)

### Triệu chứng & Bẫy Chẩn Đoán
- Khi máy thuộc cụm Admin (M201–M280) bị rớt Wi-Fi hoặc chập chờn kết nối trong ca chạy batch Nuôi Feed, preflight báo lỗi:
  `required router proxy is unreachable ... dumpsys connectivity: Wi-Fi not connected`
- Mặc dù hệ thống có cơ chế tự động kết nối lại Wi-Fi (Stage 2 Recovery: `adbjoinwifi`), toàn bộ 5 máy rớt Wi-Fi đều bị fail-closed và không hề có hành động auto-join nào được thực thi.

### Nguyên Nhân Gốc (Root Cause)
- Hàm `get_wifi_credentials_for_serial(serial)` trong `python_runner/core/vpn_preflight.py` gọi `get_default_proxy_mapping()`.
- Khi ca chạy được điều phối trên controller Kibe, mapping mặc định trỏ về `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (chỉ chứa serial máy M1–M80).
- Khi tra cứu các máy cụm Admin (M201–M280), bảng tra cứu Kibe không có serial -> hàm trả về `None`.
- Do `wifi_creds is None`, script bỏ qua hoàn toàn khối lệnh `am start -n com.steinwurf.adbjoinwifi/.MainActivity` và văng lỗi fail-closed.

### Giải Pháp & Cơ Chế Dual-Cluster Fallback
- Khi `machine = snapshot.get(clean_serial)` trả về `None`, hàm BẮT BUỘC kiểm tra fallback sang mapping của cụm đối ứng:
  - Nếu mapping chính thuộc `kibe`, kiểm tra `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx`.
  - Nếu mapping chính thuộc `admin`, kiểm tra `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`.
- Nhờ cơ chế fallback này, bất kỳ máy nào thuộc M1–M80 hay M201–M280 đều giải mã chính xác số máy và profile Wi-Fi mục tiêu (`admin 1`, `admin 2`, `kibe 1`, `kibe 2`).

---

## 2. Microsoft Basic Auth Disablement & Phục Hồi Mật Khẩu TikTok Gốc

### Vấn Đề
- Microsoft đã tắt hoàn toàn Basic Authentication trên IMAP (`outlook.office365.com` / `imap-mail.outlook.com`).
- Khi tài khoản trong `taikhoan_dat_v2_updated .xlsx` có cột `PASS = None`, script `tiktok_login_v1.py` tự chuyển sang luồng đăng nhập bằng mã OTP gửi về Hotmail. Do IMAP bị chặn Basic Auth, việc lấy OTP sẽ timeout (`[telemetry][otp_timeout] reason=mailbox_otp_not_received`).

### Quy Trình Phục Hồi
- Tuyệt đối không để `PASS = None` đối với tài khoản đã từng tạo mật khẩu, và không được điền mật khẩu ảo.
- BẮT BUỘC tra cứu ngược lại các file backup lịch sử (`taikhoan_dat_v2_updated .bak_final.xlsx`, `taikhoan_dat_v2_updated .xlsx.bak_*`) trong `D:\OneDrive\TaadaaData\admin\`.
- Nạp lại mật khẩu TikTok gốc chính xác vào cột `PASS` của file cấu hình để script thực hiện đăng nhập trực tiếp bằng Username/Password, bỏ qua hoàn toàn luồng OTP Hotmail.

---

## 3. Vision Gate Guard: Chống Báo Động Giả & Đè Tin Nhắn (`guard_media_vision_gate.py`)

### Hiện Tượng
- Coordinator gửi báo cáo kỹ thuật đính kèm thẻ `MEDIA:<path_screen.png>`, nhưng tin nhắn trên Telegram bị guard nuốt chửng và thay bằng:
  `Trạng thái: DEGRADED | Mã: UNVERIFIED_BY_VISION | Thiết bị: ...`
- Khiến người vận hành bức xúc vì tưởng hệ thống bị lỗi hoặc Agent gửi cảnh báo rác.

### Nguyên Nhân
- Bộ lọc `is_visual_claim` dùng để nhận diện xem Agent có đang "tán hươu tán vượn" về ảnh mỹ thuật hay không (hoa, cây, chân dung, cảnh quan...).
- Tuy nhiên danh sách này vô tình chứa 2 từ tiếng Việt thông thường: `"de xuat"` và `"phuong an"`.
- Bất kỳ báo cáo kỹ thuật nào có cụm từ *"Phương án xử lý"*, *"Đề xuất giải pháp"* đều bị đánh dấu `is_visual_claim = True`. Guard yêu cầu phải có vé `browser_vision` (soi mắt mỹ thuật), từ chối vé `run_winrt_ocr` của ảnh chụp màn hình UI hệ thống (`screen.png`), dẫn đến việc tin nhắn bị chuyển đổi sang template DEGRADED.

### Quy Chuẩn Đã Chuẩn Hóa
1. `is_visual_claim` chỉ kích hoạt với các từ cụ thể về đề xuất ảnh mỹ thuật: `"de xuat avatar"`, `"phuong an avatar"`, `"de xuat anh"`, `"phuong an anh"`.
2. Phân định rõ loại ảnh: Ảnh giao diện hệ thống (`screen.png`, `ui.png`) KHÔNG phải là `is_visual_image` (avatar, canvas, crop), nên vé WinRT OCR (`run_winrt_ocr`) là hợp lệ theo đúng Invariant kiểm chứng mắt đọc UI.
