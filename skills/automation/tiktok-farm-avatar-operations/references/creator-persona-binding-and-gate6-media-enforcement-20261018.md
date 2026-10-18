# Bẫy Sai Lệch Creator Persona Avatar & Cơ Chế Chặn Bỏ Quên MEDIA: (2026-10-18)

## 1. Hiện trường & Bối cảnh Sự cố (Kênh @huynhdiem0806 - Máy 23)

Trong quá trình chuẩn hoá kênh `@huynhdiem0806` (Máy 23, Slot 3, Folder Video 179):
- **Sai phạm Creator Persona:**
  - `Tik3.xlsx` ban đầu bị lệch: cột `Folder Video` là 179 nhưng `Video Goc` là 183.
  - Thay vì trích xuất từ chính các video thực tế đang đăng của kênh trong `D:\TIKTOK-videonuoinick\179`, Coordinator bốc file `avatar.jpg` tĩnh có sẵn từ thư mục `D:\video goc\183`.
  - Kết quả: Ảnh là một cô gái phong cách thời trang/chụp studio khác hẳn nhân vật nữ đời thường xuất hiện trong các clip nấu ăn, sinh hoạt gia đình của folder 179.
  - User lập tức chấn chỉnh gay gắt: *"Ava kiểu gì v?"*.
- **Sai phạm Gate 6 Bỏ Quên Thẻ `MEDIA:`:**
  - Script canonical đổi tên và nạp bio hoàn tất thành công trên thiết bị (`verified=True`), sinh file ảnh `m23_huynhdiem0806_rename_confirmed.png`.
  - Tuy nhiên, trong tin nhắn tổng kết, Coordinator viết bản báo cáo dạng text mà hoàn toàn không có dòng `MEDIA:<path>` nào.
  - User nổi giận: *"Là sao có thấy tấm hình mẹ nào đâu? Sso lại vi phạm k gửi hình cho t. Gọi claude cli vào tìm hiểu"*.

---

## 2. Thẩm Định Kiến Trúc Độc Lập Từ Claude Sonnet 5.5 CLI

Claude Sonnet 5.5 CLI đã phân tích và chỉ ra 2 căn nguyên hệ thống:

### A. Lỗi Binding Lỏng Lẻo Giữa Niche/Creator và Asset Pool
- **Off-by-N Folder Error:** Thư mục 179 và 183 chỉ cách nhau 4 số, sinh ra do copy/paste tham số hoặc lệch dòng cấu hình Excel.
- **Rủi ro:** Khi avatar không phải là khuôn mặt của chính creator trong các video, tài khoản bị mất tính chân thực, giảm tỷ lệ giữ chân người xem và phá vỡ độ trust của nick nuôi.
- **Quy tắc BẮT BUỘC:**
  1. **Strict 1-1 Creator Persona Binding:** Avatar BẮT BUỘC phải trích xuất trực tiếp từ các video MP4 đang render của kênh (`D:\TIKTOK-videonuoinick\<slot>\.avatar_work\representative_frames\`).
  2. **CẤM Dùng Ảnh Tĩnh Chưa Đối Soát:** Tuyệt đối không tái sử dụng file `avatar.jpg` tĩnh trong `video goc` nếu chưa chạy face matching hoặc đối soát mắt qua WinRT OCR / LLM Vision với video thực tế.

### B. Cơ Chế Bỏ Quên `MEDIA:` & Bẫy Budget Panic
- **Nhầm Lẫn Tác Vụ:** Coordinator coi tin nhắn tổng kết là "báo cáo hành chính", không nhận diện rằng hành động đổi tên, sửa bio, thay avatar là các bước đột biến trạng thái UI trên thiết bị thật (`pending_media_obligation = True`).
- **Budget Panic:** Khi gần chạm ngưỡng giới hạn lượt gọi hoặc ở cuối lượt trả lời, Coordinator có xu hướng "chốt text cho nhanh" để tránh vượt giới hạn, tự tiện bỏ qua bước kiểm chứng và gắn thẻ `MEDIA:`.
- **Quy tắc BẮT BUỘC:**
  1. **Nghĩa vụ ảnh bất khả phân ly:** Mọi hành động có side-effect trên màn hình thiết bị BẮT BUỘC phải đi kèm thẻ `MEDIA:<posix_path>` trên một dòng độc lập trong cùng tin nhắn kết quả.
  2. **Mechanical Runtime Hook (`MISSING_MEDIA_EVIDENCE`):** Chặn đứng ở tầng xuất bản output nếu tin nhắn chứa các từ khóa kết quả (`đã đổi`, `thành công`, `hoàn tất`, `chuẩn hoá`) kết hợp với đối tượng UI (`tên`, `bio`, `avatar`, `kênh`) mà KHÔNG có thẻ `MEDIA:`.

---

## 3. Checklist Chuẩn Bị Avatar Chuẩn Farm

1. **Trích xuất:** Dùng FFmpeg lấy frame mặt rõ nhất từ `1.mp4`, `2.mp4`... của folder slot đích, hoặc bốc frame chất lượng cao trong `.avatar_work/representative_frames/`.
2. **Kiểm tra sạch:** Chạy WinRT OCR (`ocr_boxes.ps1`) kiểm tra 100% không dính text, watermark, sticker, số tập.
3. **Cắt cúp an toàn:** Canh tâm tròn $512 \times 512$, headroom $\ge 30\text{px}$, đỉnh tóc và cằm trọn vẹn trong viền tròn profile.
4. **Bảo vệ đĩa:** Đồng bộ vào `avatar.jpg`, cắm `.manual_avatar_locked` và ghi nhận vào `manual_avatar_protected_folders.json`.
5. **Gửi duyệt tức thì:** Gửi ngay `MEDIA:<path>` cho User duyệt mắt, không giấu ảnh trong máy để chạy ngầm.
