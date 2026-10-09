# Triage & Điều tra lỗi [07] "Tất cả N email của STT đã có TK TikTok" khi chạy Reg bù theo Row

## Hiện tượng
Khi chạy preflight hoặc batch đăng ký bù tài khoản theo Row (ví dụ: `[PREFLIGHT REG BÙ ROW 5]`):
- Runner báo lỗi dạng: `Máy <STT>: [07] Tat ca N email cua STT <STT> da co TK TikTok`.
- User thắc mắc: Các email này đã là acc của các máy đó từ trước (do lệch dữ liệu/restore session cũ), nhưng tại sao máy vẫn tiếp tục báo thiếu account? Có phải thiếu account ở Row khác không?

## ⚠️ PITFALL CỐT LÕI (BẮT BUỘC TRUY SOÁT TRƯỚC KHI PHÁN CẠN MAIL)
**NICK LÀ TÀI SẢN — TUYỆT ĐỐI CẤM VỘI VÀNG PHÁN "CẠN MAIL" HAY ĐÒI NẠP THÊM MAIL MỚI!**
Khi email trong `gmail_clean_v2.xlsx` bị TikTok báo "Email này đã có tài khoản TikTok":
- **Nguyên nhân hàng đầu:** Nick ĐÃ ĐƯỢC REG THÀNH CÔNG TỪ TRƯỚC bởi chính farm, nhưng bị rơi rớt dữ liệu do:
  1. Script reg bị lỗi/crash/timeout ở pha cuối nên không ghi kịp vào `taikhoan_dat_v2_updated .xlsx`.
  2. Session trước restore hoặc clean workbook (ví dụ các file `taikhoan_dat_v2_updated_BEFORE_RESTORE*.xlsx`) đã lọc bỏ nhầm các dòng tài khoản do sai lệch công thức STT Tik/Folder (ghi `Tik = M * 8` hoặc `Tik = 2` thay vì chuẩn `(M - 201) * 8 + slot`).
  3. Lệch đồng bộ giữa bảng kết quả reg (`taikhoan_dat_v2_updated .xlsx`) và bảng vận hành slot (`taikhoan_run_safe.xlsx` / `Tik1..Tik8.xlsx`).
- **Hậu quả nếu phán bừa nạp mail mới:** Bỏ rơi nick cũ đã tạo (mất tài sản), làm phình kho mail, và tiếp tục để rác dữ liệu tồn đọng.

---

## Nguyên lý đối soát 4 lớp (Four-layer Workbook & History Audit)

### Lớp 1: Bảng phân bổ slot vận hành (`taikhoan_run_safe.xlsx` & `Tik1.xlsx` .. `Tik8.xlsx`)
- Mỗi máy vật lý có cố định **8 slots** (tương ứng Row 1 -> Row 8 / Tik1 -> Tik8).
- Cần đối soát trực tiếp trong `D:\OneDrive\TaadaaData\<cluster>\taikhoan_run_safe.xlsx`:
  - Lọc theo `May = <STT>`.
  - Kiểm tra xem 8 slot có bao nhiêu slot có `ID` và bao nhiêu slot `ID = None`.
  - Xác định chính xác các Slot đang trống (ví dụ: Slots 4, 5, 6 trống -> máy chỉ mới có 5/8 acc, đang thiếu acc ở Row 4, Row 5, Row 6).
  - Khi chạy "REG BÙ ROW 5", runner chỉ quan tâm lấp slot cho Row 5. Nếu Row 5 đang trống, máy vẫn được phân loại là **MÁY THIẾU ACC**.

### Lớp 2: Bảng kết quả đăng ký hiện tại (`taikhoan_dat_v2_updated .xlsx`)
- Ghi nhận toàn bộ các tài khoản đã được đăng ký thành công cho STT đó (`Tài Khoản` sheet).
- Kiểm tra xem số lượng acc đã ghi nhận trong bảng này có khớp với số acc trên `taikhoan_run_safe.xlsx` hay không:
  - Nếu số acc trong `taikhoan_dat_v2_updated .xlsx` lớn hơn `taikhoan_run_safe.xlsx` (ví dụ: có 6 acc nhưng run_safe chỉ có 5 acc): Có 1 acc đã reg thành công nhưng **chưa được backfill/map vào slot trống** của `taikhoan_run_safe.xlsx`.

### Lớp 3: BẢN SAO LƯU & LỊCH SỬ RESTORE (CRITICAL BACKUP RECOVERY)
- **BẮT BUỘC** tìm kiếm các email bị báo trùng trong toàn bộ các bản sao lưu:
  - `D:\OneDrive\TaadaaData\<cluster>\taikhoan_dat_v2_updated_BEFORE_RESTORE*.xlsx`
  - `D:\OneDrive\TaadaaData\<cluster>\*.bak*` và thư mục `recovery-backups`
  - Lịch sử runs: `D:\Taadaa\runtime\<cluster>\artifacts\runs\social-batch-all\*\batch_*\stt_*\tracking_result_*.json`
- **ĐỐI SOÁT CHỐNG KÍ SINH (PARASITE ACCOUNT AUDIT - CẤM GÁN LỆCH MÁY):**
  - Khi tìm thấy tài khoản trong bản backup, BẮT BUỘC đối soát chéo với STT máy trong `gmail_clean_v2.xlsx`.
  - Email được cấp cho Máy nào thì **BẮT BUỘC PHẢI KHÔI PHỤC VỀ ĐÚNG MÁY ĐÓ**.
  - **TUYỆT ĐỐI CẤM** đem tài khoản của máy này gán sang slot của máy khác chỉ để cho đủ số lượng (làm sai lệch proxy, thiết bị vật lý và biến nick thành tài khoản "kí sinh").
  - Kiểm tra chéo Cross-Host (Kibe M1-80 vs Admin M201+): Đảm bảo không có bất kỳ UID hay Email nào bị trùng lặp hoặc kí sinh giữa 2 cluster.
- Nếu tìm thấy dòng có UID, Password, Email tương ứng: **Khôi phục ngay lập tức** vào `taikhoan_dat_v2_updated .xlsx`, chuẩn hóa lại cột STT Tik/Folder theo đúng công thức:
  - Máy Kibe (1-80): `(M - 1) * 8 + slot`
  - Máy Admin (201+): `(M - 201) * 8 + slot`

### Cơ chế kỹ thuật trong script (Code Invariant trong `ensure_row_accounts.py`):
1. **Lọc mail sạch quét toàn bộ backup:** Hàm `get_available_mails_by_machine()` bắt buộc phải nạp toàn bộ email từ cả `taikhoan_dat_v2_updated .xlsx` hiện tại + `taikhoan_dat_v2_updated_BEFORE_RESTORE*.xlsx` + thư mục `recovery-backups/*.xlsx` vào tập `used_emails`. Email nào đã từng có mặt trong bất kỳ bản backup nào đều bị loại trừ vĩnh viễn, không được coi là mail sạch.
2. **Đồng bộ Safe Workbook theo đúng Host:** Hàm `apply_results()` không được phụ thuộc vào launcher cron ngoài (dễ bị gán cứng `kibe.yaml`). Bắt buộc gọi trực tiếp `sync-safe-workbook.py` với `--source`, `--output`, `--tik-dir` tương ứng với `HOST_ID` thực tế (Admin hoặc Kibe) để đồng bộ ngay lập tức sang `taikhoan_run_safe.xlsx` và các file `TikX.xlsx`.
3. **Atomic Save:** Workbook ghi qua file tạm `.tmp.xlsx` rồi atomic replace để chống lỗi corrupt zip khi ngắt đột ngột.

### Lớp 4: Pool email nguồn cấp (`gmail_clean_v2.xlsx`)
- Mỗi STT thường được cấp sẵn 8 email (Hotmail/Outlook) trong sheet `Gmail Accounts`.
- CHỈ KHI đã đối soát hết Lớp 2 và Lớp 3 mà xác nhận email này chưa từng có UID nào được tạo trên farm (email bị dính tài khoản từ bên ngoài trước khi nạp vào farm):
  - Lúc đó mới tiến hành thay thế email sạch mới vào `gmail_clean_v2.xlsx`.

---

## Quy trình xử lý chuẩn (SOP từng bước)

1. **Khẳng định phạm vi thiếu thực tế:**
   - Dùng script Python O(1) kiểm tra 8 dòng của máy trong `taikhoan_run_safe.xlsx` để chỉ rõ: Máy đang có bao nhiêu acc, thiếu chính xác ở những Row/Slot nào (ví dụ: Row 4, 5, 6).

2. **Truy vết tìm tài khoản thất lạc (Backup Recovery):**
   - Quét các email candidate bị báo trùng trong `taikhoan_dat_v2_updated_BEFORE_RESTORE*.xlsx` và các file `.bak`.
   - Trích xuất: `May, Tik, UID, Password, 2FA, Email, Password Mail, Ngày sinh`.

3. **Khôi phục và chuẩn hóa vào Workbook:**
   - Append hoặc khôi phục các tài khoản tìm thấy vào `taikhoan_dat_v2_updated .xlsx`.
   - Chuẩn hóa cột Tik theo chuẩn `(May - 201) * 8 + Slot` (với Admin) hoặc `(May - 1) * 8 + Slot` (với Kibe).

4. **Đồng bộ đa tầng vào Vận hành:**
   - Map các tài khoản đã khôi phục vào các slot trống (None) trong `taikhoan_run_safe.xlsx`.
   - Điền tương ứng vào các file `TikX.xlsx` (với X là slot thiếu, ví dụ Tik4, Tik5, Tik6).
   - Đồng bộ vào `tiktok_tracker.db` (`account_mapping`).

5. **Chạy lại Preflight xác nhận:**
   - Chạy `python D:/Taadaa/tools/ensure_row_accounts.py <row> --dry-run` để đảm bảo máy đã nhận đủ tài khoản và không còn bị trigger reg bù sai lệch.

---

## Triage lỗi Preflight Reg bù thất bại do Máy Offline / USB Hub Outage

### Hiện tượng Alert
Khi chạy preflight reg bù theo Row (ví dụ: `[PREFLIGHT REG BÙ ROW 2]`):
- Runner báo lỗi:
  - `Máy <STT>: [01_open] TikTok not foreground after clean launch`
  - `Máy <STT>: [adb-timeout] UI_XML_TIMEOUT device=<serial>`
- Hiện trường `screenshots_social/` trống hoặc không có screenshot thành công.

### Bản chất kỹ thuật
- Runner `ensure_row_accounts.py` quét thấy slot Row N trong `taikhoan_run_safe.xlsx` bị trống nên kích hoạt `_run_all_targets.py`.
- Nếu máy đang bị mất kết nối ADB (`device '<serial>' not found`), quá trình clean launch và dump UI XML qua atx-agent liên tục thất bại (`[adb warn] adb.exe: device not found`), dẫn đến timeout 90s hoặc ngoại lệ không foreground.

### Nhận diện sự cố Hub USB 20 cổng vs Cáp đơn lẻ
1. **Kiểm tra trạng thái O(1):** Chạy `python D:/Taadaa/tools/inspect_machine.py <N>`.
2. **Đối soát danh sách máy online:**
   - Nếu **1 cụm 20 máy liên tục** (ví dụ: M261–M280 trên Admin) đồng loạt biến mất khỏi `adb devices`: Kết luận ngay là **sự cố phần cứng Hub USB 20 cổng** (sập nguồn adapter Hub hoặc tuột cáp uplink USB nối vào PC host). **TUYỆT ĐỐI KHÔNG** đi mò lỗi phần mềm/script.
   - Nếu **1 máy riêng lẻ** (ví dụ: M231, M255): Lỏng cáp USB cổng đó, cáp micro-USB/Type-C bị hỏng, hoặc điện thoại sập nguồn cạn pin.

### An toàn tài khoản
- Do thất bại ở khâu mở app ban đầu, email trong `gmail_clean_v2.xlsx` **được bảo toàn 100%**, không bị tiêu hao hay ghi đè lỗi.
- Đánh dấu trạng thái `BLOCKED` (chờ phục hồi phần cứng tại rack), sau khi cắm lại Hub/cáp máy online trở lại thì preflight sẽ tự động reg bù an toàn.
