# GemPhoneFarm Injected `verify-bar-close` False Challenge & Live Switcher OCR Reconcile (2026-09-19)

## 1. Bản chất sự cố
Khi nhận Farm Alert:
`⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện máy MX: manual_challenge marker detected`
Hệ thống báo động mức cao nhất (nguy cơ văng tài khoản hoặc kẹt captcha xác minh thủ công).

## 2. Nguyên nhân kỹ thuật (False Positive Mechanism)
1. **Background Service Injected Element:**
   Phần mềm điều khiển nông trại (GemPhoneFarm) chạy nền trên Android (`com.android.systemui` notification: "GemPhone đang chạy ngầm") có thể inject element mang `resource-id="verify-bar-close"` vào view hierarchy.
2. **Co-occurrence Trap:**
   Bộ phân loại `python_runner/core/classifier.py` quy định: nếu thấy `verify-bar-close` đồng thời phát hiện từ khóa trong `manual_challenge_terms` (như `"xác minh"`, `"Xác minh"`) thì phân loại là `screen="manual-needed:manual_challenge"`.
3. **Transient Collision:**
   Khi người dùng lướt feed TikTok, caption/bio của video ("xác minh danh tính", "kênh đã xác minh") hoặc tiêu đề bài đăng tình cờ chứa chữ "xác minh", rule bị kích hoạt nhầm, khiến `safety.py` phát ra marker `manual_challenge marker detected`.

## 3. Quy trình Evidence-First Bắt buộc cho Coordinator (Anti-Panic)
1. **Không can thiệp mù quáng:** Tuyệt đối không bấm tay bypass qua ADB, không force-clear app (`pm clear`), không tự ý chạy script re-login khi chưa xác minh hiện trường.
2. **Kiểm tra trạng thái Foreground & Live Screen:**
   - Đánh thức màn hình: `adb shell input keyevent 224 && input keyevent 82`.
   - Screencap: `adb exec-out screencap -p > mX_live.png`.
   - WinRT OCR: Quét 100% text trên màn hình xem có xuất hiện captcha thật không hay chỉ là Home Feed bình thường.
3. **Đối soát Danh sách Nick trên Account Switcher (Bằng chứng tối thượng):**
   - Vào tab Hồ sơ: tap `(972, 1857)` (hoặc ATX node `:id/oly`).
   - Vuốt nhẹ 400px (`input swipe 540 1200 540 800 200`) -> tap sticky header giữa đỉnh `(500, 140)` để bung sheet "Chuyển đổi tài khoản".
   - Screencap `mX_switcher.png` + WinRT OCR đọc danh sách nick.
   - So khớp với danh sách gán máy trong `taikhoan_run_safe.xlsx`.
4. **Kết luận & Nghiệm thu:**
   - Nếu đủ 100% tài khoản trên Switcher: Xác nhận là Transient False-Positive do `verify-bar-close` chạm từ khóa feed.
   - Đính kèm `MEDIA:D:/Taadaa/reports/mX_switcher.png` chứng minh phiên đăng nhập còn nguyên vẹn 100%.
   - Gửi `input keyevent 3` (HOME) đưa thiết bị về trạng thái nghỉ.
