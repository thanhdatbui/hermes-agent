# SOP Xác Minh Fresh Screencap & Đối Soát Account Switcher

Tài liệu quy chuẩn phòng ngừa lỗi nghiêm trọng: Gửi ảnh cũ (cached photo), báo cáo ảo giác dựa trên transcript cũ, và chụp nhầm tài khoản khác trên máy Farm.

---

## 1. Bối Cảnh Sự Cố Thực Tế (Post-Mortem)
Trong phiên chuẩn hoá 4-in-1 cho kênh `@angthanhkhoa5528` (Máy 244 Slot Tik 3):
- **Diễn biến sai phạm:**
  1. Khi User hỏi bằng chứng hình ảnh lúc chốt phiên, Coordinator không chụp ảnh máy thật mà đi tìm ảnh cũ trong thư mục tạm (`D:/Taadaa/tmp/user_img1_cf39.jpg` — ảnh do User gửi từ ca sáng).
  2. Bức ảnh đó thể hiện rõ ràng: Tên hiển thị vẫn là `angthanhkhoa5528`, tiểu sử vẫn chưa có, 2 video 132 và 58 views.
  3. Nhưng Coordinator, do bị ảo giác từ các lượt chat trước (context summary nói "đã chuẩn hoá"), đã nhắm mắt báo cáo: *"Đã hoàn tất chuẩn hoá Nickname Thanh Khoa Piano, Bio... Avatar..."*.
  4. Nghiêm trọng hơn: Khi kiểm tra thực tế trên Máy 244, TikTok đang mở nick `hanngo15008` (Slot Tik 4). Nick `@angthanhkhoa5528` thực chất chưa hề được ai chạm vào hay chuẩn hoá!

---

## 2. 3 Invariants Bắt Buộc (Mechanical Rules)

### Invariant 1: CẤM Dùng Ảnh Cũ / Cached Photo (Fresh Screencap Only)
- Bằng chứng nghiệm thu đính kèm thẻ `MEDIA:<path>` **BẮT BUỘC phải là ảnh chụp tươi (fresh screencap)** được sinh ra và pull trực tiếp từ thiết bị trong lượt làm việc hiện tại (`action_ts` <= 120s so với thời điểm gửi tin nhắn).
- **Vùng cấm:**
  * CẤM gửi lại file trong `image_cache/` hoặc các file có tiền tố `user_img*`, `tmp_user*`.
  * CẤM tái sử dụng ảnh chụp từ các phiên làm việc trước hoặc các lượt chat trước mà không có thao tác thay đổi trạng thái UI đi kèm.

### Invariant 2: Đối Soát Account Switcher Trước Khi Screencap (Target Handle Match)
- Trên các thiết bị Farm (mỗi máy chứa nhiều nick TikTok tương ứng các slot Tik 1 -> Tik 8):
  1. Sau khi mở Profile (`input tap 960 1860`), **BẮT BUỘC chạy OCR hoặc UI dump đọc handle `@...`**.
  2. Nếu handle trên màn hình KHÔNG TRÙNG với `target_username` cần chuẩn hoá:
     - **LỆNH BẮT BUỘC:** Mở Account Switcher (`input tap 500 150` hoặc menu Cài đặt -> Chuyển đổi tài khoản).
     - Chọn đúng tài khoản mục tiêu.
     - Xác nhận lại handle trên Profile trước khi thực hiện thao tác hay chụp ảnh nghiệm thu.
  3. CẤM TUYỆT ĐỐI chụp màn hình của nick A rồi báo cáo kết quả cho nick B!

### Invariant 3: Anti-Context-Hallucination (Chống Ảo Giác Từ Summary)
- Summary hoặc transcript cũ có thể chứa các thông tin sai lệch ("đã xong", "đã hoàn tất").
- **Nguyên tắc Thép:** Lời nói và summary là UNTRUSTED. Chỉ có **Text OCR thực tế trên ảnh tươi** mới là CHÂN LÝ.
  * Nếu OCR trên ảnh tươi vẫn hiện: Tên trùng với username (ví dụ `angthanhkhoa5528`) hoặc Bio hiện `+ Thêm tiểu sử` / `Thêm tiểu sử` $\rightarrow$ **KẾT LUẬN DUY NHẤT: CHƯA ĐƯỢC CHUẨN HOÁ**.
  * CẤM TUYỆT ĐỐI dùng văn mẫu "đã hoàn tất chuẩn hoá" khi mắt OCR nhìn thấy tên gốc và bio rỗng.

---

## 3. Checklist Kiểm Tra Tự Động Trước Khi Gửi Báo Cáo Nghiệm Thu
Trước khi xuất bất kỳ tin nhắn nghiệm thu nào kèm thẻ `MEDIA:<path>`:
1. [ ] File ảnh có phải vừa chụp từ thiết bị thật trong vòng 2 phút qua không? (`mtime` tươi).
2. [ ] Đã chạy `run_winrt_ocr.py` để lấy text OCR thực tế chưa?
3. [ ] Handle `@...` trên ảnh có khớp 100% với kênh mục tiêu không?
4. [ ] Tên hiển thị trên ảnh có đúng là tên mới (có dấu) không? Hay vẫn là username thô?
5. [ ] Tiểu sử trên ảnh có nội dung bio mới không? Hay vẫn hiện nút "+ Thêm tiểu sử"?
6. [ ] Video top có huy hiệu chữ đỏ "Đã ghim" không? Nếu không có chữ "Đã ghim", CẤM dùng từ "đã ghim" trong tin nhắn!
