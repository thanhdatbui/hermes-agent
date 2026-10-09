# Quy Tắc Event-Driven Watchdog Cho Máy Dính Nick Ký Sinh & Kỷ Luật Canh Máy Rảnh

## 1. Bản chất sự cố
- Khi phát hiện nick trùng lặp (nick ký sinh do log nhầm giữa các máy), tuyệt đối **KHÔNG ĐƯỢC ĐOÁN MÒ KHUNG GIỜ** hay **HẸN GIỜ CỐ ĐỊNH** (ví dụ hẹn 23h30, hẹn sau ca tối...).
- Các ca nuôi feed, reg Gmail, add 2FA chạy cuốn chiếu trên 80 máy với thời lượng động. Hẹn giờ cố định sẽ dẫn đến 2 thảm họa:
  1. **Bị trôi giờ / quá hạn:** Nghĩ là máy rảnh nhưng thực tế ca khác đã vào chạy.
  2. **Tranh chấp lock & phá hoại ca nuôi chính:** Chen ngang vào máy đang chạy làm đụng độ ADB, treo app, văng lỗi cho runner chính.

## 2. Kỷ luật Event-Driven Watchdog (BẮT BUỘC)
Khi user yêu cầu: *"Canh máy rảnh thì vào làm"*:
1. **Tạo ngay cron watchdog thăm dò liên tục (`*/2 * * * *`):**
   - Script watchdog phải là `no_agent: true` chạy độc lập, nhẹ và an toàn.
   - Tuyệt đối CẤM hứa mồm mà không deploy script vào scheduler.
2. **Kiểm tra Device Lock theo từng máy mục tiêu (Granular Device Lock):**
   - Không cần phải chờ toàn bộ 80 máy cùng rảnh nếu task chỉ can thiệp trên 1 vài máy cụ thể (ví dụ M69).
   - Kiểm tra trực tiếp file lock của máy đó trong `~/.codex/device-locks/`:
     - `machine_<ID>.lock.json`
     - `serial_<SERIAL>.lock.json`
   - Khi cả 2 file lock này **KHÔNG TỒN TẠI** -> Xác nhận máy mục tiêu đang rảnh 100%.
3. **Thực thi dứt điểm ngay khi phát hiện máy rảnh:**
   - Mở app TikTok qua monkey/intent.
   - Mở Account Switcher.
   - Switch sang đúng nick ký sinh.
   - Vào Profile -> Menu 3 gạch -> Cài đặt và quyền riêng tư -> Cuộn đáy -> Đăng xuất -> Xác nhận Đăng xuất.
   - Mở lại Switcher kiểm tra xem nút **"Thêm tài khoản"** (Add Account) đã hiện lại chưa.
   - Chụp screencap bằng chứng nghiệm thu (`MEDIA:...`).
   - Ghi nhận state file (ví dụ `parasite_reconcile_state.json`) để watchdog tự động ngắt, không chạy lại lần 2.

## 3. Quy trình đối soát nick trùng trên toàn farm (O(1) Memory / Dump)
- Kiểm tra các file dump XML UI `fail_04_add_account_*.xml` trong `artifacts/ui_dumps/` kết hợp so sánh với `taikhoan_dat_v2_updated .xlsx`.
- Nếu 1 tài khoản xuất hiện trong Switcher của máy A nhưng trong Excel lại thuộc về máy B:
  - Máy B là máy chính chủ.
  - Máy A là máy bị ký sinh -> Phải đưa máy A vào danh sách TARGETS của Event-Driven Watchdog để logout ngay khi máy A rảnh.
