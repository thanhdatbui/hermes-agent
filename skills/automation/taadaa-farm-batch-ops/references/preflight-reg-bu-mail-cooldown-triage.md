# Preflight Reg Bù: Chẩn Đoán Lỗi Báo Oan Cooldown & Mua Mail Hết Stock

## 1. Bản chất cơ chế Preflight Reg Bù (`ensure_row_accounts.py <row>`)
- Trước mỗi ca nuôi, script quét các máy thiếu tài khoản ở Row đó trong `taikhoan_run_safe.xlsx`.
- Nếu phát hiện máy thiếu:
  1. Kiểm tra mail có sẵn trong `gmail_clean_v2.xlsx`.
  2. Nếu máy chưa có mail $\rightarrow$ Tự động gọi `buy_hotmail.py` để mua Hotmail OAuth2 nạp vào máy.
  3. Kích hoạt `_run_all_targets.py` để reg TikTok cho danh sách máy thiếu.
  4. Merge kết quả vào master workbook và sync sang safe workbook.

## 2. Điểm mù gây lỗi "Báo cáo láo Cooldown"
1. **Kho mail hết stock / lỗi catalog:**
   - BoxTaiKhoan lỗi catalog Product 129.
   - CloneFBIG hết sạch tài khoản (Stock: 0).
2. **Lỗi Silent Zero Purchase trong `buy_hotmail.py`:**
   - Khi không mua được tài khoản nào, hàm mua kết thúc và script thoát với **Exit Code 0** (thay vì exit code 1).
3. **Phân loại nhầm trạng thái trong `ensure_row_accounts.py`:**
   - `ensure_mail_for_machines` thấy return code 0 nên tiếp tục gọi `run_tiktok_reg_for_machines`.
   - Vào batch reg, máy không có mail nên không được đưa vào `ran_stts`.
   - Script Telegram summary tính toán:
     `cooldown_stts = sorted([m for m in missing if m not in ran_stts])`
   - Dẫn đến việc: Máy thiếu mail không chạy được bị gom nhầm thành `⏸️ Bỏ qua / Cooldown (1): 80`.

## 3. Checklist chẩn đoán O(1)
```bash
# 1. Kiểm tra stock và số dư các kho mail:
python D:/Taadaa/tools/buy_hotmail.py --stock
python D:/Taadaa/tools/buy_hotmail.py --balance

# 2. Kiểm tra danh sách máy cần mail:
python D:/Taadaa/tools/ensure_row_accounts.py <row> --dry-run
```
- Khi user chất vấn về việc báo Cooldown, BẮT BUỘC kiểm tra stock thực tế, cấm đoán mò hay suy diễn lý thuyết.
