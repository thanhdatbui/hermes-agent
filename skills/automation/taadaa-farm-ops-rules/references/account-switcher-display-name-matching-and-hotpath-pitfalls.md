# Account Switcher Display Name vs Handle & Hot-Path Architecture Pitfalls (2026-09-17)

## Bối cảnh Sự cố
- **Triệu chứng:** Farm Alert diện rộng báo `manual-needed:account-switcher-missing-expected: expected account not found in account switcher` trên 9 máy (M1, M14, M50, M51, M59, M60, M66, M71, M74).
- **Phân loại hiện trường thực tế:**
  1. **Hiển thị Display Name thay vì Handle (M14, M71):** Nick `@hong.bo.anh83` hiển thị `"Anh Hoang"`, nick `@ngc.anh.phm33` hiển thị `"Anh Pham"`. Tài khoản **VẪN CÒN NGUYÊN 100% TRÊN MÁY THẬT**, nhưng matcher chỉ so sánh `@username` nên đánh trượt -> kích hoạt auto-login recovery sai mục đích gây kẹt 2FA và trần 8 nick.
  2. **Thiếu nick thật sự (M1, M51, M59, M60, M66):** Trên UI Switcher thực tế không có nick Row 1 do trước đó chạy các batch reg bù / ghi đè slot Excel mà chưa logout/xác nhận trên máy thật.
  3. **Lỗi ngoại cảnh (M50, M74):** M50 offline ADB, M74 vướng popup bảo mật, không liên quan switcher.

## Các Bẫy Kiến Trúc & Bài Học (Từ Closeout Gate AI Review)

1. **CẤM đọc I/O (File/Excel) bên trong hàm Hot-Path Matcher:**
   - `matches_switcher_identity()` là pure function được gọi lặp lại hàng trăm lần trong các vòng lặp duyệt accessibility node XML.
   - **Anti-pattern:** Nhúng `openpyxl.load_workbook()` hoặc đọc file disk bên trong hàm matcher. Điều này gây block CPU, tăng độ trễ quét màn hình và tạo biến mutable global cache không thể invalidate.
   - **Quy tắc:** Mọi dữ liệu phụ trợ (Display Name, Alias mapping từ Master DAT) phải được load trước từ tầng Caller (preflight/context) và truyền vào matcher dưới dạng tham số `known_aliases: set[str] | dict[str, str]`, hoặc giải quyết ở tầng phân tích profile.

2. **CẤM Fuzzy Overlap lỏng lẻo bằng `in` trên token ngắn:**
   - **Anti-pattern:** Dùng `any(t1 in t2 or t2 in t1)` trên các token 2-3 ký tự (ví dụ `an`, `to`, `la`, `anh`). Điều này dẫn tới false-positive cực kỳ nguy hiểm (nick A bị nhận nhầm thành nick B, chuyển nhầm tài khoản và làm hỏng cả phiên nuôi).
   - **Quy tắc:** Chỉ đối chiếu Display Name khi có mapping 1-1 từ database/workbook chính xác, hoặc token alpha >= 4 ký tự kết hợp kiểm tra độ dài.

3. **CẤM đổi toàn cục `input tap` sang `input swipe` thời lượng dài:**
   - **Anti-pattern:** Đổi `_tap_ui_element` thành `input swipe x y x y 100` trên toàn bộ runner. Swipe cùng tọa độ không đảm bảo luôn được mọi Android View/Compose/WebView diễn giải thành Click; có thể gây nuốt sự kiện click ở các màn hình khác.
   - **Quy tắc:** Giữ `input tap` làm mặc định toàn hệ thống. Chỉ áp dụng synthetic click swipe hoặc ATX JSON-RPC click cục bộ trên đúng thành phần RecyclerView / BottomSheet đã được chứng minh nuốt tap 0ms.
