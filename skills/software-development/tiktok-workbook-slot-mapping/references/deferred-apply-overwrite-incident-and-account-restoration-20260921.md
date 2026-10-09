# Sự Cố Ghi Đè Xóa Nick Cũ Khi Nạp Deferred Apply & Quy Trình Khôi Phục Toàn Diện (2026-09-21)

## 1. Bối cảnh & Cơn thịnh nộ của User
- **Hiện tượng**: Trong đợt Preflight Reg Bù Row 7 ngày 21/09/2026, hàng loạt máy (M20, M22, M27, M32, M36, M37, M46, M48, M55...) bị báo lỗi:
  - Máy 27, 37: `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`
  - Máy 20, 46, 63: `Timeout cho login`
- **Khảo sát hiện trường $O(1)$**:
  - Trên điện thoại thật: TikTok đã đăng nhập đủ 8 tài khoản (kịch trần 8 nick của app), Account Switcher tự động ẩn nút *"Thêm tài khoản"*.
  - Trên file Excel tracking (`taikhoan_dat_v2_updated .xlsx`): Hàng Row 7 hoặc Row 8 của các máy này lại đang để trống (`None, None, None...`).
  - Khi tra cứu ngược log: Phát hiện nick cũ hợp lệ đã từng tồn tại trên máy (ví dụ `@chaunpnlb0i` M27, `@walterhflore28` M37) đã bị các nick mới reg ghi đè lên hàng trên, xóa sạch dấu vết trên Excel trong khi ô dưới cùng bị bỏ trống!
- **Phản ứng của User**:
  > *"Khôi phục nick đó vào đúng tick của nó, nick ms reg đẩy xuống hàng dưới. Đm sao lại óc chó tới mức điền đè xoá nick cũ là sso. Quét luôn xem còn nick nào bị xoá oan k. Tao bực lắm r đó, đéo hiểu sao tự xoá nick cũ, tài sản của tao đi xoá đkm"*

---

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Lỗi logic trong cơ chế Deferred Apply / Remap**:
   - Khi một đợt reg bổ sung hoàn tất, script nạp dữ liệu vào Excel không tìm ô trống ở cuối máy (Slot 7 hoặc 8), mà bị lệch chỉ số hoặc ghi đè trực tiếp vào các hàng slot trên (thường rơi vào Slot 3, Slot 5).
   - Nick mới đè bẹp nick cũ. Ô phía dưới cùng vẫn `None`.
2. **Hệ quả dây chuyền (Domino Effect)**:
   - File Excel bị thiếu dòng $\rightarrow$ Detector `_detect_clean.py` đọc Excel thấy thiếu slot $\rightarrow$ Cử máy đi reg bù $\rightarrow$ Thực tế trên điện thoại app TikTok đã đủ 8 nick $\rightarrow$ Ẩn nút "Thêm tài khoản" $\rightarrow$ Crash batch reg.
3. **Pop-up USB Debugging (`UsbDebuggingActivity`)**:
   - Xuất hiện ngẫu nhiên che mất foreground của TikTok ngay sau bước nhập OTP, khiến `wait_login_success` kẹt chờ và timeout 30s.
4. **Obfuscated Resource-ID TikTok app**:
   - TikTok v30+ đổi resource-id text tài khoản sang `ndk`, khiến bộ đếm 8 account trong `social_reg_v1.py` bị đếm = 0, ném lỗi thiếu nút thay vì ném `MACHINE_FULL_8_ACCOUNTS`.
5. **Lệch công thức Folder Video Admin Master vs Tik1..Tik8**:
   - Bên Admin (Máy 201..280) Folder Video được đánh số từ $1 \rightarrow 640$ (`Tik1..Tik8.xlsx`).
   - Script Kibe đem sang nạp dùng công thức tuyệt đối toàn farm: `(stt - 1) * 8 + slot` khiến Folder Video bị ghi thành `2106, 2108, 1624...`.

---

## 3. Kết quả Quét Đối Soát Toàn Farm (Kibe & Admin)
1. **Cụm Kibe (166 Bản Backup)**:
   - Tìm thấy và khôi phục **27 tài khoản** từng bị ghi đè / mất dấu trên Excel về đúng vị trí slot gốc. Đẩy các nick mới reg xuống slot 7 và slot 8.
   - `_detect_clean.py` đạt `Targets: 0` trên 624 mailboxes sạch.
2. **Cụm Admin (Backup `.bak_final.xlsx`)**:
   - Phát hiện **70 tài khoản** bị ghi đè nhầm ở Folder 2 và nick lặp trên Máy 264.
   - Khôi phục nguyên vẹn 69 tài khoản Folder 2 và khôi phục `@nhulinh422` vào Folder 2108 Máy 264.
   - Chuẩn hóa toàn bộ 364 Folder Video trong file tổng Admin về dải chuẩn $1 \rightarrow 640$ khớp 100% với 8 file `Tik1..Tik8.xlsx`.
3. **Đối Soát Chéo Toàn Farm**:
   - 0 nick trùng chéo giữa Kibe và Admin.
   - 0 nick ký sinh giữa các máy khác nhau trong nội bộ từng farm.

---

## 4. Kiến Trúc 3 Vòng Bảo Vệ Bất Biến (Anti-Overwrite Hard Guard)

1. **VÒNG 1 — HARD GUARD TẠI RUNNER & DEFERRED WRITER**:
   - Trong `scripts/deferred_tracking_writer.py` và `social_reg_v1.py` (`upsert_tracking_account`):
   - Trước khi gán mảng `values` vào hàng mục tiêu (`check.row` hoặc `target_row`), BẮT BUỘC đọc trước giá trị hiện có: `existing_id`, `existing_pass`, `existing_mail`.
   - LƯU Ý LỖ HỔNG LOGIC QUAN TRỌNG (Phải bao phủ cả trường hợp email cũ bị trống):
     BẮT BUỘC dùng điều kiện: `(existing_id or existing_pass) and (not existing_mail or existing_mail != new_mail)`
     Nếu chỉ dùng `and (existing_mail and existing_mail != new_mail)` thì khi email cũ để trống, guard sẽ bị bypass và làm mất ID/PASS cũ!
   - Nếu điều kiện trên thỏa mãn:
     + Trong `deferred_tracking_writer.py`: Lập tức chặn ghi và trả về:
       `TrackingWriteResult("BLOCKED_DATA_CONFLICT", blocker=f"OVERWRITE_REJECTED_EXISTING_ACCOUNT_{existing_id}_{existing_mail}")`
     + Trong `social_reg_v1.py`: Raise ngay:
       `RuntimeError(f"CRITICAL_OVERWRITE_PREVENTED: Cannot overwrite existing account @{ex_row_id} ({ex_row_mail}) at row {target_row} with new email {incoming_mail}")`
2. **VÒNG 2 — CẤM TUYỆT ĐỐI `delete_rows` VÀ `insert_rows` TRÊN TRACKING**:
   - Cấu trúc 8 hàng dọc của từng máy là bất biến. Cấm mọi script tự ý xóa/chèn hàng dọc làm trồi sụt số thứ tự dòng của các máy phía sau.
   - Cho phép tự do bổ sung các cột ngang (Columns).
3. **VÒNG 3 — NHẬN DIỆN CHUẨN MÁY ĐỦ 8 TÀI KHOẢN (`MACHINE_FULL_8_ACCOUNTS`)**:
   - Bổ sung resource-id mới (`ndk`) vào bộ đếm tài khoản của TikTok app (`_acc_count >= 8`).
   - Khi máy đã đủ 8 nick trên thiết bị, tool tự động ngắt và đóng popup về Home an toàn, không cố reg thêm nick thứ 9.
4. **VÒNG 4 — TỰ ĐỘNG DẬP POP-UP USB DEBUGGING**:
   - Hàm `dismiss_usb_debugging_dialog` tự động tick *"Luôn cho phép từ máy tính này"* và tap `OK` khi phát hiện `UsbDebuggingActivity`, khôi phục foreground cho TikTok.
