# Zero-Fingerprint Bio Clearing & Account Switcher Race Condition

## 1. Zero-Fingerprint Bio Clearing (`--clear-bio`)

### Operator Directive (2026-10-19 / 2026-10-20)
> *"Cái 2 của mày acc khác đã xài r. Đm t k biết mày nghĩ gì đồ dùng bio giống acc khác. Còn nếu mày chế ra bio hài hước khác acc khác đc thì t cho phép làm"*
> *"1 - XÓA TRẮNG BIO VỀ RỖNG 100% (như ban đầu `+ Thêm tiểu sử`)"*

### Invariants & Workflow
1. **Tuyệt đối cấm trùng Bio**: Dùng chung bio giữa các tài khoản là dấu hiệu bot lộ liễu, gây shadow-ban toàn farm. Nếu không viết được bio độc nhất 100% theo niche thì phương án tối ưu bắt buộc là **xóa trắng bio về rỗng** (`--clear-bio`).
2. **Quy trình xóa trắng chuẩn**:
   - Từ màn hình Profile, tap trực tiếp vào dòng Bio (`chia se` / `tieu su` / `khoanh`) hoặc tọa độ `(473, 703)` để mở màn hình `EDIT_PROFILE`.
   - Trong `EDIT_PROFILE`, tap dòng Tiểu sử tại `(162, 1332)`.
   - Trong `BIO_EDIT`, phát broadcast `ADB_KEYBOARD_CLEAR_TEXT` + gửi 100 phím `KEYCODE_DEL` + `ADB_KEYBOARD_CLEAR_TEXT` xóa sạch text trong ô nhập.
   - Bấm `Lưu` tại `(980, 140)` mà không gõ thêm ký tự nào.
   - Bấm Back về Profile, nghiệm thu qua WinRT OCR: xác nhận đã xuất hiện lại nút **`+ Thêm tiểu sử`** (`+ Thém tidU sd`).
3. **Cạm bẫy False-Positive OCR Video Title**:
   - Khi quét kiểm tra text bio trên Profile, WinRT OCR có thể đọc trúng tiêu đề video ở lưới đáy (ví dụ: `TRAI CHIA SẺ...`).
   - BẮT BUỘC giới hạn vùng kiểm tra $y < 850$ để tránh ngộ nhận là còn dính bio rác cũ.

---

## 2. Switch Account Race Condition & Switcher Inventory Desync

### Hiện Tượng Lỗi `exit_2` Hàng Loạt
Khi watchdog chạy cuốn chiếu, nhiều máy báo lỗi `exit_2`:
- `mo Switcher 3 lan, acc active van la @<old_user>`
- `khong tim thay @<target_user> trong Switcher (OCR)`
- `ket o trang thai PROFILE 5 lan lien tiep`

### Nguyên Nhân Kỹ Thuật & Khắc Phục

| Vấn Đề | Nguyên Nhân Gốc | Giải Pháp Kỹ Thuật |
| :--- | :--- | :--- |
| **Đổi acc bị trễ (Race Condition)** | Sau khi tap chọn acc trong Switcher, TikTok hiện toast *"Đã đổi sang..."* và về Feed, nhưng bộ nhớ đệm Profile trên Samsung S7 mất 3–5s mới nạp profile mới. Runner tap ngay tab Hồ sơ sẽ đọc trúng thông tin của acc cũ $\rightarrow$ ngộ nhận chưa đổi được $\rightarrow$ thử lại 3 lần rồi abort `exit_2`. | BẮT BUỘC chèn `time.sleep(3.5)` sau khi chọn acc trong Switcher trước khi chuyển tab Profile. |
| **Lệch Inventory (Acc không có trên máy)** | Sổ cái Excel ghi máy có acc A, nhưng thực tế khay Switcher đã bị logout hoặc thay thế bằng acc khác (chỉ còn 7 acc khác). Runner cuộn khay tìm không thấy $\rightarrow$ abort `exit_2`. | Khi Switcher đã cuộn hết sheet mà không thấy username: đánh dấu acc là `UNMAPPED / LOGGED_OUT`, bỏ qua ngay, không thử lại gây kẹt tài nguyên. |
| **Giao diện Profile canh giữa (Centered Layout)** | Profile canh giữa (Avatar, Name, Stats đều ở giữa) không có nút text *"Sửa hồ sơ"*. Cú tap fallback `(870, 558)` (của layout cũ canh trái) rơi vào nền xám trống $\rightarrow$ kẹt Profile 5 lần $\rightarrow$ `exit_2`. | Kiểm tra: Nếu không có nút text Sửa hồ sơ, tap trực tiếp vào dòng Bio / nút `+ Thêm tiểu sử` để mở màn hình chỉnh sửa. |

---

## 3. Tiêu Chí Lọc Mục Tiêu Đổi Tên (Chống Đổi Nhầm Tên Hợp Lệ)

### Sai Lầm Cũ (Over-Eager Selection)
Điều kiện cũ coi mọi nick có `len(d.split()) < 2` là tên chưa chuẩn. Hậu quả: bốc nhầm cả các nick đã có tên người thật hợp lệ (ví dụ: `@kamilhhs0tk` tên là **`Phong`**, nick máy 2 tên là **`Hà`**) và cố ép đổi thành tên 3 từ khác, gây phản ứng gay gắt từ Operator.

### Quy Chuẩn Nhận Diện Tên Thực Sự Cần Đổi (`is_target_rename`)
Chỉ đưa vào hàng chờ đổi tên khi thỏa mãn một trong các điều kiện sau:
1. **Trùng 100% username:** `d.lower() == u.lower()`.
2. **Có số đuôi rác:** `re.search(r'\d{2,}$', d)` (ví dụ: `duongkien1202`, `thuquynh9081`, `nhimnhim156`).
3. **Chuỗi không dấu dạng tài khoản:** `re.search(r'^[a-z0-9_.]+\d+$', d.lower())`.
4. **Tuyệt đối BỎ QUA:** Nếu tên đã có dấu tiếng Việt chuẩn hoặc đã là tên người (kể cả 1 từ như *Phong, Hà, Trang, Đạt...*), BẮT BUỘC giữ nguyên, không đổi.
