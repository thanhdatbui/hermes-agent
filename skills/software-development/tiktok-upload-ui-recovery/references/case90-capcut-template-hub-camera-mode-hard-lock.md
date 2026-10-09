# Case 90: CapCut Template Hub (Tab TẠO / LIVE) & 3-Layer Hard Lock for Camera Viewfinder

## 1. Hiện tượng & Triệu chứng thực tế (Máy 39 - 06/09/2026)
- **Thiết bị:** Máy 39 | Serial: `ce0117113818c4d30c` | Nick: `tachau1704` | Video #5.
- **Triệu chứng:**
  `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery`
- **Nguyên nhân cốt lõi:**
  - Trên các bản cập nhật TikTok gần đây trên Samsung (màn 1080x1920), khi robot bấm nút `[+]`, TikTok không mở trực tiếp vào Camera viewfinder mà rơi vào tab **`TẠO` (CapCut Template Hub)** hoặc tab **`LIVE`**.
  - Thanh mode ở đáy màn hình gồm: `CAMERA` (x: 217-414), `TẠO` (x: 494-585, đang active), `LIVE` (x: 668-761).
  - Tab "TẠO" chứa toàn bộ grid các template mẫu video của CapCut, không có nút Shutter hay nút Thư viện/Upload.
  - Thuật toán visual fallback cũ tìm điểm ảnh sáng ở góc phải dưới (`945, 1593`) tap trúng một video template card -> kích hoạt `_dismiss_capcut_template_surface` back văng ra ngoài Home feed -> lặp lại failure đến khi hết retry.

---

## 2. Giải pháp kỹ thuật: 3-Layer Hard Lock (`scripts/tiktok_workflow/state_machine.py`)

### Tầng 1: Tab Normalizer Gate (`_ensure_camera_viewfinder_mode`)
- Bổ sung helper chuẩn hóa mode máy ảnh trước khi tìm nút Upload.
- Mở rộng nhận diện Template Hub qua text:
  ```python
  if any(m in xml_text for m in ('text="Phát LIVE"', 'text="Trung tâm LIVE"', 'text="LIVE"', 'text="Live"')):
      needs_switch = True
  elif (
      self._is_capcut_template_surface(xml_text)
      or ('text="TẠO"' in xml_text and 'selected="true"' in xml_text)
      or any(m in xml_text for m in ('text="Mẫu"', 'text="Templates"', 'text="MẪU"', 'text="Video mới"'))
  ):
      needs_switch = True
  ```
- Nếu phát hiện đang ở LIVE hoặc TẠO:
  + Ưu tiên tap selector `CAMERA` hoặc `Máy ảnh`.
  + Nếu selector không khả dụng, tính toán tọa độ động theo độ phân giải màn hình: `adapter.tap(int(width * 0.292), int(height * 0.948))` (trên 1080x1920 là `315, 1820`), sau đó chờ 2s để viewfinder ổn định.

### Tầng 2: Early Exit Guard trong Visual Tap
- Trước khi thực hiện visual thumbnail tap:
  ```python
  xml_text = self._ensure_camera_viewfinder_mode(adapter, xml_text)
  if self._is_capcut_template_surface(xml_text):
      logger.warning("[CAMERA] Vẫn đang ở màn hình Template Hub sau switch; dừng visual thumbnail tap")
      return False
  ```
- Tuyệt đối không để visual fallback tap mù quáng khi chưa thoát khỏi Template Hub.

### Tầng 3: Negative Spatial Gate (Vùng cấm tuyệt đối)
- Grid video card của CapCut nằm ở khoảng giữa màn hình.
- Chặn cứng tuyệt đối:
  ```python
  # Negative Spatial Gate: Cấm tuyệt đối tap vào dải Y: 15% -> 75% (vùng template card CapCut)
  if int(height * 0.15) <= tap_y <= int(height * 0.75):
      logger.warning("[NEGATIVE_GATE] Chặn tap vào vùng cấm Y=%d (CapCut Template Hub)", tap_y)
      return False
  ```
- Nút thumbnail Thư viện/Album chuẩn xác luôn nằm ở biên chân màn hình (`Y > 80%`, ví dụ bên trái nút chụp `156, 1574`).

---

## 3. Bài học Quy trình Vận hành Farm (Chống kéo dài 3 tiếng)

### Bẫy Scope Creep ở khâu Review:
- Trong sự cố máy 39, Canary Test B4 đã đăng thành công video #5 trên máy thật (Tik2.xlsx cập nhật, profile lên 5 video).
- Tuy nhiên, sau đó Coordinator lại để Reviewer bới thêm các lỗi ngoài phạm vi (như draft cleanup, hashtag threshold), dẫn đến worker sửa lan và vướng mock test suite, kéo dài phiên làm việc hơn 3 tiếng.

### Kỷ luật vận hành bắt buộc:
1. **Nguyên tắc "Canary Pass = Code Freeze":**
   Khi Canary Test trên thiết bị thật đã **ĐĂNG VIDEO THÀNH CÔNG** (video lên profile, workbook cập nhật), **LẬP TỨC ĐÓNG BĂNG CODE**. Cấm hoàn toàn mọi hành vi refactor hay sửa thêm tính năng ngoài lề.
2. **Reviewer là Gatekeeper nhị phân (Bouncer, not Architect):**
   Reviewer chỉ kiểm tra: (a) Fix có đúng root cause không? (b) Máy thật đã pass chưa? (c) Có làm gãy luồng khác không? Cấm từ chối vì các tiểu tiết ngoài lề sự cố.
3. **Hard Cap cho Worker Subagent:**
   Mỗi worker subagent chỉ được cấp tối đa 10 phút và tối đa 15 tool calls. Quá 10 phút phải dừng báo cáo.
