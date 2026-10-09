# Google Login Trust Score vs 2FA & Multi-Worker Concurrency Pitfalls

## 1. Bản chất: Google Trust Score vs Ràng buộc 2FA
### Sai lầm nhận thức phổ biến
- Suy diễn sai: *"Tài khoản chưa có 2FA trên Excel/thiết bị thì không thể đăng nhập Google trên GPM/trình duyệt PC"* hoặc *"Bắt buộc phải bật 2FA mới cho login GPM"*.
- **Thực tế kỹ thuật:**
  - Google Risk Engine quyết định có cho đăng nhập hay không dựa trên **Account Trust Score**: thiết bị khởi tạo, lịch sử tương tác, độ sạch của IP proxy, và mức độ bất thường của phiên kết nối.
  - Khi Trust Score cao: Google cho phép đăng nhập **thẳng 100% chỉ bằng Email + Mật khẩu** mà không đòi hỏi bất kỳ bước 2FA, OTP hay xác minh SĐT nào.
  - Khi Trust Score chưa đủ hoặc phát hiện bất thường: Google kích hoạt **Hard Phone Checkpoint (`challenge/iap`)** đòi số điện thoại mới, dù tài khoản đã có hay chưa có 2FA.

### Chiến lược tăng Trust an toàn
1. **Reg & tương tác tự nhiên trên thiết bị gốc (Samsung S7) trước:**
   - Sử dụng luồng Direct Email OTP (như đăng ký ChatGPT trên S7 qua `watchdog_link_chatgpt_idle.py`) để tạo luồng nhận email, đọc mã và đồng bộ hòm thư thật.
   - Cơ chế cuốn chiếu tự động: `watchdog_link_chatgpt_idle.py` tự động quét danh sách các Gmail LIVE từ `master_gmail_manager.xlsx` (bỏ qua acc đã có cờ `CHATGPT_READY`), canh máy S7 rảnh giữa các ca TikTok để chạy liên kết ChatGPT. Khi hoàn tất, tự động gắn cờ `CHATGPT_READY` vào Cột 14 Excel để watchdog GPM tối ưu tiên phân bổ slot proxy số 1.
   - Tránh đăng nhập Google trên PC ngay lập tức với tài khoản mới reg tĩnh nếu chưa có hoạt động người dùng thật.
2. **Không ép cứng điều kiện 2FA trong code tuyển chọn candidate:**
   - Bộ lọc candidate không được tự ý loại bỏ tài khoản chỉ vì thiếu `2FA_Secret`. Tài khoản có Trust cao vẫn vào thẳng bằng credentials.

---

## 2. Hiệu ứng tiêu cực của Concurrency (`MAX_WORKERS > 2`) trên GPM
### Hiện tượng
- Bung 5 workers (`MAX_WORKERS = 5`) đồng thời trên GPM qua mạng nội bộ / proxy:
  - Tỷ lệ fail tăng đột biến (0/33 thành công).
  - Kể cả tài khoản có Trust Score cao và vào được thẳng trang cấp quyền OAuth (Consent / NativeApp) cũng bị **TIMEOUT 180s** và bị tính là thất bại oan.
  - Khi chuyển về chạy đơn lẻ 1 worker: Tài khoản tương tự click qua ngay lập tức.

### Nguyên nhân kỹ thuật
1. **Tranh chấp băng thông & tài nguyên:** Nhiều instance Chromium khởi động cùng lúc gây nghẽn routing proxy và trễ phản hồi từ Google / callback server local.
2. **Fraud Score tăng cao:** Nhiều request đăng nhập đồng thời xuất phát từ cùng hạ tầng mạng nội bộ khiến Google siết chặt kiểm soát và bật challenge.

### Quy tắc bất biến (Rule of Thumb)
- Đối với pipeline login Google / OAuth trên GPMLogin: **CHỈ ĐẶT `MAX_WORKERS = 1` hoặc tối đa `2`**, luôn kèm giãn cách `time.sleep(stagger)` để đảm bảo tính ổn định tuyệt đối.
