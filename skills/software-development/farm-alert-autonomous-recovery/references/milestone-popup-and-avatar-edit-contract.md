# Milestone Popup Dismissal & Profile Edit Button Contract

## 1. Context & Root Cause

Trong các ca chạy upload Avatar hoặc chuyển tài khoản (`ACCOUNT_SWITCHER`), các lỗi phổ biến thường gây ra cảnh báo giả hoặc chặn tiến trình là:

1. **`[ACCOUNT_SWITCHER_FAILED] open_switcher failed: SWITCHER_NOT_CONFIRMED`**:
   - **Hiện tượng**: Khi TikTok mở màn hình Hồ sơ cá nhân, một popup milestone/chúc mừng (ví dụ: *"Tổng số lượt thích: ... đã nhận tổng cộng N lượt thích cho tất cả video [OK]"* hoặc *"Bạn đang nghĩ gì [Xong]"*, *"Tám chuyện nào"*) hiển thị đè lên toàn bộ profile header.
   - **Hậu quả**: `_find_profile_name` và `open_switcher` không thể tìm thấy anchor định danh tài khoản hoặc bị popup chặn touch event, văng lỗi `SWITCHER_NOT_CONFIRMED` và gắn cờ `MANUAL_REVIEW`.

2. **`[AVATAR_EDIT_OPEN_FAILED] Màn Sửa hồ sơ không mở & Bẫy tử huyệt "+ Thêm tiểu sử"`**:
   - **Hiện tượng**: Trên các tài khoản mới hoặc tài khoản chưa điền bio trên TikTok 46.x / 47.x, giao diện trang cá nhân không có nút chữ *"Sửa hồ sơ"* (Edit profile) chuẩn, mà hiển thị nút `+ Thêm tiểu sử` (hoặc `Add bio`).
   - **BẪY TỬ HUYỆT (FATAL TRAP)**: Nút `+ Thêm tiểu sử` / `Add bio` **CHỈ MỞ MODAL NHẬP TEXT TIỂU SỬ**, TUYỆT ĐỐI **KHÔNG MỞ** MÀN HÌNH SỬA HỒ SƠ / THAY ĐỔI ẢNH!
     * Nếu nhầm lẫn gộp `"Thêm tiểu sử"` / `"Add bio"` vào `_find_profile_edit_button`, script sẽ tap vào đây, mở modal Bio không có bất kỳ nút avatar nào.
     * `_wait_for_avatar_edit_screen` chờ 60s không thấy marker avatar -> trả về `edit_state = "missing"`.
     * Khi `edit_state == "missing"`, nếu code không gọi `adapter.back()`, toàn bộ các bước fallback sau đó (swipe, tap avatar circle, pencil, deeplink) đều thực thi trên nền modal Bio bị kẹt, gây timeout lặp lại và văng lỗi sau 4 phút lãng phí.
   - **VỊ TRÍ THỰC TẾ NÚT SỬA HỒ SƠ (RIGHT PENCIL BUTTON)**:
     * Trên layout này, nút Sửa hồ sơ thực chất là một nút icon Bút chì (`android.widget.Button`, không có text) nằm **ngay bên phải tên hiển thị** (Display Name).
     * Toạ độ chuẩn trên màn 1080x1920: `bounds=[782,516][926,600]`, Center `(854, 558)`.
     * Khi tap vào nút Bút chì bên phải tên này, TikTok mở **chuẩn 100% màn hình Sửa hồ sơ** với đầy đủ các mục: *"Thay đổi ảnh"*, *"Tên"*, *"Tên người dùng"*, *"Tiểu sử"*.
   - **BẪY NÚT BÚT CHÌ GÓC TRÁI TRÊN CÙNG (`_find_new_profile_pencil`)**:
     * Node ImageView tại toạ độ góc trái trên cùng (`[24,96][132,204]`, Center `(75..78, 150)`) **KHÔNG PHẢI** bút chì sửa hồ sơ.
     * Tap vào đây thực chất là nút Back / Exit khiến TikTok đóng ngay lập tức và văng về màn hình chính (LauncherActivity)!
     * **BẪY HỒI QUY (REGRESSION TRAP)**: Tuyệt đối CẤM gọi `_find_new_profile_pencil` trong `_find_profile_edit_button`. Nếu gọi, script sẽ tap nhầm nút Back, log `[PROFILE_EDIT] [METRIC] event=pencil_fallback matched=1 position=(75..78, 150)`, đẩy TikTok xuống background và văng `[AVATAR_EDIT_OPEN_FAILED]` trên hàng loạt máy. Selector nút sửa hồ sơ chỉ được phép nhận diện text `"Sửa hồ sơ"` / `"Edit profile"` hoặc Button icon bút chì bên phải tên (`right_pencil_button` tại `[782,516][926,600]`, tâm `(854, 558)`).

---

## 2. Giải Pháp Chuẩn Trên `state_machine.py`

### A. Auto-Dismiss Milestone Popup trong `_dismiss_simple_close_popup`

Trong `scripts/tiktok_workflow/state_machine.py`:

```python
# Bổ sung markers cho milestone popups:
if not any(marker in lowered for marker in (
    "email từ tiktok", "nhận email", "thêm vào nhật ký",
    "thường nhật", "nhật ký của bạn", "bài đăng thường nhật",
    "bạn có tin vui", "trà hay cà phê", "tám chuyện nào", "your story",
    "tổng lượt thích", "tổng số lượt thích", "bạn đang nghĩ gì",
)):
    return False

# Bổ sung label tap "OK" và "Xong" kèm structured telemetry:
for label in ("Đóng", "Close", "Để sau", "Not now", "OK", "Xong"):
    if adapter._tap_if_found(xml_text, text=label):
        logger.info("[POPUP] Đã đóng popup benign/milestone: %s", label)
        time.sleep(1)
        return True
```

**Vị trí chèn bắt buộc trước `open_switcher` trong `_handle_account_switcher`**:
```python
switcher_profile_xml = profile_xml
if hasattr(self.context.adapter, "dump_ui") and self._dismiss_simple_close_popup(self.context.adapter, switcher_profile_xml):
    time.sleep(1)
    switcher_profile_xml = self.context.adapter.dump_ui()
```

### B. Kỷ luật Selector nút Sửa hồ sơ & Auto-Back khi kẹt modal

1. **TUYỆT ĐỐI CẤM gán `"Thêm tiểu sử"`, `"+ Thêm tiểu sử"`, `"Add bio"` làm selector nút Sửa hồ sơ trong `_find_profile_edit_button`**:
   Chỉ tìm các nút sửa hồ sơ thực thụ:
   ```python
   for text in ("Sửa hồ sơ", "Chỉnh sửa hồ sơ", "Edit profile"):
       field = adapter._find_ui_element(xml_text, text=text)
       if field and field.get("center"):
           return field
       field = adapter._find_ui_element(xml_text, text_contains=text)
       if field and field.get("center"):
           return field
   ```

2. **Kích hoạt Selector Bút Chì Bên Phải Tên (`right_pencil_button`)**:
   Khi không có text "Sửa hồ sơ", duyệt tìm nút Button không text nằm bên phải tên:
   ```python
   left, top, right, bottom = map(int, bounds.groups())
   old_edit_button = (
       650 <= left <= 850
       and 450 <= top <= 620
       and 100 <= right - left <= 220
   )
   right_pencil_button = (
       750 <= left <= 950
       and 450 <= top <= 650
       and 80 <= right - left <= 220
       and 60 <= bottom - top <= 160
   )
   if old_edit_button or right_pencil_button:
       return {"center": ((left + right) // 2, (top + bottom) // 2)}
   ```

3. **Bắt buộc `adapter.back()` khi `_wait_for_avatar_edit_screen` trả về `"missing"`**:
   Khi thử mở nút edit hoặc modal mà không thấy màn hình Sửa hồ sơ (trả về `"missing"`), bắt buộc nhấn `adapter.back()` để thoát khỏi modal rác, đưa TikTok trở lại Profile root trước khi thử fallback tiếp theo:
   ```python
   if edit_state != "ready":
       if edit_state in ("unavailable", "missing"):
           if not adapter._tap_if_found(current_xml, text="OK"):
               adapter.back()
           time.sleep(1)
           current_xml = adapter.dump_ui()
   ```

---

## 3. Quy Trình Sinh Avatar Nữ Chuẩn (Female Avatar Workflow)

Khi User yêu cầu *"Sinh ava lại cho acc này theo đúng folder. Phải là ava gái"*:

1. **Truy vấn đúng Folder Video**:
   - Đối soát username trên `farm_account_info` (`tiktok_tracker.db`) và các file Excel `Tik*.xlsx` (`Tik7.xlsx`, `Tik8.xlsx`).
   - Lấy đúng `Folder Video` (ví dụ: `Folder Video = 551`). Kho video nguồn nằm tại `D:\video goc\<folder>` và kho dẫn xuất tại `D:\TIKTOK-videonuoinick\<folder>`.
2. **Trích xuất Face Candidates & Phân loại ViT ONNX**:
   - Dùng OpenCV Haar Cascade (`haarcascade_frontalface_default.xml`) trích xuất các khuôn mặt từ các clip MP4 trong folder với padding mở rộng (head + shoulders).
   - Dùng `AIFemaleFilter` từ `scripts/ai_channel_filter.py` (ViT ONNX model `model_quantized.onnx`):
     ```python
     from ai_channel_filter import AIFemaleFilter
     filt = AIFemaleFilter()
     res = filt.classify_frame(crop)
     # Yêu cầu: res['is_female'] == True và res['female_prob'] >= 0.8
     ```
   - Chọn candidate có `female_prob >= 0.95` và chất lượng/độ phân giải cao nhất.
3. **Lưu đồng bộ Avatar**:
   - Crop vuông tâm, resize 512x512 JPEG quality 95.
   - Lưu đồng bộ vào cả hai vị trí:
     * `D:\video goc\<folder>\avatar.jpg`
     * `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg`

---

## 4. Nuance Dashboard Badge vs Workbook Slot Mapping (Bản Chất Lệch Tik & Chống Báo Ẩu "Excel Tráo Đổi")

- **Hiện tượng**: User gửi ảnh dashboard tracking hiển thị badge ví dụ `M69 · T8`, nhưng khi tìm trên `Tik8.xlsx` dòng 69 lại thấy nick khác (`nhugiang352`), còn nick cần tìm (`lykimloan8741`) lại nằm ở `Tik7.xlsx` dòng 69. User đặt câu hỏi: *"Ủa trên này ghi Tik 8 mà sao lại ở Tik 7?"* và *"Mà sao excel lại tráo đổi v?"*.
- **BẢN CHẤT GỐC RỄ (CHÂN LÝ VẬN HÀNH)**:
  * **Master Excel KHÔNG HỀ tráo đổi**: Toàn bộ hệ thống Phone Farm phân bổ slot bất di bất dịch theo công thức toán học:
    $$\text{Slot (Tik)} = \text{STT} \pmod 8 \quad (\text{với } \text{kết quả } 0 \equiv 8)$$
    Đối với Máy 69:
    - STT 551 ($551 \pmod 8 = 7$ ➔ **Tik 7**): Nick `@lykimloan8741` (Folder video: 551 — Cà phê Việt).
    - STT 552 ($552 \pmod 8 = 8$ ➔ **Tik 8**): Nick `@nhugiang352` (Folder video: 552 — Kỹ năng sống).
    Tất cả các file: Master `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik7.xlsx`, `Tik8.xlsx` **luôn luôn đồng nhất 100% từ ngày khởi tạo**.
  * **Căn nguyên lệch Database (`farm_account_info`)**:
    - Vào ngày 17/09 lúc 00:00, crawler chỉ thấy 7 nick trên Máy 69 (`nhugiang352` là nick thứ 7 lúc đó).
    - Đến 01:32 sáng ngày 17/09, `@lykimloan8741` mới được reg bổ sung (nick thứ 8).
    - Script đồng bộ database khi import đã ghi nhận theo **thứ tự thời gian xuất hiện** (gán nick cũ `nhugiang352` vào Tik 7, nick mới `lykimloan8741` vào Tik 8) thay vì tính theo công thức chuẩn $\text{STT} \pmod 8$.
    - Đợt sync ngày 22/09 giữ nguyên bản ghi này trong bảng `farm_account_info` của SQLite `tiktok_tracker.db`.
    - Dashboard (`http://localhost:1905`) đọc trực tiếp từ `farm_account_info` nên hiển thị badge `M69 · T8`, gây hiểu lầm là Tik 8.
- **CẢNH BÁO PHẢN HỒI ĐIỀU PHỐI (CHỐNG KẾT LUẬN ẨU)**:
  * CẤM TUYỆT ĐỐI phán bừa *"do Excel bị tráo đổi"* (gây hoang mang về tính toàn vẹn của sổ cái Master).
  * Khẳng định rõ: **Excel Master luôn chuẩn xác theo công thức STT $\pmod 8$**. Database lệch do lưu vết import theo thời gian tạo nick cũ.
  * Xử lý O(1) hoặc Đồng bộ toàn farm:
    - Xử lý lẻ O(1): Cập nhật ngay bảng `farm_account_info` trong SQLite khớp với Excel:
      ```sql
      UPDATE farm_account_info SET tik = 7, updated_at = datetime('now', 'localtime') WHERE username = 'lykimloan8741';
      UPDATE farm_account_info SET tik = 8, updated_at = datetime('now', 'localtime') WHERE username = 'nhugiang352';
      ```
    - Đồng bộ chuẩn toàn bộ Farm từ File Tổng Master (`taikhoan_dat_v2_updated .xlsx`):
      Chạy script chuẩn:
      ```bash
      python D:/Taadaa/tools/sync_farm_account_info.py
      ```
      Script tự động backup DB và nắn chuẩn 100% mapping của cả cụm Kibe và Admin theo công thức toán học $\text{Tik} = ((\text{Folder}-1) \pmod 8) + 1$. Chi tiết quy trình xem tại skill `tiktok-workbook-slot-mapping` (`references/sync-sqlite-farm-account-info-master-mapping.md`).

---

## 5. Kỷ Luật Test Isolation Cho `closeout_gate.py`

- **Tạo dedicated test file**: File `tests/test_avatar_edit_and_milestone.py` chạy độc lập trong ~1 giây:
  ```bash
  pytest tests/test_avatar_edit_and_milestone.py -q
  # 11 passed in 1.07s
  ```
- **Bao quát test cases**:
  1. Test milestone popup dismiss với nút `OK`.
  2. Test milestone popup dismiss với nút `Xong`.
  3. Test playcore dialog dismiss.
  4. Test `_find_profile_edit_button` KHÔNG match `+ Thêm tiểu sử` (negative test chống bẫy Bio modal).
  5. Test `_find_profile_edit_button` KHÔNG match `Add bio`.
  6. Test `_find_profile_edit_button` MATCH nút Bút chì bên phải tên (`right_pencil_button`).
  7. Test fallback `Sửa hồ sơ` text button chuẩn.
  8. Test trả về `None` khi không có nút.
  9. Test `_find_profile_edit_button` KHÔNG match ImageView top-left `[24,96][126,204]` (nút Back/Exit trap).
  10. Test telemetry observability: log `event=top_left_back_bypassed` và `event=layout_detector_matched`.

---

## 7. Kỷ Luật Sol Auditor Telemetry & Kiểm Tra Device Lock Trước Live Canary

1. **Yêu cầu Telemetry & Observability cho Sol Closeout Gate (>= 85/100)**:
   - Khi gỡ bỏ một fallback nhận diện hình học (như `_find_new_profile_pencil`), Sol Auditor sẽ trừ điểm mạnh về *Telemetry & Observability* nếu code chỉ âm thầm xóa/trả về `None` mà không có log sự kiện.
   - BẮT BUỘC:
     * Phát telemetry rõ ràng: `logger.info("[PROFILE_EDIT] [METRIC] event=top_left_back_bypassed matched=1")` khi phát hiện node Back trap.
     * Khi match layout detector: `logger.info("[PROFILE_EDIT] [METRIC] event=layout_detector_matched detector=%s center=%s", detector_name, center)`.
     * Cập nhật cả `tests/test_avatar_edit_and_milestone.py` và các test file phụ thuộc cũ (như `tests/test_lock_inheritance.py` từng assert `(75, 150)`) để test suite luôn green 100%.

2. **Kỷ luật kiểm tra Device Lock & Sàng lọc Máy Rảnh trước khi chạy Canary theo yêu cầu User**:
   - Khi User ra lệnh: *"chạy canary các máy lỗi cho tao"*, CẤM TUYỆT ĐỐI lập tức bắn lệnh canary máy thật nếu chưa kiểm tra trạng thái nuôi acc của Farm!
   - BẮT BUỘC kiểm tra:
     ```python
     # Kiểm tra tiến trình nuôi acc đang chạy
     psutil.pid_exists(feed_pid)
     # Kiểm tra device locks từng máy trong cụm lỗi
     all_locked = {int(f.stem.split('_')[1].split('.')[0]) for f in Path("~/.codex/device-locks").glob("machine_*.json")}
     ```
   - **Quy tắc sàng lọc máy rảnh trong cụm lỗi (Unlocked Machine Canary Selection)**:
     * Dù ca nuôi acc đang chạy (ví dụ Ca trưa 12:08-13:00), hệ thống nuôi acc thường chỉ bốc một số máy hoặc chạy so le (staggered).
     * Khi cụm lỗi gồm nhiều máy (ví dụ: M218, M220, M222, M223, M238): một số máy (M223, M238) bị lock, nhưng các máy khác (M218, M220, M222) hoàn toàn UNLOCKED và online bình thường!
     * **Xử lý chuẩn**:
       + Nếu TẤT CẢ các máy lỗi đều bị lock: Trả lời binary status `Chưa xong hoàn toàn` kèm danh sách máy bị kẹt và chờ nhả lock.
       + Nếu CÓ ÍT NHẤT 1 MÁY ĐẠI DIỆN TRONG CỤM LỖI RẢNH (không có file lock): Kích hoạt ngay Canary trên máy rảnh đó (ví dụ: M218 cho lỗi `AVATAR_EDIT_OPEN_FAILED`), chạy background với `notify_on_complete=True`. Không được viện cớ "toàn farm đang bận" để đóng băng hay từ chối chạy canary.
   - **Kỷ luật cấu hình Remote Host Admin cho `run_tiktok_upload_avatar.ps1`**:
     * Khi chạy canary cho máy Admin (M200+): BẮT BUỘC export đầy đủ 2 biến môi trường trước lệnh PowerShell:
       ```powershell
       $env:ADB_SERVER_SOCKET = "tcp:192.168.110.119:5037"
       $env:TAADAA_HOST_CONFIG = "D:\Taadaa\machine-config\admin.yaml"
       & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1" -Tik <N> -ForceAvatarMachineList "<M>" -MaxParallel 1 -HostConfigPath "D:\Taadaa\machine-config\admin.yaml"
       ```
     * PowerShell `Start-Job` trong `run_tiktok_upload_batch.ps1` tự động kế thừa `$env:ADB_SERVER_SOCKET` từ session gọi, giúp `automation-core.adb.AdbClient` kết nối thông suốt sang remote ADB server mà không bị lỗi `device '<serial>' not found`.

---

## 6. Xử Lý Treo Proxy Readiness & Khởi Động Lại atx-agent Sau Soft Reboot

Khi thiết bị gặp sự cố giao diện (hoặc kẹt switcher) và kích hoạt `=== SOFT REBOOT RECOVERY (AUTOMATION-CORE) ===`:
1. **Lỗi `proxy watcher readiness was not published after reboot: proxy readiness timed out`**:
   - **Bản chất**: Sau khi reboot, kernel sinh `boot_id` mới tại `/proc/sys/kernel/random/boot_id`. Hàm `wait_for_proxy_ready` trong `automation_core/readiness.py` đợi file `~/.codex/device-readiness/<serial_hash>.json` cập nhật `boot_id` mới với trạng thái `proxy_ready`. Nếu trên máy trạm chưa chạy tiến trình watcher nền, hàm sẽ timeout sau 90-180s.
   - **Triage O(1) & Khắc phục**:
     * Kiểm tra ping mạng: `adb -s <serial> shell "ping -c 2 8.8.8.8"`.
     * Đọc boot_id: `adb -s <serial> shell "cat /proc/sys/kernel/random/boot_id"`.
     * Publish ngay trạng thái ready qua automation_core:
       ```python
       from automation_core.readiness import mark_proxy_state
       mark_proxy_state(serial, "proxy_ready", boot_id=boot_id)
       ```
2. **Khởi động lại `atx-agent` sau Reboot**:
   - Tiến trình reboot trên điện thoại sẽ kill tiến trình daemon `atx-agent` trên port 7912, khiến `capture_atx_session_ui` trả về XML length = 0 (`ATX_SESSION_UNAVAILABLE`).
   - Lệnh kích hoạt lại daemon ngay tức thì:
     ```bash
     adb -s <serial> shell "/data/local/tmp/atx-agent server -d"
     ```
   - Xác nhận ngay `curl http://127.0.0.1:7912/version` hoặc chạy test `capture_atx_session_ui` trả về XML > 20KB đầy đủ hierarchy.

---

## 8. Bẫy Trùng Avatar Placeholder Do Lịch Sử Copy & Quy Chuẩn Kiểm Tra Hash Trước Khi Up Avatar (Stale Avatar Collision)

- **Hiện tượng**: User kiểm tra ảnh đại diện sau khi upload hoặc nhìn màn hình hồ sơ và thắc mắc: *"Ủa từ từ. Mặt thằng này đang dùng cho nick máy 1 row 1 rồi mà. Có bị trùng kênh không vậy?"*.
- **Căn nguyên thực tế (Stale Placeholder Hash Collision)**:
  * **Kênh video KHÔNG trùng**: Các folder video hoàn toàn độc lập, khác biệt về nội dung clip (ví dụ: Folder 1 là kênh "Bếp Việt" nấu ăn, Folder 143 là kênh "Yêu Lu" thú cưng).
  * **File `avatar.jpg` bị TRÙNG HASH 100%**:
    - Vào thời điểm khởi tạo kho (ví dụ ngày 16/08), script cũ đã copy file `avatar.jpg` từ Folder 1 sang hàng loạt folder khác (gồm 16 folder: `1, 7, 15, 23, 39, 47, 71, 87, 103, 111, 119, 143, 151, 167, 183, 199`) làm ảnh placeholder tạm.
    - Tất cả 16 file này có cùng MD5 hash `4ff32d59bb9937afaf85cf62e3b2d24c` (mặt người nấu ăn của Kênh Bếp Việt).
    - Sau này khi tải bộ video mới về các folder này (ví dụ kênh thú cưng về Folder 143), pipeline chưa kích hoạt `_make_avatar.py` để sinh lại avatar từ các video clip mới.
    - Khi uploader chạy, nó bốc file `avatar.jpg` sẵn có đem tải lên, khiến tài khoản kênh thú cưng mang khuôn mặt người nấu ăn của Kênh 1.
- **Quy trình kiểm tra & xử lý bắt buộc**:
  1. **Đối soát Hash O(1)**: Trước khi up avatar hoặc khi user thắc mắc trùng mặt:
     ```python
     import hashlib
     from pathlib import Path
     h1 = hashlib.md5(Path("D:/video goc/1/avatar.jpg").read_bytes()).hexdigest()
     htarget = hashlib.md5(Path(f"D:/video goc/{folder}/avatar.jpg").read_bytes()).hexdigest()
     # Nếu htarget == h1 hoặc trùng với placeholder hash cũ -> BỊ TRÙNG PLACEHOLDER
     ```
  2. **Trích xuất lại avatar đại diện mới từ đúng kho video của folder**:
     ```bash
     python D:/Taadaa/Tiktok-video/scripts/_make_avatar.py <folder> --source-root "D:/video goc"
     ```
     Script sẽ dùng OpenCV + YOLOv8 quét các clip trong folder, tự động chọn frame đẹp nhất và crop 512x512 JPEG.
  3. **Đồng bộ cả 2 kho nguồn**:
     Lưu file mới đồng thời vào cả `D:/video goc/<folder>/avatar.jpg` và `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg`.
  4. **Upload đè lại avatar lên tài khoản**:
     Chạy lại runner avatar-only với `-ForceAvatarMachineList "<M>"` để ép thay thế avatar trên tài khoản TikTok bằng ảnh mới chuẩn.


