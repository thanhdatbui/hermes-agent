# Quy Trình Tra Cứu O(1) & Xuất Bản Bảng Proposal Canvas Chuẩn Hoá 5-in-1

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
- Khi phát hiện lệch chủ thể (Creator Mismatch): Video thực tế là nữ (Vlog/Thời trang/Makeup) nhưng Avatar hoặc Tên hiển thị là nam (ảnh dính chữ do đợt reg nick trước đó).
- Quét các video trong kho gốc `D:/video goc/<F_src>/`:
  - Dùng OpenCV Haar Cascade (`haarcascade_frontalface_default.xml`) tìm frame có khuôn mặt đơn rõ nét (minSize >= 150x150).
  - Đo độ sắc nét bằng phương sai Laplacian (`cv2.Laplacian(face_roi, cv2.CV_64F).var()`).
  - Hậu kiểm WinRT OCR (`from winrt_ocr_util import winrt_ocr`): Kết quả OCR text phải rỗng (`''`), đảm bảo 100% không dính chữ rác hay watermark.
  - Cắt khung vuông tâm mặt kèm viền tròn preview xanh lá (`make_circle_preview`).

## 3. Tạo Bảng Proposal Canvas Chuẩn Hoá 5-in-1 (Pillow + Vietnamese Font)
- Bảng Proposal Canvas gồm 4 card phương án:
  - **PA 1 (Đề xuất):** Chân dung cận cảnh sắc nét, tươi tắn từ video gốc chính chủ.
  - **PA 2:** Phong cách vlog đời thường / trang phục tự nhiên.
  - **PA 3:** Phong cách dạo phố / selfie thời trang.
  - **PA 4:** Giữ nguyên avatar hiện tại (đối chứng lệch nhân vật).
- Thông tin chuẩn hoá 5-in-1 ở nửa dưới:
  1. *Tên hiển thị (Nickname):* Chuẩn hoá tiếng Việt có dấu đúng giới tính/nhân vật (ví dụ: `Hà My ✨`).
  2. *Username TikTok (@handle):* Chuẩn hoá theo tên nhân vật (ví dụ: `@hamy.daily`).
  3. *Tiểu sử (Bio mới):* Bio tích cực, phù hợp ngách thực tế.
  4. *Ghim Top Video:* Chọn top 3 video có lượt view cao nhất trên kênh.
  5. *Đồng bộ Ngách & Hashtag:* Cập nhật cột Keyword và Hashtag Pool trong `Tik<N>.xlsx`.

## 4. Hậu Kiểm Bắt Buộc Trước Khi Gửi MEDIA:
- BẮT BUỘC gọi WinRT OCR đọc lại bảng Proposal Canvas trước khi gửi.
- Tạo Vision Receipt hợp lệ để thỏa mãn Gate:
  ```python
  from guard_media_vision_gate import create_vision_receipt
  from winrt_ocr_util import winrt_ocr
  txt = winrt_ocr(canvas_path)
  create_vision_receipt(image_path=canvas_path, tool_called='winrt_ocr', ocr_raw_text=txt, detected_entities=[...], device_id=serial, ocr_status='OK')
  ```
- Trình bày rõ ràng những gì đã thấy tận mắt qua OCR/Vision trong phản hồi chat trước khi đính kèm `MEDIA:<path>`.
