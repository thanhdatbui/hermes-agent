# Quy trình xử lý Nick ký sinh (Parasite Account) và Đồng bộ Excel Farm

## 1. Bản chất sự cố
- Khi một nick được đăng nhập hoặc đăng ký nhầm trên máy khác (ví dụ nick thuộc máy này nhưng nằm trên Switcher máy khác), nó biến thành **nick ký sinh** làm đầy trần cứng 8 nick trên thiết bị bị chiếm dụng.
- Khi dính nick ký sinh, các luồng tự động (reg nick mới, feed-session, follow) sẽ bị nghẽn hoặc lỗi trần 8 nick.

## 2. Quy trình đồng bộ Excel 2 tầng
Khi bổ sung (backfill) nick mới thay thế hoặc cập nhật slot trên máy:
1. **File `taikhoan_dat_v2_updated .xlsx`**:
   - Xác định đúng dòng dựa trên `Máy` (Cột A) và `STT` / `Folder Video` (Cột B).
   - Cập nhật Cột C (`ID`), Cột F (`GMAIL`), Cột G (`PASS MAIL`).
   - Giữ nguyên `device ID` và các trường ngày tháng.
2. **File `taikhoan_run_safe.xlsx`**:
   - Khớp theo `May` (Cột A, lưu ý định dạng có thể là str hoặc int) và slot tương ứng.
   - Cập nhật Cột C (`ID`).
3. **Lưu ý định dạng**: File path có khoảng trắng trước đuôi `.xlsx` (`taikhoan_dat_v2_updated .xlsx`), cần dùng raw string hoặc đúng đường dẫn.

## 3. Quy trình Đăng xuất nick ký sinh an toàn
- **Công cụ sẵn có**:
  - `D:/Taadaa/tools/do_logout_account.py <machine_id> <username> <serial>`
  - `D:/Taadaa/tools/watchdog_idle_parasite_reconcile.py` (hỗ trợ cờ `--machine <id>`)
- **Tối ưu vòng lặp & thời gian thực thi (Iteration / Timeout budget)**:
  - Tránh duyệt preflight toàn diện qua nhiều máy trong một hàm lặp dài (dễ bị timeout 180s do atx-agent retry / preflight).
  - Kiểm tra lock nhanh qua `~/.codex/device-locks/machine_{id}.lock.json`.
  - Chạy trực tiếp `do_logout_account.py` theo từng máy hoặc background/async khi có nhiều máy cần logout.
  - **Bằng chứng nghiệm thu bắt buộc (Gate 6)**: Sau khi logout, BẮT BUỘC mở lại Account Switcher và chụp screencap tại chính **Account Switcher Bottom Sheet** (`D:/Taadaa/reports/m{machine_id}_verified_logout.png`). CẤM TUYỆT ĐỐI gửi ảnh màn hình Cài đặt hay Profile làm ảnh nghiệm thu dọn ký sinh.
  - **Cạm bẫy Python XML Element Boolean**: Trong `xml.etree.ElementTree`, một `Element` không có con (children) sẽ đánh giá `bool(elem) == False`. Do đó, kiểm tra `if not target_node:` sẽ bị kích hoạt sai kể cả khi node đã được tìm thấy! BẮT BUỘC dùng cú pháp rõ ràng: `if target_node is None:`.
