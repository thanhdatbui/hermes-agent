# Quy Trình Bù Mail & Đối Soát Sức Chứa Tài Khoản (TikTok Reg Ops)

## 1. Cơ Chế Atomic Save Cho File Excel
- Trong batch reg và các công cụ quản lý tài khoản (`ensure_row_accounts.py`, `apply_deferred_tracking_results.py`), thao tác ghi file trực tiếp `wb.save()` dễ bị đứt gãy hoặc crash/lock bởi OneDrive sync, gây lỗi hỏng zip (`KeyError: 'xl/workbook.xml'`).
- Bắt buộc áp dụng cơ chế lưu Atomic Save:
  ```python
  tmp_file = target_file.with_suffix(".tmp.xlsx")
  wb.save(tmp_file)
  tmp_file.replace(target_file)
  ```
- Luôn kiểm tra file backup `.bak_<timestamp>` khi phát hiện file Excel bị giảm dung lượng bất thường (<30KB).

## 2. Kiểm Tra Hiện Trường Khi Bị Báo Động `MACHINE_FULL_8_ACCOUNTS`
- Khi log batch reg báo lỗi `MACHINE_FULL_8_ACCOUNTS`, **KHÔNG** được vội kết luận máy đã đầy 8 nick để logout bừa bãi.
- Thường do popup story/daily prompt hoặc click trượt khiến switcher không hiển thị đầy đủ, che mất nút *"Thêm tài khoản"*.
- **Cách đối soát chuẩn**:
  - Dùng lệnh `python D:/Taadaa/tools/inspect_machine.py <M>` kiểm tra focus.
  - Forward port `atx-agent` (7912): `adb -s <serial> forward tcp:179xx tcp:7912`.
  - Gọi `/dump/hierarchy` để đếm chính xác số lượng `@username` và kiểm tra sự tồn tại của node *"Thêm tài khoản"*.
  - Nếu thực tế chỉ có 7 tài khoản, nút *"Thêm tài khoản"* vẫn hiển thị bình thường, nguyên nhân do dismiss popup chưa triệt để trong flow.

## 3. Bổ Sung Mail Sạch Bằng `buy_hotmail.py` (CloneFBIG Fallback)
- Khi `ensure_row_accounts.py` báo thiếu mail sạch trong `gmail_clean_v2.xlsx`:
  - Kiểm tra số dư và kho hàng:
    `python D:/Taadaa/tools/buy_hotmail.py --provider clonefbig --stock`
  - Nạp trực tiếp cho cụm Kibe hoặc Admin:
    `python D:/Taadaa/tools/buy_hotmail.py --provider clonefbig --append-kibe <N> --target-machines <M1,M2...>`
  - Mail được Graph API verify LIVE trước khi ghi, bảo đảm tỷ lệ reg thành công cao.
