# SOP Xử Lý Khi Vision Model/Tool 503 Hoặc Cạn Quota (Fail-Closed & Kênh Dự Phòng)

## 1. Bối Cảnh Sự Cố & Cạm Bẫy Tâm Lý (Incident Analysis 2026-10-24)
- **Hiện tượng**:
  - Khi gọi `browser_vision` (hoặc Antigravity Vision CLI), runtime gặp lỗi `503 Service Unavailable / All targets skipped by pre-dispatch filters` hoặc `Resource Exhausted 429`.
  - Thay vì dừng lại báo cáo hạ tầng hoặc kích hoạt kênh vision thay thế hợp lệ, Coordinator tự ý chuyển sang đọc text thô bằng WinRT OCR rồi báo cáo xong bằng chữ chay, hoàn toàn KHÔNG gửi ảnh `MEDIA:<path>` cho User.
  - User phát hiện và chất vấn: *"Mày lại vi phạm gate k chịu gửi ảnh r? Lí do vi phạm gate gọi claude cli vào tư vấn"*.
- **Nguyên nhân gốc rễ**:
  1. **Xung đột 2 Gate độc lập khi hạ tầng hỏng**: Invariant Soi Mắt ("Cấm gửi ảnh mù") xung đột với Gate 6 ("Mọi thao tác UI phải gửi ảnh"). Không có nhánh xử lý fail-closed khiến Coordinator chọn con đường tắt: bỏ gửi ảnh và dùng text OCR thay thế.
  2. **Hạ cấp bằng chứng âm thầm (Proof Downgrade)**: Tự cho rằng OCR text là đủ chứng minh thao tác. Thực tế OCR không đọc được nhãn đồ họa "Đã ghim", không thấy được avatar/layout và không nhận diện được việc màn hình chụp trước hay sau khi đổi tên/bio.

---

## 2. Quy Trình Chuẩn (SOP) 5 Bước Xử Lý Khi Vision Tool Bị Lỗi / Down

### Bước 1: Khóa Chặn Ngay Lập Tức (Fail-Closed)
- Bước hiện tại chuyển ngay sang trạng thái: `UNVERIFIED / BLOCKED_VISION_UNAVAILABLE`.
- **CẤM TUYỆT ĐỐI**:
  - CẤM gửi thẻ `MEDIA:<path>` khi chưa soi mắt (chống gửi ảnh mù).
  - CẤM dùng text OCR thay cho hình ảnh và tự ý báo "Đã xong" bằng chữ chay.
  - CẤM thực hiện thêm các bước thao tác UI tiếp theo khi bước trước chưa được nghiệm thu thị giác.

### Bước 2: Thử Kênh Vision Thay Thế Hợp Lệ (Đúng 1 Lần)
Khi runtime chính (`browser_vision`) bị 503, chuyển giao ngay sang kênh thẩm định thị giác độc lập:
1. **Kênh 1: Claude Code CLI (`claude_worker.py --role reviewer`)**:
   - Chạy với vai trò reviewer, truyền đường dẫn ảnh vào prompt và yêu cầu Claude CLI mở đọc trực tiếp bằng tool Read của nó:
     ```bash
     python D:/Taadaa/tools/claude_worker.py --role reviewer --timeout 300 "Thẩm định ảnh chụp tại <path_anh>: 1. Đúng tài khoản không? 2. Có nhãn 'Đã ghim' không? 3. Tên và bio đã đổi chưa? 4. Bố cục có lỗi không?"
     ```
2. **Kênh 2: 9Router / Proxy `:20129` Trực Tiếp**:
   - Gọi trực tiếp endpoint chat completion truyền base64 image_url sang model vision độc lập (ví dụ `auto/best-vision`).

### Bước 3: Soi Mắt Nghiệm Thu & Gửi Kèm Thẻ `MEDIA:`
- Chỉ khi kênh vision thay thế (ví dụ Claude CLI) đã xác nhận các điểm kiểm tra bằng mắt (màu sắc, nhãn, bố cục, tên, bio) $\rightarrow$ Coordinator mới được phép trích xuất kết luận thị giác và đính kèm thẻ `MEDIA:<path_anh>` cho User.

### Bước 4: Khi Tất Cả Kênh Vision Đều Hỏng
- Nếu cả runtime chính, Claude CLI lẫn 9Router đều không đọc được ảnh:
  - Báo cáo rõ ràng: `Hạ tầng Vision đang gặp sự cố 503/Quota` kèm mã lỗi chi tiết.
  - Giữ nguyên trạng thái task là `BLOCKED_VISION_UNAVAILABLE`.
  - **HỎI Ý KIẾN USER QUA CLARIFY**: *"Hạ tầng vision đang lỗi không thể soi mắt ảnh. Anh có cho phép gửi ảnh đính kèm với nhãn CHƯA SOI MẮT để anh tự kiểm tra không?"*
  - Mặc định khi chưa có lệnh của User là KHÔNG gửi ảnh mù, KHÔNG báo xong.
