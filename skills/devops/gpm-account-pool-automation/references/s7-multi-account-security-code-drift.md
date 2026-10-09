# S7 Multi-Account Security Code Drift & Fast-Path Navigation

## 1. Hiện tượng "Sai mã. Hãy thử lại." dù đã bóc đúng mã 10 số
Khi thiết bị Samsung Galaxy S7 (Android 7) có nhiều tài khoản Google (>=2 tài khoản trong Settings -> Accounts):
- Google Play Services (`com.google.android.gms`) có thể đang cache hoặc mặc định hiển thị "Mã bảo mật" của tài khoản chính đầu tiên (ví dụ: `phamthimyduyen...`).
- Nếu giao diện lấy mã trên S7 chưa được trích xuất từ đúng email đang đăng nhập trên trình duyệt GPM (`phannhu...`), Google sẽ từ chối mã với thông báo: `"Sai mã. Hãy thử lại."`.
- Nhập sai mã 10 số quá nhiều lần (>=3 lần) trên một phiên sẽ kích hoạt cơ chế đếm lỗi bảo mật của Google -> **CẦN NGÂM TĨNH 24H**, không cố nạp tiếp trên tài khoản đó để tránh bị khóa checkpoint toàn bộ tài khoản.

## 2. Đường dẫn O(1) chuẩn xác vào Mã bảo mật trên Samsung Galaxy S7 (Android 7)
Tránh dùng `am start -n com.google.android.gms/.app.settings.GoogleSettingsLink` vì trên Android 7 lệnh này có thể mở nhầm Activity "Tự động điền" thay vì cài đặt tài khoản.

Quy trình điều hướng O(1) chuẩn:
1. Mở Cài đặt hệ thống:
   `am start -a android.settings.SETTINGS`
2. Vuốt lên 1 nhịp để thấy mục Google:
   `input swipe 500 1500 500 400`
3. Tap vào mục "Google" (Các dịch vụ của Google):
   `input tap 400 580`
4. Tap vào khung hiển thị tài khoản để mở popup/menu tài khoản:
   `input tap 400 850` (bounds vùng account frame)
5. Tap nút "Tài khoản Google" (hoặc "Quản lý Tài khoản Google"):
   `input tap 490 720` (hoặc click node có text "Tài khoản Google")
6. Tap mục "Mã bảo mật":
   `input tap 400 830` (hoặc click node có text "Mã bảo mật")
7. Trên màn hình Mã bảo mật:
   - **BẮT BUỘC KIỂM TRA EMAIL HIỆN TẠI** ở đỉnh màn hình (`bounds=[216,159][792,224]`).
   - Nếu hiển thị khác target email: tap vào dropdown spinner ở đỉnh để chọn đúng target email trước khi bóc 2 mã 10 số!

## 3. Cập nhật Combo OmniRoute cho Account Gmail Pro
- Khi người dùng nạp tay tài khoản Pro (ví dụ: `g1-pro-tier`) vào OmniRoute (:20129):
  - API endpoint cập nhật combo: `PUT /api/combos/{combo_id}` (lưu ý: `combo_id` phải dùng đúng UUID hoặc ID nội bộ của combo).
  - Đối với `ag-gemini-pool-3`: thêm model `antigravity/gemini-3.8-flash-tiered` gắn với `connectionId` của tài khoản Pro.
  - Đối với `ag-claude`: thêm model `antigravity/claude-sonnet-4-6` gắn với `connectionId` của tài khoản Pro.
- Luôn ưu tiên tài khoản có 2FA TOTP (Google Authenticator 6 số) qua `pyotp` khi chạy batch tự động để tránh hoàn toàn phụ thuộc vào thiết bị vật lý và rủi ro lệch mã S7.
