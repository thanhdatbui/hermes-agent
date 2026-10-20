# Vision LLM Avatar Audit & Auto-Healing Pipeline (Quét DB Phát Hiện & Thay Thế Avatar Lỗi Toàn Farm)

## 1. Bối Cảnh & Vấn Đề Thực Tế Trên Phone Farm
Nhiều tài khoản TikTok trên farm sau các đợt cào video hoặc gán avatar hàng loạt bị tình trạng **Avatar rác / Avatar lỗi**:
- **Ảnh đồ vật cơ khí / vô tri**: Ống lồng xe máy, thụt giảm xóc, mặt đá granite, mặt bàn gỗ, tường nhà...
- **Ảnh tranh chữ & logo**: Logo kênh YouTube, chữ 3D rác, banner quảng cáo, watermark thumbnail...
- **Lệch nhân vật / lệch niche**: Kênh nữ tập gym/fitness nhưng avatar là phong cảnh hoặc người khác; kênh thú cưng nhưng avatar là ảnh chân dung người...
- **Ảnh mờ / đen / hỏng hiển thị**: Cắt sai frame chuyển cảnh (transition black frame).

Những avatar này làm hỏng độ trust của kênh TikTok, giảm tương tác tự nhiên và khiến kênh trông như tài khoản bot rác.

---

## 2. Quy Trình Chuẩn Hóa Avatar Tự Động Qua 3 Pha

```
[Database Cào Thật / Snapshots]
         │
         ▼
[Pha 1: Vision LLM Triage] ──► Phân loại VALID vs INVALID (Avatar rác, logo, đồ vật, lệch niche)
         │ (Chỉ lọc các nick INVALID / PENDING)
         ▼
[Pha 2: Auto-Extraction]   ──► Trích xuất 6-8 frames từ 1.mp4..3.mp4 trong kho video gốc
         │                 ──► Vision LLM chọn frame khuôn mặt đẹp nhất
         │                 ──► Crop 512x512, xuất avatar.jpg mới & cắm cờ khóa cứng
         ▼
[Pha 3: Watchdog Upload]   ──► Đưa vào hàng đợi thay thế (avatar_replace_queue: PENDING)
                           ──► Watchdog ca tối tự động nạp ảnh lên thiết bị thật
```

---

## 3. Chi Tiết Từng Pha Thực Thi

### Pha 1: Vision LLM Audit (Quét Thẩm Định Không Cần Chạm Thiết Bị)
1. **Truy vấn danh sách tài khoản active từ Tracker DB**:
   - Lấy danh sách cặp `(username, may, tik, folder_video, video_goc)` từ bảng quản lý hàng đợi và snapshots cào thật từ TikTok.
   - Định vị file `avatar.jpg` hiện tại trong kho video tương ứng.
2. **Gửi ảnh qua Vision LLM (OmniRoute / Gemini 3.8 / Flash)**:
   - Prompt phân loại nghiêm ngặt:
     * `VALID`: Khuôn mặt người thật, rõ nét, chính diện hoặc góc nghiêng tự nhiên, đúng chủ đề kênh (hoặc con vật rõ ràng nếu niche thú cưng).
     * `INVALID`: Chứa chữ/text, logo, đồ vật vô tri, phong cảnh không có người, mặt bị che khuất hoặc cắt lẹm.

### Pha 2: Trích Xuất & Tái Tạo Avatar Đúng Từ Video Thực Tế
1. Với mỗi folder bị gắn cờ `INVALID`:
   - Mở 3 video đầu tiên (`1.mp4`, `2.mp4`, `3.mp4`) trong kho video gốc hoặc video nuôi thực tế.
   - Trích xuất 5-10 frames đại diện tại các mốc giây tĩnh (1s, 2s, 3s, 5s).
2. Dùng Vision LLM / OpenCV Face Classifier chấm điểm:
   - Ưu tiên: Nụ cười tươi, mắt nhìn thẳng, ánh sáng đều, không dính chữ phụ đề.
3. Tự động crop vuông 512x512 theo tâm khuôn mặt, ghi đè file `avatar.jpg`.
4. Tạo cờ vật lý `.manual_avatar_locked` và đăng ký vào registry bảo vệ avatar chống bị ghi đè.

### Pha 3: Đưa Vào Hàng Đợi & Watchdog Ca Tối Nạp Lên Máy Thật
1. Cập nhật bảng `avatar_replace_queue` trong Tracker DB: Đặt `status = 'PENDING'`.
2. Cập nhật cột `Avatar` trên các file Excel `Tik*.xlsx` thành `PENDING`.
3. Con Watchdog ca tối (`post_evening_avatar_watchdog.py`, khung giờ 21:00 - 23:45) tự động quét danh sách `PENDING` và kích hoạt script nạp avatar qua Photo Picker trên từng máy.
