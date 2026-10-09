# Xử Lý Lỗi Văng/Thiếu Nick (account-switcher-missing-expected) & Đồng Bộ Mapping Database (2026-09-23)

## 1. Bản chất sự cố & Bài học từ User Steering
Khi ca nuôi acc / lướt feed TikTok phát Batch Alert:
`manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
- **User Steering Invariant**: CẤM Coordinator chỉ dừng lại ở việc inspect O(1) rồi báo cáo phân tích lý thuyết. Khi phát hiện máy thiếu nick hoặc nghi văng nick, BẮT BUỘC phải chủ động gọi script nạp lại chính thức của farm (`tiktok_login_v1.py` trong `D:/Taadaa/Tiktok_Reg`).
- **Nguyên nhân cốt lõi gây false alarm "văng nick"**:
  1. Nick không hề bị văng khỏi app TikTok, mà do vị trí `tik` trong Database SQLite (`tiktok_tracker.db` bảng `farm_account_info` và `account_mapping`) bị lệch so với thứ tự slot trong workbook `taikhoan_run_safe.xlsx` (ví dụ: máy 32 slot 7 nhưng DB lại ghi slot 3).
  2. Máy đã đủ 8 nick (`MACHINE_FULL_8_ACCOUNTS`), nick cần tìm vốn đã đăng nhập sẵn nhưng đang ở trạng thái active trên màn hình hoặc nằm ngoài viewport của Switcher khi danh sách có độ trễ render trên máy yếu (S7).

## 2. Vì sao cơ chế auto-login trong feed_swipe_smoke.py bị nghẽn?
Hàm `_maybe_recover_missing_account_via_login` trong `feed_swipe_smoke.py` gọi subprocess `reconcile_tiktok_accounts.py` qua `D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe`. Môi trường này bị nhiễm thư viện chéo từ Python 3.12 (`ImportError: cannot import name '_imaging' from 'PIL'`), dẫn đến tiến trình reconcile ngầm crash `returncode != 0`.

## 3. Quy trình chuẩn xử lý alert mất phiên / văng nick
1. **Kiểm tra hiện trường O(1) qua Switcher**:
   - Mở Profile -> Tap header Switcher -> Chụp ảnh nghiệm thu `MEDIA:`.
   - Đọc danh sách nick thực tế đang có trên app.
2. **Kiểm tra độ đầy đủ 8 slot & đối soát**:
   - Nếu máy đã có 8 nick: Đối chiếu với `taikhoan_run_safe.xlsx`. Nếu nick báo thiếu đã có trên máy -> Cập nhật lại snapshot DB / mapping và kết luận an toàn.
   - Nếu máy thiếu nick: Kích hoạt subagent chạy ngay:
     `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID_hoặc_email> --ss`
3. **Đồng bộ hóa Mapping Database SQLite**:
   - Đảm bảo `farm_account_info` và `account_mapping` trong `D:/Taadaa/data/tiktok_tracker.db` có giá trị cột `tik` (slot 1..8) trùng khớp 100% với số thứ tự ca chạy của workbook `Tik1.xlsx` .. `Tik8.xlsx` và `taikhoan_run_safe.xlsx`.
