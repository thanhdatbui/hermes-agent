# Bài Học Đối Soát Niche: Bẫy Nhãn Excel vs Mỏ Neo Video Thực Tế (Ground Truth)

## 1. Bản Chất Vấn Đề (The Excel Label Anchor Bias Trap)
- **Hiện tượng:** Khi nhận lệnh chuẩn hoá kênh hoặc trả lời câu hỏi "kênh thuộc niche nào", Coordinator tra cứu `lookup_channel.py` hoặc đọc cột `Keyword Video` trong các file `Tik<N>.xlsx`.
- **Sai lầm chết người (Confirmation Bias):** Thấy cột Keyword ghi `Xe`, Coordinator lập tức bị "neo tư duy" (Anchor Bias) vào chữ Xe. Khi nhìn lướt thumbnail hoặc ảnh chụp màn hình, não bộ tự động bẻ cong các chi tiết thị giác (mặt nước, cần câu, bụi cỏ) thành "khoang lái, kính chắn gió xe, đường cao tốc". Khi User chất vấn "Cái video cắn đề xuất là đi câu cá mà? Xe clmm à", Coordinator trước đó vẫn cố cãi vì tin vào nhãn Excel!
- **Sự thật nguyên nhân:** Trong quá trình vận hành nông trại TikTok lớn, hàng trăm hàng Excel được tạo theo template hoặc sao chép hàng loạt, việc **gán nhãn sai Keyword** (ví dụ thực tế là `Câu cá` nhưng copy nhầm nhãn `Xe`) diễn ra rất phổ biến.

## 2. Invariant Tối Cao: Video Đang Đăng Là Mỏ Neo Chân Lý (Ground Truth)
- **Quy tắc vàng:** **VIDEO THẬT LUÔN THẮNG MỌI DÒNG CHỮ TRONG EXCEL HAY SQLITE DATABASE.**
- **CẤM TUYỆT ĐỐI:** Cấm lấy nhãn `Keyword` trong Excel làm cơ sở để khẳng định niche của kênh khi chưa soi mắt đọc từng video thực tế đang đăng trên kênh.
- **Quy trình xác định Niche chuẩn 3 bước:**
  1. **Bước 1 (Soi mắt Thumbnail / Video đã đăng):** Cắt trực tiếp các thumbnail video cắn đề xuất trên ảnh màn hình kênh gửi vào. Dùng vision soi chi tiết hành động thực tế: nhân vật đang làm gì? (câu cá, nấu ăn, tập gym, lái xe...).
  2. **Bước 2 (Kiểm tra kho nguồn thực tế trên đĩa):** Trích xuất danh sách file trong `D:/TIKTOK-videonuoinick/<F_vid>` hoặc `D:/video goc/<F_src>` (hoặc kho trên Admin `D:/TIKTOK-videonuoinick-admin/<F_vid>`).
  3. **Bước 3 (Đính chính ngược lại Excel):** Nếu phát hiện nội dung video thực tế khác với cột Keyword trong Excel, **BẮT BUỘC coi Excel bị sai lệch** và chủ động cập nhật lại sổ cái Excel theo đúng video thật, tuyệt đối không được dùng chữ trong Excel để cãi lại User hay cãi lại hình ảnh thực tế!

## 3. TikTok Layout Khuyết Nút "Sửa Hồ Sơ" & Lỗi "Không Thể Lưu" Bio
- **Bẫy "Không thể lưu" (TikTok Server Rejection):** Trên các tài khoản đang cắn đề xuất hoặc tài khoản reg tự động mới, khi cố lưu Bio mới qua nút Lưu (`[925, 72][1056, 204]`), TikTok có thể chặn với toast `Không thể lưu`.
- **Cách xử lý an toàn:**
  - Không cố spam tap hay gửi broadcast liên tục (dễ dính checkpoint / shadowban thiết bị).
  - Hoàn tất các phần chuẩn hoá offline trước: đồng bộ sổ cái Excel (`Keyword`, `Hashtag Pool`), upload thay thế file `avatar.jpg` trong kho video, cắm marker `.manual_avatar_locked` và `.manual_hashtag_locked`.
  - Đưa máy về trạng thái an toàn (`LauncherActivity`, màn hình tắt, giải phóng lock) và báo cáo rõ hiện trường cho User.
