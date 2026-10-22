# Case Study: OCR Username Whitespace Splitting & Physical Tap Safety in Farm Closeout

## 1. Hiện tượng & Tình huống (Context)
- Cronjob rolling rename TikTok trên Farm Android ghi nhận lỗi `exit_2` trên Máy 69 (`@ngotrang7771`) và Máy 64 (`@hoangngan3179`).
- Tại hiện trường Máy 69: Nick đã được đổi tên thành công thành "Trang Thỏ" trên thiết bị, nhưng script canonical runner vẫn trả về `exit_2` và đánh dấu thất bại.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Lỗi OCR Username Internal Whitespace:**
   - WinRT OCR (engine `en-US`) bóc tách username `@ngotrang7771` trên màn hình Profile Samsung S7 bị dính khoảng trắng nội bộ thành `@ngotran g7771`.
   - Hàm `nickname_on_profile()` có điều kiện chặn cứng `" " not in text`, khiến dòng username hợp lệ bị loại bỏ hoàn toàn -> hàm trả về `(None, None)` -> Runner hiểu lầm chưa về đúng Profile đích và abort với mã `exit_2` (False-Positive).
2. **Cạm bẫy Tọa độ Tap Fallback & Rủi ro Farm Safety:**
   - Khi OCR không bắt được nút "Sửa hồ sơ" do tương phản thấp, script dùng tọa độ fallback.
   - Thử nghiệm sửa tọa độ từ `(540, 865)` sang `(315, 865)` mà không có Live Canary đã bị Closeout Gate đánh rớt điểm an toàn (64/100).
   - Thực nghiệm thực tế trên Máy 64 cho thấy khi trang Profile bị cuộn hoặc hiển thị ở dạng sub-profile (có nút Back `<`), vùng tọa độ `y=865` bị các tab video (như icon Khóa của "Video riêng tư") chiếm chỗ. Tapping `(315, 865)` đã bấm nhầm vào tab Video riêng tư thay vì mở Sửa hồ sơ.

## 3. Giải pháp chuẩn hóa (Best Practice)
1. **Phục hồi Username có khoảng trắng nội bộ an toàn:**
   - Cho phép dòng bắt đầu bằng `@` chứa khoảng trắng nội bộ NẾU VÀ CHỈ NẾU sau khi lọc khoảng trắng (`compact(text)`) chuỗi khớp đúng `is_target_user()`.
   - Bắt buộc từ chối nếu không khớp để tránh false-positive với các đoạn caption, mention hoặc gợi ý tài khoản khác.
   - Xử lý đồng bộ ở cả nhánh regex chính và nhánh fallback không có ký tự `@`.
   - Ghi nhận sự kiện phục hồi vào mảng telemetry `TRACE` có cấu trúc (`OCR_SPACE_RECOVERED`) để phục vụ kiểm toán.
2. **Kỷ luật Closeout Gate (Phân tách Logic OCR vs Tọa độ Vật lý):**
   - Không được tùy tiện sửa đổi tọa độ vật lý của thiết bị nếu không có Live Canary chứng minh.
   - Khi vá lỗi parser OCR, cô lập 100% trong phạm vi logic xử lý chuỗi và unit tests; giữ nguyên tọa độ tap gốc đã được phê duyệt.
   - Viết đầy đủ unit tests 2 chiều: (a) Happy-path phục hồi username lỗi, (b) Negative-path xác nhận dòng sai bị loại bỏ hoàn toàn (trả về `None, None`), (c) Tích hợp với bounding boxes thực tế trích xuất từ farm report.
