# Lessons Learned: Bẫy Blind Tapping Tọa Độ Top-Left (75, 150) & Cú Lừa Tìm Kiếm Bạn Bè Trên TikTok S7

## 1. Hiện Tượng Thực Tế
Khi điều khiển giao diện TikTok Android (bản v47.x trên Samsung S7 độ phân giải 1080x1920) để thực hiện đổi Tên hiển thị (Display Name):
- Script tự động tap mù vào tọa độ `(75, 150)` với suy nghĩ đây là nút Back/Quay lại.
- Trên thực tế:
  * Góc trên bên trái của trang **Hồ sơ (Profile)** là icon **"Tìm bạn bè / Thêm bạn" (Find Friends)** (hình người có dấu `+`), hoàn toàn không phải nút Quay lại.
  * Cú tap vào `(75, 150)` mở màn hình **Tìm bạn bè**.
  * Thanh Search trên cùng tự động được chọn (focused).
  * Lệnh gõ tên mới tiếp theo qua `AdbKeyboard` gõ thẳng chuỗi tên (ví dụ: `Hải Cường`) vào ô Search và tự động kích hoạt tìm kiếm!
  * Màn hình TikTok hiển thị:
    - Search box: `Hải Cường`
    - Nội dung giữa màn hình: **`Không tìm thấy kết quả`**
    - Đáy màn hình: Bàn phím AdbKeyboard hiển thị 4 nút: `[∞] [Clear Text] [Search] [Switch IME]`.

## 2. Hậu Quả & Rủi Ro Nghiêm Trọng
- Script không có khâu OCR Readback Verification:
  * Chụp ảnh màn hình "Không tìm thấy kết quả" nhưng vẫn ngộ nhận là đã đổi tên thành công.
  * Báo cáo ảo hoàn tất lên hệ thống trong khi tên nick không hề đổi.

## 3. Quy Chuẩn Kỹ Thuật Bắt Buộc (Anti-Blind Tapping Invariant)
1. **Tuyệt đối cấm tap mù tọa độ**:
   - CẤM gọi `tap(75, 150)` trên màn hình Profile.
   - Để vào trang Sửa hồ sơ, BẮT BUỘC dùng OCR tìm text `Sửa hồ sơ` / `Chỉnh sửa hồ sơ` (`(210, 865)`) hoặc icon cây bút chì bên phải dòng tên `(870, 558)`.
2. **State-Machine 5 Trạng Thái Khép Kín**:
   - `FEED` -> tap tab Hồ sơ `(972, 1857)`.
   - `PROFILE` -> đọc `nickname_on_profile`. Nếu chưa đúng acc mục tiêu thì mở Switcher.
   - `EDIT_PROFILE` -> OCR tìm dòng có chữ "Tên" rồi mới tap mở ô sửa tên.
   - `NAME_EDIT` -> gõ AdbKeyboard -> BẮT BUỘC đọc lại OCR kiểm tra tên mới + bộ đếm ký tự `{len}/30` -> tap Lưu `(980, 140)`.
   - `PROFILE (Readback)` -> Trở lại Profile, OCR đọc lại dòng ngay trên `@username`. Chỉ khi tên thật trên Profile khớp 100% với tên mới thì mới lưu trạng thái hoàn thành.

## 4. Quy Chuẩn Vận Hành 25 Workers Song Song & Fail-Safe Vững Chắc

1. **Back an toàn bằng phím cứng KEYCODE_BACK**:
   - Mọi thao tác lùi trang (từ Sửa tên về Sửa hồ sơ, từ Sửa hồ sơ về Hồ sơ) **BẮT BUỘC dùng `input keyevent 4`**.
   - Tuyệt đối CẤM tap tọa độ góc trên bên trái (`75, 150` hay `72, 148`) vì nếu màn hình vô tình ở tab khác hoặc đã back về Profile sớm, cú tap đó sẽ rơi trúng icon "Tìm bạn bè".

2. **Switcher Preflight Guard & Bẫy Méo Dấu OCR Trên Bottom Sheet**:
   - Trước khi sửa tên, bắt buộc đọc `@username` trên Profile.
   - Nếu `active_user != target_user`: Mở Switcher tại `(500, 140)`.
   - **Bẫy méo dấu OCR nghiêm trọng trên Switcher TikTok v47 (Galaxy S7)**:
     * Trên màn hình Chuyển đổi tài khoản (Bottom Sheet), font chữ TikTok kết hợp độ phân giải S7 khiến WinRT OCR đọc chữ `Chuyển đổi tài khoản` bị méo thành `chuydn ddi tai khoan` (hoặc `Chuydn ddi täi khoån`).
     * Regex cũ `"chuyen doi tai khoan"` hoặc điều kiện cứng `"tai khoan" in t and "chuyen doi" in t` BỊ XỊT 100%, khiến script xếp màn hình này vào `UNKNOWN`.
     * Khi rơi vào `UNKNOWN`, runner tự bấm Back đóng Switcher lại, dẫn đến tình trạng hàng loạt máy abort với lỗi `mo Switcher 3 lan, acc active van la @...`!
     * **Quy chuẩn Regex dung sai cao bắt buộc cho Switcher**:
       ```python
       if re.search(r"chuy\w{0,3}n\s*d\w{0,3}i|chuy\w{0,3}n.*kho\w{0,2}n|switch account|them tai khoan|add account", t):
           return "SWITCHER"
       if not (profile_has_user and profile_markers) and (("tai khoan" in t or "khoan" in t) and ("chuy" in t or "switch" in t or "them" in t)):
           return "SWITCHER"
       ```
   - Tìm kiếm `target_user` trong Switcher:
     * Nếu tìm thấy: Tap chọn để chuyển nick (chờ 6s).
     * Nếu chưa thấy: Cuộn sheet lên `swipe(SWIPE_SHEET_UP, 2)` (tọa độ `(540, 1500, 540, 900, 300)`).
     * Nếu KHÔNG tìm thấy sau khi cuộn: Bấm `keyevent 4` thoát an toàn và trả về `(None, False)`. **CẤM TUYỆT ĐỐI sửa đè lên nick đang active trên máy!**

3. **Chống Crash Toàn Cụm Khi Đơ ADB Transport**:
   - Khi chạy 25 workers đồng loạt, nếu 1 máy bị lỏng cáp hoặc ADB daemon trên điện thoại bị đơ, lệnh ADB sẽ văng `subprocess.TimeoutExpired`.
   - Hàm `adb(serial, *args, timeout=15)` bắt buộc bọc `try...except Exception: return ""` (hạ timeout xuống 15s).
   - Vòng lặp thu thập kết quả `as_completed([pool.submit(_worker, t) for t in targets])` bắt buộc bọc `try...except Exception: pass` cho từng `fut.result()` để sự cố của 1 máy không bao giờ làm sập cả batch.

4. **Cấu Hình Cronjob Hermes Tránh False Alert Timeout**:
   - Tác vụ 25 workers song song thực thi qua ADB + OCR thường mất từ 60s – 120s.
   - Cronjob của Hermes nếu để `deliver: 'origin'` sẽ bị gateway timeout sau 60s và bắn tin nhắn cảnh báo giả `provider timeout` về Telegram dù tiến trình nền vẫn hoàn tất 100%.
   - **BẮT BUỘC đặt `deliver: 'local'`** cho các batch watchdog nặng để tiến trình chạy ngầm im lặng, ghi log local và triệt tiêu tin nhắn spam báo ảo.

5. **Độ Trễ Khởi Động App (Splash / Cold Boot Latency Trap trên Samsung S7)**:
   - Trên các thiết bị phần cứng cũ (Galaxy S7), TikTok khởi động nguội (cold boot) thường mất từ 10–20s để vượt qua màn hình Splash ("TikTok" logo giữa màn hình đen/trắng).
   - **Cạm bẫy kịch bản tuyến tính (Linear Script)**: Dùng `time.sleep(5-6s)` cố định rồi tap ngay vào tab Hồ sơ sẽ khiến cú tap rơi vào màn hình Splash và bị nuốt chửng (dropped). Sau đó các cú tap tiếp theo rơi lệch vào Feed hoặc LIVE.
   - **Quy chuẩn State Machine bắt buộc**:
     * Nếu OCR thấy `UNKNOWN` (chỉ có chữ "TikTok" hoặc ít hơn 3 dòng text không có nút bấm): tiếp tục chờ 3-4s và chụp lại, CẤM tap mù tiếp theo.
     * Tự động dọn dẹp Search kẹt từ phiên trước: Nếu mở app lên mà thấy màn hình Search / Search Results (`id/hu0` hoặc thanh tìm kiếm có nút X), BẮT BUỘC bấm `keyevent 4` (Back) 2–3 lần để lùi về Feed/Home trước khi vào Profile.

6. **Kỷ Luật Phản Hồi Khi User Hỏi Số Worker**:
   - Khi User hỏi *"Đang chạy worker bn đó"*, Coordinator phải phân biệt chính xác ngữ cảnh tác vụ User đang quan tâm (ví dụ: số worker của watchdog đang cấu hình vs số worker của ca nuôi feed toàn farm), cấm trả lời lệch trọng tâm gây hiểu lầm.

## 7. Kiến Trúc Tách Rời Subprocess Runner vs ThreadPoolExecutor Trong Batch 25 Workers

1. **Cạm Bẫy Monolithic Inline Threading**:
   - Khi viết gộp toàn bộ logic State-Machine ADB + WinRT OCR chạy trực tiếp trong các worker thread của 1 script Python duy nhất (`tiktok_rename_rolling_watchdog.py`), trên Windows và môi trường MSYS/git-bash dễ xảy ra:
     * Tranh chấp tài nguyên PowerShell WinRT OCR (`ocr_boxes.ps1`) chạy đồng thời gây timeout hoặc xung đột file ảnh tạm (`rename_<serial>.png`).
     * Exception hoặc crash tiến trình con kéo theo toàn bộ pool dừng đột ngột hoặc bỏ dở vòng lặp kết quả.
     * Khó kiểm thử Canary độc lập trên 1 máy thật khi cần tái hiện hoặc verify.

2. **Giải Pháp Chuẩn Hóa Kiến Trúc Decoupled Subprocess**:
   - **Module CLI Runner độc lập (`do_rename_canonical_runner.py`)**:
     * Nhận tham số qua `argparse`: `--machine`, `--serial`, `--username`, `--name`.
     * Chịu trách nhiệm trọn vẹn: State-Machine OCR 35 bước, tự động chuyển tài khoản qua Switcher, gõ Unicode UTF-8 qua AdbKeyboard, xác nhận popup đổi tên 7 ngày, readback OCR nghiệm thu trên Profile.
     * Xuất đầy đủ artifact: ảnh nghiệm thu `m{m}_{u}_rename_confirmed.png` và JSON report `m{m}_{u}_rename_confirmed.json`.
     * Trả về exit code `0` kèm stdout `KET QUA: RENAMED` hoặc `KET QUA: ALREADY`.
   - **Watchdog Scheduler (`tiktok_rename_rolling_watchdog.py`)**:
     * Đóng vai trò phân phối và điều phối O(1): bốc danh sách máy rảnh không có device-lock và chưa đổi tên trong 7 ngày.
     * Gọi runner qua `subprocess.run(cmd, capture_output=True, text=True, timeout=320)` bên trong `ThreadPoolExecutor(max_workers=25)` (Timeout bắt buộc >= 300s–320s để các máy có danh sách tài khoản dài kịp cuộn sheet Switcher và tải OCR hoàn chỉnh).
     * Bọc `try...except Exception: pass` cho từng `fut.result()` trong `as_completed()`, chỉ ghi nhận vào `rename_natural_state.json` khi `ok and p.exists()`.
   - **Hiệu quả thực tế**: Cách ly hoàn toàn bộ nhớ và I/O giữa 25 máy. Máy nào đơ ADB tự rớt theo timeout 320s mà không làm nghẽn các máy khác, giúp farm chạy ổn định liên tục (thực tế đạt thông lượng 14 nick/lượt chạy).

## 8. Kỷ Luật Báo Cáo Canary (Tránh Báo Canary No-op / Ảo)
- **Tiêu chuẩn Canary Hợp Lệ**: Khi thực hiện nghiệm thu Canary trước khi chạy hàng loạt, kết quả Canary BẮT BUỘC phải là một ca thực thi trọn vẹn (End-to-End Success) trên máy có tài khoản đủ điều kiện, kiểm chứng trọn vẹn luồng thay đổi thực tế và trả về `verified=True`, kèm ảnh chụp nghiệm thu `MEDIA:<path>` đã qua soi mắt kiểm tra bằng `browser_vision`.
- **CẤM BÁO CANARY NO-OP**: CẤM TUYỆT ĐỐI báo cáo "Đã chạy Canary xong" khi kết quả runner thực chất chỉ là Skipped/No-op (ví dụ: máy test có active account không khớp target username và Switcher không có nick đó -> runner tự lùi ra an toàn trả về `(None, False)`). Trường hợp máy test không đủ điều kiện thi công, Coordinator phải lập tức bốc ngay máy khác có target account sẵn sàng để chạy thực nghiệm đầy đủ đến khi ra ảnh Profile nghiệm thu tên mới thành công.
- **Quy tắc Chống Báo Cáo Nhầm Trạng Thái**: Khi User hỏi *"Đâu kết quả chạy canary đâu?"*, Coordinator phải thừa nhận trung thực ngay lập tức nếu lượt chạy trước đó chỉ là no-op/skipped, đưa ra bằng chứng thực tế từ máy đủ điều kiện, không được cố thanh minh hay bao biện.

## 9. Cạm Bẫy False-Negative Abort ở Ô Nhập Tên (`NAME_EDIT`) do OCR Méo Dấu & Quy Chuẩn 2 Lớp (2-Tier Verification)

1. **Hiện Tượng Thực Tế**:
   - Khi gõ tên mới qua `AdbKeyboard` (`ADB_KEYBOARD_INPUT_TEXT` với Base64 chuỗi UTF-8), văn bản đưa vào Android EditText là **chuẩn xác 100%**, và bộ đếm ký tự của TikTok `N/30` trên giao diện hiển thị chính xác độ dài `len(NEW_NAME)`.
   - Tuy nhiên, trong ô nhập tên TikTok có con trỏ chuột nhấp nháy, chữ màu xám nhạt và font rendering của hệ thống Android khiến công cụ OCR Windows WinRT thường xuyên đọc sai các nguyên âm có dấu tiếng Việt (ví dụ: `Sơn Nấm` đọc thành `Sdn I\läm`, `Tươi Đậu` đọc thành `Tl-fdi DåU`, `Bùi Duy Phương` đọc thành `Bbi Duy Phi-fdng`, `Huy Tít` đọc mất chữ `Tít`...).
   - Nếu áp dụng ngưỡng so khớp cứng nhắc (`difflib ratio >= 0.70`), script sẽ ném ra lỗi `OCR khong xac nhan o nhap = ...` và tự động bấm "Hủy", khiến hàng chục máy trong batch 25 workers bị abort oan dù đã gõ tên hoàn toàn chính xác!

2. **Quy Chuẩn Kiểm Tra 2 Lớp An Toàn (2-Tier Verification)**:
   - **Lớp 1 (Ô nhập tên `NAME_EDIT`)**:
     * Kiểm tra bộ đếm ký tự: `ok_count = (count_match is not None and abs(int(count_match.group(1)) - expected_len) <= 1) or f"{expected_len}/30" in box`.
     * Kiểm tra text linh hoạt (chống rớt do méo dấu): Chỉ cần bộ đếm `ok_count` khớp chuẩn VÀ tìm thấy ít nhất 1 từ trong tên (`found_word = any(w in norm(" ".join(lines)) or any(difflib.SequenceMatcher(None, norm(l), w).ratio() >= 0.6 for l in lines) for w in words)`) HOẶC `difflib ratio >= 0.45` là BẮT BUỘC bấm "Lưu".
     ```python
     words = [norm(w) for w in NEW_NAME.split() if len(w) >= 2]
     found_word = any(w in norm(" ".join(lines)) or any(difflib.SequenceMatcher(None, norm(l), w).ratio() >= 0.6 for l in lines) for w in words)
     ratio = difflib.SequenceMatcher(None, norm(" ".join(lines)), NEW_NAME_NORM).ratio()
     ok_text = (any(is_target(l) for l in lines)
                or NEW_NAME_NORM in norm(" ".join(lines))
                or ratio >= 0.45
                or found_word)
     if not (ok_text and ok_count):
         tap(XY_NAME_CANCEL, 2)
         raise Abort(f"OCR khong xac nhan o nhap = '{NEW_NAME}' ({expected_len}/30) -> Huy, KHONG Luu")
     ```
   - **Lớp 2 (Chốt chặn tối cao tại Profile)**:
     * Sau khi bấm Lưu, máy bắt buộc quay về Profile và OCR đọc lại dòng tên nằm ngay trên `@username`.
     * Trên Profile, tên được hiển thị bằng font chữ lớn, in đậm, tương phản cao và không có con trỏ nhấp nháy nên OCR đọc cực kỳ chuẩn xác.
     * Lúc này mới áp dụng ngưỡng so khớp nghiêm ngặt (`difflib ratio >= 0.75` và `is_target_user`) để quyết định `verified=True`.


