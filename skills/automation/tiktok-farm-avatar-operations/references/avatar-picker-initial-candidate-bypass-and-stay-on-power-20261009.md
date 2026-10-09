# Avatar Picker Initial Candidate Direct Selection & Screen Power Lock (2026-10-09)

## 1. Hiện tượng & Triệu chứng lỗi (Failure Signature)
Khi chạy runner upload avatar (`-AvatarOnly` / `--avatar-smoke`) trên thiết bị thật:
- Runner chạy đến bước `ENSURE_AVATAR`:
  ```
  [INFO] tiktok_workflow.state_machine: [ENSURE_AVATAR] Không có album Pictures/Download; giữ Recent grid và chờ candidate ảnh từ MediaStore
  [INFO] tiktok_workflow.state_machine: [ENSURE_AVATAR] Tap tile ảnh đầu tiên (mới nhất sau push): (803, 1560, 1054, 1830)
  [INFO] tiktok_workflow.state_machine: [ENSURE_AVATAR] Picker Next button not confirmed via XML; attempting fallback tap (924, 1842)
  [ERROR] tiktok_workflow.state_machine: [AVATAR_CROP_OPEN_FAILED] ENSURE_AVATAR: Màn crop avatar không mở
  ```
- File chụp màn hình lỗi `avatar-crop-open-failed.png` có dung lượng ~12KB, toàn bộ pixel là màu đen kịt `[0, 0, 0]` (`Display Power: state=OFF`). Tiến trình bị timeout 300s.

## 2. Nguyên nhân cốt lõi (Root Causes)
1. **Thừa thãi mở menu Dropdown Album khi đã có sẵn candidate:**
   - Trong `_select_avatar_from_download` (`state_machine.py`), hàm luôn gọi `adapter.dump_ui()` và tự động tap "Gần đây" / "Recent" để mở dropdown album ngay cả khi lưới ảnh ban đầu (`xml_text`) đã hiển thị sẵn candidate ảnh vừa push.
   - Thao tác mở dropdown làm che khuất nút "Tiếp" (Next) hoặc khiến picker bị kẹt trạng thái popup, dẫn đến không chuyển tiếp được sang màn hình Crop avatar.
2. **Màn hình thiết bị tự động Sleep (`Screen: OFF`):**
   - Trên các máy Samsung S7, cài đặt `stay_on_while_plugged_in` có thể bằng 0. Khi chạy tác vụ chờ lâu, máy tắt màn hình dẫn đến screencap ra ảnh đen 12KB và UI bridge không phản hồi.
3. **Lệch biến môi trường version `automation-core`:**
   - Runner `run_tiktok_upload_batch.ps1` kiểm tra `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION` (mặc định yêu cầu `0.4.44` trên `venv-core024`). Nếu wrapper truyền sai version (ví dụ `0.4.45`) sẽ văng exception ngay tại preflight.

## 3. Giải pháp chuẩn hóa (Architecture & Fix Pattern)
1. **Kiểm tra `initial_candidates` trực tiếp tại lưới mở picker:**
   - Tại `_select_avatar_from_download`, kiểm tra ngay trên `xml_text` ban đầu:
     ```python
     initial_candidates = [c for c in self._avatar_picker_candidates(xml_text) if c["media_type"] in ("image", "unknown")]
     if not initial_candidates:
         # Chỉ mở dropdown album khi lưới mặc định hoàn toàn không có candidate
         ...
     else:
         candidates = initial_candidates
     ```
   - Tránh hoàn toàn việc mở dropdown không cần thiết, chọn ngay candidate đầu tiên và bấm "Tiếp" sang màn Crop.
2. **Khóa màn hình luôn sáng khi cắm sạc trước khi chạy:**
   - Chạy lệnh ADB: `adb -s <SERIAL> shell "settings put global stay_on_while_plugged_in 3"` kết hợp đánh thức màn hình (`keyevent 224`, `keyevent 82`) để triệt tiêu hoàn toàn rủi ro ảnh đen 12KB.
3. **Bộ test hồi quy (Offline Regression Testing):**
   - `pytest tests/test_avatar_edit_and_milestone.py` (39/39 PASS).
   - `pytest tests/test_tiktok_workflow.py -k avatar_picker` (4/4 PASS).
