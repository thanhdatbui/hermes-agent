# Bio uniqueness and deployment audit

## Failure pattern

A runner can rename accounts successfully while writing the same bio to every account. The dangerous version is a module-level constant such as `BIO_B64`, or a pool helper that calls `random.choice()` independently for each account without a uniqueness contract. A successful rename/OCR result does not prove that the bio was changed or was unique.

## Required contract

1. Treat display-name and bio as separate acceptance items. A `RENAMED` result must not imply `BIO_SAVED`.
2. Never hardcode a single bio payload in the runner. Generate the bio from a pool using an account-scoped seed (`username`, slot, or stable account id plus batch/date salt).
3. Enforce uniqueness within the active batch. A random pool is not sufficient: maintain a `used_bios` set or deterministic permutation and select a new candidate when a collision occurs.
4. Persist the selected bio in the per-account result/state record before the UI action, then verify the final profile OCR contains the selected bio (allowing known OCR accent distortion).
5. When replacing a hardcoded implementation, audit every executable copy and launcher/runtime mirror before restarting cron. A fixed source file does not fix a stale deployed runner.
6. If duplicate output is discovered, pause the producer watchdog first, preserve the affected reports, and repair the source/deployment path before resuming. Do not rerun a broad rename batch merely to repair bios.
7. A focused offline test must prove: same account seed is stable, two different account identities in one batch do not collide for the tested pool, and a duplicate candidate is rejected/reselected. A real-device canary is still required before claiming farm-wide completion.

## Evidence language

Report name, bio, and avatar as independent statuses. Use `BLOCKED/UNPROVEN` when OCR or the final screenshot does not verify the bio. Do not call a pool "100% unique" unless the implementation enforces and tests uniqueness for the actual batch scope.

## Session reproduction clues

When two fresh profiles show the exact same sentence, inspect the runner's bio-generation lines, deployed copies, and per-account reports. The presence of `BIO_EDIT` followed by the identical final OCR text is proof of a bio-generation/deployment defect, not proof that TikTok ignored input. A later module timestamp does not establish that the earlier batch used that module.

---

## Unexecuted Remediation & Stale On-Device Artifact Trap (User Directive 2026-10-19)

### Bối cảnh & Cạm bẫy "Bị chửi oan do không nạp đè thiết bị thật":
- Khi Operator phát hiện bot viết bio đại trà/rác và yêu cầu: *"Sửa lại các acc đã viết bio linh tinh cho tao"* / *"Viết bio kiểu hài hước nhé"*.
- **Lỗi chí tử của Agent**: Agent bóc tách danh sách acc bị ảnh hưởng, map Niche từ `Tik<N>.xlsx`, soạn 20 câu bio hài hước chuẩn vào file JSON (`humorous_niche_bios.json`), chạy unit test passed... **nhưng KHÔNG chạy tool nạp đè thực tế lên 20 điện thoại Android S7** (do vướng ca feed hoặc vội vàng chốt phiên khi nghe lệnh "Done").
- **Hậu quả bùng nổ**: Ngày hôm sau, khi watchdog đổi tên (`tiktok-rolling-rename-watchdog`) bốc trúng 1 trong 20 acc này (ví dụ Máy 35 `@martinbwahb`) để đổi tên hiển thị sang `Tiến Mã`, runner chụp ảnh Profile gửi về Telegram.
- Dòng bio rác cũ từ hôm trước (`Chia sẻ những khoảnh khắc đời thường...`) vẫn còn nguyên vẹn trên màn hình.
- Operator nhìn thấy ảnh chụp mới toanh kèm bio rác cũ và nổi giận lôi đình: *"Ai cho phép mày đi đặt bio v hqua t đã fix r mà???? Đụ mẹ lì thế"*.

### Quy chuẩn Thực thi Bắt buộc (Durable Remediation Invariant):
1. **Soạn JSON $\ne$ Hoàn thành**: Việc tạo file mapping / proposals JSON chỉ là 10% công việc chuẩn bị. Task sửa dữ liệu bậy CHỈ ĐƯỢC COI LÀ HOÀN TẤT khi đã chạy script nạp đè (hoặc xóa trắng) thành công trên 100% thiết bị vật lý thật và có ảnh chụp nghiệm thu sạch sẽ.
2. **Đối soát Dấu vết Hiện trường khi bị khiếu nại (Trace Audit O(1))**:
   - Khi Operator phản ánh *"Sao mày lại đi đặt bio đó nữa"*, KHÔNG được cãi mồm hay xin lỗi chung chung.
   - BẮT BUỘC mở ngay file JSON report của lần chạy vừa rồi (ví dụ `m35_martinbwahb_rename_confirmed.json`).
   - Kiểm tra bước `s10` (ảnh Profile lúc vừa mở app, TRƯỚC khi thực hiện bất kỳ lệnh sửa nào). Nếu bio rác đã xuất hiện ở `s10`, chứng minh bằng log: dòng bio đó là vết tích cũ còn tồn đọng do đợt trước chưa kịp nạp đè, hoàn toàn không phải do runner hiện tại vừa gõ vào.
   - Lập tức kích hoạt runner chuyên dụng nạp đè / xóa sạch bio trên máy đó ngay lập tức.
3. **Tuyệt đối tách rời Scope Đổi Tên vs Viết Bio**:
   - Task đổi tên CHỈ ĐƯỢC chạm vào Tên. Nếu runner lọt vào `BIO_EDIT`, BẮT BUỘC bấm Back `keyevent 4` thoát ra ngay lập tức, cấm lưu bất kỳ ký tự nào.

4. **Kỷ luật Xóa Trắng Bio Về Rỗng (`--clear-bio`) vs Chế Bio Hài Hước Độc Bản (User Directive 2026-10-19)**:
   - **Chỉ thị đanh thép của Operator**: *"Cái 2 của mày acc khác đã xài r. Đm t k biết mày nghĩ gì đồ dùng bio giống acc khác. Còn nếu mày chế ra bio hài hước khác acc khác đc thì t cho phép làm"*.
   - **CẤM TUYỆT ĐỐI DÙNG CHUNG BIO**: Một câu bio xuất hiện trên $\ge 2$ nick trong farm là dấu vết bot cực kỳ lộ liễu, có thể dẫn đến shadow-ban toàn cụm kênh.
   - **Phương án Ưu Tiên 1: Xóa trắng toàn bộ Bio về rỗng (`--clear-bio`)**:
     * Đây là phương án an toàn nhất và triệt để nhất khi phát hiện acc bị dính bio rác/trùng lặp.
     * Runner chạy với cờ `--clear-bio`: Focus ô tiểu sử, gửi `ADB_KEYBOARD_CLEAR_TEXT` + `keyevent 123` (MOVE_END) + `keyevent 67` (DEL) $\times 80$ + `ADB_KEYBOARD_CLEAR_TEXT`, không gõ bất kỳ ký tự nào, bấm Lưu.
     * Nghiệm thu qua WinRT OCR: Xác nhận dòng bio rác đã biến mất 100%, nút trên Profile quay về trạng thái sạch sẽ ban đầu `+ Thêm tiểu sử` (`[69, 716]`). Zero-Fingerprint an toàn tuyệt đối.
     * **Kiến trúc Batch Wiper đa luồng (`batch_clear_bios.py`)**:
       - Đọc danh sách acc bị dính bio rác từ file json.
       - Ánh xạ serial từ `taikhoan_run_safe.xlsx`, kiểm tra online qua `get_online_serials()`.
       - Đối soát an toàn qua `get_locked_machines()`, tự động bỏ qua các máy đang bận nuôi feed.
       - Dùng `ThreadPoolExecutor(max_workers=5)` gọi runner canonical với cờ `--clear-bio --name <name>` (timeout 240s) để dọn sạch song song an toàn, không làm nghẽn máy khác.
   - **Phương án 2: Chế Bio Hài Hước Độc Bản theo Niche**:
     * CHỈ ĐƯỢC PHÉP LÀM KHI: Mỗi nick có một câu bio độc nhất vô nhị (Unique Constraint), tuyệt đối không trùng với bất kỳ tài khoản nào khác trong toàn bộ database `Tik<N>.xlsx`.
     * Bám sát Niche nội dung video và mang văn phong dí dỏm, Gen Z, đời thường của người dùng thật.

---

## Phân Loại Profile An Toàn Khi OCR Rớt Ký Tự '@' (User Directive 2026-10-19)
- **Cạm bẫy**: Font chữ trên Android 8 và độ tương phản thấp khiến WinRT OCR thường đọc mất ký tự `@` trên username (ví dụ `@kamilhhs0tk` thành `kamiIhhsOtk`, `@martinbwahb` thành `marti n bwahb`).
- **Hậu quả**: Hàm `classify(lines)` nếu đặt điều kiện cứng `profile_has_user = any(l.startswith("@") for l in lines)` sẽ trả về `False`. App tiếp tục rơi xuống nhánh kiểm tra từ khóa thanh điều hướng đáy (*Trang chủ*, *Cửa hàng*, *Hộp thư*) và ngộ nhận Profile là `FEED`!
- Runner tưởng đang ở Feed nên liên tục tap vào tab Hồ sơ `(972, 1857)`, gây ra vòng lặp lặp lại 5 lần và abort với lỗi `ket o trang thai FEED 5 lan lien tiep` (`exit_2`).
- **Quy chuẩn phân loại Profile bền vững**:
  ```python
  def classify(lines):
      t = norm(" | ".join(lines))
      profile_has_user = any(l.startswith("@") for l in lines) or any(k in t for k in ("luot xem ho so", "ban dang nghi", "ban dang"))
      profile_markers = any(k in t for k in ("follower", "da follow", "daf", "thich", "dang follow"))
      if (profile_has_user and profile_markers) or (profile_markers and any(k in t for k in ("sua ho so", "them tieu su", "ban dang"))):
          return "PROFILE"
      if profile_markers and not any(k in t for k in ("danh cho ban", "de xuat", "for you")):
          return "PROFILE"
      # ... các kiểm tra EDIT_PROFILE, BIO_EDIT, NAME_EDIT, SWITCHER ...
  ```

---

## Đầy Đủ Dữ Liệu Từ Điển Âm Tiết Tiếng Việt trong `smart_name_generator.py`
- Bổ sung toàn diện các âm tiết và thanh điệu phổ biến: `diem` (Diễm), `nhu` (Như), `nguyet` (Nguyệt), `khuong` (Khương), `thuan` (Thuận), `hiep` (Hiệp), `dieu` (Diệu)... vào `TEN_MAP`.
- Thiếu các từ tố này sẽ khiến `parse_username_syllables()` bóc tách thiếu âm tiết trên các username có Họ-Tên hợp lệ (như `huynhdiem0806`), dẫn đến việc hàm đối soát `is_stereotyped()` nhận định sai là nick chưa chuẩn hóa và bốc ra xử lý không cần thiết.
