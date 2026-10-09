# Lệch Pha Preflight Excel ↔ Thiết Bị Vật Lý, Giới Hạn 8 Acc TikTok & Quy Trình Xử Lý Trùng Acc (08/09/2026)

## 1. Hiện tượng & Vấn đề thực tế (Đợt chạy 08/09/2026)
- **Phase 2a (Reg TikTok)** fail hàng loạt 25/30 máy (83.3%) với mã `FAILED_EXIT_1`.
- **Nguyên nhân kép:**
  1. **STT 03**: Mở app TikTok bấm "Thêm tài khoản" bị văng `RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`.
     - Hiện trường XML (`fail_04_add_account_012059.xml`): Trong menu Switcher của TikTok trên máy đã có đủ **8 tài khoản**. App TikTok trên Android có giới hạn trần cứng là 8 tài khoản; khi đã có 8 tài khoản thì nút "Thêm tài khoản" hoàn toàn bị ẩn khỏi giao diện.
  2. **STT 02**: Kẹt tại bước mở dropdown (`fail_03_account_dropdown_012534.xml`) do tên hiển thị tài khoản là "Hà" (rộng 168px), trong khi điều kiện lọc cũ yêu cầu `(x2 - x1) >= 220`.

---

## 2. Lệch pha giữa Preflight (Excel) và Thiết bị thật (Device Reality)

### Tại sao Preflight không skip máy đã có 8 acc?
- Preflight (`select_pending_targets` trong `scripts/tiktok_target_eligibility.py`) đếm số tài khoản dựa vào file tracking Excel (`taikhoan_dat_v2_updated .xlsx` sheet `"Tài Khoản"`).
- Nếu một tài khoản đã được đăng ký hoặc đăng nhập lên điện thoại từ trước, nhưng trên file Excel:
  + Dòng đó bị để trống `None` (chưa sync về workbook), HOẶC
  + Dữ liệu bị ghi nhầm sang STT của máy khác (như trường hợp nick `miumiu67971` vốn đăng ký trên STT 03 nhưng bị ghi sang STT 05).
- Khi đó:
  + Excel chỉ ghi nhận máy 03 có **7 tài khoản** (Row 24 đang trống).
  + Preflight kiểm tra điều kiện `counts.get(stt, 0) >= max_accounts_per_machine` (7 >= 8) $\rightarrow$ `False`.
  + Preflight kết luận máy 03 còn trống 1 slot và điều phối máy 03 đi đăng ký acc thứ 8.
  + Nhưng khi runner mở app TikTok lên, app đã có đủ 8 acc $\rightarrow$ giấu nút Add Account $\rightarrow$ crash.

### Cơ chế phòng thủ 2 tầng:
1. **Tầng 1 - Preflight (Workbook)**:
   - Trong `load_registered_mailboxes`: Ưu tiên đọc cứng sheet `"Tài Khoản"` (`if "Tài Khoản" in workbook.sheetnames`), tránh dùng `_active_worksheet` vì file Excel có thể bị lưu active sheet khác (như sheet Proxy, Sheet1) làm trả về count = 0.
2. **Tầng 2 - Device Gate tại Runtime (`tap_add_account` trong `social_reg_v1.py`)**:
   - Khi mở bottom sheet "Chuyển đổi tài khoản", sau các nhịp retry nếu không tìm thấy nút "Thêm tài khoản", BẮT BUỘC phân tích cấu trúc XML ngay tại chỗ:
     ```python
     _acc_count = sum(
         1 for _n in _root.iter("node")
         if "n72" in _n.attrib.get("resource-id", "") or "lkp" in _n.attrib.get("resource-id", "")
     )
     if _acc_count >= 8:
         log(f"   [04_add_account] Máy đã có {_acc_count} tài khoản — đạt giới hạn tối đa 8")
         keyevent(device_id, 4, wait=D_SHORT)  # dismiss dropdown
         keyevent(device_id, 3, wait=0.5)      # go home
         raise RuntimeError("[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok")
     ```
   - Tự động đóng dropdown, về Home an toàn và trả về lỗi có cấu trúc `MACHINE_FULL_8_ACCOUNTS`, không để crash mù unhandled exception.

---

## 3. Bản vá Selector Dropdown Tên Hiển Thị Ngắn
- Trong `_try_open_account_dropdown_once` (`social_reg_v1.py` dòng 2904):
  - Cũ: `if txt and not txt.startswith("@") and (x2 - x1) >= 220 and y2 <= 610...`
  - Mới: `if txt and not txt.startswith("@") and (x2 - x1) >= 120 and y2 <= 610...`
  - Lý do: Tên hiển thị người dùng tiếng Việt ngắn (Hà, Vy, An, Linh...) có độ rộng bounding box từ 140px đến 200px. Ngưỡng 220px loại trừ nhầm các tên này khiến dropdown không bao giờ được kích hoạt.

---

## 4. Quy trình điều tra tài khoản lệch máy / Trùng 2 máy (Duplicate Account Triage)

Khi phát hiện 1 tài khoản xuất hiện trên máy không khớp với Excel hoặc nghi ngờ trùng máy:

### Bước 1: Truy vết nguồn gốc đăng ký O(1)
- Không đoán mò hay quét toàn bộ đĩa.
- Tìm file artifact deferred tracking tương ứng:
  `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<ts>\batch_1\stt_<N>\tracking_result_stt<N>_<mail>.json`
- Đọc các trường nhận diện:
  + `stt`: Máy thực hiện đăng ký.
  + `serial`: Serial vật lý của điện thoại đã reg acc.
  + `tiktok_id`: Username TikTok được sinh ra.
  + `tracking_row`: Dòng dự kiến ghi vào Excel.
  + `proof_screenshot` & `proof_xml`: Bằng chứng hiện trường lúc reg.

### Bước 2: Kiểm tra thực tế thiết bị qua ATX JSON-RPC
- Dùng `dump_ui_atx.py <serial>` hoặc script inspect không bấm tay.
- Mở app TikTok $\rightarrow$ Profile $\rightarrow$ Account Switcher $\rightarrow$ Dump XML + Chụp ảnh screencap lưu `D:/Taadaa/reports/stt<N>_accounts.png`.
- Đối soát danh sách text node username thực tế trong switcher.

### Bước 3: Đối chiếu với Excel Quản Lý
- So sánh kết quả máy thật với `taikhoan_dat_v2_updated .xlsx` sheet `"Tài Khoản"` và `taikhoan_run_safe.xlsx`.
- **Nếu máy trên Excel KHÔNG chứa acc đó, nhưng máy khác chứa:** Cập nhật lại Excel để phản ánh đúng máy đang chứa tài khoản thực tế.
- **Nếu CẢ 2 MÁY CÙNG CHỨA TÀI KHOẢN ĐÓ:**
  + **DỪNG LẠI NGAY LẬP TỨC.** Tuyệt đối không tự ý xóa acc hay ghi đè Excel.
  + Lập báo cáo chi tiết gửi người dùng kèm đường dẫn ảnh bằng chứng `MEDIA:<path>` cho từng máy.
  + Trình bày rõ: Nick nào, nguồn gốc từ máy nào sinh ra, tại sao máy kia có (do cơ chế Reconcile auto-login theo Excel ghi nhầm), và xin chỉ đạo của người dùng.
