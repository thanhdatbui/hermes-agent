# Đối Soát Phone Checkpoint vs Sensitive Action Cooldown & Phối Hợp S7 Pipeline

## 1. Phân biệt Bản chất: Phone Checkpoint vs Sensitive Cooldown

Khi tự động hóa đăng nhập Google / OAuth trên GPMLogin:

| Loại lỗi | Dấu hiệu URL / UI | Ngâm Cooldown có tự hết không? | Hướng xử lý bắt buộc |
| :--- | :--- | :--- | :--- |
| **Phone Checkpoint** (Mandatory SMS) | `challenge/iap`<br>Yêu cầu nhập số điện thoại để nhận SMS | **KHÔNG BAO GIỜ TỰ HẾT**<br>(Log thực tế ngâm 14-20 ngày mở lại vẫn đòi số). | Cờ bảo mật tài khoản. Bắt buộc nhập số điện thoại (SIM thật farm) nhận mã SMS. Tuyệt đối không nhầm là ngâm sẽ tự nhả. |
| **Sensitive Action Cooldown** | `signin/rejected?rrk=77`<br>Hành động nhạy cảm bị từ chối | **CÓ THỂ CỨU SAU 72H - 7 NGÀY** | Google tạm khóa do thao tác liên tục hoặc IP bị nghi ngờ. Ngâm đủ 72h - 7 ngày không thao tác để Risk Counter hạ về 0. |
| **Challenge Selection** | `challenge/selection`<br>Màn hình "Chọn cách bạn muốn đăng nhập" | N/A (Không phải lỗi checkpoint) | Không được coi là lỗi nền tảng. Cần click chọn phương thức hợp lệ: Ưu tiên TOTP Authenticator -> S7 Prompt -> Mã bảo mật 10 số (OOTP). |

---

## 2. Phân biệt Hai Script OAuth trong Hệ Thống

1. **`cron_gpm_oauth_full_pool.py` (Script Cron Nạp OAuth Toàn Pool Trên PC):**
   - Chạy nền tự động trên PC mỗi 30 phút để nạp token lên OmniRoute (:20129).
   - Đã được tích hợp khả năng liên thông thiết bị S7:
     - Tự động tra cứu `machine_id` và `serial` của nick từ `CredentialLookup`.
     - Nhận diện `challenge/selection`: Tự click chọn phương thức *"Mã bảo mật trên điện thoại"* (`data-challengetype="8"`).
     - Nhận diện `challenge/ootp` hoặc ô Pin: Gọi `get_s7_security_code(machine_id, serial, email)` qua Device Lock độc quyền để lấy mã 10 số từ máy S7 điền vào browser, vượt qua checkpoint mà không bị dính cờ 72h.
     - Tự động phân loại: Lỗi nền tảng (khóa IP port hết ngày) vs Lỗi script/môi trường (cho phép IP thử lại).

2. **`run_oauth_s7_pipeline.py` (Script Phối Hợp Toàn Diện Điện Thoại Samsung S7):**
   - Chuyên dùng cho các tài khoản đang đăng nhập LIVE trên máy Samsung S7 (nhận diện qua `dumpsys account`).
   - Tự động gọi ADB sang S7 tương ứng:
     - Nếu gặp **Google Prompt** (`challenge/dp`): Tự động tìm thông báo, bấm "Có, đúng là tôi" và chọn đúng số PIN.
     - Nếu gặp **Mã bảo mật 10 số** (`challenge/ootp`): Tự động mở *Cài đặt Google -> Bảo mật -> Mã bảo mật* trên S7, trích xuất mã 10 số điền vào PC browser.
     - Nếu gặp `challenge/selection`: Nhận diện và chọn phương thức S7 tương ứng.

---

## 3. Lưu ý Allowlist Terminal khi Chạy Script Pipeline

- Cả Coordinator Terminal và Worker Gate đều áp dụng cơ chế Default-Deny.
- Lệnh chạy script `run_oauth_s7_pipeline.py` nếu chưa được cấu hình cho phép trong allowlist sẽ bị chặn thực thi.
- Agent bị cấm đụng vào các cơ chế hook bảo vệ an toàn hệ thống. Khi cần chạy kiểm tra tức thời, User có thể chạy trực tiếp trên shell host ngoài phiên agent:
  `python "D:/Taadaa/GPM auto/scripts/run_oauth_s7_pipeline.py" <mid>`
