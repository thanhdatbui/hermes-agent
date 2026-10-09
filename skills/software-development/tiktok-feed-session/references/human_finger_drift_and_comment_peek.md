# Human Finger Drift & Comment Peek (High Entropy Feed Session)

*Cập nhật: 2026-09-14*

### 1. Human Finger Drift (Độ cong ngón tay tự nhiên)
- **Mục tiêu**: Phá vỡ pattern bot `dx = 0` (vuốt thẳng đứng tuyệt đối), mô phỏng vuốt bằng ngón tay cái tự nhiên của người dùng nhưng không chạm vào ngưỡng kích hoạt Camera / Story pager (`dx > 150px`).
- **Thông số kỹ thuật chuẩn**:
  - `start_x`: giới hạn trong hành lang tâm an toàn `[450, 540]` (khi sample `_build_swipe_parameters`: `[460, 530]`).
  - `end_x`: lệch tự nhiên từ `start_x`:
    ```python
    raw_end_x = start_x + random.randint(-20, 15)
    end[0] = max(430, min(560, raw_end_x))
    ```
  - Guardrail chống skew bất thường: Nếu tham số swipe bên ngoài truyền vào có `|end_x - start_x| > 30px`, tự động reset về `start_x` để triệt tiêu nguy cơ vuốt nhầm tab.
- **Unit test**:
  - Kiểm tra độ trôi ngón tay trong giới hạn an toàn: `abs(start_x - end_x) <= 35` px.

---

### 2. Comment Peek (Xem lướt bình luận)
- **Mục tiêu**: Tăng entropy và đa dạng hóa hành vi tương tác trong phiên nuôi feed, giúp tài khoản giống người dùng thật hơn.
- **Tần suất**: Khoảng 8% - 15% (mặc định 12%) ở các video trong feed session (`is_feed_session`).
- **Quy trình thực hiện (`_maybe_peek_comments`)**:
  1. Trích xuất XML / UI snapshot hiện tại.
  2. Định vị nút bình luận ở cạnh phải màn hình (`center[0] >= 750`, desc chứa `bình luận`, `comment`, hoặc `read or write comment`).
  3. Bấm mở comment sheet (`input tap cx cy`).
  4. Dừng đọc lướt ngẫu nhiên từ `2.0` đến `4.0` giây.
  5. Có 50% xác suất cuộn nhẹ 1 nhịp ngắn (`input swipe 540 1400 540 1100 300`) và chờ thêm `1.0` - `2.0` giây.
  6. Bấm phím Back (`input keyevent 4`) để đóng comment sheet, nghỉ `0.5` - `1.0` giây trước khi tiếp tục feed loop.
  7. Ghi audit log với step `<step>/comment_peek` và action `comment_peek`.
