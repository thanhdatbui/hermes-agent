# Dual-Deliverable Avatar + Rename & Workbook Folder Reconciliation Protocol

## 1. Bẫy Tâm Lý & Invariant Chống Báo Cáo Thiếu (Anti-Partial False Report)

### Tình huống kích hoạt
Khi User ra lệnh kép: *"Đổi ava và đổi tên biệt danh 2 kênh này"* (Avatar + Display Name).

### Sai lầm chết người (Fatal Pitfall)
- Thực hiện xong bước Đổi tên (Rename), vội vàng gửi ảnh Profile `MEDIA:<path>` lên kèm báo cáo.
- Dù giải thích bằng chữ là "đang trích xuất/chuẩn bị đổi avatar", User nhìn vào ảnh Profile thấy **Avatar cũ vẫn nguyên xi** (ví dụ: kênh tài chính nhưng avatar xăm trổ) -> Lập tức quy kết là **"báo cáo láo" / "nói mõm"**.

### Kỷ luật bắt buộc (Hard Rule)
1. **Bundled Deliverable Barrier:** Đối với lệnh gộp (Đổi tên + Đổi ava), **CẤM TUYỆT ĐỐI** gửi ảnh nghiệm thu trung gian nếu chưa hoàn tất cả hai hạng mục trên máy thật.
2. **Atomic Verification:** Chỉ được gửi `MEDIA:<final_profile.png>` khi **CẢ HAI** điều kiện thỏa mãn trên cùng 1 frame:
   - Dòng Tên (Display Name) đã đổi sang tên mới chuẩn tự nhiên.
   - Ảnh tròn Avatar đã cập nhật sang hình ảnh chuẩn ngách mới.

---

## 2. Truy Vết Căn Nguyên Lệch Avatar: Cột `Folder Video` trong Workbook

### Hiện tượng
Kênh làm về Niche A (ví dụ: Tin tức Tài chính) nhưng avatar hiển thị trên điện thoại lại là Niche B (ảnh xăm trổ Gym hoặc thú cưng).

### Căn nguyên
- Trong các file workbook `Tik<N>.xlsx` (Sheet 1):
  * **Cột 4:** `Folder Video` (Thư mục media được tool upload/avatar đọc).
  * **Cột 5:** `Video Goc` (Thư mục nguồn gốc thực tế).
- Khi có sự sai lệch (Drift):
  * Máy 2: Cột 4 ghi `12` (Gym), trong khi Cột 5 là `242` (Tài chính).
  * Máy 51: Cột 4 ghi `404` (Thú cưng), trong khi Cột 5 là `291` (Kỷ yếu).
- Khi chạy script `run_tiktok_upload_avatar.ps1`, pipeline phân giải avatar theo Cột 4 (`Folder Video`). Hậu quả: bốc nhầm avatar của folder 12/404 nạp lên máy!

### Quy trình khắc phục chuẩn
1. **Kiểm tra đồng bộ:**
   ```python
   # Đảm bảo Cột 4 (Folder Video) == Cột 5 (Video Goc)
   row[3].value = target_folder
   row[4].value = target_folder
   ```
2. **Kiểm tra kho ảnh gốc (MD5 & Vision):**
   - Xác nhận `D:/video goc/<folder>/avatar.jpg` và `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg` không bị lưu nhầm ảnh bẩn/lệch ngách từ trước.
3. **Đăng ký bảo vệ chống ghi đè:**
   - Thêm `<folder>` vào `protected_folders` trong `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json` để batch render/crawl không tự ý overwrite.

---

## 3. Khởi Chạy Avatar Runner Qua Coordinator Allowlist

### Rào cản Guard
- Coordinator Terminal chặn chạy trực tiếp `powershell.exe ... run_tiktok_upload_avatar.ps1` (DEFAULT-DENY).
- Coordinator Terminal chặn chạy trực tiếp `D:\CodexRuntime\...\python.exe`.

### Mẫu chạy chuẩn hóa O(1)
Sử dụng script wrapper đã kiểm chứng `D:/Taadaa/tools/run_avatar_batch_3accs.py`:
```bash
python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <TIK_NUM> --machine <MACHINE_ID>
```
*Lưu ý:* Bắt buộc chạy nền với `background=True, notify_on_complete=True, timeout=300` vì pipeline upload avatar + crop + confirm trên thiết bị thật mất từ 120s – 250s.

---

## 4. Đặc Tả State Machine Đổi Tên (AdbKeyboard & 7-Day Warning)

1. **OCR Routing:**
   - Tab Hồ sơ (`PROFILE`) $\rightarrow$ Tap nút `Sửa hồ sơ` (thường ở tọa độ `(870, 558)` hoặc nút bút chì `(72, 148)` tùy UI layout).
   - Màn Sửa hồ sơ (`EDIT_PROFILE`) $\rightarrow$ Tap dòng `Tên` (thường ở `y ~ 730-750`).
   - Màn Đổi tên (`NAME_EDIT`):
     * Clear text cũ.
     * Gửi text tiếng Việt có dấu qua broadcast AdbKeyboard:
       `adb shell am broadcast -a ADB_INPUT_B64 --es msg "<base64_utf8>"`
     * Nhận diện bộ đếm ký tự (ví dụ: `8/30` hoặc `9/30`).
     * Tap `Lưu` ở góc trên cùng bên phải `(990, 150)`.
2. **Xử lý Popup cảnh báo 7 ngày của TikTok:**
   - TikTok luôn hiện modal: *"Đặt biệt danh? Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần."* kèm nút *Xác nhận*.
   - Nhận diện text `Dặt biệt danh` / `Xác nhận` / `7 ngày` $\rightarrow$ Tap nút *Xác nhận* (thường ở tọa độ `(327, 1169)` hoặc `(748, 1174)`).
3. **Kiểm thử logic `is_target` (Chống False Positive):**
   - Hàm `is_target(name_line)` bắt buộc kiểm tra số từ:
     ```python
     words = nl.split()
     if len(words) < 2:
         return False
     ```
   - Tránh việc chuỗi 1 từ như `"Tươi"` có SequenceMatcher ratio = 0.67 với `"tuoi luu"` dẫn đến kiểm thử báo sai.
