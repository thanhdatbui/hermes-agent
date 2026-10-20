# Bẫy Browser Daemon Session Crash & Cơ Chế Vision Fallback Qua Claude Worker CLI

## 1. Bản Chất Sự Cố (17/10/2026 — @anan197563 / @ajbecosmby0)
- **Hiện tượng**:
  - Khi điều phối chuẩn hóa avatar, Coordinator gọi `browser_navigate` và `browser_vision` để kiểm tra ảnh tròn preview trước khi gửi thẻ `MEDIA:`.
  - Trình duyệt ngầm gặp lỗi xung đột cấu hình daemon (`A daemon for session 'h_...' started concurrently with different daemon configuration` hoặc `Interrupted`).
  - Thay vì phát hiện mình đang "mù thị giác", Coordinator lại tự suy diễn (hallucinate) nội dung ảnh dựa trên tên file và kịch bản mong muốn: khẳng định ảnh có "mèo trắng hoa hướng dương", "mèo đầu bếp hamburger", "mèo mướp mắt xanh biếc".
  - Thực tế khi User xem ảnh thì hoàn toàn không có mèo, mà là người đàn ông diễn thuyết đeo micro, showroom cửa nhựa, mảng màu neon. User bức xúc: *"Đéo cái nào đc. Mày có thật sự dùng llm đọc ảnh trc khi gửi k v"*.
- **Nguyên nhân gốc rễ**:
  - Coordinator tin tưởng mù quáng vào kết quả trích xuất tự động mà không có tầng kiểm chứng thị giác độc lập có ground truth.
  - Khi browser vision lỗi, không có cơ chế fail-closed hay fallback sang công cụ đọc ảnh có native vision khác.

---

## 2. Quy Trình Soi Mắt Bắt Buộc (Visual Verification Ladder)

### Cấp 1: Kiểm tra `browser_vision` trả về hợp lệ
- Nếu `browser_navigate` hoặc `browser_vision` trả về bất kỳ dấu hiệu lỗi nào:
  * `{"success": false}`
  * `error: "A daemon for session ... started concurrently"`
  * `error: "Interrupted"`
  * Snapshot rỗng hoặc không tải được ảnh.
- **LỆNH CẤM**: TUYỆT ĐỐI CẤM phỏng đoán nội dung ảnh rồi gửi `MEDIA:` kèm lời mô tả bịa đặt.

### Cấp 2: Kích hoạt Claude Worker CLI Native Vision (Primary Fallback)
- Trên host Taadaa Farm, Claude CLI sở hữu năng lực Multimodal Vision tự nhiên, đọc trực tiếp file ảnh từ đường dẫn đĩa cứng.
- Chạy lệnh kiểm chứng O(1) tập trung (< 30s):
  ```bash
  python D:/Taadaa/tools/claude_worker.py --role worker --max-turns 2 --timeout 30 "Đọc ảnh <đường_dẫn_tuyệt_đối> bằng mắt thật và trả lời: 1. Trong ảnh có đúng là <chủ_thể_cần_tìm> không? 2. Khuôn mặt/mắt/mũi/tai nằm ở đâu, có nhìn vào ống kính không? 3. Có bị dính chữ, watermark, popup, viền đen hay lẹm cằm không?"
  ```
- **Kỷ luật đánh giá**:
  * Chỉ khi Claude Worker xác nhận rõ ràng: "Đúng là chủ thể X, mặt nhìn thẳng, không dính chữ/lỗi" mới được phép gửi `MEDIA:` cho User.
  * Nếu Claude Worker báo "Không có X" hoặc "Ảnh bị mờ/lệch": BẮT BUỘC bỏ ảnh đó, không được gửi đối phó.

---

## 3. Quy Trình Trích Xuất Avatar Từ Video Kênh Chuẩn Xác
1. **Lấy mẫu đa điểm (Multi-Frame Sampling)**:
   - Thay vì lấy bừa 1 frame ở giây thứ 2, trích xuất chuỗi frame ở nhiều mốc (0.5s, 1s, 2s, 3s, 5s, 10s).
2. **Claude Worker Vision Screening**:
   - Dùng Claude Worker quét nhanh danh sách frame mẫu để chọn ra 1-2 frame rõ nét nhất, mắt mở to, hướng thẳng camera.
3. **Crop Vuông & Tạo Khung Tròn**:
   - Lấy tọa độ tâm khuôn mặt từ phân tích của Claude Worker.
   - Crop 512x512 có tỷ lệ headroom (khoảng trống đỉnh đầu) 15-20%, vẽ mask tròn R=256 và làm tối 70% bên ngoài.
4. **Hậu Kiểm Trước Khi Gửi**:
   - Cho Claude Worker xem lại ảnh `_circle.jpg` cuối cùng để xác nhận lại lần chót trước khi đưa vào phản hồi kèm thẻ `MEDIA:`.
