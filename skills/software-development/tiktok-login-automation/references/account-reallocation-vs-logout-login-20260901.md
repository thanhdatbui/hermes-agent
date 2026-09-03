# Quy trình Điều chuyển mapping tài khoản thay vì Logout/Login vòng vo (2026-09-01)

## Bối cảnh & Hiện tượng
- Khi chạy phiên nuôi nick đa máy (ví dụ Máy 1 - Ca 3 / Tik5), script dừng phiên với lỗi:
  `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
- Nguyên nhân: Máy 1 đang đăng nhập đủ 6 nick trong app TikTok (`tranngan767`, `lipsellczaw`, `duongkien1202`, `ginnyhanstei80`, `ahmetsguthe17`, `buithudung2011`). Nhưng theo lịch `taikhoan_run_safe.xlsx` và `Tik5.xlsx`, Máy 1 cần chạy `janayerton71` (được reg trước đó ở Slot 5). `buithudung2011` là nick mới reg ngày 25/08 ở Slot 7 (chưa có ca nuôi).

## Chỉ đạo của User & Quy tắc Vận hành
1. **KHÔNG logout/login vòng vo trên thiết bị:**
   - Việc logout tài khoản đang có trên máy để login tài khoản khác rồi lại mang tài khoản bị logout đi login máy khác làm tăng số lần xác minh, dễ dính checkpoint / văng session / checkpoint sai mật khẩu.
2. **Ưu tiên điều chuyển mapping trên 3 file Excel:**
   - Đôn nick có sẵn trên máy (`buithudung2011`) lên Slot 5 (Tik5) của Máy 1. Dọn trống ô Slot 7.
   - Chuyển nick thiếu (`janayerton71`) sang máy khác đang trống slot (ví dụ Máy 61 Slot 5).
   - Đồng bộ ngay 3 file:
     1. `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (Sheet `Tài Khoản`)
     2. `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (Sheet `Accounts`)
     3. `D:\OneDrive\TaadaaData\kibe\Tik5.xlsx` (Sheet `TaiKhoan`)
3. **Chạy tiếp phiên ngay lập tức:**
   - Sau khi cập nhật Excel, xóa stale device lock (nếu có) và chạy lại feed session cho máy gặp sự cố với lệnh canonical:
     `run_tiktok.py --mode multi-machine-feed-session --machines <M> --account-row-index <Row> ...`
   - Máy nhận nick mới chuyển sang sẽ được login bổ sung độc lập khi rảnh.
