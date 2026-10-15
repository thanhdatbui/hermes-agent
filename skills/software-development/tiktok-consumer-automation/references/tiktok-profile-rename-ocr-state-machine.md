# TikTok Profile Rename (Display Name / Nickname) via OCR State Machine (Samsung Galaxy S7 Farm)

## Bối cảnh & Vấn đề Kỹ thuật
- **Lỗi `uiautomator dump` trên Samsung Galaxy S7 (SM-G930F/W8, Android 7/8):** Khi chạy TikTok, tiến trình `uiautomator` hệ thống thường xuyên bị quá tải, treo hoặc bị OOM killer tiêu diệt với exit code `137`.
- **`atx-agent` /dump/hierarchy:** Trên một số máy, `atx-agent` chỉ dump được status bar hệ thống mà không thấy cây node của TikTok, hoặc trả về XML rỗng/stale.
- **Giải pháp chuẩn hóa (Battle-Tested):** Sử dụng State Machine kết hợp **Native WinRT OCR** (`tools/ocr_boxes.ps1`) để nhận diện màn hình và tọa độ động theo thời gian thực (như đã áp dụng thành công trên `do_rename_m8.py` và `do_rename_m20.py`).

---

## 1. Tọa độ & Hình học UI trên Samsung Galaxy S7 (1080x1920)

| Vị trí / Thao tác | Tọa độ chuẩn S7 (X, Y) | Ghi chú |
|---|---|---|
| **Tab Hồ sơ (Profile Tab)** | `(972, 1857)` | Góc dưới bên phải thanh điều hướng bottom bar |
| **Cuộn Header Hồ sơ** | `(540, 1100)` → `(540, 600)` | Vuốt nhẹ để ghim username lên sticky header |
| **Ghim ID / Mở Switcher** | `(500, 140)` | Tap username trên header mở sheet 'Chuyển đổi tài khoản' |
| **Cuộn Sheet Switcher** | `(540, 1500)` → `(540, 900)` | Khi máy có 8 acc, cuộn lên để thấy 4 acc phía dưới |
| **Nút Sửa hồ sơ** | `find_box("sua ho s")` hoặc `(360, 730)` | Nút chữ nhật 'Sửa hồ sơ' giữa màn hình (dưới Follower). CẤM tap `(72, 148)`! |
| **BẪY TỬ HUYỆT (75, 150)** | `CẤM TAP (75, 150)` | Trên TikTok v47.x, góc trên trái là icon "Tìm bạn bè". Tap vào đây sẽ mở màn Search và gõ nhầm tên vào ô tìm kiếm ("Không tìm thấy kết quả")! |
| **Thao tác Quay lại (Back)** | `input keyevent 4` | Luôn dùng KEYCODE_BACK phần cứng để lùi trang, TUYỆT ĐỐI CẤM tap tọa độ góc trên trái! |
| **Hàng 'Tên' (Nickname)** | `(600, 752)` | Hàng đầu tiên trong 'Sửa hồ sơ', nằm trên 'Tên người dùng' |
| **Nút Xóa tên cũ (X)** | `(960, 576)` | Nút clear trong ô nhập Tên |
| **Nút 'Lưu' (Save)** | `(980, 140)` | Góc trên bên phải header màn sửa Tên |
| **Nút 'Hủy' (Cancel)** | `(90, 150)` | Góc trên bên trái header màn sửa Tên |
| **Nút 'Xác nhận' popup** | `(750, 1100)` | Popup cảnh báo đổi tên 7 ngày |

---

## 2. HARD SAFETY GATE: 'Tên' (Nickname) vs 'Tên người dùng' (Username)

### Giới hạn chính sách TikTok:
* **Tên (Nickname / Display Name):** Giới hạn đổi **1 lần mỗi 7 ngày**. Nằm ở hàng đầu tiên (`y ≈ 730–769`).
* **Tên người dùng (Username / @handle):** Giới hạn đổi **1 lần mỗi 30 ngày**. Nằm ở hàng thứ hai (`y > 850`).

### CẠM BẪY TỬ HUYỆT & CHỐT CHẶN BẮT BUỘC:
1. **Tuyệt đối CẤM tap vào hàng Tên người dùng:**
   Script bắt buộc phải có chốt chặn kiểm tra hình học giữa box nhãn 'Tên' (`ten_box`) và 'Tên người dùng' (`user_box`):
   ```python
   xy = (XY_NAME_ROW[0], center(ten_box)[1]) if ten_box else XY_NAME_ROW
   if user_box and xy[1] > user_box[1] - 30:
       raise Abort(f"Điểm tap Tên {xy} không nằm trên 'Tên người dùng' (y={user_box[1]}) -> dừng ngay!")
   ```
2. **Nhận diện và thoát ngay màn `USERNAME_EDIT`:**
   Nếu OCR phát hiện màn hình có các dấu hiệu: bộ đếm `\d{1,2}/24`, text `mỗi 30 ngày`, `chữ cái, chữ số`, `tiktok.com/@...` mà **KHÔNG** có `Tiểu sử` / `Thay đổi ảnh`:
   $\rightarrow$ Đây là màn sửa Username! Script phải lập tức bấm `keyevent 4` (Back), **TUYỆT ĐỐI KHÔNG gõ bất kỳ ký tự nào** vào ô này.

---

## 3. Quy trình Nhập liệu & Nghiệm thu An toàn

1. **Nhập text tiếng Việt qua AdbKeyboard:**
   - Xóa chữ cũ: Tap nút X `(960, 576)` kết hợp broadcast `ADB_KEYBOARD_CLEAR_TEXT`.
   - Set bàn phím: `ime set com.github.uiautomator/.AdbKeyboard`.
   - Encode Base64 chuỗi UTF-8:
     ```python
     encoded = base64.b64encode(new_name.encode("utf-8")).decode("ascii")
     shell("am", "broadcast", "-a", "ADB_KEYBOARD_INPUT_TEXT", "--es", "text", encoded)
     ```
2. **Pre-Save Verification Gate:**
   - Sau khi gõ, chụp lại OCR màn hình để kiểm tra:
     * Nội dung ô nhập khớp `new_name` (chuẩn hóa không dấu `norm(l) == new_name_norm`).
     * Bộ đếm ký tự khớp `{len(new_name)}/30` (ví dụ `11/30` cho "Phương Thảo", `6/30` cho "Hải Sa").
   - **Chỉ bấm 'Lưu' đúng 1 lần duy nhất** khi cả 2 điều kiện trên đều thỏa mãn. Nếu không khớp, bấm 'Hủy' `(90, 150)` và Abort, không bấm Lưu bừa bãi.
3. **Xử lý Popup Xác nhận 7 ngày:**
   - TikTok sẽ hiện dialog: *"Đặt biệt danh? Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần"*.
   - Tap nút 'Xác nhận' `(750, 1100)` hoặc box OCR khớp `xac nhan | confirm | dong y`.
4. **Nghiệm thu OCR trên Profile root:**
   - Sau khi bấm Lưu và xác nhận, Back về trang Hồ sơ (`PROFILE`).
   - Đọc chính xác dòng text nằm ngay phía trên `@username` (theo tọa độ `b2[3] <= b[1] + 5 and b[1] - b2[3] < 120`).
   - Bằng chứng nghiệm thu hợp lệ bắt buộc gồm:
     * Full screenshot 1080x1920 (`MEDIA:<path>.png`).
     * JSON report (`target_user`, `new_name`, `final_name_ocr`, `verified_by_ocr=True`).

---

## 4. Quy tắc Sinh Tên Tiếng Việt Tự Nhiên (User Directives)

- **CẤM dùng nguyên username/email prefix tiếng Anh dài:** (ví dụ `francesuhuntertgxg5`, `LilyanLederhos64090` $\rightarrow$ quá dài, thô, lộ bot).
- **Quy tắc rút gọn & chế tên Việt gần âm:**
  * `frances-` / `florence-` $\rightarrow$ **Phương Thảo**, **Thu Phương**, **Phương**.
  * `sadou-` $\rightarrow$ **Hải Sa**, **Sa**.
  * `lilyan-` $\rightarrow$ **Linh**, **Liên**.
  * `kylar-` $\rightarrow$ **Kỳ La**.
- **Phong cách đặt tên người thật (`make_tiktok_name` trong `social_reg_v1.py`):**
  * Họ + Đệm + Tên (25%): *Trần Minh Đạt, Nguyễn Hoài An*
  * Họ + Tên (25%): *Lê Linh, Vũ Nam*
  * Đệm + Tên (20%): *Ngọc Linh, Thanh Thảo, Khánh Vy*
  * Tên + Biệt danh đời thường (20%): *Linh Bông, Đạt Còi, Vy Miu, An Kem*
  * Tên lặp / Duo dễ thương (10%): *An An, Gạo Gạo, Miu Miu*

---

## 5. Device Lock Integration

- Toàn bộ script đổi tên bắt buộc phải acquire device lock:
  ```python
  from automation_core.device_lock import operator_device_lock

  with operator_device_lock(machine=machine_id, serial=serial, project="do_rename", timeout=300):
      # Thực thi flow an toàn, tự động restore default IME khi hoàn tất
  ```
- Tránh xung đột tuyệt đối với các cron nuôi acc (feed/follow/upload) đang chạy trên farm.

---

## 6. Rolling Rename Watchdog Architecture (25 Workers & Fail-Safe)

- **Độ song song:** Watchdog chạy `MAX_WORKERS = 25` (`ThreadPoolExecutor`) gom tối đa 25 máy rảnh khác nhau cùng lúc giữa các ca nuôi.
- **Subprocess Isolation Architecture:**
  * BẮT BUỘC tách runner thực thi thành CLI độc lập (`do_rename_canonical_runner.py --machine <M> --serial <S> --username <U> --name <N>`).
  * Watchdog `_worker` gọi qua `subprocess.run(cmd, timeout=320, capture_output=True)`. Cách ly triệt để bộ nhớ, tránh nghẽn thread pool khi 25 workers đồng thời gọi PowerShell WinRT OCR (`ocr_boxes.ps1`).
- **Xử lý trễ Splash Screen trên Samsung S7:**
  * App TikTok trên chip Exynos 8890 tải splash màn hình đen/chữ TikTok có thể mất 10–15s. State machine thiết lập `MAX_STEPS = 25-35` bước, kiên nhẫn bỏ qua 3–5 step đầu nếu màn hình vẫn ở Splash/UNKNOWN trước khi xác định kẹt.
- **Fail-Safe chống đơ ADB Transport:**
  * Lệnh gọi ADB bắt buộc có `timeout=15` bọc `try...except Exception: return ""` để khi 1 máy bị đơ kết nối USB không làm treo toàn bộ batch.
  * Vòng lặp `as_completed` bọc `try...except` cho từng future (`fut.result()`).
- **Cronjob Hermes Delivery:** Tác vụ chạy 25 workers tốn >60s bắt buộc cấu hình `deliver: 'local'` trên cronjob. CẤM để `origin` vì LLM gateway sẽ timeout sau 60s và bắn tin nhắn báo lỗi giả về Telegram.
- **Xử lý Switcher tự động & Bẫy OCR Méo Dấu (Cực kỳ quan trọng):**
  * Khi vào Profile, nếu active account khác target, mở Switcher chuyển đúng tài khoản. Nếu không có trong Switcher, bấm `keyevent 4` thoát ra an toàn và trả về `(None, False)`.
  * **Cạm bẫy OCR méo dấu tiêu đề Switcher:** Trên font chữ TikTok Samsung S7, chữ *"Chuyển đổi tài khoản"* thường xuyên bị WinRT OCR nhận diện sai dấu thành `"chuydn ddi tai khoan"` hoặc `"chuydn ddi täi khoån"`. Nếu dùng regex cứng `"chuyen doi tai khoan"` thì state machine sẽ coi là `UNKNOWN`, lập tức bấm Back đóng Switcher và báo lỗi *"mo Switcher 3 lan, acc active van la..."*.
  * **Regex chuẩn hóa chống méo dấu:**
    ```python
    if re.search(r"chuy\w{0,3}n\s*d\w{0,3}i|chuy\w{0,3}n.*kho\w{0,2}n|switch account|them tai khoan|add account", t):
        return "SWITCHER"
    if not (profile_has_user and profile_markers) and (("tai khoan" in t or "khoan" in t) and ("chuy" in t or "switch" in t or "them" in t)):
        return "SWITCHER"
    ```
  * **Timeout Subprocess khi chạy song song 25 workers:** Khi 25 máy cùng lúc gọi `ocr_boxes.ps1`, CPU host bị tải đỉnh khiến mỗi bước OCR tăng từ 1-2s lên 4-6s. Quá trình cuộn Switcher và kiểm tra 35 bước có thể mất 250–300s. Timeout subprocess trong watchdog BẮT BUỘC đặt `>= 320s` (thay vì 240s) để tránh bị SIGTERM oan khi máy đang ở bước cuối.
- **Canary Gate & Vision Inspection:** Trước khi kích hoạt hàng loạt trên 25 máy, BẮT BUỘC chạy Canary trên 1 máy thật (`test_canary_safe_rename.py`), dùng `browser_vision` soi mắt đọc ảnh `MEDIA:<path>` xác nhận nickname hiển thị đúng trên Profile, không che popup, không kẹt phím.
- **Tiêu Chuẩn Báo Cáo Canary (Chống Báo Canary No-op):** CẤM TUYỆT ĐỐI báo cáo "Đã chạy Canary xong" khi kết quả runner thực chất chỉ là Skipped/No-op (ví dụ: máy test có active account không khớp target username và Switcher không có nick đó -> runner tự lùi ra an toàn trả về `(None, False)`). Trường hợp máy test không đủ điều kiện thi công, Coordinator phải lập tức bốc ngay máy khác có target account sẵn sàng để chạy thực nghiệm đầy đủ đến khi ra ảnh Profile nghiệm thu tên mới thành công.
- **Bẫy Layout Profile Mới & Thoát Bằng Keyevent Back:** Trên một số tài khoản/phiên bản TikTok mới, layout Profile không còn nút 'Sửa hồ sơ' to giữa màn hình mà icon cây bút chì chỉnh sửa nằm ở góc trên bên trái `(75, 150)`. BẮT BUỘC chỉ được tương tác với tọa độ này khi State Machine xác nhận chắc chắn 100% đang ở `PROFILE`. Tuyệt đối CẤM tap `(75, 150)` để lùi trang sau khi Lưu, vì nếu app đã tự lùi về Profile rồi mà lại bấm tiếp `(75, 150)` thì sẽ mở màn hình Tìm kiếm bạn bè và AdbKeyboard gõ nhầm text vào ô Search! Luôn dùng `input keyevent 4` (KEYCODE_BACK phần cứng) để lùi trang an toàn.
- **Chiến Lược Tách Runner Độc Lập Cho Watchdog 25 Workers:** Khi chạy cuốn chiếu 25 workers song song, tách toàn bộ State Machine OCR 35 bước thành CLI độc lập `do_rename_canonical_runner.py` và gọi qua `subprocess.run(timeout=320)`. Cách ly triệt để bộ nhớ, chống tắc nghẽn thread pool khi nhiều máy cùng gọi WinRT OCR `ocr_boxes.ps1`, giúp farm cuốn chiếu ổn định vượt mốc hàng chục nick/phiên.

---

## 7. Bẫy OCR Méo Dấu Trong Ô Nhập Tên (NAME_EDIT) & Thuật Toán Xác Thực Mềm

### Hiện tượng & Căn nguyên:
- Khi `AdbKeyboard` gõ tên mới vào ô input (ví dụ: `Sơn Nấm`, `Tươi Đậu`, `Bùi Duy Phương`, `Đạt Tít`):
  * Chữ trong ô input màu xám nhạt, kèm con trỏ nhấp nháy (`|`) và gạch chân Android.
  * WinRT OCR quét qua ô input thường làm rớt hoặc méo các ký tự có dấu phức tạp:
    - `"Sơn Nấm"` $\rightarrow$ OCR đọc thành `"Sdn I\läm"` (similarity ratio rớt xuống ~0.62).
    - `"Tươi Đậu"` $\rightarrow$ OCR đọc thành `"Tl-fdi DåU"`.
    - `"Bùi Duy Phương"` $\rightarrow$ OCR đọc thành `"Bbi Duy Phi-fdng"`.
    - `"Đạt Tít"` $\rightarrow$ OCR đọc thành `"Dat"`.
- Nếu script áp dụng ngưỡng so khớp chuỗi khắt khe (`ratio >= 0.7`), script sẽ hiểu lầm là AdbKeyboard gõ sai text, tự động bấm 'Hủy' và Abort (`OCR khong xac nhan o nhap = ...`). Hàng loạt máy bị rớt oan dù text đã gõ đúng 100%!

### Giải pháp Xác Thực Mềm (Soft Pre-Save Verification):
1. **Bộ đếm ký tự là neo vật lý chuẩn xác nhất:**
   - TikTok luôn hiển thị bộ đếm `{len}/{max}` ở góc dưới ô input (ví dụ: `7/30`, `8/30`, `14/30`).
   - OCR đọc bộ đếm này với độ chính xác ~99%. Bắt buộc kiểm tra:
     ```python
     count_match = re.search(r"(\d{1,2})\s*/\s*30", box)
     expected_len = len(NEW_NAME)
     ok_count = (count_match is not None and abs(int(count_match.group(1)) - expected_len) <= 1) or f"{expected_len}/30" in box
     ```
2. **Thuật toán so khớp mềm kết hợp tách từ (Word-by-Word Tokenization):**
   - **Bẫy so sánh cả dòng:** Nếu so khớp `difflib.SequenceMatcher(norm(line), word)` thì khi `line` chứa nhiều từ (ví dụ `'Trpng HI-fdng'`), độ dài dòng lớn khiến ratio bị kéo tụt xuống `< 0.45` dù từ `'Trpng'` giống `'Trọng'` tới 80%!
   - **Giải pháp bóc tách mảng từ (all_ocr_words):** Bắt buộc tách toàn bộ các dòng OCR thành danh sách từ đơn:
     ```python
     words = [norm(w) for w in NEW_NAME.split() if len(w) >= 2]
     all_ocr_words = [norm(w) for l in lines for w in l.split()]
     found_word = any(any(difflib.SequenceMatcher(None, ow, w).ratio() >= 0.6 for ow in all_ocr_words) for w in words)
     ratio = difflib.SequenceMatcher(None, norm(" ".join(lines)), NEW_NAME_NORM).ratio()
     ok_text = (any(is_target(l) for l in lines)
                or NEW_NAME_NORM in norm(" ".join(lines))
                or ratio >= 0.35
                or found_word)
     ```
   - Điều kiện text hợp lệ (`ok_text = True`) khi thỏa mãn:
     * `ok_count = True`: Bộ đếm ký tự khớp `{len(NEW_NAME)}/30` (±1).
     * `ok_text = True`: Tìm thấy ít nhất 1 từ đơn (`found_word`) khớp trong `all_ocr_words` (ratio >= 0.6) HOẶC ratio toàn chuỗi >= 0.35.

3. **Cơ chế Flush Buffer Stdout Trong Tiến Trình Nền (Windows C-Runtime Buffer):**
   - Khi chạy script đa luồng / watchdog trong background trên Windows (`terminal(background=True)`), stdout mặc định bị C-runtime block-buffer (chỉ đẩy ra khi đầy 4KB hoặc tiến trình đóng sạch).
   - Lệnh in thông báo hoàn tất BẮT BUỘC dùng `print(..., flush=True)` để harness Hermes nhận được ngay sự kiện nghiệm thu (`✅ [ROLLING RENAME]`), không bị nuốt output.

4. **Chốt chặn an toàn tối cao (Post-Save Gate):**
   - Xác thực mềm ở ô input chỉ để quyết định có bấm 'Lưu' hay không.
   - Việc công nhận đổi tên thành công (`verified = True`) **vẫn bắt buộc kiểm tra 100% tại màn hình Profile root sau khi Lưu**: Tại đây font chữ in đậm lớn, WinRT OCR đạt độ chính xác `>= 75%`.
