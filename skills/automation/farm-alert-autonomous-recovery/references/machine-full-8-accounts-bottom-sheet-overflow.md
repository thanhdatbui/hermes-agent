# MACHINE_FULL_8_ACCOUNTS Bottom-Sheet Overflow, Off-Grid Folder & False Alarm Triage

## Bối cảnh & Hiện tượng (Symptom)
Khi preflight reg bù (`ensure_row_accounts.py <row>`) chạy cho các máy thiếu slot Row N (thường là Row 5, 6, 7), hàng loạt máy bị văng lỗi:
`RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`
Và báo cáo tổng kết về Telegram hiển thị:
`- Máy N: Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)`

---

## Phân biệt 4 tình huống (Triage Mandate)
TUYỆT ĐỐI CẤM vội vàng kết luận máy đã có 8 tài khoản hay vội vàng backfill đè dữ liệu! Bắt buộc trích xuất ảnh dropdown hiện trường:
`D:/Taadaa/Tiktok_Reg/screenshots_social/<STT>_03_dropdown_*.png` và chạy WinRT OCR (`windows-native-ocr`) để đếm chính xác số username hiển thị:

### Tình huống 1: FALSE ALARM (Máy thực tế chỉ có 7 acc - Phổ biến nhất)
* **Dấu hiệu**:
  - OCR trên ảnh switcher đọc được đúng **7 username**.
  - Đối soát `taikhoan_dat_v2_updated .xlsx` cũng chỉ có đúng **7 dòng tài khoản** cho máy này.
  - Cả máy thật và Excel đều chưa đạt mốc 8 tài khoản (vẫn còn 1 slot trống để đạt mốc 8).
* **Căn nguyên kỹ thuật**:
  - Màn hình SM-G930F (1080x1920) khi chứa 7 tài khoản trong bottom sheet: 7 account rows chiếm trọn chiều cao màn hình (~1700px), đẩy mục *"Thêm tài khoản"* xuống dưới đáy hoặc ngoài viewport hiển thị.
  - Script `tap_add_account()` trước đây không có thao tác cuộn (`swipe up`), chỉ tìm kiếm ở attempt đầu rồi `break`.
  - Khi không tìm thấy nút *"Thêm tài khoản"*, fallback counter `_acc_count` duyệt `_root.iter("node")` với resource-id `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk", "ng8"]`. Do cả container layout (`lli` - text rỗng) và text node (`ng8`) đều khớp điều kiện, mỗi account bị đếm 2 lần (hoặc container của nút Thêm tài khoản bị đếm gộp thành account), ra kết quả `_acc_count = 14..15 >= 8`.
  - Script ngộ nhận máy đã full 8 acc và ném ngoại lệ sai.
* **Cách khắc phục chuẩn trong `social_reg_v1.py`**:
  1. Trong vòng lặp `attempt in range(3)` của `tap_add_account`, nếu `attempt < 2` và chưa thấy nút, bắt buộc swipe cuộn bottom sheet lên: `swipe(device_id, 540, 1500, 540, 800, 400)`.
  2. Chuẩn hóa `_account_names = set()` chỉ gom các node có text/desc phi rỗng và loại trừ các chuỗi điều hướng ("Thêm tài khoản", "Chuyển đổi", v.v.). Chỉ khi `len(_account_names) >= 8` mới coi là full.

---

### Tình huống 2: LỆCH EXCEL & BẪY "OFF-GRID FOLDER" GÂY REJECT DUPLICATE
* **Dấu hiệu**:
  - OCR trên switcher đọc được đủ **8 username** khác nhau.
  - Trong `taikhoan_dat_v2_updated .xlsx` có 8 acc (hoặc đã reg thành công ở run artifact trước đó như `tracking_result_stt<STT>_*.json`), nhưng `taikhoan_run_safe.xlsx` và file `TikX.xlsx` vẫn báo Slot X bị `None`.
* **Căn nguyên cốt lõi (Off-Grid Folder Modulo 8 Collision)**:
  - Mỗi máy vật lý có 8 folder tương ứng:
    - Kibe (1..80): `base = (M - 1) * 8 + 1` -> dải folder `base .. base + 7`.
    - Admin (201..280): `base = (M - 201) * 8 + 1` -> dải folder `base .. base + 7`.
  - Nếu nick thứ 8 bị gán nhầm Folder ngoài dải chuẩn (ví dụ M209 base folder 65..72, nhưng bị ghi Folder = 74):
    - `(74 - 1) % 8 = 1` -> Script đồng bộ `sync-safe-workbook.py` coi đây là tài khoản của **Slot 2** (Tik2).
    - Nhưng Slot 2 vốn dĩ đã có nick (`khanhkhoa0908`), nên thuật toán gán slot bị lệch, đẩy **Slot 6 (Folder 70)** thành `None`.
  - Khi `ensure_row_accounts.py 6` chạy reg bù:
    - Nó thấy Slot 6 trống nên bốc mail đi reg.
    - Nick đã tồn tại trên máy và đã có trong file Excel.
    - Khi merge kết quả, `apply_results()` phát hiện UID đã tồn tại ở dòng cũ -> log: `REJECT DUPLICATE UID: @... da ton tai tai dong ...! Khong ghi de vao dong ...` -> Lưu thành công 0 account và không thể lấp slot!
* **Quy trình xử lý chuẩn**:
  1. Kiểm tra dải Folder chuẩn của máy: `target_folder = (M - 201) * 8 + slot` (hoặc `(M - 1) * 8 + slot`).
  2. Sửa cột `Folder Video` trong `taikhoan_dat_v2_updated .xlsx` về đúng số folder chuẩn của slot thiếu.
  3. Cập nhật UID và Folder vào file `Tik<slot>.xlsx` tương ứng.
  4. Cập nhật trực tiếp `taikhoan_run_safe.xlsx` để slot thiếu nhận đúng ID.
  5. Chạy `ensure_row_accounts.py <row> --dry-run` để kiểm chứng toàn bộ máy đã sạch bóng slot trống.

---

### Tình huống 3: LỆCH EXCEL DO SÓT SLOT / MAIL GIỮ CHỖ (MÁY ĐỦ 8 NICK THẬT NHƯNG EXCEL TRỐNG SLOT)
* **Dấu hiệu**:
  - OCR trên switcher đọc được đủ **8 username** khác nhau (hoặc telemetry log ghi nhận `Máy đã có 8 tài khoản (...)`).
  - Dải Folder của máy chuẩn contiguous `base .. base + 7` (không dính off-grid folder), nhưng tại Slot X (ví dụ Slot 3), cột `ID` trong `taikhoan_dat_v2_updated .xlsx` bị `None` hoặc chứa mail giữ chỗ chưa kích hoạt.
  - Safe workbook `taikhoan_run_safe.xlsx` và `TikX.xlsx` hiển thị `UID = None`.
  - Runner `ensure_row_accounts.py <X>` thấy slot trống nên kích hoạt reg bù -> TikTok văng `MACHINE_FULL_8_ACCOUNTS` vì máy đã chạm trần 8 nick.
* **Căn nguyên**:
  - Nick đã đăng ký thành công từ các đợt chạy trước (có artifact `tracking_result_stt<STT>_*.json` trong runtime) nhưng bị rơi rớt trong khâu ghi workbook (do lock OneDrive hoặc lỗi `FAILED_SYNC_OSError`), hoặc chưa từng được sync sang file tổng.
* **Quy trình xử lý chuẩn & Pitfalls**:
  1. **Fast Run-Artifact Mining**: Tra cứu artifact cũ bằng pattern:
     `D:/Taadaa/runtime/<cluster>/artifacts/runs/social-batch-all/*/batch_*/stt_<STT>/tracking_result_*.json`
     để trích xuất: `tiktok_id`, `email`, `password`, `created_date`, `serial`.
  2. **BẪY ONEDRIVE LOCK / ATOMIC REPLACE TRÊN WINDOWS**:
     - Trong Python, pattern ghi đè tạm: `tmp = path.with_suffix('.tmp.xlsx'); wb.save(tmp); tmp.replace(path)` sẽ crash với `PermissionError: [WinError 5] Access is denied` do OneDrive client khóa file khi đang sync.
     - *Xử lý an toàn*: Tạo bản backup trước bằng `shutil.copy2(path, f"{path}.bak_{timestamp}")`, sau đó mở workbook bằng `openpyxl.load_workbook(path)` và lưu trực tiếp bằng `wb.save(path)`.
  3. **Cập nhật đồng bộ 4 bên**:
     - *Master Excel* (`taikhoan_dat_v2_updated .xlsx`): Điền `tiktok_id`, `password`, `email`, `pass_mail`, `created_date`, `serial` vào đúng dòng Folder thiếu.
     - *Sổ nuôi* (`Tik<slot>.xlsx`): Điền `tiktok_id` vào dòng tương ứng STT máy.
     - *Database SQLite* (`D:/Taadaa/data/tiktok_tracker.db`): `INSERT OR REPLACE` vào bảng `farm_account_info` và `account_mapping`.
     - *Blacklist* (`D:/Taadaa/Tiktok_Reg/data/registered_emails_blacklist.json`): Bổ sung email vào danh sách để tránh bốc lại mail đã có nick.
  4. **Đồng bộ chuẩn qua Scripts**:
     - Lưu ý: Script sync nằm ở `D:/Taadaa/tiktok-luot nuoi acc/scripts/`, **KHÔNG** nằm ở `D:/Taadaa/tools/`.
     - Chạy sync Tik: `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-tik-workbooks.py" --source "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" --tik-dir "D:/OneDrive/TaadaaData/kibe"`
     - Chạy sync Safe: `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" --source "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" --output "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" --tik-dir "D:/OneDrive/TaadaaData/kibe"`
  5. **Kiểm chứng nghiệm thu**:
     - Chạy `python D:/Taadaa/tools/ensure_row_accounts.py <slot> --dry-run`, xác nhận output: `Toan bo may da day du tai khoan! Khong can reg.`

---

### Tình huống 4: BẪY XÁO TRỘN SLOT / CHÈN ĐÈ TỊNH TIẾN (SLOT DISPLACEMENT / ACCIDENTAL OVERWRITE TRAP)
* **Hiện tượng & Bối cảnh (Case M36)**:
  - Máy thật đã có đủ 8 tài khoản TikTok (`{'phuong.anh.868', 'caoanh1109', 'machaomj66a', 'jasomntqsso', 'cyennffqko8', 'buidung27114', 'loankem5', 'ngocat106'}`).
  - Tuy nhiên trong `taikhoan_dat_v2_updated .xlsx`, tài khoản reg sau (`loankem5`, `ngocat106`) bị ghi đè nhầm vào slot giữa (Slot 5 / Folder 285) thay vì slot cuối (Folder 288), làm nick cũ (`cyennffqko8` reg 25/08) bị rơi khỏi sổ cái, trong khi slot cuối (Folder 288) bị bỏ trống `None`.
  - Runner `ensure_row_accounts.py 8` thấy Slot 8 trống nên bốc mail reg bù -> văng `MACHINE_FULL_8_ACCOUNTS` vì máy đã có đủ 8 nick.
* **Căn nguyên**:
  - Khi batch reg ghi nhận deferred tracking, nếu thuật toán phân bổ slot bốc nhầm dòng trống hoặc ghi đè dòng cũ, thứ tự slot bị xáo trộn.
* **Xử lý chuẩn**:
  1. Trích xuất WinRT OCR dropdown của máy để lấy danh sách đầy đủ các username đang active.
  2. Tra cứu toàn bộ các file `tracking_result_stt<STT>_*.json` của máy trong runtime để lấy đầy đủ thông tin xác thực (`email`, `password`, `created_date`) của nick bị mất khỏi Excel.
  3. Dựng lại thứ tự 8 nick theo đúng mốc thời gian tạo (`created_date`), ánh xạ chuẩn xác vào 8 Folder `base .. base + 7` của máy.
  4. Cập nhật đồng bộ Master Excel, các file `Tik<N>.xlsx`, database `tiktok_tracker.db` và chạy lại `sync-safe-workbook.py`.

---

## Quy trình Rà soát Toàn Farm (Full-Fleet Backfill Audit Protocol & Guard Safe Audit)
Khi User hỏi *"Còn máy nào lỗi không ghi như vậy không?"* hoặc cần rà soát toàn bộ farm:
- **CẢNH BÁO BẪY `[GUARD_DANGEROUS_ROOT]`**: TUYỆT ĐỐI CẤM dùng các lệnh Python có wildcard sâu trên runtime như `c_path.glob('*/batch_*/stt_*/tracking_result_*.json')` hay `runs.glob('*/batch_*/stt_*')`. Lệnh này quét toàn bộ cây runtime gây nghẽn terminal và bị guardrail chặn đứng.
- **Quy trình 3 bước O(1) chuẩn hóa**:
  1. **Bước 1: Quét nhanh Master Workbook (`taikhoan_dat_v2_updated .xlsx`)**:
     - Mở file Master của từng cluster (`kibe` và `admin`).
     - Lọc các dòng có `UID is None` hoặc chuỗi rỗng:
       `if not uid or str(uid).strip() == '' or str(uid).lower() == 'none'`
     - Kiểm tra trùng Folder theo từng máy: `Folder` trùng nhau trên cùng 1 máy báo hiệu lỗi va chạm slot.
  2. **Bước 2: Kiểm tra Runner Preflight theo dải Row 1..8**:
     - Chạy `python D:/Taadaa/tools/ensure_row_accounts.py <row> --dry-run` cho Row 1 đến 8 (kèm env `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml"` khi kiểm tra Admin).
     - Ghi nhận danh sách các máy bị gắn cờ "chưa có tài khoản".
  3. **Bước 3: Triage O(1) theo từng máy nghi vấn**:
     - Với mỗi máy bị phát hiện: đọc file `stderr.log` trong 20-30 run gần nhất của riêng thư mục máy đó (`D:/Taadaa/runtime/<cluster>/artifacts/runs/social-batch-all/<run_id>/batch_*/stt_<STT>/stderr.log`).
     - Nếu có lỗi `MACHINE_FULL_8_ACCOUNTS`: chắc chắn 100% máy đã đủ 8 nick nhưng bị sót ghi sổ (như M62, M36).
     - Chạy WinRT OCR trên `screenshots_social/<STT>_03_dropdown_*.png` và trích xuất `tracking_result_stt<STT>_*.json` của riêng máy đó để khôi phục credentials và backfill ngay lập tức.

### Kỹ thuật Fast Run-Artifact Mining (Khôi phục acc mà không chạm thiết bị)
Khi hàng loạt máy báo "Lệch Excel - Cần kiểm tra backfill":
- 90% các máy này đã đăng ký thành công ở các đợt chạy trước (1-2 ngày trước) nhưng bị rớt lại ở khâu ghi Excel.
- Tra cứu trực tiếp các file JSON artifact trong thư mục:
  `D:/Taadaa/runtime/<cluster>/artifacts/runs/social-batch-all/<run_id>/batch_*/stt_<M>/tracking_result_*.json`
- Trích xuất: `tiktok_id`, `email`, `created_date`, `serial`.
- Backfill ngay lập tức vào `taikhoan_dat_v2_updated .xlsx`, `Tik<slot>.xlsx` và `taikhoan_run_safe.xlsx`. Việc này giải quyết dứt điểm 100% lỗi lệch Excel trong vài giây mà không cần khởi động lại máy hay tốn email trong pool.

---

## Lưu ý về Xiaowei ADB & Remote Cluster (Admin Host)
- Executable `C:\Program Files (x86)\xiaowei\tools\adb.exe` trên Windows có cơ chế tích hợp tự động đọc biến môi trường `ADB_SERVER_SOCKET` (ví dụ `ADB_SERVER_SOCKET=tcp:192.168.110.119:5037`).
- Khi env này được export trong subprocess, mọi lệnh ADB gọi qua `adb.exe -s <serial> shell ...` tự động điều hướng sang server remote Admin mà không cần truyền cờ `-H` / `-P` thủ công.
- **BẪY INHERITANCE LEAK TỪ PROCESS CHA**: Nếu môi trường cha (như Kibe session) đã có `ADB_SERVER_SOCKET=tcp:localhost:5037`, script wrapper chạy batch Admin (như `ensure_row_accounts.py`) TUYỆT ĐỐI KHÔNG ĐƯỢC dùng điều kiện `if "ADB_SERVER_SOCKET" not in env`. Phải ghi đè thẳng: `if HOST_ID == "admin": env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"`. Nếu không ghi đè, toàn bộ process con sẽ gọi ADB về localhost Kibe -> báo `device '<serial>' not found` và sập hàng loạt ở `[01_open] TikTok not foreground after clean launch`.
- **GỠ KẸT SOCKET HUB USB 20 CỔNG (M261-M280)**: Khi cụm Hub 4 bị chập chờn nguồn hoặc vừa cắm lại cáp USB, các máy hiện `device` trong `adb devices` nhưng mọi lệnh `adb shell` đều bị timeout > 5s. Tuyệt đối CẤM `adb kill-server` trên remote Admin host. Chạy vòng lặp lệnh O(1) gỡ kẹt từng socket thiết bị:
  `"C:\Program Files (x86)\xiaowei\tools\adb.exe" -H 192.168.110.119 -P 5037 -s <serial> reconnect`
  Lệnh trả về `reconnecting <serial> [device]` trong < 0.5s, đưa toàn bộ cụm máy hoạt động bình thường ngay lập tức.
