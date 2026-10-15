# TikTok Rolling Rename 25-Worker Batch Architecture & OCR State-Machine Resilience

## 1. Bối cảnh & Yêu cầu Vận hành
Trên farm TikTok 80 máy (Samsung Galaxy S7, 1080x1920, Android 7/8), hàng trăm tài khoản bị đặt tên hiển thị (Display Name) rập khuôn (trùng username bot, cụt số, hoặc 1 từ trơ trọi).
Yêu cầu vận hành:
- Đổi tên cuốn chiếu tự động sang chuẩn **"User bình thường"** (70% Họ Đệm Tên / 30% Tên + Biệt danh đời thường).
- Tốc độ cao: Chạy song song **25 workers** (`MAX_WORKERS = 25`) giữa các ca nuôi feed.
- An toàn tuyệt đối: Không tap nhầm vào ô Search, không đổi đè nick khác, chịu lỗi khi máy bị lag/đơ ADB, và nghiệm thu 100% bằng OCR + Vision.

---

## 2. Kiến Trúc Decoupled Subprocess Runner (Chống Sập Pool 25 Workers)

### Cạm bẫy Monolithic Inline Threading:
Nếu gộp toàn bộ logic State Machine ADB + WinRT OCR (`ocr_boxes.ps1`) chạy trực tiếp trong các worker thread của 1 script Python duy nhất:
- 25 threads đồng thời gọi PowerShell WinRT OCR gây tranh chấp socket / file ảnh tạm.
- Khi 1 máy bị đơ USB / crash ADB daemon, unhandled exception có thể làm sập toàn bộ `ThreadPoolExecutor` hoặc làm gián đoạn việc ghi state file.

### Giải pháp Chuẩn Hóa Decoupled Architecture:
Tách thành 2 tầng độc lập:
1. **CLI Runner Đơn Máy (`do_rename_canonical_runner.py`)**:
   - Nhận tham số qua `argparse`: `--machine <M>`, `--serial <S>`, `--username <U>`, `--name <N>`.
   - Chịu trách nhiệm trọn vẹn: Quản lý 35 bước State Machine, tự động kiểm tra và chuyển nick qua Switcher, gõ Unicode UTF-8 qua AdbKeyboard, xác nhận popup 7 ngày, nghiệm thu OCR trên Profile.
   - Xuất artifact: `m{M}_{U}_rename_confirmed.png` và `m{M}_{U}_rename_confirmed.json`.
   - Trả về exit code `0` khi `KET QUA: RENAMED` hoặc `KET QUA: ALREADY`.
2. **Watchdog Scheduler (`tiktok_rename_rolling_watchdog.py`)**:
   - Phân bổ O(1): bốc danh sách máy rảnh không có device-lock và chưa đổi tên trong 7 ngày.
   - Gọi runner qua `subprocess.run(cmd, capture_output=True, text=True, timeout=320)` trong `ThreadPoolExecutor(max_workers=25)`.
   - Bọc `try...except Exception: pass` cho từng `fut.result()` trong `as_completed()`, chỉ ghi state khi `ok and p.exists()`.
   - **Timeout Subprocess >= 320s**: Khi 25 máy cùng lúc gọi OCR, CPU host đạt đỉnh khiến mỗi step OCR kéo dài từ 1-2s lên 4-6s. Runner 35 bước có thể mất 250–300s. Đặt timeout `>= 320s` để tránh bị kill nhầm ở bước cuối.

---

## 3. Các Tử Huyệt UI & Bẫy Méo Dấu WinRT OCR

### A. Bẫy Blind Tapping Top-Left (75, 150) -> Mở Ô Search TikTok:
- **Hiện tượng**: Trên TikTok v47 (Samsung S7), góc trên bên trái màn hình Profile là icon **"Tìm bạn bè / Thêm bạn" (Find Friends)**.
- **Hậu quả**: Nếu dùng `tap(75, 150)` để lùi trang sau khi Lưu, app sẽ mở màn hình Tìm bạn bè, con trỏ tự focus vào thanh Search. AdbKeyboard gõ tên mới thẳng vào ô Search -> Màn hình hiện `Không tìm thấy kết quả`.
- **Quy chuẩn**:
  * **CẤM TUYỆT ĐỐI tap tọa độ góc trên bên trái**.
  * Mọi thao tác lùi trang BẮT BUỘC dùng **`input keyevent 4` (KEYCODE_BACK phần cứng)**.

### B. Bẫy Méo Dấu Tiêu Đề Switcher ("Chuyển đổi tài khoản"):
- **Hiện tượng**: Trên Bottom Sheet chuyển tài khoản, WinRT OCR thường đọc chữ `Chuyển đổi tài khoản` thành `chuydn ddi tai khoan` (hoặc `Chuydn ddi täi khoån`).
- **Hậu quả**: Regex cứng `"chuyen doi tai khoan"` bị xịt 100% -> Runner xếp vào `UNKNOWN` -> Tự bấm Back đóng Switcher -> Báo lỗi `mo Switcher 3 lan, acc active van la...` trên hàng loạt máy.
- **Quy chuẩn Regex dung sai cao**:
  ```python
  if re.search(r"chuy\w{0,3}n\s*d\w{0,3}i|chuy\w{0,3}n.*kho\w{0,2}n|switch account|them tai khoan|add account", t):
      return "SWITCHER"
  if not (profile_has_user and profile_markers) and (("tai khoan" in t or "khoan" in t) and ("chuy" in t or "switch" in t or "them" in t)):
      return "SWITCHER"
  ```

### C. Bẫy False-Negative Abort ở Ô Nhập Tên (`NAME_EDIT`) - 2-Tier Verification:
- **Hiện tượng**:
  * Văn bản gõ qua `AdbKeyboard` (`ADB_KEYBOARD_INPUT_TEXT` với Base64) là **chuẩn xác 100%**.
  * Bộ đếm ký tự `{len}/30` hiển thị chính xác độ dài `len(NEW_NAME)`.
  * Tuy nhiên, ô nhập có con trỏ nhấp nháy, chữ màu xám nhạt khiến WinRT OCR đọc méo các nguyên âm tiếng Việt:
    - `"Sơn Nấm"` $\rightarrow$ đọc thành `"Sdn I\läm"` (ratio rớt xuống ~0.62).
    - `"Tươi Đậu"` $\rightarrow$ đọc thành `"Tl-fdi DåU"`.
    - `"Bùi Duy Phương"` $\rightarrow$ đọc thành `"Bbi Duy Phi-fdng"`.
    - `"Đạt Tít"` $\rightarrow$ đọc thành `"Dat"`.
  * Nếu dùng ngưỡng `ratio >= 0.70`, script hiểu lầm là gõ sai text -> tự bấm "Hủy" -> Hàng chục máy abort oan.
- **Quy chuẩn 2-Tier Verification**:
  1. **Tier 1 (Soft Gate tại ô input `NAME_EDIT`)**:
     - Kiểm tra bộ đếm: `ok_count` khớp `{len}/30` (dung sai ±1).
     - **Bẫy so khớp cả dòng (Line vs Word Penalty):** Nếu so sánh `difflib.SequenceMatcher(None, norm(l), w)` thì khi một dòng OCR gom cả cụm từ (ví dụ `"Trpng HI-fdng"`), độ dài dòng lớn khiến ratio bị kéo tụt xuống `< 0.45` dù từ `"Trpng"` giống `"Trọng"` tới 80%!
     - **Giải pháp bóc tách mảng từ đơn (`all_ocr_words`):** Bắt buộc bóc tách mảng từ đơn lẻ `all_ocr_words = [norm(w) for l in lines for w in l.split()]` để so khớp độc lập từng từ.
     - Kiểm tra text mềm: Khớp ít nhất 1 từ đơn (`found_word`) HOẶC `ratio >= 0.35` là BẮT BUỘC bấm "Lưu":
     ```python
     words = [norm(w) for w in NEW_NAME.split() if len(w) >= 2]
     all_ocr_words = [norm(w) for l in lines for w in l.split()]
     found_word = any(any(difflib.SequenceMatcher(None, ow, w).ratio() >= 0.6 for ow in all_ocr_words) for w in words)
     ratio = difflib.SequenceMatcher(None, norm(" ".join(lines)), NEW_NAME_NORM).ratio()
     ok_text = (any(is_target(l) for l in lines)
                or NEW_NAME_NORM in norm(" ".join(lines))
                or ratio >= 0.35
                or found_word)
     if not (ok_text and ok_count):
         tap(XY_NAME_CANCEL, 2)
         raise Abort(f"OCR khong xac nhan o nhap = '{NEW_NAME}' ({expected_len}/30) -> Huy, KHONG Luu")
     ```
  2. **Tier 2 (Strict Gate tại Profile)**:
     - Sau khi Lưu, quay về màn hình Profile root. Tại đây tên hiển thị font in đậm lớn, tương phản cao, WinRT OCR đạt độ chính xác cao.
     - Áp dụng kiểm tra nghiêm ngặt `ratio >= 0.75` và `is_target_user(final_user)` để chốt `verified = True`.

---

## 4. Kỷ Luật Vận Hành Hermes Cron, Stdout Flush & Canary Testing

1. **Cơ chế Flush Buffer Stdout Trong Tiến Trình Nền (Windows C-Runtime Buffer)**:
   - Khi chạy script đa luồng / watchdog trong background trên Windows (`terminal(background=True)`), stdout mặc định bị C-runtime block-buffer (chỉ đẩy ra khi đầy 4KB hoặc tiến trình đóng sạch).
   - Lệnh in thông báo hoàn tất BẮT BUỘC dùng `print(..., flush=True)` để harness Hermes nhận được ngay sự kiện nghiệm thu (`✅ [ROLLING RENAME]`), không bị nuốt output.
2. **Cấu hình `deliver: 'local'` cho Batch nặng**:
   - Batch 25 workers chạy mất 60s–180s. Hermes Cron timeout mặc định là 60s.
   - BẮT BUỘC cấu hình `deliver: 'local'` để tránh bắn cảnh báo lỗi giả `provider timeout` về Telegram.
2. **Kỷ luật nghiệm thu Canary (Anti-No-op Pass)**:
   - CẤM báo "Canary Passed" khi kết quả chỉ là No-op / Skipped (ví dụ: máy test không có target account nên tự lùi ra an toàn trả về `False`).
   - Phải bốc máy có tài khoản đủ điều kiện, chạy end-to-end đến khi ra `verified=True`, và soi mắt kiểm tra ảnh qua `browser_vision` trước khi chạy hàng loạt.
3. **Đồng bộ đa tầng**:
   - Khi chỉnh sửa script watchdog hoặc runner:
     `D:\Taadaa\tools\` $\rightarrow$ `D:\Taadaa\Hermes\deploy\hermes-home\scripts\` $\rightarrow$ chạy `cron_sync_watchdog.py` để đồng bộ sang `%LOCALAPPDATA%\hermes\scripts\` và `OneDrive\hermes-cron\scripts`.
