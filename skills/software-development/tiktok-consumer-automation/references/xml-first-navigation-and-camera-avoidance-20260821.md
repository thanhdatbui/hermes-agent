# XML-First Navigation & Popup Handling Rules (2026-08-21)

## 1. Nút Tạo Video (+) và Vùng Đáy Màn Hình (Bottom Navigation)
- Vị trí nút Tạo Video (+): Nằm ở chính giữa đáy màn hình `[432, 1794][648, 1920]` (Tâm là `X: 540, Y: 1857`).
- CẤM các lệnh vuốt bắt đầu từ `Y=1800` (đè đúng đỉnh nút + gây nhảy vào Camera). Tọa độ vuốt / đóng Notification Shade phải bắt đầu từ `Y <= 1540`.
- Tuyệt đối không dùng fallback tọa độ `(540, 1700)` hay click mù khi không tìm thấy node tab điều hướng ("Hồ sơ", "Trang chủ") trong XML. Mọi click điều hướng phải resolve từ XML node có `bounds` thực sự.

## 2. Phân Loại Màn Hình Camera / Tạo Video (`classifier.py`)
- Phải quét exact match mode ở vùng cận đáy `Y >= 1000` và yêu cầu tối thiểu `>= 2` distinct modes (`15s`, `60s`, `10 phút`, `văn bản`, `templates`, `photo`, `camera`).
- CẤM tìm substring các từ đơn như `"ảnh"` hay `"tạo"` vì sẽ gây False Positive trên các video feed có caption "Ảnh" hoặc nhãn "Có chứa nội dung do AI tạo".

## 3. Quy Tắc Xử Lý Popup Thường Gặp
- **Popup "Follow bạn bè của bạn"**: Tự động click toàn bộ các nút "Follow lại" / "Follow back" trên danh sách bạn bè gợi ý để tăng follow chéo tự nhiên cho nick, sau đó mới đóng popup.
- **Popup "Làm nổi bật những nhà sáng tạo mà bạn quan tâm" (Creator Highlight)**: Xuất hiện tự nhiên khi chuyển sang tab "Đã follow" lần đầu. Đóng bằng nút "Đã hiểu" hoặc phím Back.
- **Popup "Để phát LIVE, bạn cần"**: Thoát bằng nút "Đã hiểu" và phím Back để về lại Feed.
- **Modal "Chuyển đổi tài khoản"**: Phải đóng modal (gửi phím Back hoặc tap nút X) trước khi quét tìm các node điều hướng dưới đáy màn hình.
