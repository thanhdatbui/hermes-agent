# Hướng dẫn xử lý Preflight Reg Bù: Lệch Excel Backfill & Nick Ký Sinh (MACHINE_FULL_8_ACCOUNTS)

Tài liệu chuẩn hóa quy trình điều phối và khắc phục sự cố khi Preflight `ensure_row_accounts.py` báo lỗi:
`Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)` hoặc `RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS`.

---

## 1. Bản chất sự cố
- Tiến trình Preflight (`ensure_row_accounts.py <row>`) đọc file Excel `taikhoan_dat_v2_updated .xlsx` hoặc `taikhoan_run_safe.xlsx` thấy máy thiếu nick ở Row đó (ô `ID = None`).
- Hệ thống tự động kích hoạt script reg TikTok bổ sung (`_run_all_targets.py`).
- Khi TikTok mở menu **Chuyển đổi tài khoản (Switcher)** để bấm *"Thêm tài khoản"*, TikTok đếm thấy trên app đã có đủ **8 tài khoản** (đạt trần tối đa của TikTok) $\rightarrow$ Nút *"Thêm tài khoản"* bị ẩn hoàn toàn $\rightarrow$ Văng lỗi `MACHINE_FULL_8_ACCOUNTS`.

---

## 2. Quy trình điều phối O(1) & Phân loại nguyên nhân

Khi gặp lỗi này, **CẤM hỏi user trắc nghiệm rườm rà**. Coordinator lập tức:
1. Đọc ảnh chụp hiện trường dropdown Switcher trong `D:/Taadaa/Tiktok_Reg/screenshots_social/<machine>_03_dropdown_*.png` hoặc chụp screencap tươi.
2. Dùng WinRT OCR đọc danh sách tài khoản:
   ```bash
   python "C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py" "<screenshot_path>"
   ```
3. Đối soát 8 nick trên máy với dữ liệu Excel của máy đó:

### Trường hợp A: Nick chính chủ bị ghi nhầm máy / Sót dòng
- **Dấu hiệu:** Nick thứ 8 có trên thiết bị thật, từng được reg thành công trên chính máy này (có file `tracking_result_*.json` trong `D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/`), nhưng trên Excel lại bị lưu nhầm vào dòng của máy khác hoặc dòng Slot của máy này đang để trống (`None`).
  - *Ví dụ thực tế (22/09/2026):*
    - Máy 61 có nick `@anggiathinh2905` (reg ngày 26/08) nhưng Excel ghi nhầm ở Máy 28 (Row 222).
    - Máy 76 có nick `@cyennffqko8` (reg ngày 25/08) nhưng Excel ghi nhầm ở Máy 36 (Row 289).
- **Quy trình xử lý:**
  1. Tạo bản backup Excel có timestamp:
     `taikhoan_dat_v2_updated .xlsx.bak-backfill-m<N>-<timestamp>`
  2. Điền chính xác đầy đủ 10 cột cho slot đó của máy trên `taikhoan_dat_v2_updated .xlsx` (ID, PASS, GMAIL, PASS MAIL, NGÀY TẠO, SERIAL...).
  3. Xóa ô duplicate ở dòng máy bị ghi nhầm về `None`.
  4. Chạy đồng bộ sang safe workbook:
     ```bash
     D:/Taadaa/python-envs/automation/Scripts/python.exe "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py"
     ```
  5. Verify readback và chạy `python -c "from ensure_row_accounts import get_missing_machines_for_row; print(get_missing_machines_for_row(<row>))"` để chắc chắn máy đã thoát khỏi danh sách thiếu.

---

### Trường hợp B: Nick ký sinh (Parasite Account) từ máy khác
- **Dấu hiệu:** Thiết bị có 7 nick chính chủ đúng theo Excel, nhưng nick thứ 8 lại thuộc quyền sở hữu của máy khác (ví dụ: Máy 3 có `@anhhoang7786` chính chủ thuộc Máy 14).
- **Nguyên tắc xử lý: DÙNG SCRIPT CÓ SẴN TRONG `D:/Taadaa/tools/`, CẤM TỰ VIẾT LẠI TAY!**
  - Script logout đơn máy:
    ```bash
    python D:/Taadaa/tools/do_logout_account.py <machine_id> <username> <serial>
    ```
  - Script đối soát & logout đa máy:
    `D:/Taadaa/tools/run_logout_all.py`

#### ⚠️ PITFALL HIỂM HÓC: Item 8 bị cắt đáy màn hình trên Samsung S7 (SM-G930F)
- Màn hình S7 có độ phân giải 1080x1920. Mỗi account item trong bottom sheet Switcher cao ~216px.
- **Item thứ 8 nằm tại bounds `[0, 1788][1080, 1920]`**, sát mép dưới màn hình.
- Accessibility tree (atx-agent) và OCR thường **KHÔNG đọc được** hoặc đọc sót text của item 8 do bị che khuất một phần.
- **BẮT BUỘC:** Khi vừa mở Account Switcher bottom sheet, phải gửi 1 swipe nhẹ lên trên 500px:
  ```python
  run_adb(['shell', 'input', 'swipe', '540', '1500', '540', '1000', '300'])
  ```
  Thao tác này đẩy Item 8 lên vùng giữa màn hình (y ≈ 1300), giúp atx-agent đọc được node và tap trúng 100%.

---

## 3. Checklist an toàn bắt buộc khi can thiệp thiết bị (Invariants)
1. **Device Lock:** BẮT BUỘC bọc trong `acquire_device_lock(machine=N, serial=..., project='tiktok-reg', user_authorized=True)`.
2. **Session Exclusivity:** Nếu máy đang giữ lock chạy ca chính (feed session / upload), CẤM can thiệp, chờ máy rảnh.
3. **Capture-Before-Cleanup:** Chụp ảnh nghiệm thu Switcher chứng minh nút *"Thêm tài khoản"* đã hiển thị lại và nick ký sinh đã biến mất TRƯỚC KHI thực hiện `am force-stop` và `keyevent 3` về Home.
4. **Không hỏi rườm rà:** Khi user phát lệnh hoặc gửi alert, coordinator trực tiếp chẩn đoán và dispatch worker thực hiện trọn gói.
