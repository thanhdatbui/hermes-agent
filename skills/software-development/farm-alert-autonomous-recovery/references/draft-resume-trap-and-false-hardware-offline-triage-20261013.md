# Triage: Bẫy Quy Kết Nhầm Phần Cứng & Bug "Draft Resume Trap" Gây Stale Upload (13/10/2026)

## 1. Bối Cảnh Sự Cố & Bài Học Điều Phối (User Correction)
- **Hiện tượng:** Watchdog `daily-stale-upload-accounts-watchdog` báo cáo 108 nick bị đóng băng > 14 ngày (trong đó có M10, M13, M19, M44, M55, M69, M74...).
- **Sai lầm chẩn đoán của Agent:** Kiểm tra `adb devices` thấy một số máy rớt USB (offline) $\rightarrow$ Vội vàng kết luận *"Máy 10, 44, 55, 69 kẹt nick hơn 20 ngày là do offline phần cứng mất kết nối USB/ADB"*.
- **Phản hồi chỉnh đốn của User:** *"Mấy máy kibe bị off phần cứng đó là vừa bị đây thôi đéo có chuyện hơn 20 ngày bị"*.
- **Bằng chứng thực tế sau đối soát:**
  * Các máy đó (M44, M55, M69, M13, M19) **hoàn toàn online và chạy đều đặn mỗi ngày**.
  * Trên cùng một máy, **7/8 slot vẫn đăng video ầm ầm** (Tik 1: 33 clip, Tik 2: 18 clip, Tik 3: 13 clip, Tik 4: 12 clip...).
  * Việc rớt ADB chỉ là hiện tượng nghẽn bus EHCI tạm thời sau 24h chạy liên tục, tự phục hồi sau chu kỳ auto-reboot định kỳ 11:35 trưa.
  * Chỉ có DUY NHẤT 1 slot cụ thể trên máy bị kẹt ngày đăng clip.

## 2. Invariant Chẩn Đoán: Phân Biệt "Máy Offline Tức Thời" vs "Slot Kẹt Logic"
- **CẤM TUYỆT ĐỐI:** Lấy thời điểm máy rớt ADB tức thời để quy chụp nguyên nhân nick bị kẹt dài ngày (> 14 ngày).
- **Quy trình Triage 3 bước bắt buộc:**
  1. **Kiểm tra đa slot trên cùng máy:** Truy vấn `snapshots` trong `D:\Taadaa\data\tiktok_tracker.db` hoặc đọc `taikhoan_run_safe.xlsx` để xem các slot khác (Tik 1..8) của máy đó có tăng clip trong 1–7 ngày qua không.
  2. **Nếu các slot khác vẫn tăng clip:** $\rightarrow$ Khẳng định 100% phần cứng máy BÌNH THƯỜNG. Lỗi khu trú tại riêng tài khoản/workflow của slot bị kẹt.
  3. **Đọc `execution.log` & `checkpoint.json` của slot bị kẹt:** Truy vết thư mục run gần nhất tại `D:\CodexRuntime\tiktok-video\runs\run_<serial>_*` để xác định chính xác state máy bị văng (`MANUAL_REVIEW`, UI blocker, hay crash).

---

## 3. Bản Chất Bug "Draft Resume Trap" (Bẫy Kẹt Bản Nháp)
*(Gây kẹt vĩnh viễn cho M44 Tik 5, M21 Tik 7... kéo dài > 20 ngày)*

### 3.1. Cơ chế lỗi trong `state_machine.py`
1. Khi tài khoản TikTok vô tình có 1 bản nháp cũ lưu trên profile, `ACCOUNT_READY` gắn cờ `self.context.has_profile_draft = True`.
2. Khi vào state `VIDEO_PICK`: Script kích hoạt `_resume_draft_from_profile(adapter, xml_text)`.
3. Script tap mở bản nháp nhưng **không vào được Composer** (`COMPOSER_NOT_CONFIRMED`). Hàm trả về `False`.
4. Script in log: `[VIDEO_PICK] Mở bản nháp không thành công; tiếp tục fallthrough luồng upload chuẩn`.
5. **Điểm chết người:** Khi fallthrough, màn hình điện thoại **vẫn đang kẹt trong thư viện bản nháp hoặc editor bản nháp**, không có thanh điều hướng Home với nút `[+]` (Quay).
6. Script cố gắng tìm nút tạo video `[+]` $\rightarrow$ Thất bại $\rightarrow$ Văng lỗi:
   `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control`
7. Workflow dừng ở `MANUAL_REVIEW`, không đăng được clip.
8. Ở các ca nuôi tiếp theo (cách nhau 96h theo chu kỳ 4 ngày), bản nháp vẫn nằm nguyên trên profile $\rightarrow$ **Lặp lại lỗi y hệt và kẹt vĩnh viễn**.

### 3.2. Giải pháp kỹ thuật chuẩn hóa (Phương án A: Dọn sạch bản nháp lỗi khi resume thất bại)
Ngay sau khi `_resume_draft_from_profile` trả về `False`:
```python
logger.warning("[VIDEO_PICK] Mở bản nháp không thành công; dọn sạch bản nháp và tiếp tục fallthrough")
if not self.context.dry_run:
    try:
        prof_xml = self._open_profile_root_recovered(adapter)
        self._delete_all_profile_drafts(prof_xml)
    except Exception as _del_err:
        logger.warning("[VIDEO_PICK] Dọn dẹp bản nháp gặp lỗi: %s", _del_err)
self.context.has_profile_draft = False
if not self._normalize_to_home_for_video_pick(adapter, adapter.dump_ui()):
    logger.error("[VIDEO_PICK] Không thể trở về Home sau khi mở bản nháp thất bại")
    return False
xml_text = adapter.dump_ui()
```
* **Kỷ luật xử lý triệt để:** Bắt buộc gọi `_delete_all_profile_drafts(prof_xml)` để xóa sạch toàn bộ bản nháp lỗi trên profile nếu resume thất bại. Tránh để bản nháp rác tồn đọng khiến các chu kỳ nuôi sau tiếp tục rơi vào bẫy retry.
* **Chuẩn hóa điều hướng:** Gọi `_normalize_to_home_for_video_pick` để bấm `Back` thoát sạch các subpage/thư viện nháp, đưa app về màn hình **Trang chủ** có nút `[+]` được kiểm chứng visual gate trước khi tiếp tục luồng upload chuẩn.

---

## 4. Nghiệm Thu Thực Tế Bằng Canary Trên Máy Thật (Machine 21 Case Study)
- **Thiết bị:** Máy 21 (`ce011601fca4ee2505`), tài khoản `@rillecoq5ml` (Tik 7, slot từng bị kẹt lúc 08:10 với lỗi `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`).
- **Thực thi:** Chạy upload clip số 4 (`167/4.mp4`) sau khi áp dụng bản vá.
- **Diễn biến log (`run_ce011601fca4ee2505_20261013_104342`):**
  1. `[ACCOUNT_READY]` phát hiện bản nháp trên profile.
  2. `[VIDEO_PICK]` resume bản nháp thất bại $\rightarrow$ fallthrough $\rightarrow$ kích hoạt `[MEDIA_PUSH] Normalize Home: Back bounded subpage` thành công về Home.
  3. Bấm chọn video số 4, đăng bài và verify post thành công.
  4. Số video profile tăng từ 3 lên 4; Excel `Tik7.xlsx` cột *Video Đã Đăng* tăng lên 4.
  5. WinRT OCR ảnh profile xác nhận bài đăng mới hiển thị trên lưới video.

---

## 5. Bẫy Device Lock Khi Viết Script Canary Thủ Công
- **Bẫy:** Nếu script wrapper tự gọi `acquire_device_lock(project="custom-canary")`, rồi gọi subprocess `python -m scripts.tiktok_workflow`, tiến trình con sẽ bị chặn với lỗi:
  `[NEEDS_USER_DECISION] ACQUIRE_LOCKS: device needs user decision (locked by another owner)`
- **Nguyên nhân:** Subprocess tự quản lý lock và thấy lock đang bị chiếm bởi một tiến trình cha khác project ID.
- **Giải pháp:** Cho phép `scripts.tiktok_workflow` tự acquire và release device lock của chính nó, hoặc truyền `CODEX_DEVICE_LOCK_RUN_ID` tương thích.

---

## 6. WinRT OCR PowerShell Type Loading Trap
- **Bẫy:** Khi gọi WinRT OCR qua PowerShell trong Python subprocess, lệnh có thể văng lỗi:
  `ERROR: Unable to find type [Windows.Storage.StorageFile].`
- **Nguyên nhân:** Thiếu nạp runtime types của Windows trước khi gọi các lớp WindowsRuntime.
- **Khắc phục:** Luôn khai báo và nạp đầy đủ mảng `$types` trong PowerShell:
  ```powershell
  $types = @(
      "Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime",
      "Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime",
      "Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime",
      "Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime",
      "Windows.Media.Ocr.OcrResult, Windows.Media.Ocr, ContentType=WindowsRuntime",
      "Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime",
      "Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime",
      "Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime"
  )
  foreach ($t in $types) { try { [void][Type]::GetType($t, $true) } catch {} }
  ```
  Và đảm bảo `$imgPath` là đường dẫn tuyệt đối với dấu gạch chéo ngược Windows (`D:\...`).
