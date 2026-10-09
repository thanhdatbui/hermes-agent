# Phòng vệ 2 Lớp Trần 8 Tài Khoản, Chống Trùng Mail Kho & Khắc Phục Lệch Nick (08/09/2026)

## Bối cảnh sự cố đêm 08/09/2026

1. **Hiện tượng vỡ chuỗi reg đêm:**
   - Máy STT 03 báo lỗi crash `RuntimeError` do TikTok ẩn nút "Thêm tài khoản".
   - Kiểm tra UI XML dump (`fail_04_add_account_012059.xml`): app TikTok máy 03 đã đầy cứng 8 tài khoản (`anderyepax4`, `ninhy05100`, `trangtran168432`, `lequynh2043`, `kylarpwp2ht`, `verasdhkn0r`, `brifeqme954` và `miumiu67971`).
   - Trên file Excel `taikhoan_dat_v2_updated .xlsx`: Máy 03 chỉ map 7 nick, dòng 24 trống. Nick `miumiu67971` lại đang được map cho Máy 05 (Row 39).
   - Kiểm tra thực tế trên thiết bị: Cả Máy 03 và Máy 05 ĐỀU ĐANG CHỨA nick `miumiu67971`.

2. **Truy vết nguyên nhân gốc rễ:**
   - **Nạp trùng mail vào kho `gmail_clean_v2.xlsx`:** Sáng 26/08, khi crawl lại 62 đơn hàng từ shop web, script lấy danh sách đã mua (có cả đơn cũ ngày 25/08) `zip()` gán cào bằng cho các máy thiếu mà KHÔNG kiểm tra `if email not in existing_clean_emails`. Hậu quả: `karistinelso@hotmail.com` bị gán ở dòng 22 (Máy 03, ngày 25/08) và lại bị gán tiếp ở dòng 39 (Máy 05, ngày 26/08).
   - **Chạy song song & Deferred Apply race condition:** Sáng 26/08 Máy 05 reg thành công `miumiu67971` lúc 08:02. Máy 03 chạy lúc 09:48 thấy mail `karistinelso` chưa ghi vào Excel nên login thẳng vào `miumiu67971`. Khi merge kết quả deferred, tool lấy file có timestamp mới nhất (`written_at: 10:45 > 09:56`) nên ghi đè Máy 05 vào Excel, bỏ rơi Máy 03.
   - **Đọc sai sheet khi Preflight:** Hàm `load_registered_mailboxes` dùng `_active_worksheet(workbook)`. Nếu file Excel được mở/lưu ở sheet khác (không phải `'Tài Khoản'`), openpyxl đọc nhầm sheet đó trả về rỗng -> Preflight tưởng toàn farm 0 tài khoản -> bốc máy đã đầy tài khoản đi reg tiếp.

---

## 4 Quy Tắc Kiến Trúc Bắt Buộc

### 1. Khử trùng lặp tuyệt đối khi nạp mail vào kho `gmail_clean_v2.xlsx`
- BẤT KỲ script nào nạp email (từ web crawl, file text, hay API mua) BẮT BUỘC phải đối chiếu khử trùng lặp:
  ```python
  existing_clean_emails = {
      str(ws.cell(r, 2).value).strip().lower()
      for r in range(2, ws.max_row + 1)
      if ws.cell(r, 2).value
  }
  # Chỉ nạp email nếu CHƯA TỪNG xuất hiện trong kho
  valid_to_append = [acc for acc in new_accs if acc['email'].lower() not in existing_clean_emails]
  ```
- TUYỆT ĐỐI CẤM lấy danh sách crawl cũ rồi `zip()` gán cào bằng theo STT máy thiếu (`assigned_machines`).

### 2. Preflight Target Eligibility: Đọc Sheet Tường Minh
- Trong `scripts/tiktok_target_eligibility.py` (và mọi reader đọc master tracking `taikhoan_dat_v2_updated .xlsx`):
  - BẮT BUỘC ép cứng đọc sheet `'Tài Khoản'`:
    ```python
    sheet_name = 'Tài Khoản'
    if sheet_name in workbook.sheetnames:
        worksheet = workbook[sheet_name]
    else:
        worksheet = _active_worksheet(workbook, label)
    ```
  - CẤM dùng bare `workbook.active` vì sheet active bị phụ thuộc vào thao tác lưu cuối cùng của người dùng hoặc tool khác.

### 3. Phòng Vệ 2 Lớp Trần 8 Tài Khoản (Dual-Layer 8-Account Limit Defense)
- **Lớp 1 (Preflight Gate - Excel):**
  - Đọc đúng sheet `'Tài Khoản'`, đếm chính xác số nick TikTok đã có (`tiktok_id is not None`).
  - Máy có $\ge 8$ accounts BẮT BUỘC bị loại trừ ngay từ khâu preflight (`MAX_ACCOUNTS_PER_MACHINE = 8`), không bao giờ cấp target reg.
- **Lớp 2 (Runtime Device Gate - TikTok UI):**
  - Trong `social_reg_v1.py` (tại bước bung Account Switcher dropdown / `tap_add_account`):
    * Hạ ngưỡng width lọc bounding box của nickname từ $\ge 220\text{px}$ xuống $\ge 120\text{px}$ để nhận diện đầy đủ các nick ngắn ($\le 3$ ký tự như "Hà" 168px).
    * TikTok làm rối (obfuscate) resource-id của các dòng tài khoản theo phiên bản cập nhật: `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"]`.
    * Quét toàn bộ node trong UI XML khớp bất kỳ resource-id nào trong danh sách trên. Nếu đếm $\ge 8$ accounts:
      ```python
      _acc_count = sum(
          1 for _n in _root.iter("node")
          if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
      )
      if _acc_count >= 8:
          keyevent(device_id, 4, wait=D_SHORT)  # dismiss dropdown
          keyevent(device_id, 3, wait=0.5)      # go home
          raise RuntimeError("[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok")
      ```
  - Tránh hoàn toàn việc TikTok ẩn nút "Thêm tài khoản" làm script văng `RuntimeError: Khong tim thay nut Them tai khoan` gây vỡ batch.

### 4. Xử lý Popup Hệ thống "Cho phép gỡ lỗi USB" (USB Debugging Prompt)
- Khi thiết bị cắm lại cáp hoặc reset daemon adb, hộp thoại hệ thống *"Cho phép gỡ lỗi USB?"* ("Allow USB debugging") có thể bật đè lên màn hình TikTok hoặc xuất hiện khi lost foreground trong `wait_login_success`.
- `dismiss_usb_debugging_dialog(device_id, xml=None)`:
  * Nhận diện markers: `"cho phep go loi usb"`, `"allow usb debugging"`, `"luon cho phep tu may tinh nay"`, `"always allow from this computer"`.
  * Tích chọn checkbox "Luôn cho phép từ máy tính này" / "Always allow from this computer".
  * Bấm nút "OK" (hoặc fallback tọa độ 890, 1140 trên 1080x1920).
  * Tích hợp vào `_dismiss_system_popups()` và 2 vị trí trong vòng lặp `wait_login_success` (trước check package và khi lost foreground về Launcher).

### 5. Xử Lý Khi Phát Hiện 1 Nick Nằm Trên 2 Máy
- Khi đối soát phát hiện 1 nick xuất hiện trên cả 2 thiết bị:
  1. Kiểm tra đối chiếu app TikTok thật trên cả 2 máy bằng ATX/screencap.
  2. Giữ nick trên máy đang được nuôi / chạy feed / upload ổn định theo Excel.
  3. Đăng xuất nick khỏi máy bị đăng nhập ké/nhầm (đưa máy về đúng số lượng tài khoản thực tế để sẵn sàng nhận target reg mới).
  4. Báo cáo bằng chứng ảnh và trạng thái cho người dùng trước khi thực hiện thay đổi phá hủy.
