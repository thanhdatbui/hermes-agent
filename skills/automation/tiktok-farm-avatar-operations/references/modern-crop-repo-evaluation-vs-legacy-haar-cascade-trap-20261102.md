# Bài học: Tránh bẫy nhầm lẫn repo cắt ảnh hiện đại với script Haar Cascade cũ & Quy trình kiểm tra repo chuẩn (2026-11-02)

## 1. Hiện tượng & Sai lầm nghiêm trọng của Agent
- **Hiện tượng:** Khi Người dùng hỏi *"session khác vừa kéo repo cắt ảnh, kiểm tra coi dùng đc k"* và chất vấn *"sao giờ lại bảo repo từ 15 năm trước"*:
- **Sai lầm:** Agent không dùng `session_search` để tra đúng lịch sử các phiên thảo luận của Người dùng (nơi đã khảo sát 4 repo GitHub hiện đại: `leblancfg/autocrop`, `Sotejaswini/AI-Video-Thumbnail-Generator`, `pouriamdr/Video-Face-Extractor`, `Fierens96/autocropface`).
- Ngược lại, Agent đi quét thư mục đĩa và đọc trúng các script tự chế cũ (`detect_and_crop.py`, `crop_faces.py`) vốn dùng `cv2.CascadeClassifier(haarcascade_frontalface_default.xml)` từ 15 năm trước, rồi quy chụp hồ đồ rằng repo người dùng đề cập là công nghệ cổ lỗ sĩ.

## 2. Bản chất kỹ thuật của các Repo Cắt Ảnh Hiện Đại
| Công cụ / Repo | Thuật toán nền tảng | Ưu điểm thực chiến | Nhược điểm đối với Farm TikTok |
| :--- | :--- | :--- | :--- |
| **`leblancfg/autocrop`** (v2.0.0, 10/2026) | **YuNet (FaceDetectorYN)** | Cực mạnh về căn giữa khuôn mặt người, tự động tính headroom, bắt tốt góc nghiêng 90 độ, chuẩn Studio. | Chỉ nhận diện mặt NGƯỜI, hoàn toàn bỏ qua hoặc fail với kênh ĐỘNG VẬT (chó, mèo, thú cưng). |
| **`AI-Video-Thumbnail-Generator`** | **YOLOv8 + Motion Detection** | Bắt được cả Người, Chó, Mèo (`person`, `dog`, `cat`), có lọc motion blur. | Thiết kế cho thumbnail 16:9, cần tinh chỉnh offset để ra avatar vuông 1:1. |
| **Pipeline Chuẩn Taadaa Farm** | **Frame Sampling + Laplacian Sharpness + YOLOv8/YuNet + Zero-Text OCR** | Chủ động 100% đối tượng theo ngách (Người / Thú cưng), loại sạch sub chữ tin tức bằng WinRT OCR, căn tâm 1:1 có bù trán. | Cần điều phối engine phù hợp theo ngách kênh. |

## 3. Quy tắc bắt buộc khi Người dùng nhắc về Repo / Công cụ từ Session khác
1. **BẮT BUỘC tra cứu `session_search` trước khi kết luận:** Dùng từ khóa `"repo"`, `"clone"`, tên tác vụ trong các session gần nhất để nắm đúng Ground Truth và đề xuất của Hội đồng Cố vấn.
2. **CẤM quy chụp công nghệ dựa trên script rác local:** Script rác trên đĩa không đại diện cho repo người dùng thảo luận.
3. **Phân loại ngách trước khi áp dụng tool crop:**
   - Kênh Người (Vlog, Nữ sinh, Làm đẹp, Chuyên gia): Ưu tiên `autocrop` / `YuNet`.
   - Kênh Thú cưng (Chó, Mèo): Bắt buộc dùng `YOLOv8` (`yolov8n.pt`).
   - Kênh Tin tức / Thời sự / Xe cộ: Kiểm tra Zero-Text OCR; nếu clip toàn chữ sub/logo, không cố bóc avatar cá nhân giả tạo mà dùng logo biểu tượng hoặc frame xe sạch.
