# Avatar Picker Initial Candidate & Core Version Preflight (2026-10-09)

## 1. Bẫy Mismatch Version `automation-core` trong Launcher Batch (`run_tiktok_upload_batch.ps1`)
### Hiện tượng
Khi gọi launcher PowerShell:
```powershell
echo RUN | powershell.exe -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik 5 -ForceAvatarMachineList "5"
```
Quá trình dừng ngay lập tức với exception:
```
automation-core version mismatch: expected=0.4.45; actual=0.4.44; 
runtime=D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe; reason=metadata version did not match expected contract
```

### Nguyên nhân & Cách xử lý
- Launcher `run_tiktok_upload_batch.ps1` mặc định kiểm tra biến môi trường `$env:TIKTOK_VIDEO_AUTOMATION_CORE_VERSION`. Nếu biến này đặt là `0.4.45` mà môi trường `venv-core024` trên host Kibe cài bản `0.4.44` (hoặc ngược lại), launcher sẽ fail-closed ngay ở preflight check.
- **Quy tắc:** Khi invoke từ Python wrapper hoặc terminal, bắt buộc kiểm tra nhanh:
  ```python
  import importlib.metadata as m; print(m.version("automation-core"))
  ```
  Sau đó thiết lập biến môi trường tương ứng:
  `env["TIKTOK_VIDEO_AUTOMATION_CORE_VERSION"] = "0.4.44"` (hoặc version thực tế của runtime được chỉ định).

---

## 2. Bẫy Thừa Mở Dropdown Album Gây Kẹt Khi Picker Đã Có Sẵn Candidate
### Hiện tượng
- Sau khi push file avatar vào `/sdcard/Pictures/` và scan MediaStore, TikTok mở Photo Picker.
- Log ghi nhận:
  ```
  [INFO] tiktok_workflow.state_machine: [ENSURE_AVATAR] Không có album Pictures/Download; giữ Recent grid và chờ candidate ảnh từ MediaStore
  [INFO] tiktok_workflow.state_machine: [ENSURE_AVATAR] Picker Next button not confirmed via XML; attempting fallback tap (924, 1842)
  [ERROR] tiktok_workflow.state_machine: [AVATAR_CROP_OPEN_FAILED] ENSURE_AVATAR: Màn crop avatar không mở
  ```
- Ảnh chụp màn hình `avatar-crop-open-failed.png` hiển thị màn hình đen kịt do mở nhầm menu hoặc không bấm trúng nút xác nhận.

### Nguyên nhân
- Khi Photo Picker mở ra trên giao diện TikTok, tab mặc định "Gần đây" (Recent) đã hiển thị ngay ô ảnh avatar vừa push ở vị trí đầu tiên.
- Code cũ luôn mặc định tap vào dropdown "Gần đây" (`album_menu_opened = True`), làm bung album dropdown menu. Nếu máy không có album tên riêng "Pictures" hay "Download", code cố gắng đóng dropdown nhưng làm mất focus của lưới ảnh hoặc gây delay khiến bước tap tiếp theo bị trượt.

### Giải pháp chuẩn hóa
Trong `_select_avatar_from_download` (`scripts/tiktok_workflow/state_machine.py`):
1. **Quét candidate ngay khi picker mở:**
   ```python
   initial_candidates = [c for c in self._avatar_picker_candidates(xml_text) if c["media_type"] in ("image", "unknown")]
   ```
2. **Nếu đã có `initial_candidates`:**
   - Hoàn toàn **bỏ qua bước mở dropdown album** (`album_menu_opened`), giữ nguyên giao diện tĩnh và chọn thẳng candidate đầu tiên (`candidates = initial_candidates`).
3. **Chỉ khi `initial_candidates` rỗng:**
   - Mới mở dropdown album "Gần đây" để tìm album Pictures/Download và reload lại `download_xml`.
4. **Bộ test hồi quy bắt buộc:**
   - `pytest tests/test_avatar_edit_and_milestone.py` (39/39 PASS)
   - `pytest tests/test_tiktok_workflow.py -k avatar_picker` (4/4 PASS)

---

## 3. Tiêu Chuẩn Thẩm Định Avatar Thể Thao / Vật Tay (Arm Wrestling)
1. **Kiểm tra Niche & Video Grid thực tế:**
   - Khi nick có video là VĐV thi đấu vật tay hoặc tập thể hình cơ bắp (như YouTuber Hải Phệt hoặc giải vật tay phong trào), avatar cũ dính nhầm nhân vật khác (ví dụ: ảnh trẻ con có banner "24h NEWS", hoặc avatar nữ trong khi kênh thuần nam).
2. **Trích xuất cận cảnh có khoảng thở (Headroom):**
   - Dùng Haar Cascade quét các video chính trong folder (video 1, 2, 7), tính toán crop vuông 512x512:
     - Đỉnh đầu/trán cách mép trên 10-15% (headroom).
     - Không để bàn tay/nắm đấm che miệng hoặc cằm.
     - Kiểm tra không dính watermark/subtitle chữ chạy qua cằm.
3. **Đánh giá qua Vision API:**
   - Điểm số phải đạt $\ge 7.0/10$ (nét mặt rõ ràng, phong thái thể thao năng động, bố cục cân đối khi cắt tròn).
4. **Đồng bộ 2 đầu kho & SQLite Queue:**
   - Copy file sang cả `D:\video goc\<Folder>\avatar.jpg` và `D:\TIKTOK-videonuoinick\<Folder>\avatar.jpg`.
   - `UPDATE avatar_replace_queue SET status='PENDING', last_error=NULL, updated_at=datetime('now','localtime') WHERE username='...';`
   - Đồng bộ bản sao sang OneDrive `D:\OneDrive\TaadaaData\tiktok_tracker.db`.
