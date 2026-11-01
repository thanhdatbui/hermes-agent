# Quy Trình Tra Cứu O(1) & Xuất Bản Bảng Proposal Canvas Chuẩn Hoá 5-in-1

## 0. BƯỚC 0 BẮT BUỘC: Soi Mắt Ảnh Profile Đầu Vào Trước Khi Tra Cứu (Anti-Premature-Inference)
- **Invariant tuyệt đối:** Khi nhận lệnh kèm ảnh profile hoặc ảnh màn hình kênh (`[Image attached at: ...]`), Coordinator **BẮT BUỘC** phải stage ảnh và gọi `browser_vision` đọc tận mắt trước khi chạy bất kỳ script tra cứu nào.
- **Mục tiêu nhận diện:**
  1. Xác định chính xác `@username` và tên hiển thị trên ảnh.
  2. Đọc rõ nội dung video đã đăng (thumbnail, view count, chủ thể video). Video đang đăng là **MỎ NEO CHÂN LÝ (Ground Truth)** của kênh.
  3. Xác định dạng avatar hiện tại (ảnh cá nhân thật hay ảnh rác gán lúc reg nick).
- **Cấm:** Cấm dựa vào nhãn Keyword trong Excel (thường xuyên bị ghi sai như `Anime` trong khi video là `Thú cưng`) hoặc quét mò các clip khác trong thư mục để tự suy diễn sai lệch chủ thể kênh.

## 1. Tra Cứu Toạ Độ Farm O(1) & Ngăn Ngừa Quét Đĩa
- **Lệnh tra cứu tức thì:**
  ```bash
  python D:/Taadaa/tools/lookup_channel.py -u <username> --json
  ```
  Lệnh trả về đầy đủ: `machine`, `slot`, `tik_workbook` (Tik<N>.xlsx), `folder_video_render` (F_vid), `folder_video_goc` (F_src), và telemetry hiện tại.
- **Kỷ luật an toàn tuyệt đối:** CẤM dùng `os.walk` hay `glob` quét đĩa diện rộng để tìm file Excel hoặc video (sẽ bị Guard chặn lập tức). Đường dẫn chuẩn nằm tại:
  - Máy Kibe (< 200): `D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx` và `taikhoan_run_safe.xlsx`.
  - Máy Admin (>= 200): `D:/OneDrive/TaadaaData/admin/Tik<N>.xlsx`.
  - Database đồng bộ: `D:/Taadaa/data/tiktok_tracker.db`.

## 2. Trích Xuất Avatar Khớp Chủ Thể Video & Sạch Chữ 100%
- Khi phát hiện lệch chủ thể (Creator Mismatch): Video thực tế là nữ (Vlog/Thời trang/Makeup) hoặc thú cưng nhưng Avatar hoặc Tên hiển thị bị lệch.
- **Kỷ luật chống treo (Anti-Hang Invariant):**
  - CẤM TUYỆT ĐỐI gọi trực tiếp `cv2.VideoCapture` trần trụi trong luồng terminal foreground (sẽ bị deadlock ở native C++ Media Foundation/DirectShow trên Windows gây treo 60 phút).
  - BẮT BUỘC dùng hàm cô lập tiến trình có hard timeout 10s:
    ```python
    from anti_hang_guard import safe_extract_video_frame
    frame = safe_extract_video_frame(vid_path, timestamp_s=2.0, timeout_s=10.0)
    ```
- Đo độ sắc nét bằng phương sai Laplacian (`cv2.Laplacian(face_roi, cv2.CV_64F).var()`).
- Hậu kiểm WinRT OCR (`from winrt_ocr_util import winrt_ocr`): Kết quả OCR text phải rỗng (`''`), đảm bảo 100% không dính chữ rác hay watermark (như Kangen Water, chữ quảng cáo).
- Cắt khung vuông tâm mặt kèm viền tròn preview xanh lá (`make_circle_preview`).

## 3. Tạo Bảng Proposal Canvas Chuẩn Hoá 5-in-1 (Pillow + Vietnamese Font)
- Bảng Proposal Canvas gồm 4 card phương án:
  - **PA 1 (Đề xuất):** Chân dung cận cảnh sắc nét, tươi tắn từ video gốc chính chủ.
  - **PA 2:** Phong cách đời thường / góc chụp khác.
  - **PA 3:** Phong cách dạo phố / góc chụp thứ 3.
  - **PA 4:** Avatar hiện tại hoặc góc chụp thứ 4 từ clip khác.
- **CẤM NHÂN BẢN ẢNH (ANTI-DUPLICATE INVARIANT):** CẤM TUYỆT ĐỐI lấy 1 file ảnh duy nhất nhân bản thành 4 ô (chỉ zoom nhẹ hay đổi độ sáng) rồi bịa đặt lời mô tả khác nhau. Cả 4 ô tròn bắt buộc phải là 4 khung hình / góc chụp khác nhau thật 100%.
- Thông tin chuẩn hoá 5-in-1 ở nửa dưới:
  1. *Tên hiển thị (Nickname):* Chuẩn hoá tiếng Việt có dấu đúng giới tính/nhân vật (ví dụ: `Hà My ✨`, `Bắp Ngô Daily`).
  2. *Username TikTok (@handle):* Chuẩn hoá theo tên nhân vật nếu cần.
  3. *Tiểu sử (Bio mới):* Bio tích cực, phù hợp ngách thực tế, có dấu 100%.
  4. *Ghim Top Video:* Chọn top 3 video có lượt view cao nhất trên kênh (chỉ ghim khi >= 1.000 view).
  5. *Đồng bộ Ngách & Hashtag:* Cập nhật cột Keyword và Hashtag Pool trong `Tik<N>.xlsx`.

## 4. Hậu Kiểm Bắt Buộc Trước Khi Gửi MEDIA (Banned WinRT OCR Loophole):
- **CẤM DÙNG WINRT OCR ĐỂ CẤP RECEIPT:** `guard_media_vision_gate.py` đã chặn vô điều kiện `tool_called='winrt_ocr'` cho mọi ảnh visual/proposal/canvas với lỗi `UNVERIFIED_BY_VISION`. CẤM dùng OCR quét chữ trên canvas để lách luật.
- **BẮT BUỘC SOI MẮT THẬT QUA BROWSER VISION:**
  1. Mở file canvas qua `browser_navigate(url="file:///D:/...")`.
  2. Gọi `browser_vision` mở mắt soi trực tiếp cả 4 ô tròn: xác nhận đúng chủ thể, không dính người/vật thể lạ, không dính watermark, không trùng lặp ảnh.
  3. Đăng ký receipt hợp lệ:
     ```python
     from guard_media_vision_gate import create_vision_receipt
     create_vision_receipt(image_path=canvas_path, tool_called='browser_vision', ocr_raw_text='...', detected_entities=[...], ocr_status='OK')
     ```
- Trình bày rõ ràng và trung thực những gì đã thấy tận mắt qua vision trong phản hồi chat trước khi đính kèm `MEDIA:<path>`.
- **Kỷ luật trình bày:** CẤM xả raw `git diff` vào chat Telegram của người dùng. Chỉ báo cáo kết quả thực thi và trạng thái hoàn thành.
