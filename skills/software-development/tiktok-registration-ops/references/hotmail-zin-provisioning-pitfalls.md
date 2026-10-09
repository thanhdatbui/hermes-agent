# Quy Tắc & Cạm Bẫy Cấp Mail Hotmail Zin Cho Batch Reg TikTok

## 1. Yêu Cầu Bắt Buộc: Phải Là Mail ZIN Chưa Qua Dịch Vụ
- **Tiêu chí tối cao:** Tuyệt đối KHÔNG BAO GIỜ chọn mua các sản phẩm ghi *"Hàng qua TikTok"*, *"Hàng qua reg TikTok"*, *"Hàng qua dịch vụ"* dù có hỗ trợ OAuth2 / Graph API.
- **Hậu quả:** Mail đã qua TikTok khi đưa vào farm reg sẽ lập tức bị chặn, báo tài khoản/email đã tồn tại hoặc checkpoint văng lỗi.
- **Yêu cầu chuẩn:** Hotmail/Outlook **ZIN / CHƯA QUA DỊCH VỤ** (Graph API OAuth2 format: `Email|Pass|RefreshToken|ClientID|RecoveryEmail`).

## 2. Cạm Bẫy Báo Cáo "Cooldown Ảo" Khi Hết Mail Trong Kho
- Trong `ensure_row_accounts.py`, hàm `send_telegram_summary` tính toán:
  `cooldown_stts = sorted([m for m in missing if m not in ran_stts])`
- Nếu `buy_hotmail.py` gặp sự cố hết hàng (Stock: 0) hoặc ID sản phẩm không tồn tại nhưng lại thoát Exit Code 0 (nuốt lỗi), script tiếp tục chạy `_run_all_targets.py`.
- Do máy thiếu thực tế không có mail trong `gmail_clean_v2.xlsx`, nó bị loại khỏi batch chạy (`ran_stts` không có máy này).
- Cuối cùng, script tự động gom máy này vào `cooldown_stts` và gửi thông báo Telegram:
  `⏸️ Bỏ qua / Cooldown (N): <machine>`
- **Quy tắc điều tra:** Khi thấy Farm báo Preflight Reg bù bị Cooldown, ĐỪNG vội tin là máy dính cooldown, BẮT BUỘC kiểm tra:
  1. Ngày tạo `created_date` trên `taikhoan_dat_v2_updated .xlsx` có đúng là hôm nay không.
  2. Số lượng mail khả dụng trong `gmail_clean_v2.xlsx` cho máy đó.
  3. Tồn kho và trạng thái mua mail của BoxTaiKhoan / CloneFBIG.

## 3. Giải Pháp Tái Phân Bổ Mail Zin Khi Sàn Hết Hàng
- Khi cả CloneFBIG và BoxTaiKhoan đều hết hàng Hotmail Zin:
  - Quét `gmail_clean_v2.xlsx` đối soát với `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx`.
  - Tìm các máy **đã đạt 8/8 tài khoản TikTok** trên Farm nhưng vẫn còn tồn dòng Hotmail Zin chưa sử dụng (token Microsoft Graph API live 100%).
  - Chuyển gán số máy ở cột A sang máy đang thiếu slot để kích hoạt reg bù ngay lập tức mà không phải chờ nhà cung cấp restock.
