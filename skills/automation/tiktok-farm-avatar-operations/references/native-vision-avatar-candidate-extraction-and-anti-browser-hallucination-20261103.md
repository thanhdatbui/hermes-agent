# Native Vision Avatar Candidate Extraction & Anti-Browser Hallucination (2026-11-03)

## 1. Bẫy Dùng `browser_vision` Để Đọc Ảnh Local & Nguy Cơ Ảo Giác
- **Hiện tượng:** Khi Agent tạo ra file canvas 4 phương án avatar (`m28_avatar_proposal_canvas.jpg`), thay vì để mô hình Gemini Multimodal đọc pixel trực tiếp, Agent lại gọi vòng vo `browser_navigate(file:///...)` và `browser_vision`.
- **Hậu quả:** 
  - Tại turn gọi `browser_vision`, Agent chỉ nhận thông báo text `Image loaded into context` chứ chưa nhận pixel trong turn đó.
  - Agent bịa đặt (hallucinate) nội dung chi tiết (như bịa ra *"cô gái công sở mặc áo sơ mi trắng ngồi nghiêng"* hay *"mặt cún cưng"*) trong khi thực tế chưa nhìn thấy ảnh thật.
- **Quy chuẩn dứt điểm:**
  - Mô hình Native Multimodal (`ag-gemini-pool-3`, Gemini Web, v.v.) đọc trực tiếp pixel ảnh đính kèm trong prompt.
  - CẤM TUYỆT ĐỐI mở browser đối phó để soi ảnh local. Mọi thẩm định phải dựa trên mắt đọc pixel thật hoặc thuật toán thị giác máy tính đo lường khách quan.

## 2. Kỹ Thuật Lọc Viền Phụ Đề Chân Dung (Canny Bottom Edge Noise)
Khi tự động crop avatar chân dung 1:1 từ video nguồn TikTok, 90% video dính phụ đề (subtitles/captions) ở 25% phía dưới khung hình:
```python
import cv2

# Phát hiện khuôn mặt (YuNet hoặc Cascade)
# Target crop box mở rộng 3.5x - 4.0x kích thước mặt để lấy bố cục vai + đầu
sz = int(max(fw, fh) * 3.5)
# ... căn tâm và clamp toạ độ x1, y1 ...

crop_gray = gray[y1:y1+sz, x1:x1+sz]
# Kiểm tra độ nhiễu biên cạnh ở 25% phía đáy ảnh
bottom_crop = crop_gray[int(sz * 0.75):, :]
bottom_noise = cv2.Canny(bottom_crop, 50, 150).mean()

# Ngưỡng sạch chữ: bottom_noise < 10.0 (loại bỏ hoàn toàn phụ đề dính vào áo/ngực)
# Kết hợp độ nét khuôn mặt:
face_sharpness = cv2.Laplacian(gray[fy:fy+fh, fx:fx+fw], cv2.CV_64F).var()
```
- Giúp trích xuất tự động 4 phương án sạch chữ 100% từ 100+ frame trong kho video mà không cần lọc tay.

## 3. Nhận Diện Nguồn Tin Tức / Phóng Sự Rác Để Đổi Nguồn (Source Swap)
- Khi toàn bộ khuôn mặt phát hiện được đều là nhân vật đang trả lời phỏng vấn tin tức, micro đài truyền hình hoặc hiện trường phóng sự:
  - Đây là **Nguồn tin tức / phóng sự bị cấm** theo User Profile Invariant: *"T cấm lấy nguồn mấy kênh tin tức rồi mà"*.
  - **Dừng ngay việc cố cắt avatar từ nguồn rác:** Báo cáo trung thực hiện trường và đề xuất **Phương án 2 (Đổi nguồn mới triệt để)**:
    1. Dọn sạch 100% kho render cũ (`D:/TIKTOK-videonuoinick/<F>`).
    2. Dọn sạch 100% kho video gốc cũ (`D:/video goc/<F>`).
    3. Bảo lưu nguyên vẹn cursor `Video Đã Đăng` (ví dụ: đã đăng 10 clip thì clip render mới bắt đầu từ `11.mp4`).
    4. Kéo nguồn mới từ `sources.qualified30.json` (thuộc các ngách hot: Ẩm thực, Bếp Việt, Hài hước, Thú cưng, Động lực).

## 4. Kỷ Luật Tool-Use Enforcement & Chống Hứa Suông ("Để Em...")
- Từ khóa nhạy cảm kích hoạt trừng phạt: Các phát ngôn chứa cụm từ *"để em nạp..."*, *"để em làm..."* nếu không đi kèm tool call thực thi ngay sẽ bị hệ thống Guard reject với mã:
  `[System Notice: Your response promised action ('để em...') but emitted NO tool calls.]`
- **Cách phản hồi chuẩn:**
  - Cung cấp kết quả thực thi hoàn tất (Artifact trên đĩa: file ảnh đơn lẻ `PA1.jpg`, file canvas `m28_avatar_clean_proposals.jpg`).
  - Đưa ra đường dẫn file và lệnh kích hoạt cơ giới hóa (`python D:/Taadaa/tools/run_upload_avatar.py --tik <N> --machine <M>`).
  - Không hứa hẹn suông dạng *"để em..."*.
