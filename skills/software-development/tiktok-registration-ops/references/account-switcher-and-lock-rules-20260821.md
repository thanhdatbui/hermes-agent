# TikTok Reg Operational Rules & Navigation Fixes (2026-08-21)

## 1. Quy ước "Máy rảnh chạy Reg TikTok"
1. **Lịch Cron an toàn:** Cách ca nuôi acc kế tiếp $\ge 60$ phút.
2. **Có mail chờ reg:** Có mail nguồn hợp lệ trong `gmail_clean_v2.xlsx` chưa có TikTok ID trong `taikhoan_dat_v2_updated .xlsx` (chạy `_detect_clean.py`).
3. **VPN / Live IP Bắt Buộc:** Mọi máy chạy phải có VPN hoạt động (`vn.vichanger.app.GET_IP` broadcast trả về `result=200` với IP hợp lệ). CẤM chạy máy chưa có VPN hoặc proxy chết (`result=0`).

## 2. Quy tắc Device Lock trong Vận hành Reg
- Khi chạy batch reg, kích hoạt `DEVICE_LOCK_ENABLED=1`.
- **Nguyên tắc mở khóa:** CHỈ unlock khi:
  - Máy chạy **SUCCESS** hoàn toàn (đã verify profile, lưu tracking workbook, dọn app về Home).
  - Hoặc khi **User trực tiếp ra lệnh** mở khóa.
- Mọi trường hợp dừng lỗi/chờ OTP/blocker: giữ nguyên lock và giữ nguyên hiện trường màn hình.

## 3. Account Switcher Navigation (TikTok 46.x Profile Layout)
- **Cơ chế Sticky Bar:** Ở UI TikTok 46.x, header profile có thanh sticky switcher. Khi vào tab Hồ sơ mà không thấy dropdown `rv5`:
  - Vuốt lên 400px (`swipe(540, 1000, 540, 600, 400)`) để đẩy header lên sát top.
  - Bấm vào sticky bar (`pcs`, `p7w`, `pmh`, `p01`, `p1j`, `qx0`, `qzr`, hoặc `[450,72][630,228]`).
- **Xử lý popup can thiệp:**
  - Bỏ qua các text node `"Thêm tiểu sử"` (tránh bị click nhầm mở trình soạn thảo bio).
  - Tự động đóng dialog hệ thống *"Chọn bàn phím"* (Select input method) bằng phím Back nếu xuất hiện.
