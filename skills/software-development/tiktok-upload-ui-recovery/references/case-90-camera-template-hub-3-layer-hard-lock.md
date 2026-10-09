# Case 90: Khóa Cứng 3 Tầng Chống Kẹt CapCut Template Hub / LIVE Khi Mở Camera TikTok (Máy 39)

Ngày ghi nhận: 06/09/2026.
Thiết bị: Máy 39 (serial `ce0117113818c4d30c`, nick `tachau1704`, video số 5).
Repo: `D:/Taadaa/Tiktok-video` (`scripts/tiktok_workflow/state_machine.py`).
Lỗi: `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery`.

---

## 1. HIỆN TƯỢNG VÀ NGUYÊN NHÂN GỐC RỄ (ROOT CAUSE)

- **Hiện tượng**: Khi workflow mở nút tạo bài `[+]` để upload video, TikTok trên máy 39 rơi vào tab "TẠO" (CapCut Template Hub) hoặc tab "LIVE" thay vì Camera Viewfinder thông thường.
- **Cơ chế gây vòng lặp lỗi**:
  1. Trong tab "TẠO", màn hình hiển thị Grid danh sách các mẫu CapCut (không có nút Chụp hay nút Thư viện ảnh/video).
  2. Thuật toán visual fallback dò tìm thumbnail album ở thanh đáy nhưng lại tap trúng video card template bên phải (`0.875 * width, 0.83 * height`).
  3. Hành vi này kích hoạt `_dismiss_capcut_template_surface`, gửi `KEYCODE_BACK` làm văng ứng dụng trở lại Home feed.
  4. Script tiếp tục thử lại (retry loop) và lặp lại kịch bản cũ, dẫn tới `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` và giữ hiện trường upload.

---

## 2. GIẢI PHÁP KHÓA CỨNG 3 TẦNG (3-LAYER HARD LOCK)

Được thiết kế dựa trên tư vấn của Senior Farm Architect & Code Reviewer:

### Tầng 1: Tab Normalizer Gate (`_ensure_camera_viewfinder_mode`)
- Trước khi tìm kiếm bất kỳ nút hay thumbnail nào, hệ thống bắt buộc kiểm tra xem màn hình có đang ở tab sai hay không:
  + Phát hiện LIVE: `"Phát LIVE"`, `"Trung tâm LIVE"`, `"LIVE"`, `"Live"`.
  + Phát hiện Template Hub: `self._is_capcut_template_surface(xml_text)`, `'text="TẠO"' and 'selected="true"'`, hoặc các nhãn `"Mẫu"`, `"Templates"`, `"MẪU"`, `"Video mới"`.
- Nếu phát hiện đang ở tab sai: Tự động tap chuyển tab sang `"CAMERA"` / `"Máy ảnh"` bằng selector hoặc tọa độ tỷ lệ màn hình động (`int(width * 0.292), int(height * 0.948)`), nghỉ 2 giây cho giao diện camera ổn định trước khi tiếp tục.

### Tầng 2: Template Early-Exit Guard
- Tại đầu hàm `_tap_visual_camera_upload_entry`:
  ```python
  xml_text = self._ensure_camera_viewfinder_mode(adapter, xml_text)
  if self._is_capcut_template_surface(xml_text):
      logger.warning("[CAMERA] Vẫn đang ở màn hình Template Hub sau switch; dừng visual thumbnail tap")
      return False
  ```
- Nếu sau khi tap chuyển tab mà màn hình vẫn là Template Hub, lập tức ngắt sớm (`return False`) để FSM xử lý chuyển state an toàn, cấm tuyệt đối việc cố đấm ăn xôi tap mù quáng vào template card.

### Tầng 3: Negative Spatial Gate & Strict Left Priority
- **Negative Spatial Gate (Vùng cấm tuyệt đối)**:
  ```python
  if int(height * 0.15) <= tap_y <= int(height * 0.75):
      logger.warning("[NEGATIVE_GATE] Chặn tap vào vùng cấm Y=%d (CapCut Template Hub)", tap_y)
      return False
  ```
  Chặn cứng toàn bộ các cú tap có tọa độ Y rơi vào dải `15% -> 75%` màn hình (vùng hiển thị Grid video card của CapCut).
- **Strict Left Priority**: Nút album thư viện luôn nằm ở góc dưới bên trái (`0.145 * width, 0.82 * height`). Khi cụm bên trái (`left_targets`) có ứng viên, loại bỏ hoàn toàn các ứng viên bên phải (`right_targets`) để không bao giờ chạm vào nút Mẫu/Hiệu ứng CapCut.

---

## 3. BÀI HỌC VẬN HÀNH & KỶ LUẬT AGENT

1. **Canary Pass = Code Freeze Ngay Lập Tức**:
   - Khi Canary Test B4 đã chạy thành công trên máy thật (Máy 39 đăng xong video 5, Tik2.xlsx cập nhật), toàn bộ code logic liên quan phải được **đóng băng**.
   - Cấm Coordinator ném diff cho reviewer soi các vấn đề ngoài lề (draft cleanup, hashtag threshold), vì điều này làm worker sửa lan sang các module khác, gãy mock test suite và kéo dài phiên hơn 3 tiếng.
2. **Nghiệm Thu Trực Quan Farm**:
   - Kết thúc phiên xử lý lỗi thiết bị, Coordinator **CHỈ ĐƯỢC PHÉP GỬI ẢNH CHỤP MÀN HÌNH THIẾT BỊ (SCREENCAP)** qua `MEDIA:<path_to_png>`. Tuyệt đối không gửi file video từ kho nuôi nick.
