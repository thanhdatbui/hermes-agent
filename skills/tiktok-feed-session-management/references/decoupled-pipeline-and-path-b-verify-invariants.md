# Tách Rời 3 Quy Trình (Feed — Follow — Upload) & Kỷ Luật Đối Soát Nhả Follow

## 1. Nguyên Tắc Tách Rời 3 Quy Trình Độc Lập
- **Ngữ cảnh:** Trước đây, trong `multi_machine_feed_session.py`, nếu một máy chạy lướt Feed thất bại (do app lỗi, socket ATX-Agent kẹt, timeout hoặc không đủ 3 swipe warm), hệ thống tự động `sensitive-skip-fail` và hủy bỏ toàn bộ phiên Follow tiếp sau đó.
- **Quy tắc bất biến mới:**
  - 3 quy trình **Lướt Feed ➔ Chạy Follow Hook ➔ Đăng Video (Upload Hook)** vận hành độc lập.
  - **Lướt Feed fail (kể cả 0 swipe / lỗi kỹ thuật) KHÔNG ĐƯỢC PHÉP chặn Follow Hook**:
    Hệ thống ghi nhận Feed fail, sau đó vẫn tiếp tục khởi chạy Follow Hook bình thường cho nick đó.
  - Tương tự, nếu Follow fail/nhả thì đến cuối ca hệ thống vẫn khởi chạy Upload Hook đăng video bình thường.
  - *Ngoại lệ duy nhất:* Chỉ bỏ qua khi tài khoản dính lỗi bảo mật nặng (`_SENSITIVE_ACCOUNT_WORDS`: `banned`, `suspended`, `checkpoint`, `logged_out`).

## 2. Invariant Đối Soát Nhả Follow & Phòng Ngừa Phạt Cooldown Oan
- **Triết lý bảo vệ nick:**
  - Khi TikTok server nhả follow THẬT ➔ **BẮT BUỘC phải dừng session và khóa cooldown ngay lập tức** để tránh việc tiếp tục spam nút follow khiến nick bị TikTok quét checkpoint / ban vĩnh viễn.
  - CẤM TUYỆT ĐỐI sửa runner theo hướng "nhả thật nhưng vẫn lì lợm bấm follow tiếp".
- **Bẫy Verify Path B (Optimistic UI vs False Release):**
  - Khi bấm Follow trong danh sách Follower (Mode 2), UI chuyển sang "Đang follow".
  - Khi mở sang trang Profile cá nhân của nick đích để verify (Path B):
    + App TikTok đã tự động fetch profile mới nhất từ server.
    + **CẤM gọi `pull_to_refresh_profile` (vuốt kéo màn hình xuống)**: Thao tác vuốt này làm giật layout, đẩy nút bấm ra ngoài viewport hoặc kích hoạt vòng quay loading che mất nút, khiến OCR/XML đọc ra `unknown` / `manual` rồi ngộ nhận thành lỗi.
    + Sau khi mở Profile, cho UI settle 1.5s rồi đọc nút quan hệ (`id/fds`):
      * Thấy `Following / Đang theo dõi / Bạn bè` ➔ **Thành công 100%**.
      * Thấy `Follow / Theo dõi` (nút đỏ ban đầu) ➔ **Server TikTok đã nhả thật** ➔ Dừng session và phạt cooldown để bảo vệ nick.
      * Màn hình còn loading ➔ Cho phép retry tối đa 2 nhịp (1s) trước khi kết luận, cấm phán nhả bừa bãi khi chưa có bằng chứng chắc chắn.

## 3. Khắc Phục Lỗi Kẹt ADB Socket / ATX-Agent Trên Dàn Máy Lớn
- Hiện tượng: Khi hub USB 80 cổng bị nghẽn tải I/O đột ngột, socket ADB kết nối tới máy bị treo cứng (hang), khiến cả `screencap` lẫn port-forward `7912` của `atx-agent` bị timeout.
- Cứu hộ nóng JIT (In-flight Reconnect):
  - Khi adapter bắt được `TimeoutError` hoặc `adb connection dropped`, chạy nóng `adb -s <serial> reconnect` (tốn < 2s) và khởi tạo lại kết nối `atx-agent`.
  - Thử lại ngay lần 2 trước khi đánh dấu fail, tránh để script nuôi acc bị block chờ hết timeout rồi bỏ cuộc oan.
