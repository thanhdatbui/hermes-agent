# Admin Cluster Hotmail Accounts: Workbook Schema Mapping & Auto-Login OTP Timeout Triage

## 1. Chuẩn Hóa Schema Cột Master Excel Admin (`taikhoan_dat_v2_updated .xlsx`)
Khi đối soát tài khoản cụm Admin (Máy 201–280), CẤM TUYỆT ĐỐI đoán mò thứ tự index cột tuple `row[3]`, `row[4]`. Bắt buộc dùng mapping chính xác theo header row 1 của sheet `Tài Khoản`:

| Index | Tên Cột | Ý nghĩa thực tế | Ghi chú cụm Admin (201-280) |
| :---: | :--- | :--- | :--- |
| **0** | `Máy` | Số thứ tự máy (201-280) | Kiểu số int |
| **1** | `Folder Video` | Slot tài khoản (1-640) | 8 slot/máy |
| **2** | `ID` | TikTok Username (@handle) | Ví dụ: `huynhthiloan112` |
| **3** | `PASS` | Mật khẩu TikTok tĩnh | **Thường là `None`** trên cụm Admin (do reg qua Hotmail OTP) |
| **4** | `2FA` | Secret Key 2FA | Chuỗi base32 hoặc `None` nếu chưa bật |
| **5** | `GMAIL` | Hộp thư (Hotmail/Outlook) | Ví dụ: `shackmierez11@hotmail.com` |
| **6** | `PASS MAIL` | Mật khẩu hộp thư | Mật khẩu đăng nhập Hotmail / webmail |
| **7** | `NGÀY THÁNG NĂM SINH`| Ngày sinh tài khoản | Chuỗi ngày hoặc format date |
| **8** | `NGÀY TẠO` | Ngày đăng ký / tạo nick | Thường kèm serial device |
| **9** | `device ID` | Serial máy Android | 9886... |

⚠️ **PITFALL CHẾT NGƯỜI (HALLUCINATION MISMAPPING):**
- Đọc `row[3]` là `None` rồi vội vàng kết luận *"Nick không có email/pass"* là SAI HOÀN TOÀN. `row[3]` là `PASS` TikTok, còn `GMAIL` nằm ở `row[5]` và `PASS MAIL` nằm ở `row[6]`.
- Luôn truy xuất theo tên cột hoặc dictionary:
  ```python
  acc = {
      "id": row[2],
      "tiktok_pass": row[3] or "",
      "email": row[5] or "",
      "mail_pass": row[6] or "",
  }
  ```

---

## 2. Bản Chất Luồng Auto-Login Cho Nick Có `PASS: None` Trên Cụm Admin
- **Hiện tượng:** Máy dừng ở màn hình One-Tap Login ("Chào mừng bạn trở lại"), log báo timeout 420s ở `start_fast_login` và tiếp tục timeout 600s ở `start_reconcile` (tổng 17 phút).
- **Cơ chế vận hành đúng:**
  1. Nick mục tiêu chưa có trên máy (chưa nạp vào Switcher).
  2. Feed runner kích hoạt `tiktok_login_v1.py <N> --email <id>`.
  3. `tiktok_login_v1.py` kiểm tra thấy `account["usable"] == True` vì có cặp `login_email` (Hotmail) + `mail_pass` hợp lệ (dù `tiktok_pass` là `None`).
  4. Script bấm *"+ Thêm tài khoản khác"*, chọn đăng nhập bằng Email, điền email Hotmail vào form.
  5. Vì không có mật khẩu TikTok tĩnh, TikTok bắt buộc chuyển sang màn hình **Gửi mã xác nhận về Email (OTP flow)**.
- **Điểm nghẽn gây Timeout 17 phút:**
  - `handle_tiktok_email_otp()` chờ nhận mã OTP từ hòm thư Hotmail.
  - Nếu hòm thư Hotmail chưa có Graph API token trên PC, hoặc mạng delay khiến OTP chưa về kịp hộp thư trong thời gian chờ, tiến trình sẽ tiếp tục loop kiểm tra cho đến khi chạm trần timeout an toàn:
    * `fast_login_timeout_seconds`: 420s (7 phút).
    * `reconcile_timeout_seconds`: 600s (10 phút).
- **Kết luận chẩn đoán chuẩn:**
  - **KHÔNG PHẢI:** Nick bị thiếu dữ liệu trong sổ cái.
  - **KHÔNG PHẢI:** Nick bị văng phiên hay logout.
  - **CHÍNH XÁC LÀ:** Luồng đăng nhập tự động đã kích hoạt đúng, nhưng bị nghẽn ở khâu lấy mã xác thực OTP từ hộp thư Hotmail về.
