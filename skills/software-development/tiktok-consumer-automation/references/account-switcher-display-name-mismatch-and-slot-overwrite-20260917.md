# Account Switcher Display Name vs Handle Mismatch & Shift Overwrite Pitfall (2026-09-17)

## 1. Hiện tượng & Triệu chứng lỗi (Alert)
- Hàng loạt máy (11-20% batch, e.g. M1, M14, M50, M51, M59, M60, M66, M71, M74) dừng phiên với chữ ký:
  `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
- Khi auto-reconcile (`reconcile_tiktok_accounts.py`) nhảy vào cứu thì bị **Timeout 900s** hoặc **Exit Code 4** (`Máy đã có 8/16 tài khoản — đạt giới hạn tối đa 8`).
- Màn hình thiết bị thực tế vẫn đang có đủ tài khoản và đang ở trạng thái an toàn.

## 2. Root Cause 1: Display Name vs Username Handle Mismatch
- **Thực tế trên UI TikTok:** Trong menu bottom sheet "Chuyển đổi tài khoản" (`account switcher`), TikTok thường ưu tiên hiển thị **Tên hiển thị (Display Name)** (ví dụ: `"Anh Hoang"`, `"Anh Pham"`, v.v.) thay vì handle `@username` (ví dụ: `hong.bo.anh83`, `ngc.anh.phm33`).
- **Matcher Bug trong code:** Hàm `matches_switcher_identity(node_value, expected_account)` chỉ so khớp text node với `expected_account` (dạng handle `@...`), chỉ hỗ trợ rstrip số hoặc prefix.
  Khi đem `"Anh Hoang"` so sánh với `"hong.bo.anh83"` -> trả về `False`.
- **Hệ quả dây chuyền:** Runner kết luận nhầm là máy bị thiếu tài khoản -> kích hoạt `_maybe_recover_missing_account_via_login` -> cố gắng đăng nhập lại tài khoản vốn đã có trên máy -> máy đã kẹt trần 8 nick nên không có nút "Thêm tài khoản" -> script kẹt cứng và crash.

## 3. Root Cause 2: Shift / Ghi đè Slot thô bạo trên Excel
- Tool reg bù (`ensure_row_accounts.py` hoặc migration scripts) khi thấy thiếu nick đã tính toán lại index `(m-1)*8 + slot` và **ghi đè thẳng vào file master Excel** mà KHÔNG kiểm tra trạng thái thực tế trên app TikTok của điện thoại.
- Nick cũ (ví dụ `ahmetsguthe17` trên M1) bị ghi đè mất khỏi file Excel (trở thành nick mồ côi), nhưng trên máy thật **CHƯA HỀ BỊ LOGOUT**.
- Hệ quả: Nick cũ vẫn chiếm 1 trong 8 slot tối đa của app TikTok -> app hết slot, mất nút "+ Thêm tài khoản", gây lỗi cascade cho toàn bộ quy trình nuôi và login.

## 4. Quy tắc vận hành & Khắc phục
1. **CẤM GHI ĐÈ EXCEL KHI CHƯA LOGOUT TRÊN MÁY THẬT:** Tuyệt đối không xóa/đè dòng tài khoản trên Excel khi nick đó vẫn đang login trên app TikTok của thiết bị. Muốn thay nick, bắt buộc phải qua quy trình: Logout trên máy thật -> verify switcher đã nhả slot -> mới update Excel.
2. **RESOLVE DISPLAY NAME TRƯỚC KHI KẾT LUẬN THIẾU NICK:** Khi so khớp trong Switcher, nếu không thấy match handle, runner phải tra cứu Display Name tương ứng của nick đó trong metadata master (`taikhoan_dat_v2_updated .xlsx`), hoặc tap vào ứng viên để vào màn Profile root đọc handle thật (`:id/sr3` hoặc sticky header) trước khi kích hoạt login recovery.
3. **CẤM TỰ TIỆN LOGOUT NICK ROW 1/ROW 2:** Các nick đang nuôi ổn định tuyệt đối không được logout hay xóa data app, đặc biệt khi chưa xác minh tình trạng sống/chết của Gmail/Hotmail liên kết.
