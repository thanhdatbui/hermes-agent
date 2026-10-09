# Kỷ Luật Lưu Trữ Excel & Đối Soát Sức Chứa Thiết Bị (Farm Ops)

## 1. Cơ Chế Atomic Save Cho File Excel (Chống Corrupt Workbook)
- **Vấn đề**: File dữ liệu farm (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `gmail_clean_v2.xlsx`) thường xuyên đồng bộ qua OneDrive hoặc được truy cập đồng thời bởi nhiều scripts/runners. Lệnh `wb.save(target_path)` trực tiếp rất dễ bị lỗi nếu tiến trình bị kill, timeout hoặc OneDrive sync lock giữa chừng, làm file bị teo về 1-2 KB và hỏng cấu trúc zip (`KeyError: 'xl/workbook.xml'`).
- **Quy tắc bắt buộc**: Mọi script sửa/ghi đè file workbook Excel bắt buộc phải:
  1. Sao lưu backup file trước khi ghi: `shutil.copy2(target, f"{target}.bak_{ts}")`.
  2. Áp dụng **Atomic Write**: Lưu ra file tạm cùng thư mục `.tmp.xlsx`, sau đó dùng `replace` để hệ điều hành hoán đổi file tức thời:
     ```python
     tmp_path = target_path.with_suffix(".tmp.xlsx")
     wb.save(tmp_path)
     tmp_path.replace(target_path)
     ```
  3. Khôi phục nhanh khi gặp file lỗi: Nếu file chính bị hỏng, kiểm tra ngay file `.bak_<timestamp>` gần nhất có dung lượng hợp lệ (>35KB) và copy đè lại.

---

## 2. Phòng Ngừa Báo Động Giả `MACHINE_FULL_8_ACCOUNTS` (Anti-False-Positive)
- **Hiện tượng**: Runner hoặc log đăng ký báo `MACHINE_FULL_8_ACCOUNTS` và bỏ qua máy, nhưng thực tế trong app mới chỉ có 7 tài khoản.
- **Nguyên nhân**: 
  - Các modal popup chen ngang (như Daily prompt, Story prompt, Chia sẻ vị trí, Đề xuất kết bạn) che khuất footer của Account Switcher.
  - OCR nhận diện bị trượt hoặc click mở dropdown bị trượt vào vùng trống/header.
- **Quy tắc xử lý**:
  - **CẤM TUYỆT ĐỐI** vội vàng chạy script logout tài khoản khi chỉ nhìn vào log cũ hoặc lỗi `MACHINE_FULL_8_ACCOUNTS`.
  - **Bắt buộc kiểm tra hiện trường O(1)**: 
    1. Forward cổng atx-agent: `adb -s <serial> forward tcp:179xx tcp:7912`.
    2. Dump hierarchy XML thực tế qua `/dump/hierarchy`.
    3. Đếm số lượng node `@username` thực tế và tìm text `"Thêm tài khoản"` / `"Chuyển đổi tài khoản"`.
    4. Chỉ thực hiện quy trình giải phóng slot/logout khi và chỉ khi hierarchy XML xác nhận 100% đã có đủ 8 nick và nút "Thêm tài khoản" hoàn toàn biến mất.

---

## 3. Cấp Bù Mail Sạch Cho Máy Thiếu (Hotmail OAuth2)
- Khi chạy `ensure_row_accounts.py <row> --dry-run` phát hiện máy thiếu acc và kho `gmail_clean_v2.xlsx` không còn mail sạch khả dụng cho máy đó:
  - Kiểm tra số dư và kho cung cấp qua `buy_hotmail.py`:
    ```bash
    python D:/Taadaa/tools/buy_hotmail.py --balance
    python D:/Taadaa/tools/buy_hotmail.py --provider clonefbig --stock
    ```
  - Nếu `boxtaikhoan` hết số dư, dùng provider `clonefbig` (kho hàng nghìn mail, giá 270đ/acc) để mua và nạp trực tiếp vào máy:
    ```bash
    python D:/Taadaa/tools/buy_hotmail.py --provider clonefbig --append-kibe 1 --target-machines <M>
    ```
  - Tool tự động kiểm tra token Microsoft Graph API (`access_token OK`) trước khi append, đảm bảo mail nạp vào là LIVE 100%.
