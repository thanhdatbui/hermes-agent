# Pitfall & Invariant: Vòng Đời Hotmail -> GPM -> ChatGPT (Thiếu TikTok PASS & Bug DONE Ảo)

## 1. Sự Cố Kẹt WAIT_7D: Bẫy Kiểm Tra TikTok Password Trên Account Reg Bằng OTP

### Hiện tượng
- Báo cáo 6h `cron_hotmail_gpm_lifecycle_6h_report.py` báo:
  - `Đang ngâm 7 ngày chờ đổi (WAIT_7D): 425`
  - `Đã đủ 7 ngày ngâm: 286 (Kibe: 0 | Admin: 286)`
  - `Thiếu thông tin TikTok: 232 (Kibe: 3 | Admin: 229)`
- 229 tài khoản Admin đã ngâm quá 7 ngày nhưng không bao giờ được chuyển sang `CHANGE_INFO`.

### Nguyên nhân gốc rễ
1. **Quy tắc Farm đối với tài khoản TikTok reg bằng OTP/Email:**
   - Theo skill `tiktok-reg-hotmail-outlook-flow`, luồng đăng ký bằng email OTP trên điện thoại KHÔNG có màn hình đặt mật khẩu.
   - User cấm tuyệt đối sinh mật khẩu giả (`make_tiktok_password()`) ghi vào tracking. Do đó, trong `taikhoan_dat_v2_updated .xlsx`:
     - Cột 3 (`ID` - TikTok username): Có dữ liệu (e.g. `phamphuc19462`, `bobo861293`...).
     - Cột 4 (`PASS` - TikTok password): **Để trống** (`None` / `""`).
2. **Logic sai trong code Supervisor & Lifecycle Report:**
   ```python
   # batch_gpm_5profiles_supervisor.py
   "has_tiktok": bool(u_name and p_word)
   has_tik = bool(info.get("has_tiktok") or (info.get("username") and info.get("password")))

   # cron_hotmail_gpm_lifecycle_6h_report.py
   has_tiktok = bool(raw.get("has_tiktok") or (raw.get("username") and raw.get("password")))
   ```
   - Code yêu cầu bắt buộc phải có CẢ username VÀ password mới tính là `has_tiktok = True`.
   - Kết quả: Toàn bộ 229 nick đã có nick TikTok hợp lệ trên máy bị phán đoán sai thành `has_tiktok = False`, kẹt vĩnh viễn ở `WAIT_7D`.

### Invariant & Khắc phục
- Trong mọi script supervisor và report vòng đời Hotmail -> GPM, điều kiện xác nhận tài khoản đã có TikTok là **chỉ kiểm tra `bool(username)`** (có ID TikTok):
  ```python
  has_tiktok = bool(raw.get("has_tiktok") or raw.get("username"))
  ```

---

## 2. Bẫy "DONE Ảo" (Silent False-Positive Success) Trong Đổi Pass Bảo Mật Hotmail

### Hiện tượng
- State supervisor cụm Admin ghi nhận 188 nick ở trạng thái `DONE` / `COMPLETED`.
- Tuy nhiên kiểm tra thực tế trong workbook `taikhoan_dat_v2_updated .xlsx`, 100% mật khẩu Cột 7 vẫn là mật khẩu mua gốc của shop, chưa hề đổi sang mật khẩu mạnh 14 ký tự và chưa thiết lập 2FA.

### Nguyên nhân gốc rễ
1. **Lệch cấu trúc bảng giữa Cụm Kibe và Cụm Admin:**
   - Kibe workbook có 12 cột (Cột 12 là `PASS CHATGPT`).
   - Admin workbook chỉ có 10 cột.
   - Trong `gpm_change_hotmail_security.py` (hàm `find_target_accounts`):
     ```python
     has_tiktok = bool(user_val and len(row) > 3 and row[3])
     has_chatgpt = bool(len(row) > 11 and row[11] and str(row[11]).strip())
     if not (has_tiktok and has_chatgpt):
         continue
     ```
     Với Admin, `len(row) <= 10` nên `has_chatgpt` luôn là `False`.
2. **Exit Code 0 khi không tìm thấy target:**
   - Khi supervisor gọi `python gpm_change_hotmail_security.py --email <admin_mail> --live`, script duyệt workbook không khớp điều kiện trên, in log:
     `[-] Không tìm thấy tài khoản Hotmail mục tiêu phù hợp.` và chạy dòng `return 0` trong `main()`.
   - Supervisor kiểm tra:
     ```python
     ok = run_cmd(cmd, timeout=1200)
     return {"key": key, "status": "COMPLETED" if ok else "FAILED", "stage": stage, "next_stage": "DONE" if ok else stage}
     ```
   - Vì exit code là 0, `run_cmd` trả về `True` (`ok = True`). Supervisor lập tức chuyển tài khoản sang `DONE`, tạo ra hàng trăm tài khoản "DONE ảo".

### Invariant & Khắc phục
1. **Thoát mã lỗi khi chạy Targeted Mode:**
   - Khi script nhận tham số đích danh `--email`, nếu không tìm thấy tài khoản mục tiêu phù hợp trong workbook, **BẮT BUỘC trả về exit code 1** (thay vì 0):
     ```python
     if not targets:
         log("[-] Không tìm thấy tài khoản Hotmail mục tiêu phù hợp.")
         return 1 if args.email else 0
     ```
2. **Không chặn kiểm tra Cột 12 khi đã chỉ định `--email`:**
   - Nếu đã truyền `--email` từ supervisor, cho phép xử lý trực tiếp tài khoản đó. Điều kiện lọc chung chỉ áp dụng cho chế độ quét tự động (batch scan không tham số).

---

## 3. Kỷ Luật Điều Phối Khi Gặp Hand-Off Lock & Lệnh "Fix Đi"

1. **Strike-3 Reviewer Hand-Off Active:**
   - Khi file `D:/Taadaa/runtime/handoff_lock_active.json` tồn tại, hệ thống chặn cứng lệnh `clarify`.
   - Coordinator cấm dùng clarify xin phép hay đưa menu lựa chọn; bắt buộc điều tra bằng chứng O(1), xác định đúng contract và tự xử lý.
2. **Xử lý 55 nick QUARANTINE:**
   - Các nick bị cách ly do `login_retry_count >= 3` tại bước `HOTMAIL_LOGIN` thường do sự cố mạng/proxy nhất thời.
   - Kiểm tra xem mật khẩu mail trong state có đầy đủ không (thực tế 100% đều có sẵn).
   - Reset cuốn chiếu `login_retry_count = 0` và đưa về `PENDING` theo từng đợt để supervisor chạy lại với proxy sống.
