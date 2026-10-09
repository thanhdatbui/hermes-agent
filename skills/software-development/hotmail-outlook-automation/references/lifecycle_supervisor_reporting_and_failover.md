# Quy Chuẩn Báo Cáo Vòng Đời & Điều Phối Supervisor Hotmail (GPM -> ChatGPT -> Codex)

## 1. Tiêu Chuẩn Báo Cáo Trực Quan & Khả Năng Hành Động (Actionable Reporting)
- **Vấn đề thực tế:** Khi báo cáo chỉ ghi chung chung `Tài khoản gặp lỗi (FAILED): 232/416`, người vận hành hoàn toàn không biết hệ thống đang chạy hay kẹt, nick nào cần xử lý, nick nào đang tự hồi phục.
- **Quy chuẩn hiển thị bắt buộc:**
  1. **Tách bạch 3 nhóm trạng thái rõ ràng:**
     - **Hoàn thành / Đang chạy tốt:** Tỉ lệ và số lượng nick từng stage (`HOTMAIL_LOGIN`, `CHATGPT_REG`, `CODEX_OAUTH`, `WAIT_7D`, `CHANGE_INFO`, `DONE`).
     - **Đang Cooldown tự động (Self-Healing):** Ghi rõ số lượng nick và thời gian còn lại (ví dụ: `còn 3h`, `còn 48h`) để người vận hành biết hệ thống đang tự quản lý.
     - **Lỗi cần can thiệp thực tế:** Danh sách cụ thể từng máy/email, lỗi chi tiết và thời gian xảy ra (`Xh trước`) để người vận hành vào fix xử lý được ngay.
  2. **Hiển thị đầy đủ phễu đầu vào:** Bắt buộc có mục thống kê `HOTMAIL_LOGIN` ngay đầu báo cáo (Đã login thành công X/Total, Số nick fail, Số nick pending lần đầu, Hoạt động 6h gần nhất).

---

## 2. Kỷ Luật Đối Soát Hotmail Mua (Chống Báo Sai Lỗi Pass)
- **Đặc thù tài khoản:** Toàn bộ Hotmail trong farm là tài khoản mua tự động qua API shop (`boxtaikhoan`), luôn có định dạng đầy đủ `mail|pass|refresh_token|client_id`.
- **Cấm quy chụp lỗi pass:**
  - Khi script báo lỗi đăng nhập hoặc mật khẩu rỗng, CẤM vội vàng kết luận là tài khoản bị đổi/sai pass.
  - BẮT BUỘC tra cứu đối soát ngược lại các nguồn dữ liệu gốc:
    + Master Tracking: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (Cột `GMAIL` và `PASS MAIL`).
    + Kho sạch: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
    + File import mua hàng: `D:\Taadaa\Hotmail\latest_bought_*.txt`, `hotmail_all_60_bought.txt`.
    + Lịch sử giao dịch API trong session Hermes trước đó (`session_search`).
- **Bẫy Case-Sensitive trong Excel & State File:**
  - Email trong file Excel có thể bị gõ hoa ký tự bất kỳ (ví dụ `alejadelainE@hotmail.com`).
  - Hàm nạp state / lookup phải luôn chuẩn hóa `email.strip().lower()`. Nếu so sánh có phân biệt hoa thường, trường `mail_password` sẽ không map được và bị gán rỗng `''`.

---

## 3. Ngắt Nhánh Phụ Thuộc Khi Dịch Vụ Cạn Số Dư (External Out-of-Funds Gate)
- **Hiện tượng nghẽn luồng:** Khi dịch vụ bên ngoài (như 5SIM thuê số OTP) hết tiền (`balance < min_cost`), các lệnh gọi API sẽ fail hàng loạt.
- **Hậu quả nếu không có Circuit Breaker:**
  - Supervisor liên tục unblock các nick fail sau mỗi tick cron ngắn (30 phút).
  - Hàng trăm nick fail quay vòng chiếm trọn 100% các worker slot (5 luồng) của hệ thống.
  - Các giai đoạn khác (`HOTMAIL_LOGIN`, `CHATGPT_REG`, `CHANGE_INFO`) bị bỏ đói (Starvation).
- **Cơ chế xử lý chuẩn:**
  1. **Feature Flag ngắt nhánh:** Cung cấp cờ cấu hình (ví dụ `ENABLE_CODEX_OAUTH = 0`).
  2. **Bypass an toàn:** Khi nhánh OTP tắt, tài khoản reg ChatGPT thành công sẽ chuyển thẳng sang giai đoạn ngâm tiếp theo (`WAIT_7D` chờ đổi info), đồng thời tận dụng cookie phiên Web đưa vào pool `chatgpt-web` của OmniRoute.
  3. **Tạm dừng Cron phụ:** Pause các cron job liên quan (ví dụ `update-5sim-pools-6h`) để tránh spam request API lỗi.
