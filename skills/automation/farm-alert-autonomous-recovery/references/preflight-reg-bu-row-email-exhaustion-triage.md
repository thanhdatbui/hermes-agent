# Preflight Reg Bù Row — Bẫy [07] "Cạn Mail" & [01_open] Triage Protocol

## 1. BẪY TỬ HUYỆT: [07] Tất cả N email của STT đã có TK TikTok

### Hiện tượng & Cảnh báo
Khi preflight reg bù (`ensure_row_accounts.py <row>`) chạy cho các máy thiếu slot, script báo lỗi:
`❌ [REGISTER ERROR] STT <N> thất bại do ngoại lệ: [07] Tat ca 3 email cua STT <N> da co TK TikTok`

**CỐT LÕI VẬN HÀNH (INVARIANT):**
- **NICK LÀ TÀI SẢN FARM**: Tuyệt đối CẤM vội vàng kết luận "cạn mail", cấm đòi nạp/mua thêm mail mới ngay lập tức!
- Thực tế 90% trường hợp này là **NICK ĐÃ ĐƯỢC REG THÀNH CÔNG TỪ TRƯỚC VÀ ĐANG ĐĂNG NHẬP TRÊN THIẾT BỊ**, nhưng bị rơi rớt dữ liệu khỏi `taikhoan_dat_v2_updated .xlsx` (do script bị crash trước khi ghi file, do lỗi format/merge Excel, hoặc do restore/clean xóa nhầm).
- Khi runner thấy slot trong `taikhoan_run_safe.xlsx` bị trống (`None`), nó tự bốc 3 email kế tiếp trong `gmail_clean_v2.xlsx` của STT đó ra để reg. Vì các email này thực chất đã được reg và đang nằm trong app TikTok trên máy, TikTok từ chối ở bước nhập email (chuyển sang màn hình "Chọn một tùy chọn đăng nhập" hoặc OTP login), khiến script văng ngoại lệ `[07]`.

### Hai mắt xích kỹ thuật gây rớt dữ liệu:
1. **Lỗi `FAILED_SYNC_OSError` nuốt chửng kết quả**:
   - Ở cuối batch reg (`_run_all_targets.py`), tiến trình gọi `write_deferred_results_sequential()` để ghi toàn bộ kết quả `tracking_result_*.json` vào sổ gốc `taikhoan_dat_v2_updated .xlsx`.
   - Nếu file Excel bị khóa bởi OneDrive sync hoặc một tiến trình Python/Excel khác đang mở vào đúng tích tắc đó, hàm ném ngoại lệ `OSError`.
   - Kết quả: Toàn bộ máy thành công trong batch bị đánh dấu `"workbook_write": "FAILED_SYNC_OSError"` trong `all_results.json`.
   - Máy thật đã đăng ký thành công và giữ nick đăng nhập, file `tracking_result_*.json` đã sinh đầy đủ UID và pass, nhưng sổ Excel gốc và safe workbook không có dữ liệu!
2. **Trùng Slot Folder (Modulo 8 Collision & Off-Grid Folder)**:
   - Sổ gốc lưu Folder video cho mỗi nick. Khi sync sang `taikhoan_run_safe.xlsx`, slot 1..8 được map theo công thức: `(Folder - 1) % 8 == target_slot`.
   - Nếu máy có 2 nick nhưng Folder cùng chia dư cho 8 (ví dụ Folder 121 và 129 cùng mod 8 = 1, chiếm Slot 1 / Tik1), runner sẽ thấy các Slot khác (Slot 5, 6, 7) bị `None` (trống giả).
   - **Bẫy Off-Grid Folder**: Khi một nick được gán số Folder vượt ngoài dải chuẩn `base..base+7` (ví dụ M216 base là `(216-201)*8 + 1 = 121..128`, nhưng nick bị ghi Folder `129`): `(129-1)%8 = 0` chiếm Slot 1 đè lên Folder 121, bỏ trống Slot 5/7 trong `taikhoan_run_safe.xlsx`.
3. **Bộ lọc candidate mail của `_detect_clean.py` / `social_reg_v1.py`**:
   - Khi log báo: `[07] Tat ca N email cua STT X da co TK TikTok` với số lượng N nhỏ (ví dụ N = 2 trong khi STT có 8 mail trong `gmail_clean_v2.xlsx`):
   - Script đọc `gmail_clean_v2.xlsx`, đối chiếu với danh sách email đã có trong sổ `taikhoan_dat_v2_updated .xlsx` (hoặc tracking cache). Các email đã có trong sổ sẽ bị skip (`-> skip <email>: da co TikTok trong tracking`).
   - Chỉ các email **chưa có trong sổ gốc** mới được đưa vào danh sách thử (`→ N email(s) se thu: [...]`).
   - Nếu các email này chính là nick đã reg thành công trên máy từ trước nhưng bị rớt khỏi sổ gốc (ví dụ `demeloschrenk8277@hotmail.com` đã reg thành `@nguyennhulinh8277` trên M216), TikTok khi submit email sẽ chuyển sang màn hình OTP login / "Email đã đăng ký" và abort ngay để tránh login đè, dẫn đến kết luận sai lầm là cạn mail.

### Vòng lặp kẹt cứng (Infinite Reg Loop):
- Preflight thấy slot trống giả trong `taikhoan_run_safe.xlsx` -> Tự kích hoạt reg bù.
- Script lấy các email còn lại được gán cho STT đó trong `gmail_clean_v2.xlsx`.
- Những email này chính là các email đã đăng ký thành công ở các đợt bị `FAILED_SYNC_OSError` (hoặc đã có nick).
- Khi script gõ email vào TikTok, TikTok chặn và chuyển sang màn hình mật khẩu / OTP login ("Email đã đăng ký").
- Script thử hết các email đều bị báo đã có nick -> văng lỗi `[07]`.

### Quy trình điều tra O(1) chuẩn hóa
1. **Kiểm tra slot thiếu thực tế**:
   Đọc `taikhoan_run_safe.xlsx` của cluster (Kibe hoặc Admin) tại STT <N>. Xác định chính xác các Slot (1..8) nào đang có giá trị `None`.
2. **Kiểm tra `all_results.json` trong runtime batch**:
   Kiểm tra các thư mục batch gần nhất tại `D:/Taadaa/runtime/<cluster>/artifacts/runs/social-batch-all/<timestamp>/all_results.json`:
   Tìm STT máy xem có cờ `"workbook_write": "FAILED_SYNC_OSError"` hay không.
3. **Kiểm chứng hiện trường trên thiết bị (WinRT OCR)**:
   - Trích xuất ảnh dropdown switcher gần nhất: `D:/Taadaa/Tiktok_Reg/screenshots_social/<STT>_03_dropdown_*.png` (hoặc chụp mới qua ADB / `inspect_machine.py`).
   - Chạy WinRT OCR:
     ```bash
     python "C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py" "D:/Taadaa/Tiktok_Reg/screenshots_social/<STT>_03_dropdown_<timestamp>.png"
     ```
   - Đọc danh sách tất cả username đang đăng nhập thực tế trên máy (ví dụ máy đã có 7 username).
4. **Đối soát 3 bên & Tìm nick rơi rớt (3-Way Reconciliation)**:
   - **Bên 1 (Thiết bị thật)**: Danh sách username từ WinRT OCR trên ảnh dropdown.
   - **Bên 2 (Sổ gốc Excel)**: Danh sách username/email của STT đó trong `taikhoan_dat_v2_updated .xlsx`. So khớp để xác định chính xác username nào đang chạy trên máy mà chưa có dòng trong sổ gốc.
   - **Bên 3 (Kho mail)**: Đọc `gmail_clean_v2.xlsx` của STT đó. Nhận diện email tương ứng với username "ma" qua hậu tố số (ví dụ `@nguyennhulinh8277` khớp với email `demeloschrenk8277@hotmail.com` tạo ngày 16/09).
5. **Truy vết thông tin tài khoản (Password/Email)**:
   - Tra cứu trong `D:/Taadaa/Tiktok_Reg/social_reg_log.txt`:
     Tìm dòng `[ACCOUNT_RECORD] STT: <N>` hoặc regex `\[ACCOUNT_RECORD\] STT: <N>.*`.
   - Tra cứu trong runtime JSON artifacts:
     `D:/Taadaa/runtime/<cluster>/artifacts/runs/social-batch-all/*/*/stt_<STT>/tracking_result_*.json`.
   - Tra cứu các bản sao lưu: `taikhoan_dat_v2_updated*.xlsx.bak*`.
6. **Chuẩn hóa Slot Folder video**:
   - Kiểm tra Folder của tất cả các nick trên máy: Folder hợp lệ phải nằm trong dải `(May - 201) * 8 + 1 .. (May - 201) * 8 + 8`.
   - Nếu có Folder vượt dải (ví dụ Folder 129 trên M216), chuyển về đúng slot còn trống (ví dụ Folder 127 cho Slot 7).
7. **Backfill phục hồi về đúng máy gốc**:
   - Ghi nhận lại tài khoản vào `taikhoan_dat_v2_updated .xlsx` đúng STT của máy gốc (tuyệt đối không gán sang máy khác gây ra tài khoản kí sinh).
   - Điền username vào đúng Slot trống (Row X) trong `taikhoan_run_safe.xlsx` và `TikX.xlsx`.
   - Cập nhật bảng `farm_account_info` và `account_mapping` trong `D:/Taadaa/data/tiktok_tracker.db`.
8. **Quy trình nghiệm thu sau khi fix Lock Excel & Backfill (Post-Fix Verification Checklist)**:
   - **Xác nhận Excel đã nhận**: Kiểm tra số dòng và giá trị các cột STT, Tik, TikTok ID, Email tại dòng mới trong `taikhoan_dat_v2_updated .xlsx`.
   - **Xác nhận Safe Workbook đã khớp**: Đọc `taikhoan_run_safe.xlsx` tại dải 8 dòng của STT máy đó, đảm bảo slot vừa backfill không còn mang giá trị `None`.
   - **Giám sát PID & Tiến trình nền đang chạy**: Trước khi chạy `ensure_row_accounts.py <row> --dry-run`, bắt buộc kiểm tra xem có tiến trình cha nào đang chạy hay không (`tasklist /FI "IMAGENAME eq python.exe"`). `ensure_row_accounts.py` có mutex lock: nếu tiến trình khác đang chạy (ví dụ đang reg Row 5), lệnh mới sẽ tự exit ngay (`Another ensure_row_accounts (PID ...) is already running, exiting`).
   - **Đánh giá tình trạng online sau sự cố Hub USB**: Khi Hub USB 20 cổng được cắm lại nguồn/cáp, chạy script đối soát O(1) giữa `adb devices` và `PROXYgandienthoai.xlsx`. Bóc tách rõ: số lượng máy đã online (ví dụ 79/80) và định danh chính xác máy duy nhất còn offline (ví dụ M255) do cáp riêng, tránh báo cáo nhầm là toàn bộ cụm vẫn kẹt.
9. **Xử lý slot còn thiếu thật sự & Tái phân bổ kho mail thừa (Zero-Cost Mail Reallocation)**:
   - Khi máy đã phục hồi đủ các nick có sẵn nhưng vẫn khuyết 1 slot (ví dụ có 7 nick, thiếu slot 7) và cạn mail chưa dùng:
     * **TUYỆT ĐỐI CẤM MUA MAIL MỚI NGAY KHI CHƯA RÀ SOÁT KHO THỪA**:
       1. **Quét mail chưa gán máy (`Machine = None`)**: Trong `gmail_clean_v2.xlsx`, tìm các dòng có cột 1 rỗng (`ws.cell(r, 1).value is None`). Đây là các mail đã mua trong các đợt trước nhưng chưa phân bổ (ví dụ các hàng unassigned do chèn dở).
       2. **Quét máy có thặng dư mail**: Đếm số mail chưa dùng theo từng máy (`email not in used_in_tiktok`). Nhiều máy có sẵn 5-7 mail dự phòng (ví dụ M255, M266), có thể điều chuyển an toàn sang máy đang cần.
       3. **Quét kho text lô mua cũ**: Tra cứu các file `D:/Taadaa/Hotmail/latest_bought_*.txt`, `hotmail_all_*.txt`, `hotmail_input.txt` tìm các mail chưa từng xuất hiện trong `taikhoan_dat_v2_updated .xlsx` của cả 2 cụm.
       4. **Kiểm tra Token Live Microsoft Graph**: Gọi `verify_graph_token(refresh_token, client_id)` từ `D:/Taadaa/tools/buy_hotmail.py` để đảm bảo HTTP 200 lấy được `access_token` hợp lệ trước khi cấp.
       5. **Tái gán vào `gmail_clean_v2.xlsx`**: Sao lưu file (`.bak_<timestamp>`), điền STT máy vào cột 1 của mail hợp lệ vừa tìm được.
       6. **Kiểm chứng Preflight**: Chạy `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/<host>.yaml" python D:/Taadaa/tools/ensure_row_accounts.py <row> --dry-run` để xác nhận `Can mua mail: 0 may` trước khi chạy reg bù thật.

10. **Bẫy lỗ hổng Slot giữa chừng & Chuẩn hóa Slot dồn toa (Contiguous Slot Packing Protocol)**:
    - **Hiện tượng (False Full Alarm)**:
      * Máy thực tế có 7 nick (thiếu 1 nick), preflight alert báo `Reg bù Row 7` (hoặc Row N).
      * Khi chạy `ensure_row_accounts.py 7 --machines <STT>`, runner báo: `[ADMIN] Row 7: Toan bo may da day du tai khoan! Khong can reg.` và exit 0 ngay lập tức, không chịu reg bù.
    - **Căn nguyên cốt lõi (Gapped Mapping Trap)**:
      * `ensure_row_accounts.py <row>` kiểm tra đúng 1 ô tại `slot_idx = row - 1` trong dải 8 dòng của STT đó trong `taikhoan_run_safe.xlsx`.
      * Nếu 7 nick hiện hữu bị xếp nhảy cóc (ví dụ Slot 4 để `None`, nhưng Slot 7 và 8 lại có nick `thanhsoc869` và `yenau9428`):
        - Kiểm tra Row 4: script thấy `None` -> báo thiếu Row 4.
        - Kiểm tra Row 7: script thấy `thanhsoc869` -> kết luận Row 7 đã đủ -> skip!
      * Dẫn tới tình trạng người vận hành tưởng máy thiếu Row 7, chạy lệnh Row 7 thì bị skip, trong khi máy thực tế vẫn khuyết 1 nick!
    - **Quy tắc chuẩn hóa Slot dồn toa (Contiguous Slot Packing)**:
      1. Khi máy có $K$ nick thực tế ($K < 8$): BẮT BUỘC sắp xếp $K$ nick lấp kín liên tục từ **Slot 1 đến Slot $K$** trong `taikhoan_run_safe.xlsx`.
      2. Các Slot còn lại từ **Slot $K+1$ đến Slot 8** BẮT BUỘC để `None` (cột 3 username `None`, cột 4 `0`, cột 5 `None`).
      3. Tuyệt đối KHÔNG ĐƯỢC để lỗ hổng ở giữa (gapped mapping). Toàn bộ slot trống phải dồn về cuối dải (Slot 8 nếu có 7 nick).
      4. Sau khi dồn toa chuẩn hóa: Slot cần reg bù duy nhất LUÔN LÀ **Row $K+1$** (ví dụ máy có 7 nick thì gọi `ensure_row_accounts.py 8 --machines <STT>`).
    - **Quarantine email lỗi từ chối bởi TikTok**:
      * Khi email bị TikTok từ chối ở bước reg vì tài khoản đã tồn tại bên ngoài (`DA CO tai khoan TikTok tren he thong` như `barbarajeanyhhy321@hotmail.com`):
      * BẮT BUỘC cập nhật ngay cột 11 của dòng email đó trong `gmail_clean_v2.xlsx`: `ws.cell(r, 11).value = 'used'`.
      * Việc này giúp bộ lọc `_detect_clean.py` loại bỏ vĩnh viễn email rác, không bao giờ bốc lại gây lỗi `[07]`.

11. **Tiêu chuẩn Bằng chứng Thị giác (Visual Evidence Invariant) khi Báo cáo Reg Hoàn tất — Bẫy ảnh Ngày sinh / Feed**:
    - **Cảnh báo lỗi nghiêm trọng (Bị User phản ứng "là sao tới đây đâu có gì chứng minh là đã xong")**:
      * Gửi ảnh màn hình chọn ngày sinh (DOB picker với hình bánh sinh nhật `216_07c_after_otp_*.png`): Đây CHỈ LÀ BƯỚC TRUNG GIAN trong luồng đăng ký, chưa hề chứng minh tài khoản được tạo thành công!
      * Gửi ảnh màn hình lướt Feed / For You Page (`216_09_result_*.png`): Màn hình này chỉ hiển thị video đề xuất chung, không có username hay dấu hiệu nhận diện tài khoản nào đang đăng nhập.
    - **BẰNG CHỨNG HỢP LỆ DUY NHẤT (The Only Valid Visual Evidence)**:
      * BẮT BUỘC gửi ảnh chụp màn hình **Tab Hồ sơ (Profile)** sau khi hoàn tất tạo nick: `D:/Taadaa/Tiktok_Reg/screenshots_social/profile_<stt>_after_ensure.png` (được runner tự động lưu tại bước `[10] Ensure profile name + tracking` và ghi nhận trong `tracking_result_stt<stt>_*.json` tại trường `proof_screenshot`).
      * Ảnh này BẮT BUỘC thể hiện đủ 4 dấu hiệu nhận diện rõ ràng:
        1. Username / handle mới tạo: `@<handle>`
        2. Tên hiển thị (display name)
        3. Bộ chỉ số mới toanh của nick vừa tạo: `0 Đã follow | 0 Follower | 0 Thích`
        4. Nút bấm `+ Thêm tiểu sử` hoặc `Sửa hồ sơ`, và thanh điều hướng chân trang đang active ở tab **Hồ sơ** (Profile).
      * Báo DONE mà không đính kèm đúng ảnh `profile_<stt>_after_ensure.png` bị coi là VI PHẠM GATE 6 (báo cáo mồm / chứng cứ ảo).

12. **BẪY OFF-GRID FOLDER COLLISION & LỆCH CỘT NGÀY TẠO / DEVICE ID (MÁY N >= 201 ADMIN RECOVERY PROTOCOL)**:
    - **Hiện tượng & Nhận diện**:
      * Máy thực tế trên thiết bị đã đăng ký đủ 8 nick (kiểm tra WinRT OCR dropdown có 7 nick + profile hiện tại = 8 nick).
      * Tuy nhiên trên `Tik1.xlsx` đến `Tik8.xlsx`, một số file bị ghi đè nick trùng, trong khi các file khác (ví dụ `Tik4.xlsx`, `Tik6.xlsx`) lại bị `MISSING_ID` hoặc `None`.
      * Trong `taikhoan_dat_v2_updated .xlsx`, 2 nick cuối cùng (nick 7 và 8) bị ghi số `Folder Video` nhảy vọt ngoài dải chuẩn `base..base+7`.
      * Ví dụ cụ thể (Máy 256):
        - Công thức base chuẩn của cụm Admin: `base = (May - 201) * 8 + 1`. Với Máy 256: dải chuẩn là `441 .. 448`.
        - Khi reg bù nick 7 và 8, script ghi nhầm Folder ngoài dải: `cout8602` ghi Folder `449`, `buingocyen2822` ghi Folder `450` (trùng dải base của Máy 257).
        - Khi tính modulo: `(449-1)%8 = 0` (Slot 1) đè vào `Tik1.xlsx`, `(450-1)%8 = 1` (Slot 2) đè vào `Tik2.xlsx`, để trống Folder 444 (Slot 4) và Folder 446 (Slot 6) thành `None`.
      * **Bẫy lệch cột ngày tạo & device ID**:
        - Khi ghi sổ gốc, cột `NGÀY TẠO` (cột 9) bị để `None`, chuỗi ngày `'2026-09-25 08:09:31'` bị đẩy sang cột 10 (`device ID`), và serial `'ce0716071d2cb11a02'` bị đẩy sang cột 11 (cột thừa).
    - **Quy trình phục hồi chuẩn 5 bước**:
      1. **Sao lưu an toàn**: Tạo snapshot timestamp vào `D:/OneDrive/TaadaaData/admin/archive_history/`.
      2. **Chuẩn hóa sổ gốc `taikhoan_dat_v2_updated .xlsx`**:
         - Dùng `atomic_workbook_update` từ `automation_core.workbook`.
         - Đưa số Folder về đúng slot còn trống trong dải chuẩn (ví dụ Folder 449 -> 444 cho Slot 4; 450 -> 446 cho Slot 6).
         - Kéo ngày tạo về cột 9, serial về cột 10, xóa cột 11.
      3. **Đồng bộ sổ phân phối `TikX.xlsx` (Cụm Admin)**:
         - Cập nhật đúng nick và số video đã đăng vào đúng file: `Tik1` trả về Slot 1 (`bhj20533v3s`), `Tik2` trả về Slot 2 (`rhacebfbp2n`), `Tik4` gán `cout8602` (Folder 444), `Tik6` gán `buingocyen2822` (Folder 446).
      4. **Re-sync Safe Workbooks**:
         - Chạy `TAADAA_HOST_ID=admin python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" --source "D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx" --output "D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx" --tik-dir "D:/OneDrive/TaadaaData/admin"`.
         - Chạy `python "D:/Taadaa/tools/sync_combined_safe_workbook.py"`.
      5. **Kiểm chứng Preflight**: Chạy `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml" python D:/Taadaa/tools/ensure_row_accounts.py <row> --machines <N> --dry-run` cho cả 8 rows để xác nhận 100% các hàng đều báo "Toàn bộ máy đã đầy đủ tài khoản! Không cần reg."

    - **12.1. Căn nguyên Code Defect trong `deferred_tracking_writer.py` & Cơ chế Dual Hard Guard (Chống Ghi Nhầm Tuyệt Đối)**:
      * **Lỗ hổng cốt lõi (Linear `max + 1` Bug)**:
        Trong `D:/Taadaa/Tiktok_Reg/scripts/deferred_tracking_writer.py`, hàm `_allocate_tracking_row` từng có logic:
        ```python
        if all(1 <= value <= MAX_TRACKING_ACCOUNTS_PER_MACHINE for value in used_tik):
            tik = next((v for v in range(1, 9) if v not in used_tik), None)
        else:
            tik = (max(used_tik) + 1) if used_tik else 1  # <-- LỖ HỔNG CHÍ MẠNG
        ```
        Khi máy dùng Folder Video thực tế (như `441, 442, 443, 445, 447, 448` trên M256), `used_tik` chứa các giá trị > 8. Nhánh `else` tự động kích hoạt và lấy `max(used_tik) + 1` = `448 + 1` = **`449`**, rồi nick tiếp theo là **`450`**. Việc cộng dồn tuyến tính này phá vỡ dải 8 slot (`441..448`), ghi lấn sang dải của Máy 257 (base 449) và làm trống giả Slot 4, 6.
      * **Cơ chế Dual Hard Guard khắc phục tận gốc**:
        1. **Lớp 1 — Thuật toán cấp phát chuẩn hóa dải 8 slot (`_allocate_tracking_row`)**:
           - Tự động tính toán `base_folder`:
             `base = ((stt - 201) if stt >= 200 else (stt - 1)) * 8 + 1`
             `c_folders = [base + i for i in range(MAX_TRACKING_ACCOUNTS_PER_MACHINE)]`
           - Script CHỈ ĐƯỢC PHÉP bốc các Folder còn thiếu nằm bên trong `c_folders` (ví dụ thiếu 444 và 446 thì bốc 444, sau đó 446).
           - Khi đủ 8 Folder trong dải, hàm trả về `None, None` (từ chối cấp phát tiếp), TUYỆT ĐỐI KHÔNG CÒN LỆNH `max + 1`.
        2. **Lớp 2 — Bộ chặn chặn đứng ghi đè ngoài dải (`_check_expected_row`)**:
           - Trước khi ghi bất kỳ kết quả deferred nào vào workbook, script kiểm tra:
             ```python
             base = ((stt - 201) if stt >= 200 else (stt - 1)) * 8 + 1
             if expected_tik and not (1 <= expected_tik <= 8 or base <= expected_tik <= base + 7):
                 blocker = f"OFF_GRID_FOLDER_{expected_tik}_FOR_STT_{stt}_BASE_{base}"
             ```
           - Nếu có kết quả mang Folder ngoài dải (ví dụ 449 trên Máy 256), script lập tức BLOCKED và từ chối ghi vào file Excel.
        3. **Đồng bộ `avatar_after_reg.py`**:
           - Chuẩn hóa công thức `fallback_folder` cho cả cụm Admin (`stt >= 200`): `((stt - 201) * 8) + 7`.
        4. **Kiểm chứng tự động trong CI/Test suite**:
           - `tests/test_deferred_tracking.py` có 2 test cases bắt buộc:
             `test_resolve_tracking_slot_allocates_canonical_folder_for_admin_machine` và `test_check_expected_row_blocks_off_grid_folder`.

13. **BẪY MỞ ACCOUNT DROPDOWN TRÊN PROFILE TIKTOK 46.X — MŨI TÊN CHEVRON VS TÂM CHỮ (TEXT CENTER TRAP), SINGLE-ACCOUNT TRAP & CỬ CHỈ SAMSUNG PAY**:
    - **Hiện tượng**:
      * Khi chạy preflight reg bù (`social_reg_v1.py`), máy dừng lại ở bước `[03_dropdown] Khong mo duoc account dropdown`.
      * Log ghi nhận: `✓ dropdown display-name (295, 322) text='bongbong0289' rid='com.ss.android.ugc.trill:id/sv6'` nhưng không mở được sheet switcher. Sau đó script fallback vào Settings nhưng cuộn 8 lần không thấy nút "Chuyển đổi tài khoản" và văng lỗi.
    - **Căn nguyên cốt lõi & Các bẫy tử huyệt**:
      * **BẪY MÁY CHỈ CÓ 1 TÀI KHOẢN (SINGLE-ACCOUNT TRAP)**:
        - Trên layout Profile mới của TikTok 46.6.3, khi thiết bị chỉ mới đăng nhập đúng 1 tài khoản (như M266 chỉ có nick Slot 1 `bongbong02892`):
          1. Header Profile: Hoàn toàn KHÔNG CÓ mũi tên dropdown chevron ▼ hay nút switcher (cả `sv6` lẫn `rz5` chỉ là TextView/Button tĩnh hiển thị tên, tap vào không có tác dụng).
          2. Trong `Cài đặt và quyền riêng tư` (Settings): Mục `"Chuyển đổi tài khoản"` / `"Thêm tài khoản"` HOÀN TOÀN KHÔNG TỒN TẠI (TikTok chỉ hiện mục này khi máy đã có từ 2 tài khoản trở lên). Ở đáy Settings chỉ có danh mục `"Đăng nhập"` với lựa chọn duy nhất là `"Đăng xuất"`.
        - *Cơ chế thêm nick thứ 2 trên máy 1 nick*: TikTok thiết kế bắt buộc phải qua flow: Vào Settings -> Bấm "Đăng xuất" (TikTok tự lưu session nick cũ vào One-tap login) -> Màn hình Profile trở về trạng thái Login/Signup có nút đỏ "Đăng ký" -> Tiếp tục flow chọn Email để reg nick thứ 2. Sau khi reg xong, TikTok mới kích hoạt switcher chứa cả 2 nick.
      * **BẪY CỬ CHỈ SAMSUNG PAY & SAFE SWIPE BOUNDS (SAMSUNG S7 1080x1920)**:
        - Trên dòng Samsung Galaxy S7 (SM-G930F/L/K/S), mép dưới màn hình `[300, 1893][780, 1920]` có tab vuốt nhanh Samsung Pay ("Thanh toán đơn giản") và gesture dock.
        - CẤM TUYỆT ĐỐI dùng tọa độ vuốt bắt đầu từ `y >= 1500` (như `swipe 540 1650 540 350`) hoặc tap vào vùng dock điều hướng `y >= 1790`. Lệnh vuốt quá sát đáy sẽ kéo thanh Samsung Pay / App drawer hoặc bấm Home, làm TikTok bị đẩy xuống background và văng ra LauncherActivity.
        - *Quy chuẩn Safe Swipe Bounds*: BẮT BUỘC dùng dải an toàn `y_start <= 1400` (khuyến nghị `1350`), `y_end >= 450` (khuyến nghị `500`), duration `300-350ms`.
      * **KỶ LUẬT GỬI ẢNH NGHIỆM THU (CHỐNG GỬI ẢNH MÀN HÌNH HOME ANDROID)**:
        - User duyệt lỗi bằng mắt qua ảnh (`MEDIA:`). CẤM TUYỆT ĐỐI gửi ảnh màn hình Home/Launcher của điện thoại làm bằng chứng hiện trường ứng dụng (tránh phản ứng gay gắt của User: *"Gửi tao màn home của máy chi v"*).
        - Bằng chứng gửi User BẮT BUỘC phải là ảnh giao diện app TikTok (Profile, Settings, Popup lỗi). Nếu app bị rơi xuống background, phải launch app lên foreground (`monkey -p ...`) trước khi screencap.
      * **BẪY TAP MÉP PHẢI cx_arrow vs TAP TÂM (cx, cy) CHO DISPLAY-NAME (sv6)**:
        - Vùng display-name (`sv6` hoặc `rz5`) là một TextView/Button kéo dài từ mép trái màn hình sang phải (`x1=39, x2=551`).
        - Nếu ép tap cứng mép phải `cx_arrow = max(x1 + 24, x2 - 28)` (tọa độ ~527), cú tap sẽ rơi vào khoảng trống ngoài lề (blank margin) của nút và không trigger click listener.
        - Cơ chế chuẩn: BẮT BUỘC tap tâm `(cx, cy)` trước (`(x1 + x2) // 2`, tương tự tọa độ đã giúp các máy như M267 mở dropdown thành công), sau đó nếu `_wait_account_dropdown_open` chưa bung mới thử fallback sang mép phải `(cx_arrow, cy)`. CẤM chỉ tap duy nhất mép phải.
      * **BẪY POPUP PHẦN THƯỞNG TIKTOK (SparkActivity)**:
        - Khi vào tab Profile, TikTok bung modal hybrid: *"Phần thưởng TikTok / Điểm của bạn / Bạn phải đủ 18 tuổi trở lên... [Hủy] [Đồng ý]"*. Popup này che toàn bộ giao diện khiến mọi tap vào display-name hay menu đều bị chặn. Cần bổ sung pattern `"phan thuong tiktok"`, `"diem cua ban"` và tap nút `"Hủy"` trong `dismiss_profile_overlays`.
      * **BẪY TREO UIAUTOMATOR STUB & LỖI KILL OPERATION NOT PERMITTED**:
        - `com.github.uiautomator` chạy dưới uid app (`u0_a191`), lệnh `kill -9` từ shell user sẽ văng lỗi `kill: Operation not permitted`.
        - BẮT BUỘC dùng lệnh quản lý gói: `adb shell "am force-stop com.github.uiautomator && am force-stop com.github.uiautomator.test"` để hạ sạch tiến trình stub trước khi restart daemon atx-agent.

14. **BẪY [7c] KHÔNG LẤY ĐƯỢC OTP TỪ EMAIL (DEAD INBOUND MAILBOX / GRAPH API ZERO MESSAGES TIMEOUT)**:
    - **Hiện tượng & Nhận diện**:
      * Khi chạy preflight reg bù (`ensure_row_accounts.py <row>`), runner dừng tại bước nhập OTP và log:
        `[otp-graph] Graph API không thấy OTP mới sau timeout -> Không mở app Outlook (tránh sai state)`
        `❌ [REGISTER ERROR] STT <N> thất bại do ngoại lệ: [7c] Không lấy được OTP từ <email>`
    - **Căn nguyên cốt lõi (Dead Inbound Mailbox)**:
      * Hộp thư Hotmail/Outlook có token OAuth2 Microsoft Graph hợp lệ (`verify_graph_token` trả về `True` và đổi được `access_token`).
      * Tuy nhiên luồng nhận thư (inbound routing/MX) của tài khoản bị nghẽn, bị Microsoft quarantine hoặc chưa kích hoạt nhận thư ngoại bộ từ TikTok.
      * Màn hình TikTok đã gửi mã ("Kiểm tra email của bạn", "Gửi lại mã 58s"), nhưng khi query Graph API `/v1.0/me/messages` hoặc `/v1.0/me/mailFolders`, toàn bộ folder (Inbox, Junk Email) đều có `totalItemCount = 0` (hộp thư rỗng hoàn toàn).
      * Runner thăm dò suốt 120s timeout không có thư mới -> ném lỗi `[7c]`.
    - **Quy trình phục hồi chuẩn 4 bước (Zero-Stall Quarantine & Fall-Forward)**:
      1. **Kiểm chứng O(1) qua Microsoft Graph API**:
         - Đọc `token` (cột 9) và `client_id` (cột 10) từ `gmail_clean_v2.xlsx`.
         - Đổi `access_token` qua endpoint `https://login.microsoftonline.com/consumers/oauth2/v2.0/token`.
         - Thăm dò `/v1.0/me/mailFolders`: nếu `Inbox` và `Junk Email` đều có `totalItemCount = 0` sau khi TikTok đã phát mã -> khẳng định 100% email chết đường nhận thư.
      2. **Cách ly email chết (Quarantine Dead Mailbox)**:
         - Tạo backup timestamp file `gmail_clean_v2.xlsx` vào `archive_history/`.
         - Set cột 11 `trạng thái = 'used'` tại dòng của email đó trong `gmail_clean_v2.xlsx` của cụm (`admin` hoặc `kibe`).
         - Cột 11 có nhãn disallowed sẽ khiến `_detect_clean.py` / `load_source_rows` loại trừ vĩnh viễn email này.
      3. **Kiểm tra email sạch kế tiếp của máy**:
         - Quét các email còn lại được gán cho STT máy trong `gmail_clean_v2.xlsx`.
         - Dùng Graph API kiểm tra `verify_graph_token == True` và kiểm tra tin nhắn có sẵn (`msgs > 0`) để đảm bảo email thay thế hoàn toàn thông suốt.
      4. **Tái kích hoạt reg bù**:
         - Chạy dry-run: `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/<host>.yaml" python D:/Taadaa/tools/ensure_row_accounts.py <row> --machines <STT> --dry-run` để xác nhận `Can mua mail: 0 may` và target mới được bốc tự động.
         - Chạy thật: `ensure_row_accounts.py <row> --machines <STT>`.
      5. **Nghiệm thu thị giác & Chuẩn hóa cột sau reg (Post-Reg Visual & Column Audit)**:
         - **WinRT OCR Verification**: Bắt buộc chạy WinRT OCR trên `D:/Taadaa/Tiktok_Reg/screenshots_social/profile_<stt>_after_ensure_<timestamp>.png` kiểm tra đủ 4 dấu hiệu: handle `@<uid>`, display name, bộ chỉ số `0/0/0`, tab Hồ sơ active.
         - **Kiểm tra lệch cột sổ cái Master**: Khi runner append dòng mới vào `taikhoan_dat_v2_updated .xlsx`, nếu DOB rỗng, ngày tạo có thể bị đẩy sang cột 10 và serial bị đẩy sang cột 11. Chuẩn hóa O(1): kéo ngày tạo về cột 9, serial về cột 10, xóa cột 11.
         - **Đồng bộ toàn diện**: Chạy `sync-safe-workbook.py`, `sync_combined_safe_workbook.py`, và `sync_farm_account_info.py` để đảm bảo 100% ground truth đồng nhất.

    - **14.1. Căn nguyên Code Defect & BẪY TỬ HUYỆT BLACKLIST EMAIL TIMEOUT OTP (CHỐNG COOK OAN TÀI SẢN MAIL)**:
      * **Bẫy nghiệp vụ chết người**:
        Khi một email dính lỗi `[7c] Không lấy được OTP`, phản xạ sai lầm là tự động nạp nó vào `data/registered_emails_blacklist.json` hoặc set vĩnh viễn `trạng thái = 'used'`.
        **CỐT LÕI VẬN HÀNH (INVARIANT)**:
        - `registered_emails_blacklist.json` là danh sách loại trừ vĩnh viễn CHỈ DÀNH RIÊNG cho email **ĐÃ ĐĂNG KÝ TIKTOK THÀNH CÔNG** (để chống reg đè / login nhầm).
        - Một email dính timeout OTP **CHƯA hề có tài khoản TikTok**. Hòm thư của nó vẫn sống hoàn toàn bình thường (vẫn gửi nhận thư bình thường).
        - Nếu tự ý đưa vào `registered_emails_blacklist.json`, toàn bộ hệ thống sẽ coi email này đã có nick và vĩnh viễn không bao giờ dùng lại ➡️ **tự tay "cook luôn" tài sản mail farm đã bỏ tiền ra mua**.
      * **Giải pháp chuẩn trong runner (`social_reg_v1.py`)**:
        Khi hết timeout mà OTP chưa về:
        ```python
        elif any(email.lower().endswith(dom) for dom in ("@hotmail.com", "@outlook.com", "@live.com", "@msn.com")):
            save_ui_xml(device_id, f"fail_{stt or 'x'}_otp_not_found")
            screenshot(device_id, f"fail_{stt or 'x'}_otp_not_found")
            log(f"   [telemetry][otp_timeout] provider=microsoft email={email} reason=mailbox_otp_not_received")
        ```
        Chụp ảnh màn hình, lưu UI XML làm chứng cứ và phát structured telemetry event `[telemetry][otp_timeout]`. **TUYỆT ĐỐI CẤM gọi `record_registered_email_blacklist(email)`** khi chỉ mới dính timeout OTP.
      * **Bảo toàn tài nguyên**: Email dính timeout được bảo toàn nguyên vẹn trong kho mail (`gmail_clean_v2.xlsx` giữ nguyên trạng thái hoặc chuyển xuống cuối hàng đợi), sẵn sàng để retry ở ca khác sau khi hết cooldown hoặc đổi proxy/IP.

    - **14.2. Bẫy kết luận vội "Hòm thư hỏng" vs Thực nghiệm phân biệt TikTok Risk Engine "Silent Drop"**:
      * **Hiện tượng & Hoài nghi hợp lý**: Khi Graph API query không thấy thư OTP nào (0 thư ở cả Inbox lẫn Junk), trực giác thường cho rằng "hòm thư Microsoft bị lỗi / token chết". Tuy nhiên điều này rất thường là ngộ nhận.
      * **Phương pháp thực nghiệm đối soát O(1) qua Graph API**:
        1. **Test tự gửi (Self-send)**: Dùng API `POST /v1.0/me/sendMail` gửi một email từ chính tài khoản đó tới chính nó.
        2. **Test gửi chéo (Cross-account send)**: Dùng token của một tài khoản Microsoft khác gửi thư sang tài khoản đang nghi vấn.
        3. **Kết luận khoa học**: Nếu cả hai thư test đều cập bến Inbox sau 1–2 giây, khẳng định **100% hòm thư Microsoft hoàn toàn bình thường, token sống và pipeline nhận thư hoạt động hoàn hảo**.
      * **Bản chất kỹ thuật (TikTok Risk Engine "Silent Drop")**:
        - Giao diện app TikTok hiển thị: *"Kiểm tra email của bạn: Sử dụng liên kết này hoặc mã được gửi đến..."* để tránh làm lộ cơ chế chống bot cho người dùng.
        - Nhưng ở tầng backend, hệ thống Risk Control / Anti-fraud của TikTok đã gắn cờ thiết bị/IP/pattern email và âm thầm hủy bỏ (silent drop) lệnh phát email OTP, hoặc MTAs của ByteDance bị Microsoft SmartScreen chặn ngầm ở tầng mạng gateway.
        - Do đó, hòm thư dù hoàn toàn bình thường nhưng đối với TikTok tại thời điểm đó nó bị "liệt OTP".
      * **Kỷ luật xử lý**: Phải phân biệt rõ giữa "Hòm thư hỏng" và "TikTok Silent Drop". Không được quy chụp hòm thư hỏng, và tuyệt đối CẤM đưa email chưa có nick vào `registered_emails_blacklist.json`.

    - **14.3. Kỷ luật sửa tận gốc Code Runner (Chống sửa Data Excel chữa cháy tạm thời)**:
      * **Bài học sống còn từ phản biện của User ("Thế có mỗi hotmail kia bị thì kệ nó k cần fix script à?")**:
        - Khi gặp lỗi farm làm sập batch (như `[7c]` không lấy được OTP), nếu chỉ sửa tay trên file Excel (cách ly cột 11 `trạng thái = 'used'`) rồi báo DONE là **chữa cháy tạm thời, chưa giải quyết tận gốc**.
        - Nếu code runner không tự động bắt lỗi và ghi nhận telemetry chuẩn, hàng chục máy khác trên farm khi gặp sự cố tương tự sẽ tiếp tục sập và làm tê liệt quy trình tự động hóa.
      * **Quy tắc bất di bất dịch**:
        - Mọi lỗi văng ra từ runner khiến tiến trình dừng bất thường BẮT BUỘC phải được xem xét vá trực tiếp vào code runner (bổ sung error handler, structured telemetry, và bảo toàn tài nguyên).
        - Đi kèm unit test focused chứng minh hành vi và chạy Closeout Gate thẩm định trước khi kết thúc phiên.

---

## 3. THỰC ĐƠN ĐỐI SOÁT ADB ADMIN TỪ XA (Remote Cluster Check O(1))

Để kiểm tra `adb devices` trên cụm Admin (192.168.110.119:5037) từ máy Kibe mà **không cần SSH**:

```python
import subprocess
ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
res = subprocess.run([ADB, '-H', '192.168.110.119', '-P', '5037', 'devices'],
                    capture_output=True, text=True)
```

- `inspect_machine.py <N>` tự động phân biệt N < 200 (Kibe local) vs N >= 200 (Admin remote).
- **CẤM `kill-server`** trên Admin remote: dùng `reconnect` thay thế khi socket stall.
- **`ensure_row_accounts.py` có mutex lock**: nếu tiến trình khác đang chạy (`PID...`), lệnh mới tự exit. Kiểm tra PID bằng `wmic process where "ProcessId=<PID>" get CommandLine` trước khi retry.
- **Lệnh xác nhận batch online sau sự cố Hub**:
  ```python
  # Đối soát O(1) giữa adb devices và PROXYgandienthoai.xlsx
  attached = set(...)  # parse từ adb devices output
  offline = [stt for stt, serial in zip(stts, serials) if serial not in attached]
  print(f"Online: {len(attached)} | Offline: {offline}")
  ```

### Căn nguyên kỹ thuật
Lỗi `[01_open] TikTok not foreground after clean launch` rất thường là **triệu chứng hạ nguồn (downstream symptom)** của việc thiết bị bị rớt kết nối ADB (`device '<serial>' not found`) hoặc atx-agent không phản hồi:
1. `atx-agent dump exhausted (3/3 attempts + reset) - refusing unsafe shell uiautomator dump`.
2. Lệnh `adb shell dumpsys window` hoặc `am start` trả về `adb.exe: device '<serial>' not found`.
3. Script không thấy package TikTok trong foreground và ném lỗi `[01_open]`.

### Bẫy Nuốt Lỗi ADB Offline Thành [01_open] trong Error Extractor & Kỷ Luật Thứ Tự Phân Loại
- **Phản biện sống còn từ User**: *"Nếu v alert phải báo đúng chứ báo lung tung v"* — Khi máy bị rớt phần cứng / tuột cáp USB, cảnh báo Telegram gửi về người vận hành BẮT BUỘC phải chỉ đúng căn nguyên gốc `ADB offline (device not found)`, tuyệt đối cấm báo ngọn `[01_open] TikTok not foreground after clean launch` làm hoang mang người vận hành và dẫn đến điều tra lạc hướng.
- **Căn nguyên bug nuốt lỗi**:
  Trong hàm `_extract_reg_error(stt_dir)` (ở `ensure_row_accounts.py` hoặc các aggregator tương tự):
  * Tiến trình con `social_reg_v1.py` khi gặp ADB rớt chỉ log warning và tiếp tục chạy đến bước kiểm tra focus, sau đó văng `RuntimeError: [01_open] TikTok not foreground after clean launch`.
  * Bộ phân loại `_extract_reg_error` duyệt ngược log, bắt dòng `RuntimeError:` gán vào biến `err_line`.
  * Đoạn code kiểm tra ADB offline:
    ```python
    if not err_line:
        if "device" in text_lower and "not found" in text_lower:
            return "ADB offline (device not found)"
    ```
    Bị kẹp bên trong nhánh `if not err_line:`. Do `err_line` đã có chuỗi `[01_open]`, nhánh này bị bỏ qua hoàn toàn, dẫn đến lỗi mất kết nối vật lý bị nuốt chửng và đẩy lỗi ngọn về Telegram alert!
- **Kỷ luật Error Classification Priority**:
  Bộ lọc kiểm tra kết nối thiết bị (`"device" in text and "not found"`, `"device offline"`, `"offline"`) BẮT BUỘC nằm ở **mức ưu tiên số 1**, đứng TRƯỚC mọi phân loại exception ứng dụng (`err_line`):
  ```python
  if ("device" in text_lower and "not found" in text_lower) or "device offline" in text_lower or "offline" in err_lower:
      return "ADB offline (device not found)"
  ```

### Phân loại sự cố (Hardware vs Software)
- **Rớt đơn lẻ**: Kiểm tra cáp USB hoặc cổng hub của máy đó. Dùng `adb -s <serial> reconnect`. Nếu `adb reconnect` trả về `device '<serial>' not found`, dùng SSH kiểm tra PnP device trên host:
  `ssh admin-farm "powershell -Command \"Get-PnpDevice | Where-Object { \$_.InstanceId -like '*<serial>*' } | Select-Object FriendlyName, Status, Present, Problem\""`
  Nếu `Present: False` và `Problem: CM_PROB_PHANTOM` -> Khẳng định 100% rớt phần cứng vật lý (lỏng cáp hoặc sập nguồn máy lẻ), chuyển L3 BLOCKED kèm evidence, CẤM retry hay dispatch sửa code.
- **Sập cụm Hub 20 cổng (USB Hub Outage)**:
  - Khi một dải liên tục 10-20 máy (ví dụ M261–M280 trên cụm Admin) đồng loạt báo lỗi `[01_open]`.
  - Đối soát dải máy trong `PROXYgandienthoai.xlsx` với cấu trúc phần cứng rack farm.
  - Nếu toàn bộ dải biến mất khỏi `adb devices`, nguyên nhân là sự cố vật lý: sập nguồn adapter Hub USB hoặc lỏng cáp uplink USB nối vào máy chủ.
  - **Hành động**: Đánh dấu BLOCKED kèm bằng chứng thiết bị offline, yêu cầu cắm lại cáp vật lý. CẤM tự ý retry hay dispatch sửa code vô ích.
