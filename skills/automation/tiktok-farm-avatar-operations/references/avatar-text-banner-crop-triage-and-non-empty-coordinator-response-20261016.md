# Avatar Text-Banner Crop Triage, F_src vs F_vid Drift & Non-Empty Coordinator Response Protocol (2026-10-16)

## 1. Hiện Tượng & Cạm Bẫy Thực Tế
1. **Bẫy Avatar Cắt Nhầm Biển Hiệu / Banner Chữ (Text-Banner False Avatar)**:
   - Trong quá trình tự động hóa avatar trước đây, các script tự động dò tìm vật thể hoặc crop ngẫu nhiên có thể cắt trúng một góc biển hiệu, banner chữ quảng cáo (ví dụ: chữ in hoa "Nghi...", "Rất Tốt", nền vàng đỏ).
   - Khi Operator yêu cầu *"Chuẩn hoá acc này"* kèm ảnh chụp Profile:
     * Dùng local vision endpoint (`http://127.0.0.1:20129/v1/chat/completions`) kiểm tra ảnh chụp màn hình Profile và ảnh `avatar.jpg` trong cả hai kho $F_{vid}$ (`D:/TIKTOK-videonuoinick/<F_vid>/`) và $F_{src}$ (`D:/video goc/<F_src>/`).
     * Nếu avatar hiện tại là ảnh banner chữ không có người hoặc vật thể chủ đạo, xác định ngay là avatar rác cần thay thế.

2. **Đối Soát Kênh $F_{src}$ (Nguồn cào) vs $F_{vid}$ (Render đích)**:
   - Trong `Tik<N>.xlsx`, dòng tài khoản thường có:
     * Cột D (`Folder Video`): Thư mục video render đích ($F_{vid}$).
     * Cột E (`Video Gốc`): Thư mục video gốc nguồn cào ($F_{src}$).
   - Thường xảy ra tình trạng: Trong $F_{vid}$ chứa avatar rác (hoặc chưa có avatar), nhưng trong $F_{src}$ (`D:/video goc/<F_src>/avatar.jpg`) đã có sẵn avatar chất lượng cao (ví dụ: chân dung reviewer mặc áo polo gắn micro cài áo) hoặc các frame đại diện (`.avatar_work/representative_frames/`).
   - Cần đồng bộ avatar chuẩn từ $F_{src}$ sang $F_{vid}$ và cắm marker `.manual_avatar_locked`, `.manual_hashtag_locked` để bảo vệ.

3. **Kỷ Luật Coordinator: CẤM Trả Về Lượt Trả Lời Trống (Empty Response Anti-Pattern)**:
   - **Triệu chứng**: Sau khi Coordinator dispatch subagent chạy nền (`delegate_task(..., role='leaf')`), Coordinator chạy thêm một số lệnh kiểm tra terminal rồi kết thúc lượt trả lời mà KHÔNG xuất ra bất kỳ văn bản phản hồi nào cho User (khiến hệ thống harness báo lỗi: *\"You just executed tool calls but returned an empty response. Please process the tool results above and continue with the task\"*).
   - **Quy tắc bất biến**:
     * Khi dispatch subagent chạy nền (`delegate_task`), Coordinator BẮT BUỘC phải phản hồi ngay cho User trong cùng lượt đó.
     * Cấu trúc phản hồi tức thì:
       1. **Định vị O(1)**: Handle, Display Name, Máy, Slot, Serial, Trạng thái nguồn video ($F_{src}, F_{vid}$).
       2. **Kiểm toán 3 món (Ava - Hashtag - Pin)**: Đánh giá chi tiết hiện trạng từng món theo ảnh User gửi và đối chiếu kho farm.
       3. **Hành động đã dispatch**: Báo cáo rõ Worker đang xử lý gì ở chế độ nền (cắt preview, sync kho, update queue) và các bước tiếp theo.
     * TUYỆT ĐỐI CẤM im lặng hoặc chỉ có suy nghĩ nội tâm mà không sinh ra nội dung phản hồi cho User.

## 2. Quy Chuẩn Soi Mắt Avatar Cục Bộ Qua Browser Tools (`browser_navigate` + `browser_vision`)
- **Nguyên tắc Invariant**: Trước khi đính kèm bất kỳ thẻ `MEDIA:<path>` nào (ảnh preview avatar, vòng tròn xanh, màn hình Profile/Switcher), Coordinator BẮT BUỘC phải mở ảnh soi mắt thực tế, CẤM gửi ảnh mù / đối phó.
- **Quy trình thực thi chuẩn O(1) với file cục bộ**:
  1. Dùng `browser_navigate(url="file:///D:/Taadaa/reports/avatar_opt1_preview.jpg")` để tải trực tiếp ảnh từ đĩa vào trình duyệt nội bộ.
  2. Gọi `browser_vision(annotate=False, question="Xác nhận chi tiết hình ảnh: Chủ thể là ai, mặc áo gì, bố cục vòng tròn xanh có vừa vặn không, có bị lẹm cằm hay đỉnh đầu không?")`.
  3. Lặp lại với các phương án so sánh (Phương án 2).
  4. Trích dẫn ngắn gọn kết quả soi mắt (headroom, cằm, trang phục, micro, góc máy) vào phản hồi gửi User để chứng minh tính trung thực của bằng chứng.

## 3. Kỷ Luật Ngân Sách T1 Coordinator & Cạm Bẫy Tooling
- **Ngân sách T1 cứng**: Tối đa 5 files, <= 200 dòng cộng dồn cả session. Khi nhận thông báo `[COORDINATOR WRITE DENIED]: Hết ngân sách T1`, Coordinator BẮT BUỘC dừng tự ghi file mà chuyển sang dispatch Worker qua `delegate_task(role='leaf')` hoặc tái sử dụng các tool inspect có sẵn (`inspect_machine.py`, `inspect_user_screenshot.py`).
- **Bẫy Null Character trong terminal với inline python (`\"`)**: Khi truyền script inline qua `terminal` lệnh `python -c "..."`, việc escape nháy kép `\"` có thể kích hoạt lỗi `ValueError: open: embedded null character in path` trong `lifecycle_guard.py`. Khắc phục: Dùng nháy đơn bọc ngoài `python -c '...'` hoặc lưu script riêng rồi thực thi.

