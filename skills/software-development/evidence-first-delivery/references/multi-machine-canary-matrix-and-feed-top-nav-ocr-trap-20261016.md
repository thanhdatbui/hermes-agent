# Bài học thực chiến: Bẫy Canary Đơn Máy & Sự cố OCR Nhận Nhầm Tab Bar Feed (2026-10-16)

## 1. Bối cảnh & Sự cố thực tế
Sau khi điều tra nguyên nhân runner follow báo cáo thành công +4, +5 nhưng Web TikTok hiển thị 0 (do bẫy Optimistic UI cache và nút "Nhắn tin" bị phân loại nhầm là `followed`), Coordinator và Worker đã hoàn thành bản vá:
- Dọn dẹp `FOLLOWED_KEYWORDS` trong `ocr.py` (loại bỏ `nhan tin`, `message`, `gui tin nhan`).
- Dọn dẹp fallback `followed_kw` trong `mode2_follow_followers.py`.
- Đồng bộ matcher semantic trong `verify_follow.py`.

Sau khi chạy xong pytest (330+ tests passed), Coordinator tiến hành Canary trên **Máy 6** (Profile `@ourshashine` có mở DM):
- Cả XML và OCR đều phân loại chính xác `not_followed`.
- Định vị đúng tâm nút đỏ `(247, 653)`.
Coordinator vội vã báo cáo: *"Đã xong hết 100%, anh duyệt để chốt phiên"*.

User lập tức can thiệp và chấn chỉnh workflow kiểm thử:
> *"Sao canary có 1 máy thì lấy gì đảm bảo máy khác k lỗi"*

## 2. Phát hiện lỗi nghiêm trọng nhờ mở rộng Canary Đa Máy
Thực hiện chỉ đạo của User, Coordinator mở rộng Canary sang 3 máy tiếp theo:
1. **Máy 7 (Profile chính chủ `@huehoafi23`):** Kiểm tra xem stat counter `1 Đã follow` có bị nhận nhầm không -> Kết quả trả về `unknown` (đạt).
2. **Máy 8 (Màn hình Video Feed / For You):** 
   - Màn hình đang phát video, phía trên cùng có thanh tab điều hướng: `LIVE`, `Bạn bè`, `Đang follow`, `Dành cho bạn`.
   - **BẮT ĐƯỢC LỖI CHÍ TỬ:** Tab `Bạn bè` nằm ở tọa độ $y_1 = 141, y_2 = 175$. Do `classify_button_from_ocr` đặt mặc định $y_{min} = 0$, hàm đã bốc chữ `Ban bé` và phán nhầm màn hình Feed lướt video là **`followed`**!
   - Nếu không có lệnh chấn chỉnh của User, lỗi này sẽ khiến script ngộ nhận mọi màn hình Feed có chữ "Bạn bè" là đã follow thành công, gây sai lệch thống kê hàng loạt trên toàn Farm.

## 3. Bản vá dứt điểm tại chỗ
- **Ngưỡng lọc Action Band:** Nút action trên profile TikTok không bao giờ nằm ở dải điều hướng $y < 200$. Cập nhật $y_{min} = 200$ làm mặc định cho `classify_button_from_ocr` và `find_follow_button_center_ocr`.
- **Unit test bổ sung:** Thêm `test_classify_button_ignores_feed_top_nav_tabs` trong `test_ocr.py` mô phỏng chính xác tọa độ các tab Feed `("Ban bé", (333, 141, 461, 175))` để ngăn chặn hồi quy.
- **Tái kiểm tra thực tế:** Chạy lại trên Máy 8 -> OCR trả về `unknown` chuẩn xác.

## 4. Kỷ luật cốt lõi rút ra
1. **Một máy không bao giờ đại diện cho toàn Farm:** Các máy trên Farm chạy nhiều phiên bản TikTok khác nhau (`46.x`, `47.x`), obfuscated IDs khác nhau (`id/fds`, `id/ff8`, `id/fij`, `id/fo4`, `id/fmp`), và đang dừng ở các activity khác nhau.
2. **Ma trận Canary tối thiểu 4 góc nhìn:**
   - Góc 1: Profile đối tượng có nút nhắn tin (chứng minh không bị lừa bởi optimistic UI và nút chat).
   - Góc 2: Profile chính chủ có nhãn đếm (chứng minh không dính bẫy substring stat counters).
   - Góc 3: Màn hình Feed / Lướt video (chứng minh không nhận nhầm tab điều hướng).
   - Góc 4: Màn hình Cài đặt / Sửa hồ sơ (chứng minh cơ chế fail-closed hoạt động an toàn).
3. **Mọi máy đều phải có ảnh soi mắt:** Không chấp nhận exit code suông; mỗi máy trong ma trận đều phải xuất ảnh `MEDIA:<path>` kèm visual readback trung thực.
