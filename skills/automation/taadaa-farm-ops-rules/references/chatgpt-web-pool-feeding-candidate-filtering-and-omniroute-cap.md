# Quy Chuẩn Nạp Acc ChatGPT Web Vào Pool OmniRoute & Kỷ Luật Lọc Candidate (2026-10-26)

## 1. INVARIANT BẮT BUỘC: LỌC CANDIDATE THEO SUPERVISOR STATE (CHỐNG BỐC ACC CHƯA REG)
- **Sự cố thực tế**: Khi viết script query trực tiếp từ database GPMLogin (`profile_data.db`) chỉ theo regex `%@hotmail.com%`, hệ thống sẽ bốc nhầm hàng trăm tài khoản mới chỉ dừng ở giai đoạn tạo profile (`stage: "HOTMAIL_LOGIN"`), chưa từng đăng ký ChatGPT (`chatgpt_registered_at is None`).
- **Hậu quả**: Khi mở profile lên trang `chatgpt.com`, OpenAI nhận diện là tài khoản mới và điều hướng sang `/create-account/password`, gây tốn worker vô ích, văng lỗi timeout và làm sai lệch telemetry nạp pool.
- **Quy tắc bắt buộc**:
  1. TUYỆT ĐỐI KHÔNG bốc candidate thuần từ tên profile GPM.
  2. BẮT BUỘC cross-check danh sách email với supervisor state (`batch_gpm_5profiles_supervisor_state.json` của cả Kibe và Admin).
  3. Chỉ chấp nhận các tài khoản thỏa mãn ít nhất một trong các điều kiện:
     - `chatgpt_registered_at` có timestamp hợp lệ.
     - `stage` thuộc `["DONE", "WAIT_7D", "CHANGE_INFO"]`.
     - `has_chatgpt == True`.

## 2. ĐỊNH MỨC PHÂN BỔ TRẦN PROXY (2 ACC / 1 IP)
- **Chính sách**: Trần tạm thời tối đa 2 tài khoản active trên mỗi proxy (`proxy_registry`).
- **Thuật toán nạp**:
  - Đối soát từng port proxy active:
    - Nếu port đã có $\ge 2$ acc `chatgpt-web` active -> Bỏ qua hoàn toàn (`needed = 0`).
    - Nếu port có 1 acc active -> Chỉ nạp thêm đúng 1 acc (`needed = 1`).
    - Nếu port có 0 acc active -> Nạp đúng 2 acc (`needed = 2`).
- **Đồng bộ OmniRoute (`storage.sqlite`)**:
  - Ghi bản ghi vào `provider_connections` (`provider='chatgpt-web'`, `is_active=1`, `priority=1`, `max_concurrent=3`).
  - Ghi bản ghi vào `proxy_assignments` với `scope = 'account'`, `scope_id = <connection_id>`, `proxy_id = <proxy_id>` khớp chuẩn port của profile GPM.
  - Tự động append connection ID vào các combo: `chatgpt-web-pool` và `gpt-web-sol`.

## 3. CƠ CHẾ THU HOẠCH SESSION (FAST RESCUE VS EMAIL OTP RE-AUTH)
- **Fast Session Rescue (< 15s)**:
  - Dành cho các tài khoản đang có phiên đăng nhập sẵn. Mở profile -> vào `chatgpt.com` -> trích xuất ngay `__Secure-next-auth.session-token` từ CDP cookie context -> đóng profile và đồng bộ.
  - Nếu không có token -> đánh dấu `session_expired` và thoát ngay, không treo luồng.
- **Xử lý tài khoản đã reg nhưng hết hạn session**:
  - OpenAI không cho dùng Google SSO (cấm click "Continue with Google" vì làm bẩn profile và lỗi xác thực).
  - Khi điền email vào form đăng nhập, OpenAI sẽ điều hướng sang `auth.openai.com/email-verification` để yêu cầu mã OTP 6 số gửi về Hotmail.
  - BẮT BUỘC dùng `MicrosoftGraphOTPProvider` (trong `chatgpt_gpm_direct_reg.py`) để lấy mã OTP tự động qua Microsoft Graph API thay vì thử điền mật khẩu tĩnh hay click bừa.

## 4. KỶ LUẬT THỰC THI COORDINATOR & QUẢN LÝ TIẾN TRÌNH
- **CẤM BASE64 OBFUSCATION TRONG TERMINAL**: Tuyệt đối không bọc code Python vào `exec(base64.b64decode(...))` để chạy qua shell. Các guard an ninh và runtime sẽ nhận diện đây là hành vi thực thi mã lạ/độc, kích hoạt approval prompt làm gián đoạn workflow tự động của User.
- **Dọn dẹp tiến trình Chrome ngầm**: Khi chạy batch nhiều worker (ví dụ 5 worker song song), trong khối `finally` bắt buộc gọi `stop_gpm(pid)` và kiểm tra `psutil` để kill triệt để các tiến trình Chrome con của profile đó, tránh rò rỉ RAM và nghẽn CPU của host.
