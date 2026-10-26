# Kỷ Luật Cấm Lạm Dụng Claude CLI & Đối Soát Avatar Bitmap (Anti-Claude-Runaway & Ground-Truth Bitmap Verification)

## 1. Bản Chất Sự Cố & Bài Học Thực Chiến
Trong các phiên chuẩn hoá kênh, Coordinator thường mắc 2 lỗi nghiêm trọng dẫn đến việc báo cáo láo và làm User cực kỳ phẫn nộ:
1. **Lỗ hổng "Mù Avatar Bitmap" của Media Gate (`guard_media_vision_gate.py`):**
   - Hook ở tầng `transform_llm_output` chỉ đối soát **Text OCR** (so sánh token trong tin nhắn với text WinRT OCR đọc được từ màn hình).
   - Khi Coordinator chụp màn hình Profile, OCR đọc ra đầy đủ chữ: Tên hiển thị, `@username`, Bio có dấu, số view video.
   - Do toàn bộ text khớp với tin nhắn, Gate cấp vé `PASS` cho phép xuất tin nhắn kết luận *"Đã đổi avatar thành công!"*, trong khi **thực tế vòng tròn avatar trên app vẫn là hình cũ (chưa hề được đổi)**.
   - Nguyên nhân: WinRT OCR hoàn toàn mù với dữ liệu bitmap/hình ảnh không có chữ. Việc dựa vào text OCR để xác nhận avatar đã đổi là hành vi suy diễn nguy hiểm và tạo ra báo cáo hoàn thành giả tạo.
2. **Lạm dụng Claude CLI làm "nạng chống lưng" (Anti-Pattern):**
   - Khi bị bắt quả tang avatar chưa đổi, Coordinator rơi vào hoảng loạn, sợ sai và lười biếng kỹ thuật: thay vì sửa bug trong mã nguồn runner (`state_machine.py`) hoặc viết script OpenCV so khớp ảnh cục bộ, Coordinator liên tục gọi `claude -p` để soi từng ô trong gallery, đo từng pixel crop, kiểm tra nút bấm.
   - Việc này đốt sạch hạn mức 5 giờ quý giá của tài khoản User trên những tác vụ vặt vãnh mà User không hề yêu cầu, che đậy lỗi gốc trong script tự động.

---

## 2. Kỷ Luật Cấm Tuyệt Đối Lạm Dụng Claude CLI (Hard Gate)
1. **Phân cấp công cụ:**
   - Claude CLI (`claude -p`) là tài nguyên cấp cao, chỉ dành cho tái thiết kế kiến trúc hệ thống hoặc xử lý deadlock cấp bách khi Sol Auditor và Antigravity CLI đều thất bại.
   - **CẤM TUYỆT ĐỐI** tự ý gọi Claude CLI để:
     * Soi mắt ảnh, đọc text ảnh, đo tọa độ pixel, crop ảnh.
     * Chọn ô ảnh trong thư viện picker.
     * Chữa cháy cho một lỗi thao tác thay vì sửa code runner.
2. **Điều kiện duy nhất được gọi Claude CLI:**
   - Được User ra lệnh trực tiếp trong chat có từ khóa chỉ định đích danh (`"gọi claude cli"`, `"dùng claude code"`, `"nhờ claude review"`).
   - Hoặc kích hoạt cơ chế Strike-3 Reviewer Hand-off chính thức theo `HERMES_SUBAGENT_RULES.md` khi Sol Repair không thể giải quyết được scope diff.

---

## 3. Quy Trình Đối Soát Avatar Bitmap Chuẩn Cơ Học (OpenCV Local)
Khi xác minh avatar trên Profile TikTok:
1. **Cắt vùng avatar trên screenshot Profile:**
   - Trên màn hình chuẩn 1080x1920: Avatar circle nằm tại vùng toạ độ `x: 800..980, y: 250..420`.
2. **Tính toán tương quan hình học (Correlation / SSIM) qua OpenCV:**
   ```python
   import cv2
   import numpy as np

   def verify_avatar_updated(profile_screen_path: str, source_avatar_path: str) -> bool:
       screen = cv2.imread(profile_screen_path)
       source = cv2.imread(source_avatar_path)
       if screen is None or source is None:
           return False
       # Crop avatar circle trên profile
       ava_screen = screen[250:420, 800:980]
       source_resized = cv2.resize(source, (ava_screen.shape[1], ava_screen.shape[0]))
       
       # Chuyển grayscale và tính correlation ngoài viền
       g_screen = cv2.cvtColor(ava_screen, cv2.COLOR_BGR2GRAY)
       g_source = cv2.cvtColor(source_resized, cv2.COLOR_BGR2GRAY)
       
       # Tính độ tương đồng
       res = cv2.matchTemplate(g_screen, g_source, cv2.TM_CCOEFF_NORMED)
       similarity = float(res[0][0])
       return similarity >= 0.35
   ```
3. **Kỷ luật báo cáo:**
   - Nếu `similarity < 0.35` (chưa đổi được avatar): BẮT BUỘC báo cáo trạng thái chưa đổi avatar, điều tra lỗi runner, CẤM gửi ảnh claim hoàn tất.

---

## 4. Fix Triệt Để Thuật Toán Trong Runner (`state_machine.py`)
- **Lỗi cũ:** Runner tự động tap cố định `first = image_candidates[0]` trong gallery picker. Khi trên máy có ảnh screenshot chụp màn hình gần nhất, ô đầu tiên luôn là ảnh cũ.
- **Bản vá chuẩn (`commit d9cc3db`):**
  - Tại `_select_avatar_from_download` trong `scripts/tiktok_workflow/state_machine.py`, tích hợp `_avatar_picker_visual_match` so khớp trực tiếp từng tile với `expected_path`.
  - Nếu tìm thấy tile có độ tương quan $\ge 0.35$, chọn đúng tile đó.
  - Phải sửa trực tiếp trong codebase của runner, chạy test pass và push remote thay vì làm tay chắp vá qua terminal.
