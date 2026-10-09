# Phân Biệt SMTP Probe Live vs Login Checkpoint & Quy Tắc Quét Đáy Workbook Gmail

## 1. Cạm Bẫy: checkmail.live Báo LIVE Nhưng Tài Khoản Thực Tế Bị Kẹt Checkpoint

### Hiện tượng
- Công cụ kiểm tra nhanh như `check_gmail_live_fast.py` hoặc dịch vụ `checkmail.live` gửi truy vấn probe / SMTP handshake kiểm tra hòm thư và trả về `LIVE`.
- Tuy nhiên, khi đưa tài khoản vào ứng dụng trên thiết bị (Android Samsung S7) hoặc mở trình duyệt web đăng nhập, Google lập tức chặn lại ở màn hình:
  `"Xác minh danh tính của bạn. Do có hoạt động bất thường, bạn cần xác minh danh tính để tiếp tục đăng nhập"` (Google Challenge `challenge/iap` đòi số điện thoại).

### Bản chất kỹ thuật
- **SMTP Probe (`checkmail.live`):** Chỉ kiểm tra trạng thái máy chủ thư Google có tiếp nhận thư gửi đến hòm thư đó hay không (`RCPT TO: <email>`). Một tài khoản bị Google khóa chiều đăng nhập (Login Challenge / Phone Checkpoint) nhưng chưa bị xóa tài khoản (`Account Disabled` / `550 User unknown`) thì **vẫn nhận được thư**. Do đó web check SMTP luôn báo `LIVE`.
- **Interactive Login (On-device / Web):** Google áp dụng Risk-Based Authentication (RBA). Khi tài khoản mới hoặc bị nghi ngờ bot, chiều đăng nhập tương tác đòi hỏi SMS OTP hoặc passkey.
- **Quy tắc điều phối:** Tuyệt đối không suy diễn tài khoản "sẵn sàng đăng nhập ngay" chỉ dựa trên kết quả `checkmail.live`. Đối với các tài khoản dùng để đăng nhập app/game/TikTok, trạng thái live tương tác chỉ được xác nhận khi có phiên đăng nhập sẵn trên thiết bị hoặc vượt qua web auth mà không bị đòi số điện thoại.

---

## 2. Quy Tắc Tìm Kiếm & Vị Trí Lưu Trữ Trong `gmail_clean_v2.xlsx`

### Cơ chế lưu trữ tài khoản mới
- Khi hệ thống đăng ký tự động (`run_all.ps1`, `run_parallel.ps1`, hoặc `gmail_reg_v10.py`) tạo thành công tài khoản Gmail mới:
  - Dữ liệu được gom vào file JSON tạm (`machine_<STT>.success.json`).
  - Sau đó script `merge_success_results.py` hoặc fallback `persist_success_result()` thực hiện chèn dòng mới vào workbook `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx`.
  - **Dòng mới được ghi nối tiếp vào đáy bảng (Insert at bottom / Max Row), KHÔNG chèn gom cụm theo số máy ở phần đầu bảng.**

### Cạm bẫy truy vết
- Các đợt reg cũ (tháng 3 đến tháng 8/2026) nằm ở các dòng đầu tiên (ví dụ Máy 3 nằm ở dòng 7, 8, 9).
- Các đợt reg mới (tháng 9, 10/2026) của cùng Máy 3 sẽ nằm ở đáy file (ví dụ dòng 526, 527).
- **Quy tắc điều phối:** Khi kiểm tra xem một máy đã có Gmail mới reg hay chưa, **BẮT BUỘC quét toàn bộ bảng hoặc duyệt ngược từ dưới lên (reverse scan)**. CẤM chỉ đọc vài chục dòng đầu rồi kết luận "không có trong kho".
