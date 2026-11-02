# Auto Video Avatar Extraction (YOLOv8 + Sharpness Scoring) & Anti-Hardcoded Crop Traps (2026-11-02)

## 1. Triệu chứng & Sai lầm nghiêm trọng (Root Cause)
- **Tự viết script crop tọa độ tĩnh:** Sử dụng `img[cy - sz//2 : cy + sz//2, cx - sz//2 : cx + sz//2]` mò mẫm trên video khiến avatar bị lệch tâm, chém trúng lưng/mông hoặc vật thể rác (bàn tay dính mỡ, long đền cao su).
- **Lỗi chém cụt mặt (Clamp vs Pad failure):** Khi đầu/mặt đối tượng nằm sát mép khung hình, việc cắt cố định mà không bù padding làm mất nửa khuôn mặt, bay tai, lẹm mõm.
- **Phóng đại mẩu ảnh nhỏ (<400px):** Cắt một góc nhỏ 180x180 rồi upscale lên 512x512 gây vỡ hạt pixel, mờ căm và nhòe nhoẹt.

## 2. Kiến trúc giải pháp chuẩn hóa tự động (Pipeline Architecture)
Thay vì dùng repo đồ chơi (như `autocrop` vốn chỉ nhận diện mặt người qua YuNet, mù với chó/mèo) hoặc crop tay, hệ thống bắt buộc sử dụng pipeline cơ giới hóa 5 bước:

1. **Frame Sampling & Motion Filter:**
   - Trích xuất frame theo bước nhảy đều (mỗi 0.5s trong 5-10s đầu).
   - Loại bỏ frame trùng lặp hoặc mờ do chuyển động.
2. **Object Detection (YOLOv8 Weights Local):**
   - Sử dụng weights có sẵn tại `D:/Taadaa/Tiktok-video/yolov8n.pt`.
   - Bắt các class COCO chuẩn: `0: person`, `15: cat`, `16: dog`.
   - Ngưỡng tin cậy cứng: `confidence >= 0.5`.
3. **Sharpness Scoring trên BBox (Laplacian Variance):**
   - **BẮT BUỘC:** Tính Laplacian Variance **CHỈ trên vùng Bounding Box** của đối tượng, tuyệt đối KHÔNG tính trên toàn frame (tránh trường hợp nền nhà/tường gạch có vân nét nhưng mặt con vật bị nhòe mà vẫn thắng điểm).
4. **Smart Square Crop & Dynamic Padding:**
   - Căn tâm hình ảnh theo trung tâm bounding box.
   - Thêm tỷ lệ khoảng trống (`headroom = 0.25 - 0.35`) để tạo bố cục thoáng.
   - Khi bounding box chạm mép frame: Bắt buộc dùng `cv2.copyMakeBorder` (Pad đều bằng màu nền/border) thay vì Clamp cắt cụt đầu/mặt đối tượng.
5. **Fail-Closed Gate:**
   - Nếu duyệt toàn bộ video mà không tìm thấy đối tượng hợp lệ (conf >= 0.5): Trả về `NO_SUBJECT` và kích hoạt báo cáo BLOCKED.
   - **CẤM TUYỆT ĐỐI** tự ý center-crop mò mẫm rồi báo cáo hoàn thành dối trá.
