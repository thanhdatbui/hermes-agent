# Case UI-67: Thảm họa Update TikTok đè 47.0.3 văng Switcher bắt 2FA OTP Hotmail & Lệnh khóa Auto-update Google Play

## 1. Hiện tượng thực tế trên Máy 38 (2026-09-20)
Khi dùng `adb install-multiple -r -d` cài đè gói TikTok 47.0.3 (Split APKs) lên máy 38 đang chạy 46.9.3:
1. **Lần đầu khởi động bị Crash (Văng app):**
   - Logcat báo lỗi: `java.lang.ClassNotFoundException: Didn't find class "X.1OEX"`.
   - Nguyên nhân: Dynamic feature dex của Split APK chưa tương thích kịp với Android 8 trên Samsung S7.
2. **Văng toàn bộ tài khoản trong Switcher (Mất Token / Invalidate Session):**
   - TikTok 47.0.3 thay đổi schema mã hóa SQLite / SharedPreferences cục bộ.
   - Khi vào lại app, TikTok kích hoạt luồng `NewUserJourneyActivity` (Giao diện người dùng mới toanh).
   - Menu Cài đặt & quyền riêng tư **MẤT HOÀN TOÀN NÚT "CHUYỂN ĐỔI TÀI KHOẢN" (SWITCH ACCOUNT)**, chỉ còn trơ trọi nút "Đăng nhập".
   - Khi cố mở phiên tài khoản thì TikTok lập tức chặn lại đòi:
     `Xác minh 2 bước — Nhập mã được gửi đến c***9@hotmail.com`.

## 2. Bài học xương máu cho Phone Farm
- **CẤM TUYỆT ĐỐI UPDATE ĐỒNG LOẠT TOÀN DÀN LÊN BẢN MỚI:**
  - Nếu chạy batch update 80 máy, hơn 600 tài khoản farm sẽ bị logout đồng loạt và bị kẹt sau lớp 2FA Hotmail OTP.
- **TẮT CẬP NHẬT NGẦM GOOGLE PLAY STORE TOÀN BỘ 80 MÁY:**
  - Lệnh tắt auto-update ngầm trên Android:
    `adb shell "settings put global auto_update_apps 0"`
  - Tắt auto-update KHÔNG hề ảnh hưởng tới TikTok hay luồng reg Gmail/Outlook, mà ngược lại bảo vệ layout và token phiên không bị phá vỡ.
- **NGUYÊN TẮC RESILIENT RUNNER (ĐA PHIÊN BẢN):**
  - Runner bắt buộc phải hỗ trợ song song các selector của cả bản 46.x (`id/fm9`) và bản 47.x (`id/fmp`).
  - Không được ép máy chạy theo 1 bản duy nhất bằng cách update đè mạo hiểm.
