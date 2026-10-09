# Parasite Reconcile & Machine Full Pitfalls (Taadaa Farm)

## Bối cảnh sự cố (2026-09-24)
Trong quá trình vận hành Preflight Reg Bù Row 8 (`ensure_row_accounts.py`), hệ thống liên tục gặp tình trạng các máy báo `Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)` hoặc dính lỗi `[04_add_account] MACHINE_FULL_8_ACCOUNTS`. Dù trước đó đã có các phiên fix nick ký sinh, sự cố vẫn tái diễn do 3 bẫy kỹ thuật cốt lõi sau:

---

## 1. Bẫy "Hoàn tất ảo" trong State Machine Logout (`parasite_reconcile_state.json`)

### Hiện tượng:
- Phiên trước báo "Đã logout 10/10 máy thành công", nhưng phiên sau các nick ký sinh (ví dụ: `@anggiathinh2905` trên M61, `@quachtieu2106` trên M69) vẫn nằm nguyên trong Switcher.
- Watchdog tự động bỏ qua (skip) vì file `parasite_reconcile_state.json` đã lưu `"DONE"`.

### Nguyên nhân kỹ thuật trên TikTok S7 (Android 7):
- Khi hiện popup *"Bạn có chắc chắn muốn đăng xuất?"*:
  - Node chữ *"Đăng xuất"* (resource-id `com.ss.android.ugc.trill:id/a6d`) có thuộc tính `clickable="false"` ở bounds `[48,1632][1032,1692]`.
  - Node container bấm thực sự là `clickable="true"` ở bounds `[0,1584][1080,1740]`, trọng tâm tại `(540, 1664)`.
  - Nếu script dùng selector cũ (ví dụ tìm `a6e` hoặc tap vào chữ `clickable="false"`), sự kiện click không ăn, popup không đóng, nick **chưa bị out**.
  - Script cũ không kiểm tra readback mà tự động ghi `state[key] = "DONE"`.

### Quy tắc bất biến (Invariant):
1. **Tọa độ chuẩn xác nhận popup Đăng xuất:** Tap vào container `(540, 1664)` (bounds `[0,1584][1080,1740]`).
2. **Readback Verification trước khi set DONE:** 
   - Sau khi tap logout, BẮT BUỘC mở lại TikTok -> vào Profile -> mở Switcher dropdown.
   - Dump UI XML hoặc chạy WinRT OCR đọc danh sách nick hiện tại.
   - CHỈ ĐƯỢC PHÉP ghi nhận `"DONE"` vào file state khi và chỉ khi:
     a) Username mục tiêu KHÔNG CÒN xuất hiện trong danh sách.
     b) Tổng số tài khoản trên Switcher đã giảm và nút *"Thêm tài khoản"* đã hiển thị lại.
   - Nếu nick vẫn còn: BẮT BUỘC giữ trạng thái `"PENDING"` hoặc quăng lỗi cảnh báo, CẤM ghi nhận `"DONE"`.

---

## 2. Bẫy đếm nhầm nút "Thêm tài khoản" thành Nick thứ 8 (`tap_add_account`)

### Hiện tượng:
- Thiết bị thực tế chỉ có đúng 7 tài khoản chuẩn (như Máy 3), hoàn toàn không có nick ký sinh, nhưng khi chạy reg bù lại bị quăng lỗi:
  `RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`

### Nguyên nhân kỹ thuật trong `social_reg_v1.py`:
- Trong hàm `tap_add_account`, bộ đếm tài khoản quét theo resource-id:
  ```python
  _acc_count = sum(
      1 for _n in _root.iter("node")
      if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
  )
  ```
- Trên nhiều phiên bản TikTok, hàng nút *"Thêm tài khoản"* / *"Add account"* ở đáy Switcher cũng mang chính `resource-id` là `lli` hoặc `lrq`.
- Khi máy có 7 nick + 1 nút *"Thêm tài khoản"*, bộ đếm quét được: `7 + 1 = 8 nodes`.
- Điều kiện `if _acc_count >= 8:` bị kích hoạt oan, script tự đóng dropdown và quăng lỗi dù nút thêm tài khoản đang hiển thị bình thường!

### Quy tắc bất biến (Invariant):
- Khi đếm số lượng tài khoản trong Switcher, BẮT BUỘC loại trừ các node có `text` hoặc `content-desc` chứa:
  `"Thêm tài khoản"`, `"Add account"`, `"Thêm tài khoản khác"`, `"Add another account"`.
- Nếu đã tìm thấy nút *"Thêm tài khoản"* (bằng text/desc hoặc OCR), TUYỆT ĐỐI CẤM quăng lỗi `MACHINE_FULL_8_ACCOUNTS`.

---

## 3. Bảo toàn tài sản Farm: Phân biệt Nick Ký Sinh vs Lệch Mapping Workbook (M24 Pattern)

### Hiện tượng:
- Preflight quét `taikhoan_run_safe.xlsx` hoặc `Tik8.xlsx` thấy Row 8 bị trống (`None`).
- Script kiểm tra thiết bị thấy đã có 8 nick, vội vàng kết luận máy bị nick ký sinh chiếm chỗ.

### Nguy cơ mất tài sản P0:
- Trên thực tế tại Máy 24, cả 8 nick trên thiết bị đều là tài khoản chính chủ của farm (`trinhgiang7694` ở Slot 7 và `baomai0316` ở Slot 8). Cả 2 đều đang LIVE và có dữ liệu trong SQLite `tiktok_tracker.db`.
- Do lệch pha đồng bộ giữa các file Excel (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik7.xlsx`, `Tik8.xlsx`), tài khoản `@trinhgiang7694` bị rớt khỏi dòng hiển thị.
- Nếu vội vàng đăng xuất nick thứ 8, hệ thống sẽ **xóa nhầm tài sản thật của farm**.

### Quy tắc bất biến (Invariant):
- **CẤM LOGOUT MÙ:** Trước khi quyết định logout bất kỳ tài khoản nào trên máy bị báo 8 nick:
  1. Tra cứu username trong SQLite `D:/Taadaa/data/tiktok_tracker.db` (`farm_account_info` và `snapshots`).
  2. Tra cứu username trong file lịch sử `taikhoan_dat_v2_updated_BACKUP_SAFE.xlsx`.
  3. NẾU username thuộc về chính máy đó (cùng số máy `may`): Đây là **TÀI SẢN BỊ LỆCH WORKBOOK**. BẮT BUỘC backfill đồng bộ vào cả 4 file master (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik7.xlsx`, `Tik8.xlsx`).
  4. CHỈ ĐƯỢC PHÉP LOGOUT khi xác định chắc chắn nick đó thuộc máy khác (ký sinh) hoặc là nick ngoài luồng không có trong kho tài sản.
