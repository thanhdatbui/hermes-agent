# Canonical Single Avatar Launcher & Strict Anti-Ad-Hoc Script Invariant (2026-10-17)

## 1. Bối cảnh & Sự cố Phân tâm Điều phối (Incident 17/10/2026)
- **Hiện trường:** Đổi avatar cho Máy 59 (tài khoản `@vantieu11`, slot Tik 4, folder 468).
- **Lỗi nhận diện ban đầu (Stale Avatar Trap):** Coordinator lấy file `avatar.jpg` có sẵn trong `TIKTOK-videonuoinick/468/` mà không kiểm tra, gửi nhầm ảnh ngón tay cầm dây cáp tai nghe (avatar cũ) cho User mà không soi mắt đối soát qua `browser_vision`. Bị User chửi gắt: *"Mày có xem hình trc khi gửi tao k đấy"*.
- **Sai lầm kiến trúc (Ad-hoc Script Reinvention Trap):** Khi phát hiện TikTok trên máy đang mở sẵn nick `@thutuan4916` (của ca Tik 8), Coordinator hoảng sợ nghĩ rằng runner tự động sẽ upload nhầm avatar vào nick đó. Thay vì dùng pipeline chuẩn, Coordinator tự ý viết script tạm `D:/Taadaa/tmp/execute_m59_avatar.py` để tự điều khiển ADB chuyển nick và upload, sau đó dispatch subagent sửa code dính timeout 600s, làm nghẽn toàn bộ phiên làm việc.
- **Hệ quả & Phản ứng của User:** User chặn lại và chất vấn: *"Ủa t nhớ có file up avatar r mà sao mày còn đi tạo cái ms. Ý tao là script m59_avatar.py là sao? Tao hỏi thi công xong vụ tự ý viết sxript ava lung tung chưa? Claude cli duyệt chưa"*.

---

## 2. Luật Thép Anti-Ad-Hoc Script (Claude CLI Sonnet 5.5 Approved)
Đã được mã hóa chính thức vào `D:/Taadaa/PROJECT_RULES.md` (dòng 100–117) và được Claude CLI review đạt **`VERDICT: APPROVED`**:

1. **Định nghĩa "đổi avatar lẻ":** Áp dụng cho mọi thao tác đổi avatar trên **<= 3 máy** (ngoài ca batch tự động 80 máy).
2. **CẤM TUYỆT ĐỐI Coordinator và Worker:**
   - CẤM viết script mới bất kỳ để đổi avatar lẻ (ví dụ `execute_m<N>_avatar.py`, `run_avatar_m<N>.py`, script tạm trong `tmp/`...).
   - CẤM sửa hoặc tái sử dụng các script cũ có sẵn (`do_upload_avatar_m*.py`, `prep_*_avatar.py`, `tmp_*`), kể cả sao chép rồi chỉnh tham số.
3. **Cơ chế Switch Account Tự Động (Zero Panic):**
   - Pipeline chuẩn của Farm trong `run_tiktok_upload_batch.ps1` **đã tích hợp sẵn `ACCOUNT_SWITCHER`** (`automation_core.tiktok.account_switcher`).
   - Runner tự động đọc username từ `Tik<N>.xlsx`, tự kiểm tra nick đang active trên máy, nếu khác nick mục tiêu sẽ tự động mở switcher và chuyển sang đúng nick trước khi vào màn Sửa hồ sơ.
   - Coordinator tuyệt đối không bao giờ được hoảng sợ khi thấy máy đang mở nick khác.

---

## 3. Launcher Chuẩn Duy Nhất & Cơ Chế Hoạt Động
Mọi tác vụ đổi avatar lẻ BẮT BUỘC sử dụng duy nhất một launcher có sẵn:
```bash
python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Tik> --machine <May>
```
*Lưu ý:* Phải chạy nền qua `terminal(background=True, notify_on_complete=True, timeout=300)` để harness tự đánh thức, cấm tuyệt đối viết vòng lặp polling sleep.

### Cách thức launcher hoạt động:
1. Tự động nhận diện cấu hình host: `machine >= 200` dùng `admin.yaml`, còn lại dùng `kibe.yaml`.
2. Tự động xóa biến môi trường rác `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION`.
3. Kích hoạt `run_tiktok_upload_avatar.ps1` với `-ForceAvatarMachineList <May>`, `-Tik <Tik>`, `-MaxParallel 1`, chế độ `-AvatarOnly`.
4. Engine PowerShell:
   - Dọn sạch MediaStore trên điện thoại (`/sdcard/Pictures/*`, `/sdcard/DCIM/*`).
   - Đọc `Tik<Tik>.xlsx` lấy `Folder Video` của nick mục tiêu.
   - Tự động chuyển tài khoản (`account_switcher`) nếu chưa đúng nick.
   - Push `avatar.jpg` lên máy, mở Sửa hồ sơ -> Thay đổi ảnh -> Tải ảnh lên -> Checkbox tile 1 -> Tiếp -> Lưu.
   - Xuất artifact xác nhận: `avatar-uploaded-confirmed.png` và `report.json`.

---

## 4. Checklist Chuẩn 3 Bước O(1) Bắt Buộc Tuân Thủ

- **Bước 1 — Chuẩn bị Avatar & Soi Mắt Pre-flight:**
  1. Tra database `D:/Taadaa/data/tiktok_tracker.db` (`account_mapping` / `avatar_replace_queue`) để xác định Folder Video.
  2. Trích xuất frame nét chính chủ từ `D:/TIKTOK-videonuoinick/<folder>/` (creator chiếm 40%–60% khung hình, nhìn thẳng, không dính logo/cáp cũ).
  3. Cắt crop chân dung vuông `512x512` và tạo preview đối sánh khung tròn.
  4. **Soi mắt kiểm tra trước khi gửi:** Bắt buộc mở ảnh qua `browser_vision` hoặc WinRT OCR để xác nhận mắt nhìn thấy người thật, sau đó gửi `MEDIA:<path>` cho User xem trước.
  5. **Dual-Sync:** Đồng bộ file thành phẩm vào cả 2 kho:
     - `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg`
     - `D:/video goc/<folder>/avatar.jpg`

- **Bước 2 — Kích hoạt Launcher Chuẩn:**
  ```bash
  python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Tik> --machine <May>
  ```

- **Bước 3 — Nghiệm thu Thực Tế (Gate 6):**
  1. Đọc artifact `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/avatar-uploaded-confirmed.png`.
  2. Chạy WinRT OCR (`automation_core.ocr.ocr_screen_boxes`) và soi mắt qua vision:
     - Xác nhận đúng tên hiển thị và `@username`.
     - Xác nhận vòng tròn avatar đã hiển thị khuôn mặt người thật mới.
  3. Chỉ khi PASS mới cập nhật:
     - SQLite `avatar_replace_queue`: `SET status='DONE'`.
     - Excel `Tik<N>.xlsx`: Cột `Avatar` = `OK`.
  4. Nếu FAIL: Leo thang theo Escalation Ladder ($L0 \to L3$). CẤM tự ý viết script bypass.

---

## 5. Bẫy Tái Phạm Máy 34 (Incident 18/10/2026 — Vụ việc do_save_avatar_m34.py)
- **Hiện tượng:** Khi đổi avatar M34 (`@yobi1965`), runner chuẩn bốc nhầm ảnh chậu cây kim tiền "20 lần" do MediaStore dính thumbnail video cũ. Coordinator hoảng sợ và tự ý đẻ ra `do_save_avatar_m34.py` và `do_upload_avatar_m34_exact.py` để tap ADB trần. Kết quả: tap trượt tọa độ, tap nhầm ảnh trình duyệt, vướng checkbox Story, làm kẹt nick và mất thời gian cả buổi chiều.
- **Lời chấn chỉnh của User:** *"Và tại sao lại có cái script lồn gì avatar 34.py? Tao đã thiết kế script upload ava r mà?"*.
- **Quy tắc bất biến bổ sung:**
  - **Căn nguyên bốc nhầm ảnh:** Khi photo picker bốc nhầm ảnh, 100% nguyên nhân là rác cache trong `/sdcard/DCIM/.thumbnails/` hoặc thư viện ảnh có ảnh lạ chưa được quét dọn sạch.
  - **Giải pháp đúng kỷ luật:** Xóa sạch thư mục `.thumbnails` trên máy (`rm -rf /sdcard/DCIM/.thumbnails/*`), đảm bảo file `avatar.jpg` là ảnh duy nhất trong gallery, cắm `.manual_avatar_locked` tại cả 2 kho video gốc và kho nuôi nick, rồi chạy lại ĐÚNG runner chuẩn `run_avatar_batch_3accs.py`.
  - **CẤM TUYỆT ĐỐI** viết bất kỳ script tap tay ADB nào thay thế runner chuẩn!

