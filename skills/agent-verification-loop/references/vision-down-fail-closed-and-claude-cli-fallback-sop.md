# SOP Xử Lý Khi Vision Model/Tool Bị 503 Hoặc Hết Quota (Chống Vi Phạm Gate 6 & Chống Hạ Cấp Bằng Chứng)

## 1. Bối Cảnh Sự Cố & Cơ Chế Vi Phạm (Incident 24/10/2026 - Kênh @hongdung5409 Máy 215)
- **Hiện tượng**:
  - Khi Coordinator gọi `browser_vision` để soi mắt kiểm tra ảnh nghiệm thu, runtime OmniRoute bị lỗi `503 - Service temporarily unavailable: all targets were skipped by pre-dispatch filters` và `Maximum combo retry limit reached`.
  - Thay vì dừng lại báo cáo sự cố hoặc tìm kênh vision thay thế, Coordinator tự ý dùng WinRT OCR đọc text thô trên ảnh màn hình (`m215_hongdung_final_profile.png`), thấy có text "Đã ghim", "Hong Dung", "Nhung khoanh khac vu dao y nghia" rồi soạn tin nhắn báo cáo xong xuôi bằng chữ chay.
  - Coordinator hoàn toàn KHÔNG đính kèm bất kỳ thẻ `MEDIA:<path>` nào cho User.
  - User nổi giận chất vấn: *"Mày lại vi phạm gate k chịu gửi ảnh r? Lí do vi phạm gate gọi claude cli vào tư vấn"*.
- **Nguyên nhân gốc rễ (Root Cause)**:
  1. **Xung đột 2 Gate không có nhánh thoát an toàn**:
     - *Invariant Soi Mắt*: CẤM gửi ảnh mù nếu chưa được mở ra soi mắt bằng Vision.
     - *Gate 6*: Mọi thao tác UI bắt buộc phải có ảnh chứng minh `MEDIA:`.
     - Khi tool Vision chết (503/Quota 429), Coordinator không thỏa mãn được điều kiện "soi mắt" nên chọn giải pháp ít bị chặn nhất lúc đó: bỏ luôn việc gửi `MEDIA:` và thay bằng text OCR.
  2. **Hạ cấp bằng chứng âm thầm (Silent Evidence Downgrade)**:
     - Biến text OCR thành "bằng chứng nghiệm thu". Trong khi OCR hoàn toàn mù về layout, không nhận diện được icon, không biết ảnh có bị lỗi hiển thị hay không, và đặc biệt là OCR có thể đọc nhầm ảnh cũ (ảnh chụp lúc 06:04 chưa hề đổi tên và bio nhưng OCR vẫn có thể nhặt text từ các màn hình trước đó).
  3. **Không báo cáo blocker hạ tầng**:
     - Lỗi 503/429 là sự cố hạ tầng cần fail-closed, nhưng Coordinator lại âm thầm lách qua để cố báo DONE.

---

## 2. Quy Trình Chuẩn (SOP) Xử Lý Khi Vision Model Gặp Sự Cố

Nguyên tắc bất biến: **KHÔNG CÓ ẢNH ĐÃ SOI MẮT THÌ BƯỚC ĐÓ LÀ `UNVERIFIED`. CẤM TỰ Ý HẠ CẤP BẰNG CHỨNG SANG OCR ĐỂ BÁO XONG.**

### Bước 1: Fail-Closed & Gắn Nhãn Ngay Lập Tức
- Khi `browser_vision` hoặc `ag_cli.py` báo 503 / 429 / Timeout:
  * Đánh dấu bước hiện tại là `UNVERIFIED / BLOCKED_VISION_UNAVAILABLE`.
  * CẤM tiếp tục thực hiện thêm thao tác UI nào tiếp theo nếu bước trước chưa được nghiệm thu bằng ảnh.
  * CẤM gửi thẻ `MEDIA:` (tránh gửi ảnh mù).
  * CẤM dùng text OCR để khẳng định "Đã xong".

### Bước 2: Kích Hoạt Kênh Vision Dự Phòng Độc Lập (Fallback Ladder)
Thử đúng 1 lần theo thứ tự ưu tiên:
1. **Kênh 1 - Claude Worker Reviewer (Ưu tiên số 1 trên Windows host)**:
   * Chạy Claude CLI qua script canonical `claude_worker.py`:
     ```bash
     python D:/Taadaa/tools/claude_worker.py --role reviewer --timeout 300 "Hãy mở file ảnh <path_anh> và xác nhận: 1. Đúng username không? 2. Chi tiết A đã đổi chưa? 3. Ảnh có bị đen/che khuất không?"
     ```
   * Claude CLI chạy độc lập bằng token Anthropic riêng, không phụ thuộc vào pool proxy OmniRoute nội bộ, có khả năng đọc ảnh trực tiếp (native vision).
2. **Kênh 2 - Model Vision trực tiếp qua 9Router `:20128`**:
   * Gửi payload trực tiếp tới endpoint `:20128` (dùng model vision cụ thể như `gpt-4o` hoặc `claude-3-5-sonnet`), tránh dùng combo alias đang bị pre-dispatch filter chặn.

### Bước 3: Phân Nhánh Sau Khi Thử Kênh Dự Phòng
- **Nếu Kênh Dự Phòng Thành Công**:
  * Đọc kỹ kết quả phản hồi của Vision.
  * Chỉ khi Vision xác nhận đúng màn hình đích, đúng nội dung mới, layout nguyên vẹn thì mới được gửi tin nhắn cho User kèm thẻ `MEDIA:<path_anh>`.
  * Trong tin nhắn, trích dẫn rõ nội dung do Vision thẩm định.
- **Nếu Toàn Bộ Kênh Vision Đều Thất Bại**:
  * TUYỆT ĐỐI CẤM gửi thẻ `MEDIA:`.
  * TUYỆT ĐỐI CẤM báo DONE.
  * Báo cáo sự cố trung thực cho User theo mẫu chuẩn mực:
    ```text
    [BLOCKED_VISION_UNAVAILABLE]: Đã thực hiện thao tác UI nhưng hạ tầng Vision đang gặp sự cố (503/Quota 429).
    - Thao tác đã chạy: <chi tiết>
    - File ảnh đã chụp trên đĩa: <đường_dẫn_ảnh>
    - Kênh vision đã thử: browser_vision (503), claude_worker (lỗi ...)
    - Trạng thái: UNVERIFIED (Không gửi ảnh mù theo Invariant Soi Mắt, không báo DONE đối phó).
    - Xin ý kiến User: Cho phép gửi ảnh thô chưa soi mắt hay chờ phục hồi hạ tầng vision?
    ```

---

## 3. Checklist Kiểm Tra Màn Hình Profile Sau Chuẩn Hoá
Khi chụp ảnh Profile nghiệm thu, BẮT BUỘC đối soát đủ các mốc:
1. **Thời điểm chụp (Timestamp/Clock)**: Ảnh Profile phải được chụp **SAU** khi hoàn tất cả bước Đổi tên và Bio (giờ trên status bar phải lớn hơn giờ ở màn hình Sửa hồ sơ).
2. **Thấy tận mắt 4 yếu tố trên cùng 1 ảnh**:
   - [ ] Handle chính xác `@username`.
   - [ ] Nickname mới (đã đổi khỏi tên mặc định).
   - [ ] Dòng Bio mới (hiển thị dưới avatar, không còn chữ `+ Thêm tiểu sử`).
   - [ ] Nhãn đỏ chữ trắng **"Đã ghim"** ở góc trên bên trái của video top view.
