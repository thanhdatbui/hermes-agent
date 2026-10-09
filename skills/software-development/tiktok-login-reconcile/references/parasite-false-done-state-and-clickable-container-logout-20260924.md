# Bẫy State Ảo "DONE" Trong Dọn Nick Ký Sinh & Bấm Chuẩn Container Popup Đăng Xuất (2026-09-24)

## Bối cảnh sự cố
User thắc mắc: *"Xử lý cho tao ủa tao fix vụ kí sinh r mà sao cứ bị hoài thế?"*
Khi chạy Preflight Reg Bù cho Row 8, hệ thống báo hàng loạt máy thất bại do `MACHINE_FULL_8_ACCOUNTS` (M3, M24, M61, M69). Kiểm tra thực tế:
- Máy 61 vẫn còn nguyên nick ký sinh `@anggiathinh2905` (nick của M28).
- Máy 69 vẫn còn nguyên nick ký sinh `@quachtieu2106`.
- Máy 24 đã có đủ 8 nick chính chủ nhưng bị lệch mapping Excel (Row 8 để trống).
- Máy 3 có 7 nick chính chủ nhưng nút "Thêm tài khoản" bị cuộn dưới đáy, bộ đếm node XML đếm nhầm >= 8.

---

## 1. Nguyên nhân gốc rễ (Root Cause)

### 1.1. Bẫy State Ảo "DONE" trong `parasite_reconcile_state.json`
- Trong các đợt chạy trước, script `watchdog_idle_parasite_reconcile.py` điều hướng vào Settings bấm "Đăng xuất". Khi TikTok hiện popup xác nhận *"Bạn có chắc chắn muốn đăng xuất không?"*, thao tác bấm bị trượt hoặc chưa kịp ăn thì script đã ghi nhận `"DONE"` vào file `parasite_reconcile_state.json`.
- Ở tất cả các lần quét tiếp theo, script kiểm tra `if state.get(key) == "DONE": continue` và **tự động bỏ qua vĩnh viễn** máy đó, tạo ra hiện tượng tưởng đã fix nhưng thực tế nick ký sinh vẫn nằm nguyên trên máy suốt nhiều ngày.

### 1.2. Cấu trúc UI Dialog Xác Nhận Đăng Xuất trên TikTok Android
Khi popup *"Bạn có chắc chắn muốn đăng xuất?"* xuất hiện ở cuối màn hình Cài đặt:
- Node text hiển thị: `text='Đăng xuất'`, `resource-id='com.ss.android.ugc.trill:id/a6d'`, **`clickable='false'`**, bounds `[48,1632][1032,1692]`.
- Container thực sự nhận sự kiện click: node cha/layout bao bọc có **`clickable='true'`**, bounds **`[0,1584][1080,1740]`**, tọa độ tâm chuẩn: **`(540, 1664)`**.
- Nếu script tìm theo selector text và tap vào element con `clickable='false'`, sự kiện click có thể bị nuốt chửng (swallowed), popup không đóng và tài khoản hoàn toàn chưa bị đăng xuất!
- Ngoài ra, selector resource-id và bounds có thể biến thiên theo phiên bản TikTok (`a6d`, `a6e`, `button1`, bounds bắt đầu bằng `[0,` hoặc `[48,`). Bộ lọc cần chấp nhận mọi biến thể: `any(k in r for k in ["a6d", "a6e", "button1"]) or ("đăng xuất" in t.lower() and any(k in b for k in ["[48,", "[0,"]))`.

### 1.3. Bẫy Màn Hình Tắt Trong Chế Độ Chờ Rảnh (Screen Sleep / Timeout)
- Thiết bị chạy chế độ rảnh (idle) thường tự tắt màn hình sau timeout (15s - 30s).
- Khi watchdog phát hiện máy rảnh và mở app, nếu không chủ động bật sáng và giữ màn hình (`svc power stayon true && input keyevent 224 && input keyevent 82`), uiautomator dump sẽ chập chờn hoặc tap không ăn.
- Khi hoàn tất hoặc kết thúc ca xử lý, BẮT BUỘC khôi phục trạng thái năng lượng: `svc power stayon false` cùng với force-stop và keyevent Home để không làm chai pin / quá nhiệt thiết bị.

---

## 2. Quy trình & Invariant Bắt Buộc

### 2.1. Invariant: Kiểm Tra Biến Mất Trước Khi Đánh Dấu "DONE"
Tuyệt đối CẤM ghi `"DONE"` vào file state ngay sau khi tap Đăng xuất. BẮT BUỘC thực hiện quy trình nghiệm thu 2 lớp:
1. Tap xác nhận đăng xuất tại container `clickable='true'` `(540, 1664)`. Đợi 4 giây.
2. Mở lại TikTok $\rightarrow$ vào Profile $\rightarrow$ mở account dropdown Switcher.
3. Chụp screencap Switcher nghiệm thu và chạy WinRT OCR:
   - Xác nhận nick ký sinh **ĐÃ HOÀN TOÀN BIẾN MẤT** khỏi Switcher.
   - Nút *"Thêm tài khoản"* (Add account) đã xuất hiện trở lại.
4. CHỈ KHI thỏa mãn cả 2 điều kiện trên mới được cập nhật `"DONE"` vào `parasite_reconcile_state.json`. Nếu nick vẫn còn: đánh dấu `"PENDING"` hoặc `"FAILED"` và báo động ngay.

### 2.2. Phân Định Tài Sản Farm vs Nick Ký Sinh (Case M24)
- **CẤM NHẬN ĐỊNH VỘI VÀNG:** Khi máy bị `MACHINE_FULL_8_ACCOUNTS`, không được mặc định coi tài khoản thứ 8 là "ký sinh" hay "rác" để mang đi logout.
- **Đối soát Source of Truth:**
  - Kiểm tra bảng `farm_account_info` và `snapshots` trong SQLite `D:/Taadaa/data/tiktok_tracker.db`.
  - Nếu nick thứ 8 (ví dụ `@trinhgiang7694` hay `@baomai0316` trên M24) có `status = 'LIVE'` và thuộc quyền sở hữu của máy đó $\rightarrow$ ĐÂY LÀ TÀI SẢN FARM BỊ LỆCH MAPPING EXCEL.
  - **Hành động chuẩn:** Không can thiệp thiết bị; thực hiện backfill đồng bộ ngay vào cả 4 file master (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik7.xlsx`, `Tik8.xlsx`).

### 2.3. Điều Phối Subagent (Gate 1 & Gate 5)
- **CẤM dispatch gộp nhiều máy vật lý vào 1 worker subagent:** Thao tác ADB + mở app + chuyển nick + Settings + cuộn trang trên 3-4 máy vật lý tuần tự chắc chắn vượt quá ngân sách 600s/15 tool calls dẫn đến timeout.
- **Quy chuẩn:** Phân rã theo từng máy độc lập (1 subagent per device) hoặc tách riêng nhánh sửa file Excel (vài giây) khỏi nhánh can thiệp thiết bị vật lý.

### 2.4. Vá Lỗi False-Positive Đếm Nhầm Nút "Thêm tài khoản" (Case Máy 3)
- **Hiện tượng:** Máy chỉ có đúng 7 tài khoản chuẩn, nút "Thêm tài khoản" vẫn hiện ở đáy Switcher, nhưng hàm `tap_add_account` vẫn quăng `MACHINE_FULL_8_ACCOUNTS`.
- **Cơ chế:** Nút "Thêm tài khoản" mang cùng resource-id (`lli`, `lrq`) với account rows. `_acc_count` đếm 7 nick + 1 nút = 8 nodes >= 8.
- **Code Fix:**
  ```python
  _acc_count = sum(
      1 for _n in _root.iter("node")
      if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
      and not any(x in (_n.attrib.get("text", "") + _n.attrib.get("content-desc", "")).lower() for x in ["thêm tài khoản", "add account", "add another"])
  )
  ```
- **Test:** Đã kiểm thử hồi quy 4 test cases trong `tests/test_acc_count_exclude_add_btn.py` (pass 100%).

### 2.5. Unit Test Hồi Quy Cho Selector Popup Đăng Xuất (`tests/test_parasite_reconcile_dialog.py`)
Đảm bảo các biến thể selector không bị suy thoái khi cập nhật logic đăng xuất ký sinh trong `watchdog_idle_parasite_reconcile.py`:
- Test 1 (`test_confirm_node_a6d_and_bounds`): Bắt trúng node `a6d` với bounds `[0,1584][1080,1740]` hoặc `[48,1632][1032,1692]` cùng text 'Đăng xuất'.
- Test 2 (`test_confirm_node_a6e_backward_compatibility`): Duy trì tương thích ngược với phiên bản app cũ chứa resource-id `a6e`.
- Test 3 (`test_confirm_node_without_logout_text_or_matching_id_returns_none`): Dialog chứa nút hành động khác (vd: "Hủy") không bị nhận nhầm thành nút đăng xuất (trả về `None`).
- Lệnh chạy: `pytest D:/Taadaa/tools/tests/test_parasite_reconcile_dialog.py -q` (3 passed).

