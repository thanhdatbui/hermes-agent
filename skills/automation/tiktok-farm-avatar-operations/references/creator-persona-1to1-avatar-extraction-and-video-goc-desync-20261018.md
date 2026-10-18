# Creator Persona 1-1 Avatar Extraction & Video Goc Desync Trap (2026-10-18)

## 1. Hiện trường Sự cố (Kênh @huynhdiem0806 - Máy 23)
- **Bối cảnh:** Chuẩn hoá kênh `@huynhdiem0806` trên Máy 23 (Tik 3, Slot 3, Folder Video nuôi nick 179).
- **Lỗi sai lệch Persona:**
  - File Excel `Tik3.xlsx` có sự sai lệch thông tin giữa 2 cột: `Folder Video = 179` nhưng `Video Goc = 183`.
  - Coordinator chủ quan, không kiểm tra nội dung video thực tế đang đăng mà bốc thẳng file `avatar.jpg` tĩnh có sẵn trong `D:\video goc\183\avatar.jpg`.
  - Hậu quả: Ảnh là một cô gái phong cách thời trang/chụp studio hoàn toàn khác với cô gái đời thường trong các clip nấu ăn, sinh hoạt gia đình của folder 179.
  - User lập tức chấn chỉnh gay gắt: *"Ava kiểu gì v?"*.

## 2. Thẩm định Kiến trúc & Nguyên nhân Gốc rễ
1. **Lệch Mapping Cấu Hình (Off-by-N Configuration Desync):**
   - Sự không nhất quán giữa `Video Goc` và `Folder Video` trong bảng tính Excel dễ dẫn tới việc bốc nhầm tài nguyên từ các thư mục lân cận.
2. **Thiếu Khâu Đối Soát Persona (Blind Static Asset Re-use):**
   - File `avatar.jpg` tĩnh trong thư mục gốc có thể là tàn dư từ các đợt render cũ hoặc lấy nhầm từ folder khác. Tái sử dụng file tĩnh mà không đối soát với khuôn mặt trong video thực tế là nguồn cơn chính gây mất trust và phá vỡ tính đồng nhất của kênh.
3. **Phá Vỡ Trải Nghiệm & Độ Trust:**
   - Kênh TikTok nuôi nick hướng tới organic view. Nếu người xem thấy video là một người nhưng avatar là người khác hoàn toàn, tỷ lệ click vào trang cá nhân và follow sẽ giảm sút nghiêm trọng, thuật toán dễ đánh giá là tài khoản reup/spam.

## 3. Quy Tắc Bất Biến: Strict 1-1 Creator Persona Binding
- **Nguyên tắc cốt lõi:** Avatar BẮT BUỘC 100% phải là khuôn mặt của chính creator xuất hiện trong các video đang nuôi nick của folder đó.
- **Nguồn trích xuất duy nhất:** BẮT BUỘC lấy từ thư mục frame đại diện của chính folder render:
  `D:\TIKTOK-videonuoinick\<Folder>\.avatar_work\representative_frames\`
  (chọn frame cận cảnh rõ nét nhất, ví dụ `v04_003.jpg`).
- **Tiêu chuẩn Avatar đạt chuẩn:**
  1. *Chủ thể:* Đúng người trong video, chiếm 45%–60% khung hình, khuôn mặt nằm chính tâm hình tròn $512 \times 512$.
  2. *Độ sạch chữ (Clean Text):* WinRT OCR (`ocr_boxes.ps1`) quét sạch 100% không dính text, subtitle, số tập, sticker hay logo watermark.
  3. *Headroom:* Khoảng cách từ đỉnh đầu đến mép trên tối thiểu $30\text{px}$, cằm không chạm mép dưới để không bị lẹm khi TikTok lồng khung tròn profile.
  4. *Khóa bảo vệ:* Sau khi tạo ảnh thành phẩm, copy đồng bộ vào cả 2 kho (`D:\TIKTOK-videonuoinick\<Folder>\avatar.jpg` và `D:\video goc\<Folder>\avatar.jpg`), cắm cờ `.manual_avatar_locked` và ghi nhận vào `manual_avatar_protected_folders.json`.

## 4. Quy trình Thực thi Upload Chuẩn (Single Machine Avatar Runner)
- Tuyệt đối CẤM viết script ad-hoc tap tay ADB hay tự chế runner mới.
- Chạy qua launcher chuẩn hỗ trợ tham số máy và ca Tik:
  `python D:/Taadaa/run_avatar_m1.py <Machine> <Tik>`
  (gọi engine `run_tiktok_upload_avatar.ps1` với `-ForceAvatarMachineList <Machine> -Tik <Tik> -MaxParallel 1 -AvatarOnly`).
- Runner tự động:
  1. Dọn dẹp cache `/sdcard/DCIM/.thumbnails/*` và `/sdcard/DCIM/Camera/*` để loại bỏ nguy cơ photo picker chọn nhầm ảnh cũ.
  2. Tự động kiểm tra và chuyển đúng tài khoản (`account_switcher`) nếu máy đang mở tài khoản khác.
  3. Đẩy ảnh mới vào thiết bị, vào Sửa hồ sơ -> Thay đổi ảnh -> Tải ảnh lên -> Chọn tile đầu tiên -> Lưu.
  4. Xác nhận artifact nghiệm thu: `avatar-uploaded-confirmed.png` và `report.json` với `status: AVATAR_SMOKE_SUCCESS`.
- Nghiệm thu thực tế qua WinRT OCR và Vision kiểm tra mắt trước khi báo cáo User.
