# Gemini Pro Link Sniper Preflight Session Gate & Antigravity 403 Rescue Protocol

## 1. Bối Cảnh & Bài Học Thực Chiến (2026-10-22)
Trong ca vận hành ngày 2026-10-22, khi tự động canh mua 2 link Google Gemini Pro 18M từ SumiStore:
- **Đơn 1 (nguyenkhoi14031998@gmail.com):** Bắn lệnh mua thành công lúc 08:07:10 nhưng profile GPM M40 chưa hề được đăng nhập Google. Script bị nghẽn ở màn hình sign-in (`accounts.google.com/signin`), để ngâm link quá 5 phút. Khi quay lại đăng nhập xong thì link đã bị Google One hủy và redirect về trang mặc định 15GB (`g1_landing_page=5`), mất quyền bảo hành của shop.
- **Tài khoản chuanh250416@gmail.com:** Dính lỗi upstream 403 `VALIDATION_REQUIRED`. Việc quét QR code trần trên điện thoại cá nhân (Safari tự động mở nhầm session Google khác) hoặc re-OAuth trần trên trình duyệt web không giải quyết được cờ chặn thiết bị của Google.

---

## 2. Quy Tắc Bắt Buộc: Preflight GPM Session Trước Khi Săn Link Flash
Khi mua link bảo hành ngắn (5-10 phút) như Gemini Pro 18M hoặc Google One Family:

### BẮT BUỘC KIỂM TRA SESSION SỐNG TRƯỚC (PREFLIGHT HARD GATE):
1. Trước khi bật vòng lặp polling kho hoặc gọi `execute_buy()`:
   - Khởi chạy GPM Profile mục tiêu qua Local API (`/api/v3/profiles/start/{id}?skip_proxy_check=true`).
   - Kết nối Playwright qua CDP (`http://{remote_debugging_address}`).
   - Truy cập `https://one.google.com/home` (timeout 25s): Xác nhận KHÔNG bị redirect về `accounts.google.com/signin` hoặc trang giới thiệu `about`.
   - Truy cập `https://families.google/families/`: Xác nhận KHÔNG bị rơi vào `family/details` (chưa ở trong nhóm gia đình nào khác).
2. **Nếu Session Chết / Văng Login:** In cờ `[⛔ BLOCK]`, **TUYỆT ĐỐI CẤM MUA**, tự động chuyển sang tài khoản tiếp theo trong danh sách hoặc dừng lại cảnh báo.
3. **Chỉ khi Preflight PASS 100%:** Mới cho phép nạp tiền và bắn API mua hàng.
4. **Kỷ luật trung thực:** Thời gian mua đơn hàng bắt buộc lấy chính xác từ trường `time` / `checked_at` của API JSON response, nghiêm cấm làm tròn hay khai báo sai lệch.

---

## 3. Quy Trình Cứu Antigravity Pro 403 `VALIDATION_REQUIRED`
Khi tài khoản Antigravity Pro bị Google chặn với lỗi:
```json
{
  "code": 403,
  "message": "Verify your account to continue.",
  "status": "PERMISSION_DENIED",
  "reason": "VALIDATION_REQUIRED"
}
```

### Tại sao không thể gỡ bằng OAuth web thông thường?
Google gắn cờ rủi ro thiết bị và IP lịch sử của máy S7 quản lý tài khoản. Việc re-OAuth trần trên trình duyệt GPM hoặc bóc URL `validation_url` / QR code quét qua trình duyệt điện thoại cá nhân sẽ:
- Dễ bị mở nhầm tài khoản Google khác đang active trên điện thoại.
- Không thỏa mãn điều kiện xác minh thiết bị của ứng dụng Antigravity thật.

### Quy trình cứu chuẩn (Đã kiểm chứng tại `D:\Taadaa\GPM auto\scripts\antigravity_rescue\`):
1. **Quét phân loại Pro:** Chạy `python scan_pro_accounts.py` để xác định chính xác tài khoản bị `BLOCKED` (403) vs `QUOTA_EXHAUSTED` (429).
2. **Khởi động VM Rescue:** Chạy `python rescue_antigravity_start.py <email>`:
   - VM `D:\VM\ag-onboard\ag-onboard.vmx` được revert về snapshot `baseline-v2.17`.
   - Proxy của tài khoản được tra cứu từ `master_gmail_manager.xlsx` và bật TUN trong VM.
   - Khởi chạy ứng dụng Antigravity Desktop GUI thật trong VM.
3. **Xác minh thiết bị:**
   - Trong giao diện Antigravity VM, click **Continue with Google** và đăng nhập `<email>`.
   - Khi Google bung màn hình xác thực thiết bị và mã QR, chụp màn hình mã QR.
   - Dùng **Camera mặc định của điện thoại thật** (Samsung/iPhone) quét mã QR. **CẤM dùng app Zalo** (Zalo sẽ nuốt link và fail đối với Google challenge).
4. **Kiểm định cô lập (Isolated Verification):**
   - Chạy `python verify_and_finalize.py <email>` hoặc `scan_pro_accounts.py`.
   - Sử dụng cơ chế `isolated_chat_test()`: Tắt tạm thời toàn bộ connection khác trong OmniRoute, chỉ kích hoạt duy nhất connection đích để kiểm tra trực tiếp.
   - CẤM chỉ tin tưởng kết quả HTTP 200 từ `ag-gemini-pool-3` thông thường vì router có cơ chế tự động fallback sang tài khoản sống khác gây ngộ nhận thành công (False-Positive Live).
