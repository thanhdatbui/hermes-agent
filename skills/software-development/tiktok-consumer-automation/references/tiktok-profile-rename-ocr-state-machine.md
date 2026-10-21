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
| **Nút Sửa hồ sơ** | `find_box("sua ho s")` hoặc `(72, 148)` | Nút chữ nhật 'Sửa hồ sơ' giữa màn hình (dưới Follower). Nếu không có text thì fallback về icon bút chì góc trên bên trái `(72, 148)`. CẤM tap tọa độ ma `(870, 558)`! |
| **BẪY TỬ HUYỆT (75, 150) & BẪY OCR "i ijä"** | `CẤM TAP (75, 150) SAU KHI LƯU` | Tuyệt đối CẤM tap `(72, 148)` hay `(75, 150)` để lùi trang sau khi Lưu (bắt buộc dùng keyevent 4 Back). Tại màn hình PROFILE khi chưa có text nút, bắt buộc fallback về icon bút chì `(72, 148)` để vào `EDIT_PROFILE`. |
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
- **Xử lý trễ Splash Screen trên Samsung S7 qua mạng 4G Proxy (Cạm bẫy abort sớm UNKNOWN):**
  * App TikTok khởi động cold-boot (`am force-stop` rồi launcher monkey) qua proxy 4G mất từ 25–30s để vượt qua màn hình Splash (logo TikTok / màn đen).
  * Nếu cài cứng `MAX_SAME_STATE = 4`, script kiểm tra mỗi 5–6s sẽ chạm mốc 5 lần liên tiếp ở step 5 (giây 25) và văng `Abort("ket o trang thai UNKNOWN 5 lan lien tiep")`, ngay trước khi app kịp vào Feed ở giây thứ 29.
  * **Giải pháp chuẩn hóa:** Bổ sung bộ đếm đệm `unknown_splash_count`: khi `state == "UNKNOWN"` và `len(lines) <= 3 and not errors_in(lines)`, cho phép splash tải tối đa 8 step (~35–40s) bằng cách reset `same = 1` trong thời gian splash, tránh abort oan khi app chỉ đang load chậm. Tuyệt đối không bấm phím `Back` trong thời gian này.
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
- **Bẫy Nút '+ Thêm tiểu sử' & Bẫy OCR 'i ijä' trên tài khoản chưa có Bio (Samsung S7 Pitfall 18/10/2026):**
  * Trên các kênh chưa nạp Bio (trống trơn), thay vì hiển thị nút chữ to *"Sửa hồ sơ"*, TikTok lại hiển thị nút to **`+ Thêm tiểu sử`** (`bounds=[350, 825][730, 909]`, WinRT OCR thường đọc thành `+ Thém tidU sd` hoặc `i ijä`).
  * Nếu regex tìm kiếm nút chỉ tìm `r"(sua|chinh sua|edit)\s*h[o0]"`, match sẽ trả về `None`, kích hoạt fallback `XY_EDIT_PENCIL = (75, 150)` và tap trúng icon Tìm bạn bè (`FindFriendsPageActivity`).
  * **Giải pháp khắc phục:**
    1. Bổ sung regex nhận diện nút `+ Thêm tiểu sử`: `r"(sua|chinh sua|edit)\s*h[o0]|(th[eéèêi]m\s+)?ti[ed][u\w]\s*s[ud]|i\s*ij[aä]"`.
    2. Thêm state `BIO_EDIT` trong state machine: Khi bấm vào `+ Thêm tiểu sử`, TikTok sẽ nhảy thẳng vào màn hình nhập tiểu sử (`0/160`). Script phải nhận diện state này, gõ Bio tiếng Việt (nếu có), bấm `Lưu` (hoặc Back) để quay lại màn hình `Sửa hồ sơ` tiếp tục đổi Tên.
    3. Đổi vĩnh viễn toạ độ fallback `XY_EDIT_PENCIL` từ `(75, 150)` sang khối giữa màn hình `(300, 985)` hoặc `(540, 867)`, tuyệt đối CẤM tap `(75, 150)`.
- **Chiến Lược Tách Runner Độc Lập Cho Watchdog 25 Workers:** Khi chạy cuốn chiếu 25 workers song song, tách toàn bộ State Machine OCR 35 bước thành CLI độc lập `do_rename_canonical_runner.py` và gọi qua `subprocess.run(timeout=320)`. Cách ly triệt để bộ nhớ, chống tắc nghẽn thread pool khi nhiều máy cùng gọi WinRT OCR `ocr_boxes.ps1`, giúp farm cuốn chiếu ổn định vượt mốc hàng chục nick/phiên.
- **Bẫy Tọa Độ Ma (870, 558) vs Icon Bút Chì Header (72, 148) (Sự cố 20/10/2026):**
  * Trong runner đổi tên, nếu đặt tọa độ fallback `XY_EDIT_PENCIL = (870, 558)` (khoảng trống bên phải màn hình) và cài điều kiện `b[1] >= 680` để Abort vì "sợ tap mù", khi gặp giao diện TikTok không có text button "Sửa hồ sơ", runner sẽ tap vào khoảng trống, màn hình giữ nguyên ở `PROFILE`. Sau 5 lần lặp cùng trạng thái, runner kích hoạt `same > MAX_SAME_STATE` và văng `exit_2` trên hàng loạt máy.
  * Tọa độ icon bút chì mở màn hình Sửa hồ sơ ở góc trên bên trái trên giao diện chuẩn Samsung S7 là `(72, 148)` (đã được kiểm chứng thực tế và soi mắt qua vision). BẮT BUỘC dùng:
    ```python
    XY_EDIT_PENCIL = (72, 148)
    btn = find_box(boxes, r"(sua|chinh sua|edit)\s*(h[o0]|profile)")
    xy = center(btn) if btn else XY_EDIT_PENCIL
    tap(xy, 4)
    ```
    tuyệt đối không dùng tọa độ ma `(870, 558)` hoặc cấm tap mù cứng nhắc khiến máy tự abort vô cớ.

---

## 11. Regression Gate Đa Giao Diện Cho Runner Đổi Tên (Multi-Layout Regression Gate)

### 3 Biến Thể Giao Diện Profile Cần Tương Thích Đồng Thời (Không Hardcode 1 Kiểu):
1. **Biến thể A (Giao diện nút to trung tâm):** Có text button rõ ràng `"Sửa hồ sơ"` / `"Edit profile"` ở giữa màn hình (dưới chỉ số Follower). Cơ chế: Quét OCR regex `r"(sua|chinh sua|edit)\s*(h[o0]|profile)"` và tap tâm box (`center(btn)`).
2. **Biến thể B (Giao diện thanh Header S7):** Không có text button ở giữa, nút mở màn Sửa hồ sơ là **icon cây bút chì màu trắng góc trên bên trái** header `(72, 148)`. Cơ chế: Fallback tự động khi `btn is None` -> tap `(72, 148)`.
3. **Biến thể C (Vào từ Chip / Nút Bio):** Tài khoản chưa có Bio hiển thị chip `+ Thêm tiểu sử` (`+ Thém tidU sd`) hoặc nút sửa cạnh bio. Cơ chế: Regex `r'\+\s*th[eé]m|tid\w{0,2}\s*s|th[eé]m\s*ti|tieu\s*su'` để vào thẳng màn sửa.

### Biến Thiên Tọa Độ Trong Màn Sửa Hồ Sơ (`EDIT_PROFILE`):
- Vị trí dòng `Tên` (Nickname) dao động giữa các bản TikTok: có máy ở `Y ≈ 680`, máy ở `Y ≈ 730–770`.
- **CẤM hardcode tọa độ Y cố định:** Dùng hàm ghép đôi hàng ngang `edit_rows(boxes)`: tìm box nhãn `norm(t) == "ten"` bên trái (`x < 400`), sau đó lấy `cy = center(ten_box)[1]` để tìm giá trị text hoặc tap vào tọa độ `(XY_NAME_ROW[0], cy)` để khớp đúng ô nhập tên của từng máy.

### Quy Trình Kiểm Thử Hồi Quy Trước Khi Rollout (Regression Verification Checklist):
1. **Chạy test suite logic offline:** `pytest tools/tests/test_do_rename_m8.py` (48 tests) bảo đảm các hàm `norm`, `compact`, `classify`, `nickname_on_profile`, `edit_rows` pass 100% trên toàn bộ các sample OCR từ nhiều máy khác nhau.
2. **Kiểm tra cú pháp:** `python -m py_compile D:/Taadaa/tools/do_rename_canonical_runner.py`.
3. **Canary 1 máy thật rảnh:** Chạy thử trên 1 target thật, trích xuất screenshot `MEDIA:<path>.png` và dùng `browser_vision` soi mắt kiểm tra đúng tên mới trước khi kích hoạt watchdog hàng loạt.


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

---

## 8. Kiến Trúc Cụm Kép: Cụm Kibe (Máy 1–80) vs Cụm Admin (Máy 201–280)

### Phân Định Phần Cứng & Kết Nối Vật Lý:
- **Cụm Kibe (Máy 1–80):** Cắm cáp USB trực tiếp vào host local Kibe PC (`C:\Program Files (x86)\xiaowei\tools\adb.exe`).
- **Cụm Admin (Máy 201–280):** Cắm cáp USB trực tiếp vào máy tính Admin-PC (`192.168.110.119`, ~77 máy online).
- **CẤM TUYỆT ĐỐI:** Chạy ADB local từ Kibe PC để điều khiển dải máy 201–280 (không tìm thấy thiết bị, gây timeout).

### Đồng Bộ & Thực Thi Song Song 2 Cụm (Tổng 50 Workers):
1. **Dữ liệu tài khoản dùng chung:**
   - File sổ cái `D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx` chứa đầy đủ thông tin mapping cả 160 máy (sheet `Accounts`: Máy 1–80 và Máy 201–280).
2. **Cơ chế triển khai trên Admin-PC:**
   - Đồng bộ module `do_rename_canonical_runner.py` và `ocr_boxes.ps1` sang `Admin-PC` qua OneDrive (`Taadaa_Sync_Shared/hermes-cron/scripts`) hoặc SSH (`tools/admin_ssh.py`).
   - Khởi chạy runner/watchdog trên chính `Admin-PC` để tận dụng USB bus và WinRT OCR cục bộ của Admin-PC.
   - Khi chạy song song: Host Kibe chạy 25 workers cho cụm 1–80; Host Admin chạy 25 workers cho cụm 201–280 $\rightarrow$ Tổng công suất đạt **50 workers song song** toàn farm mà không gây nghẽn bus USB hay quá tải CPU.

---

## 9. Cấu Hình Cronjob Tự Động Báo Cáo Về Phiên Chat (`deliver='origin'`)

- Khi User yêu cầu: *"Để im session này tới ca rảnh chạy tiếp rồi báo cáo ở session này"*:
  * Cấu hình cronjob: `cronjob(action='update', job_id=..., deliver='origin')`.
  * **Điều kiện tiên quyết bắt buộc:** Job BẮT BUỘC phải có `no_agent=True` để chạy theo mô hình classic script watchdog.
  * **Cơ chế im lặng khi không có việc (Watchdog Silence):** Khi farm đang trong ca nuôi feed (`is_feed_active() == True`) hoặc không có máy rảnh, script gọi `sys.exit(0)` với stdout rỗng. Scheduler Hermes sẽ im lặng hoàn toàn, không spam tin nhắn rác vào chat.
  - **Cơ chế bắn tin khi có kết quả:** Khi có máy hoàn tất đổi tên, script in kết quả với `print(..., flush=True)` và stdout này sẽ được daemon Cron tự động đẩy thẳng về phiên chat Telegram của User mà không bị timeout 60s như chế độ agent LLM.

  ---

  ## 10. Mở Rộng Cập Nhật Tiểu Sử (Bio) Qua OCR State Machine & 4 Cạm Bẫy Tử Huyệt (18/10/2026)

  Khi mở rộng `do_rename_canonical_runner.py` để hỗ trợ cờ cập nhật tiểu sử song song (`--bio "<text>"`), các cạm bẫy sau đây đã xuất hiện trong thực chiến và được chuẩn hóa:

  ### 1. Bẫy Early Return Thoát Sớm Khi Tên Đã Khớp (The Premature Return Trap)
  - **Hiện tượng:** Nick đã có Tên hiển thị chuẩn từ trước (`is_target(name) == True`). Runner kiểm tra điều kiện thấy tên khớp liền lập tức `return "ALREADY"`, bỏ qua hoàn toàn việc đổi Bio dù có truyền tham số `--bio`!
  - **Khắc phục:** Bắt buộc kiểm tra đồng thời cả 2 điều kiện trước khi return:
    ```python
    if is_target(name):
        if not TARGET_BIO or bio_saved:
            return "RENAMED" if saved else "ALREADY"
        print(f"   Ten da dung ('{name}'), tiep tuc vao man Bio de cap nhat...")
    ```

  ### 2. Chạm Trực Tiếp Dòng Bio Trên Profile (Direct Bio Row Tap)
  - **Hiện tượng:** Tại màn hình Profile (`state == "PROFILE"`), nếu cố bấm icon cây bút chì `(870, 558)` hoặc các nút header lệch vị trí, runner dễ bấm hụt hoặc mở nhầm giao diện tìm bạn bè.
  - **Khắc phục:** Dò tìm trực tiếp box text của tiểu sử hoặc nút `+ Thêm tiểu sử` trên màn hình Profile và tap trực tiếp:
    ```python
    bio_box = find_box(boxes, r"tieu su|chia se|goc nho|\+|diem|ke ban")
    xy = center(bio_box) if (bio_box and bio_box[1] > 750) else (500, 860)
    tap(xy, 3.5)
    ```
    Thao tác này đưa ứng dụng chuyển thẳng vào màn hình `BIO_EDIT` (`0/160` hoặc `EDIT_PROFILE`) mà không cần qua các menu trung gian.

  ### 3. Bẫy Sai Action / Extra Key Của AdbKeyboard (The Silent Broadcast Failure Trap)
  - **Hiện tượng:** Subagent đoán mò intent broadcast theo tutorial trên mạng: dùng `-a ADB_INPUT_B64 --es msg <base64>` hoặc `ADB_CLEAR_TEXT`. `AdbKeyboard` không hỗ trợ các action này nên **nuốt lệnh trong im lặng (silent no-op)**.
  - **Hậu quả nghiêm trọng:** Chuỗi bio mới không hề được gõ vào, trong khi lệnh backspace vẫn chạy làm xóa cụt text cũ, lưu lại chuỗi rác cụt lủn (ví dụ chỉ còn chữ *"ngay"*), gây bức xúc tột độ cho Operator (*"Clmm bio mới của mày đây đó hả?"*).
  - **Quy chuẩn Action & Extra Key bất biến:**
    * Clear text: `am broadcast -a ADB_KEYBOARD_CLEAR_TEXT` kết hợp vòng lặp backspace `shell("input", "keyevent", " ".join(["67"] * 20))` 5 lần.
    * Input base64 text: BẮT BUỘC dùng `-a ADB_KEYBOARD_INPUT_TEXT --es text <BASE64_STRING>` (Extra key là `text`, CẤM dùng `msg`).

  ### 4. Bẫy False-Positive SWITCHER Do Phụ Đề Video Feed & Cơ Chế Launcher Recovery
  - **Hiện tượng:** Video Feed trên TikTok thường có phụ đề / caption chứa các từ *"khoảnh khắc"*, *"chuyện"*, *"thêm"*, *"tài khoản"*. Nếu regex nhận diện `SWITCHER` quá lỏng (như `chuy\w{0,3}n.*kho\w{0,2}n` hoặc `("khoan" in t and "them" in t)`):
    * State machine sẽ nhận diện nhầm video Feed thành màn hình `SWITCHER`!
    * Runner thực hiện cuộn sheet và tap phím Back liên tục trên video Feed, khiến TikTok bị đóng và văng ra màn hình Home (Android Launcher).
  - **Khắc phục:**
    1. Siết chặt regex `SWITCHER` thành cụm từ nguyên vẹn: `r"chuyen doi tai khoan|switch account|them tai khoan|add account"`.
    2. Bổ sung cơ chế **Launcher Recovery** trong trạng thái `UNKNOWN`: Nếu các dòng OCR phát hiện đang ở launcher (`photos`, `chrome`, `gmail`, `cai dat`, `launcher`), tự động phát lệnh monkey intent khởi chạy lại TikTok (`shell("monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")`) để phục hồi luồng thay vì bấm Back vô ích.
