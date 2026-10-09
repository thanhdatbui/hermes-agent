# Kỷ Luật Xử Lý Nick Ký Sinh (Parasite Account) & Chống Lỗi Báo Cáo "False DONE"

## 1. Bối cảnh & Nguyên nhân cốt lõi khiến lỗi "Ký sinh bị hoài"
Khi vận hành Farm TikTok, lỗi `MACHINE_FULL_8_ACCOUNTS` (chạm trần 8 nick, app ẩn nút "Thêm tài khoản") liên tục tái diễn dù trước đó đã có báo cáo "đã fix". Nguyên nhân gốc rễ bao gồm:

### A. Lỗ hổng "Báo cáo hoàn tất dối" (Premature State Marking)
- Trong các script logout tự động (ví dụ `watchdog_idle_parasite_reconcile.py` hoặc worker logout), flow thao tác UI: Switch nick -> Settings -> Cuộn trang -> Bấm "Đăng xuất".
- Khi app TikTok hiện popup xác nhận dialog (*"Bạn có chắc chắn muốn đăng xuất không?"*), tọa độ tap bị trượt hoặc dialog tải chậm không ăn lệnh.
- Nick **chưa hề bị đăng xuất**, nhưng script đã vội vàng ghi nhận `"DONE"` vào file state (`parasite_reconcile_state.json`) và báo cáo đã xử lý xong.
- Các vòng lặp hoặc watchdog sau đó đọc file state thấy `"DONE"` liền tự động bỏ qua (skip), khiến nick ký sinh tiếp tục chiếm slot trên máy nhiều ngày liền.

### B. Nhầm lẫn giữa "Nick ký sinh thật" và "Tài sản Farm bị lệch Excel"
- **Nick ký sinh thật (Cross-machine parasite):** Nick của máy khác (ví dụ nick của Máy 16, Máy 28) vô tình bị login sang máy này trong các đợt chạy test/reg cũ.
- **Tài sản Farm bị lệch Excel:** Máy thực tế đã đủ 8 nick chính chủ hợp lệ (ví dụ Máy 24 có 8 nick LIVE trong SQLite `farm_account_info`), nhưng trên file Excel (`taikhoan_run_safe.xlsx` hoặc `Tik8.xlsx`) bị khuyết dòng Row 8 (`None`) do lỗi trôi dòng / chưa đồng bộ. Runner thấy Row 8 trống tưởng thiếu nick nên gọi reg bù -> vấp lỗi `MACHINE_FULL_8_ACCOUNTS`.
- **HẬU QUẢ NẾU CHẨN ĐOÁN SAI:** Nếu Coordinator/Worker thấy 8 nick mà tưởng nhầm nick thứ 8 là ký sinh đem đi logout, farm sẽ mất trắng một tài khoản chính chủ đang nuôi.

---

## 2. Quy trình & Hard Invariants bắt buộc khi xử lý Nick Ký Sinh

### Invariant 1: Phân loại tài sản trước khi Logout (CẤM LOGOUT MÙ)
Trước khi ra lệnh logout bất kỳ nick nào trên máy bị full 8 acc:
1. Truy vấn SQLite `D:/Taadaa/data/tiktok_tracker.db`:
   ```sql
   SELECT username, may, tik FROM farm_account_info WHERE username = '<target_nick>';
   SELECT * FROM snapshots WHERE username = '<target_nick>' ORDER BY timestamp DESC LIMIT 1;
   ```
2. Nếu nick thuộc chính máy đó (hoặc đang LIVE và có lịch sử nuôi):
   -> **BẢO VỆ TÀI SẢN:** CẤM LOGOUT. Tiến hành **BACKFILL** vào Excel (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik*.xlsx`).
3. Chỉ thực hiện logout khi xác nhận nick thuộc máy khác (cross-machine) hoặc nick rác không rõ nguồn gốc.

### Invariant 2: Cơ chế Verify 2 lớp trước khi ghi nhận "DONE"
Tuyệt đối CẤM ghi nhận `"DONE"` vào state file hoặc báo cáo hoàn tất nếu chỉ thực hiện hành động tap logout mà chưa verify readback:
1. **Thao tác Logout:**
   - Tap "Đăng xuất" -> Xử lý dứt điểm popup xác nhận (`btn_confirm` hoặc tap đúng nút Đăng xuất màu đỏ).
2. **Readback Verification:**
   - Mở lại app TikTok -> Vào Profile -> Mở Switcher dropdown.
   - Dump UI qua `atx-agent` (port 7912) và chụp screencap Switcher.
   - **ĐIỀU KIỆN CHẤP NHẬN HOÀN THÀNH:**
     + Nick mục tiêu **HOÀN TOÀN BIẾN MẤT** khỏi cây UI XML / OCR của Switcher.
     + Tổng số nick trên Switcher còn đúng **<= 7**.
     + Nút **"Thêm tài khoản"** (`Add account`) đã **XUẤT HIỆN TRỞ LẠI**.
3. Nếu nick vẫn còn: Bắt buộc đánh dấu `FAILED` và thử lại flow xử lý popup dialog, TUYỆT ĐỐI CẤM ghi `DONE`.

### Invariant 3: Bằng chứng hình ảnh hiện trường (Gate 6)
- Mỗi máy sau khi logout thành công bắt buộc lưu ảnh screencap Switcher vào `D:/Taadaa/reports/m{machine_id}_verified_logout.png`.
- Gửi báo cáo kèm dòng `MEDIA:<path_anh>` riêng biệt để người dùng kiểm chứng trực tiếp nút "Thêm tài khoản" đã mở lại.
- Teardown an toàn: `am force-stop` và đưa máy về Home launcher SAU KHI đã chụp ảnh nghiệm thu.

---

## 3. Quy tắc Decompose Worker khi thao tác thiết bị vật lý (Chống Timeout 600s)
- **CẤM gộp nhiều máy vào 1 subagent nối tiếp:** Mỗi máy Samsung S7 thực hiện trọn vẹn chu kỳ (wake -> mở app -> dump UI atx -> profile -> switcher -> settings -> swipe x5 -> logout -> confirm popup -> restart app -> verify readback) mất từ 2 đến 4 phút. Nếu dispatch 1 subagent ôm 3-4 máy tuần tự, thời gian thực thi sẽ vượt ngưỡng timeout 600s (10 phút) của hệ thống delegation và bị huỷ đột ngột (killed/timeout).
- **Quy tắc phân rã bắt buộc:**
  + Tách riêng tác vụ can thiệp thiết bị vật lý (logout/screencap) và tác vụ file (Excel/SQLite). Tác vụ Excel hoàn thành trong vài giây, không được để chờ thiết bị.
  + Mỗi máy vật lý cần can thiệp phải được dispatch thành 1 worker subagent độc lập (parallel fan-out) với budget riêng (max 5-6 calls, timeout < 5 phút).
  + Khi 1 máy gặp trục trặc ADB hoặc kẹt popup, các máy khác vẫn hoàn tất bình thường mà không bị chết chùm.

---

## 4. Quy trình Re-Arm / Reset State khi phát hiện "DONE ảo"
Khi người dùng phản ánh hoặc hệ thống phát hiện nick ký sinh vẫn còn trên máy dù trước đó đã có báo cáo hoàn tất:
1. **Kiểm tra file state:** Đọc `D:/Taadaa/runtime/kibe/cron-state/parasite_reconcile_state.json`.
2. **Re-arm (Xóa state ảo):** Xoá key mục tiêu (ví dụ `"m61_anggiathinh2905"`) hoặc đặt lại thành `"PENDING"` trước khi gọi lại script/watchdog:
   ```json
   {
     "m61_anggiathinh2905": "PENDING",
     "m69_quachtieu2106": "PENDING"
   }
   ```
3. Chạy lại script logout với flag chỉ định máy: `python D:/Taadaa/tools/watchdog_idle_parasite_reconcile.py --machine <N>`.

---

## 5. Bẫy nút "Thêm tài khoản" bị che khuất dưới đáy Switcher (Màn hình 7 nick)
- Trên một số màn hình máy Samsung S7 (1080x1920 density 480), khi switcher có 7 tài khoản, nút *"Thêm tài khoản"* / *"Add account"* bị đẩy sát xuống mép dưới đáy màn hình hoặc nằm ngoài viewport.
- Runner tìm text không thấy sẽ quăng lỗi không tìm thấy nút hoặc rơi vào fallback đếm node XML.
- **Khắc phục:** Thực hiện một thao tác cuộn nhẹ từ giữa màn hình lên (`adb shell input swipe 540 1400 540 800 300`) bên trong bottomsheet Switcher để kéo nút "Thêm tài khoản" vào vùng nhìn thấy trước khi kết luận máy bị kẹt trần 8 nick.
