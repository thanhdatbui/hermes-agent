# m26 OTP WebView blocker — hồ sơ debug đầy đủ (25/08/2026)

## Triệu chứng
- Màn "Nhập mã gồm 6 chữ số" (Xác minh danh tính, SparkActivity + WebView `com.bytedance.lynx.hybrid.webkit.WebKitView`).
- EditText `code-input`: `focused="true"` nhưng `bounds="[0,0][0,0]"`, NAF=true.
- `dumpsys input_method`: `mServedView=WebKitView{... 0,0-1080,1920}`, `mCurRootView=DecorView@c097f22[SparkActivity]`, nhưng `mShowRequested=false mInputShown=false` — IME không bao giờ bật.
- Gõ mọi cách không vào số; màn không đổi trạng thái.

## Đã thử (TẤT CẢ fail — đừng lặp lại)
1. Tap Y = 300,400,500,560,620,660,700,720,760,850 rồi keyevent từng số (KEYCODE 7–16) → không ăn.
2. `input text <số>` trực tiếp → không ăn.
3. AdbKeyboard: `ime set com.github.uiautomator/.AdbKeyboard` + broadcast `ADB_INPUT_TEXT` → không ăn.
4. Samsung Keypad mặc định (`com.sec.android.inputmethod/.SamsungKeypad`) → không ăn.
5. `keyevent 61` (TAB), `keyevent 84`, `keyevent 66`, long-tap/swipe tại ô → không ăn.
6. Kill toàn bộ app_process + force-stop uiautomator → dump sống lại nhưng input vẫn chết.
7. REBOOT máy (fix được dump chết + dialog LSPosed) → input OTP VẪN không ăn.
8. Restart TikTok qua MainActivity thay vì monkey → vẫn vậy.
9. Probe tự động 5 tọa độ, check `code-input text=` sau mỗi lần → tất cả None.

## Nghi phạm chính
- TikTok version **46.6.3** trên m26 vs **46.4.3** trên m44 (máy keyevent ăn). Build mới đổi WebView OTP sang Lynx hybrid view không nhận IME từ adb.

## Blocker thứ 2 cùng máy — màn "Chọn phương thức xác minh"
- Sau khi quay lại gate từ Settings → Tài khoản → Mật khẩu, màn chọn method hiện lại nhưng nút **Tiếp enabled=false**.
- Row email `q***3@gmail.com` có icon tròn phải bounds `[876,642][948,711]` (center ~912,676) — tap row (400,681 / 540,681) và icon đều không tick được (XML: icon chỉ là `android.widget.Image` non-clickable, không có checked-state).
- Các lần trước luồng chạy được vì method được pre-select sẵn khi đi từ luồng BẬT 2FA lần đầu.

## Kết luận + handoff
- Đây là blocker của MÁY (UI build mới), không phải lỗi script hay mail. Mail Gmail LIVE hoàn toàn (đọc OTP mới OK lúc 17:51).
- Đã lock giữ (`release_on_terminal=False`) bàn giao user nhập tay.
- Khi user xử lý xong: verify UI trạng thái 2FA + test pass cột D ở màn tạo mật khẩu mới (nhập pass Excel vào mật khẩu mới; báo "phải khác mật khẩu cũ" = pass cũ trùng Excel = ĐÚNG).
