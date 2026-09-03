# PHÂN BIỆT MÀN MAGIC-LINK vs OTP + ATX CLICK (confirmed 2026-08-17, máy 75)

## 1. Hai màn KHÁC NHAU — phân biệt bằng marker (user xác nhận từng ảnh)

### MÀN MAGIC LINK
- Text: "Kiểm tra hộp thư của bạn" + "Bạn có thể đăng ký bằng **liên kết** được gửi đến <email>" + nút **"Gửi lại email"**
- KHÔNG có ô nhập mã, KHÔNG có bàn phím số
- Marker (strip_accents lowercase): `kiem tra hop thu`, `dang ky bang lien ket`, `lien ket duoc gui`, `gui lai email`, `sign up with a link`, `dang nhap bang lien ket`, `login with a link`
- Xử lý: mở Outlook app → mở mail TikTok → **ATX click** nút "[Xác minh email]" đỏ (nút đó LÀ magic link)

### MÀN OTP
- Text: "Nhập mã gồm 6 chữ số" + "Để đặt mật khẩu, hãy nhập mã..." + 6 ô vuông nhập + bàn phím số + "Gửi lại **mã** 32s"
- Marker: `nhap ma gom 6 chu so`, `nhap ma`, `ma xac minh`, `ma xac nhan`, `gui lai ma`, `resend code`, `enter the code`
- Xử lý: đọc OTP từ inbox (Graph token / Outlook app) → điền vào 6 ô

### Chống nhầm chủ chốt
- `gui lai EMAIL` (magic) != `gui lai MA` (OTP): chuỗi "gui lai email" KHÔNG match marker "gui lai ma"
- `kiem tra hop thu` / `lien ket` chỉ xuất hiện ở magic
- Code: `_post_auth_ui_state` check magic markers TRƯỚC otp_required → return "magic_link"; call site xử lý `fallback_state in ("otp_required","magic_link")` chung qua `handle_tiktok_email_otp` (tự prefer_magic_link)

## 2. ATX CLICK cho nút trong Outlook/WebView (bắt buộc)

- Nút "[Xác minh email]" đỏ trong mail TikTok là **WebView link** (`resource-id="link"`, class android.view.View, clickable=true)
- `adb input tap` (shell) **KHÔNG kích hoạt** được link trong WebView → click "ăn" nhưng không có tác dụng (foreground vẫn Outlook)
- PHẢI dùng **atx-agent JSON-RPC click**:
  1. Lấy pid process `com.github.uiautomator`: `adb shell "ps -A | grep com.github.uiautomator"`
  2. `adb forward tcp:7912 tcp:7912`
  3. `POST http://127.0.0.1:7912/session/{pid}:com.github.uiautomator/jsonrpc/0` body `{"jsonrpc":"2.0","id":1,"method":"click","params":[x,y]}` → result True → TikTok app mở (verified 16:06 máy 75)
- Helper đã có trong social_reg_v1.py: `_atx_click(device_id,x,y)` + `_atx_find_click(device_id,*texts)` (tìm node clickable rồi ATX click)
- ATX primary mọi thao tác (rule 16/08) — uiautomator shell chỉ fallback

## 3. Flow magic-link hoàn chỉnh (17/08, đã encode)
1. Màn "Kiểm tra hộp thư" (magic link) → `_read_magic_link_with_inbox_recovery`
2. Bước 1: mở Outlook app → `_atx_find_click("Xác minh email","Xac minh email","Verify email")` → OK → return MAGIC_LINK
3. Bước 2 (recovery): dismiss popup feedback ("KHÔNG, CẢM ƠN"/"Khong, cam on"/"No thanks") → tap "Hộp thư đến"/"Hop thu den"/"Inbox" → tap mail "TikTok" → ATX click nút Xác minh email
4. Bước 3: chỉ còn canonical reader (treo được — caller bọc try/except)

## 4. PITFALL đã gặp (không lặp lại)
- Popup feedback Outlook "Chúng tôi muốn lắng nghe phản hồi của bạn — KHÔNG, CẢM ƠN/CHẮC CHẮN" chặn đầu list Hộp thư đến → phải dismiss trước khi tap mail TikTok
- Link hết hạn ~20 phút ("Liên kết có hiệu lực trong 20 phút") → mail quá cũ phải bấm "Gửi lại email" để có mail mới
- ResolverActivity ("Mở bằng": TikTok / Samsung Internet) khi am start VIEW link tiktok.com → chọn TikTok + "CHỈ MỘT LẦN" mới vào được app
- Graph URL + intent mở Chrome KHÔNG xác nhận đăng ký (Chrome foreground → script tưởng "rời màn" = false positive)