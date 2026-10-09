# Account Switcher Display Name vs Handle Mismatch & Excel Shift Overwrite Trap (2026-09-17)

## Bối cảnh
Khi chạy feed session hoặc login reconcile trên farm TikTok, runner gặp hàng loạt lỗi `account-switcher-missing-expected: expected account not found in account switcher`.

## 2 Vấn đề gốc rễ phát hiện (Root Causes)

### 1. Matcher Bug: Display Name vs Handle (`@username`)
- **Hiện tượng**: TikTok lưu danh sách tài khoản trong Account Switcher sheet (`:id/lrq`, `:id/lkp`) với text/content-desc hiển thị là **Tên hiển thị (Display Name tiếng Việt)** thay vì Handle `@username`. Ví dụ:
  - Máy 14: Display Name `"Anh Hoang"` vs Handle `@hong.bo.anh83`.
  - Máy 71: Display Name `"Anh Pham"` vs Handle `@ngc.anh.phm33`.
- **Root cause**: Hàm `matches_switcher_identity` ban đầu chỉ so khớp chuỗi trực tiếp hoặc prefix/suffix số (`crystal.1.1` vs `crystal.1.15`). Khi so sánh `"Anh Hoang"` với `"hong.bo.anh83"`, hàm trả về `False`.
- **Hệ quả**: Runner tưởng nhầm tài khoản bị thiếu trên máy $\rightarrow$ kích hoạt `_maybe_recover_missing_account_via_login` cố login lại $\rightarrow$ máy đã đủ 8 tài khoản (không có nút "Thêm tài khoản") $\rightarrow$ timeout 15 phút, báo lỗi hệ thống.
- **Giải pháp**: Bổ sung cơ chế so khớp token overlap (`_clean_alpha_tokens` loại bỏ dấu tiếng Việt và ký tự đặc biệt). Nếu các token chữ của Display Name khớp đầy đủ vào các token chữ của username/email hoặc ngược lại, coi như trùng khớp danh tính.

### 2. Excel Slot Overwrite Trap (Ghi đè slot Excel mù quáng)
- **Hiện tượng**: Tài khoản cũ đang nuôi (như `ahmetsguthe17` trên Máy 1) biến mất khỏi master workbook `taikhoan_dat_v2_updated .xlsx` nhưng vẫn tồn tại trên app TikTok của máy thật.
- **Root cause**: Script reg bù (`ensure_row_accounts.py` hoặc các đợt dồn slot) tính toán vị trí dòng theo công thức `(m - 1) * 8 + slot` rồi ghi đè thẳng dữ liệu tài khoản mới vào Excel mà không kiểm tra tình trạng thực tế trên app TikTok.
- **Hệ quả**:
  - Tài khoản cũ không bị logout trên app, trở thành "nick mồ côi" chiếm dụng slot của máy.
  - Máy chạm trần 8 nick, mất nút "Thêm tài khoản".
  - Các lần login tài khoản mới sau này đều thất bại vì app không còn chỗ.
- **Quy tắc bất di bất dịch**:
  1. CẤM TUYỆT ĐỐI ghi đè hoặc shift slot trong Excel khi chưa đối soát và logout thực tế trên app TikTok.
  2. Bất kỳ thay đổi danh sách tài khoản nào trên Excel phải đi kèm thao tác trên thiết bị thật: kiểm tra switcher, logout nick cũ nếu cần, xác nhận nút "Thêm tài khoản" xuất hiện trở lại.
