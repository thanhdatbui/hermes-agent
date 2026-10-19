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

### D. Bẫy Mất Ký Tự `@` Trên Profile Gây Kẹt Vòng Lặp FEED (Error Spam `exit_2` trên M3, M28):
- **Hiện tượng**:
  * Trong hàm phân loại màn hình `classify(lines)`, điều kiện nhận diện `PROFILE` yêu cầu cứng:
    `profile_has_user = any(l.startswith("@") for l in lines)`
    `profile_markers = any(k in t for k in ("follower", "da follow", "daf", "thich"))`
    `if profile_has_user and profile_markers: return "PROFILE"`
  * Font chữ hoặc chất lượng ảnh chụp Samsung S7 khiến WinRT OCR thường xuyên đánh rơi hoặc méo ký tự `@` đầu username (ví dụ: `@kamilhhs0tk` đọc thành `kamiIhhsOtk`, hoặc username bị nhận diện thành text thường).
  * Khi thiếu `@`, `profile_has_user` trả về `False`. Script rơi xuống dòng kiểm tra navigation bar:
    `if re.search(r"de xu|danh cho ban|for you|trang ch|hop th|cua hang", t): return "FEED"`
    vì dưới đáy màn hình Profile luôn có nút thanh điều hướng *"Trang chủ"* (`Trang chi`).
- **Hậu quả**:
  * Runner ngộ nhận màn hình Profile là màn hình `FEED`!
  * Tại `state == "FEED"`, runner thực hiện lệnh: tap tab Hồ sơ `XY_PROFILE_TAB (972, 1857)`.
  * Do máy THỰC TẾ ĐANG Ở PROFILE, việc tap tab Hồ sơ chỉ làm app reload lại đúng trang Profile.
  * Lần quan sát tiếp theo lại nhận diện là `FEED` $\rightarrow$ lặp lại 5 lần liên tiếp $\rightarrow$ kích hoạt `MAX_SAME_STATE = 4` abort: `ket o trang thai FEED 5 lan lien tiep` (`exit_2`), gây lỗi hàng loạt trên các máy rớt dấu `@`.
- **Quy chuẩn sửa đổi**:
  * Nới lỏng kiểm tra `PROFILE`: Nhận diện qua profile markers (`follower`, `follow`, `thich`, `luot xem`, `nghi gi`, `tieu su`) kết hợp với thanh điều hướng dưới đáy (`Hồ sơ` / `H6 sd` ở $y > 1800$).
  * Nếu màn hình đã có thanh điều hướng Hồ sơ ở đáy và có các chỉ số tương tác, BẮT BUỘC phân loại là `PROFILE`, tuyệt đối không để rơi xuống `FEED`.

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

---

## 5. Kết Quả Thực Nghiệm & Số Liệu Sản Xuất (Production Benchmark - 16/10/2026)

- **Quy mô triển khai:** Farm 80 máy Samsung Galaxy S7 (SM-G930F), tập ứng viên gồm 419 tài khoản rập khuôn (trùng tên bot, cụt số, 1 từ).
- **Hiệu năng vận hành:**
  * Watchdog 25 workers (`ThreadPoolExecutor` + Decoupled Subprocess Runner) chạy chu kỳ mỗi 15 phút.
  * Thời gian mỗi batch 25 workers: 40–90 giây.
  * Tỷ lệ thành công nhảy vọt từ ~8% (2 nick/đợt khi dính bẫy méo dấu Switcher & OCR ô input nhấp nháy) lên **30%–56% (7–14 nick/đợt)** ngay sau khi áp dụng:
    1. Bẻ khóa Switcher dung sai cao (`chuy\w{0,3}n.*kho\w{0,2}n` + `switch account`).
    2. Xác thực mềm ô input bằng bóc tách mảng từ `all_ocr_words` + bộ đếm `N/30`.
    3. Nâng timeout subprocess lên 320s.
- **Thành quả thực tế:**
  * Đã hoàn tất đổi tên chuẩn "User bình thường" và nghiệm thu Profile OCR 100% cho **152 / 419 tài khoản** liên tục trong đêm, cấp cooldown 7 ngày an toàn.
  * Xóa bỏ hoàn toàn 100% hiện tượng tap nhầm ô Search / "Không tìm thấy kết quả", zero device lock collision, zero farm freeze.
