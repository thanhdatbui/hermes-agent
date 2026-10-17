# Cảnh Báo Bẫy Idempotency Receipt Treo & Kiểm Chứng Ảnh Thực Tế (2026-10-17)

## 1. Bẫy Idempotency Receipt Treo (`idempotency/post-attempts/`)
- **Cơ chế:** Khi workflow chạy, nếu ở ca trước máy đã từng bấm Post nhưng mạng lag, văng app hoặc kẹt màn hình trước khi `state_machine.py` kịp hoàn thành thì file receipt treo (`status != completed` hoặc receipt rác) vẫn tồn tại trong:
  `D:/CodexRuntime/tiktok-video/idempotency/post-attempts/machine_<M>_account_<acc>_video_<N>.json`
- **Hậu quả nghiêm trọng:**
  - Lần chạy tiếp theo, `state_machine.py` phát hiện receipt cũ này sẽ kích hoạt nhánh:
    `[POST_RECEIPT] Receipt chưa hoàn tất; chuyển thẳng VERIFY_POST trước MEDIA_PUSH`.
  - Quy trình **BỎ QUA TOÀN BỘ** việc dọn Gallery, đẩy video mới (`MEDIA_PUSH`) và bấm Đăng (`POST`).
  - Nó bay thẳng vào bước quét Profile (`VERIFY_POST`). Nếu tài khoản trước đó đã có sẵn video cũ trên lưới, phép so sánh số lượng video có thể gây ngộ nhận đã đăng thành công, báo `status: SUCCESS` và tự ý tăng số `posted` trong Excel, dẫn tới **DONE ẢO / MẤT CLIP CỦA NGÀY**.
- **Quy tắc xử lý:**
  1. Khi cần chạy lại / rerun bù cho máy bị lỗi, Coordinator BẮT BUỘC kiểm tra và dọn sạch các file receipt cũ của máy đó trong `idempotency/post-attempts/`.
  2. Dọn sạch file media tạm trong `/sdcard/DCIM/Camera/*` trước khi push video mới.
  3. Kiểm tra log execution: Nếu thấy xuất hiện `[POST_RECEIPT] ... chuyển thẳng VERIFY_POST`, đây là dấu hiệu nhảy cóc, TUYỆT ĐỐI CẤM báo DONE mà phải triệt tiêu receipt và rerun lại quy trình thật.

## 2. Invariant Soi Mắt Đọc Ảnh Thực Tế (Chống Báo Done Vô Cảm)
- **Menu Ngữ Cảnh ("Ghim lên đầu", "Đặt ở chế độ riêng tư", "Chia sẻ"):**
  - Khi script quét lưới Profile bằng thao tác swipe, nếu độ trễ màn hình cao có thể bị hiểu nhầm thành nhấn giữ (long-press), làm bung menu *"Ghim lên đầu / Đặt ở chế độ riêng tư / Chia sẻ"*.
  - Màn hình này **KHÔNG PHẢI** là bằng chứng xuất bản thành công (`post-published-surface.png`).
  - Coordinator BẮT BUỘC dùng `browser_vision` hoặc OCR đọc từng dòng text trên ảnh:
    - Bằng chứng xuất bản thật sự: Phải đọc thấy dòng thời gian vừa đăng (ví dụ `• Vừa xong`, `• 2 giây trước`) hoặc ô video mới xuất hiện trên lưới Profile với tile tăng trưởng rõ ràng.
    - CẤM nhìn `status: SUCCESS` của script rồi suy diễn nội dung ảnh!
