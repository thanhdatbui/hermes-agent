# Samsung MTP USB Popup Permanent Disable & TikTok 8-Account Limit / Deferred Sync Root Cause (2026-09-20)

## 1. Tắt Vĩnh Viễn Popup Samsung USB Connection (`com.samsung.android.MtpApplication`)
- **Triệu chứng**:
  - Máy farm (Samsung Galaxy S7) khi cắm cáp USB, điện áp USB hub chập chờn, hoặc máy khởi động lại tự động bật dialog toàn màn hình của `com.samsung.android.MtpApplication/.USBConnection`:
    *"Chú ý: Thiết bị được kết nối không thể truy cập dữ liệu..."*.
  - Dialog này cướp focus của app, chặn phím bấm, và làm treo hoặc timeout các lệnh ADB (`[adb-timeout] device=... timeout=20`).
- **Giải pháp triệt để (Permanent Disable)**:
  - Chạy lệnh ADB vô hiệu hóa package `MtpApplication` trên user 0:
    ```bash
    adb -s <serial> shell pm disable-user --user 0 com.samsung.android.MtpApplication
    ```
  - Sau lệnh này, package chuyển sang state `disabled-user`. Popup USB không còn xuất hiện vĩnh viễn kể cả khi cắm/rút cáp hay reboot máy.

---

## 2. Root Cause Trùng Lặp 8 Tài Khoản & Lỗi Ẩn Nút "Thêm Tài Khoản"
- **Triệu chứng trên farm khi chạy Reg bù Row 8**:
  - Nhóm 1: Báo `[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`.
  - Nhóm 2: Báo `[04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account'...)`.
- **Cơ chế thực tế trên app TikTok**:
  - TikTok giới hạn cứng tối đa 8 tài khoản đăng nhập cùng lúc trên 1 thiết bị.
  - Khi đã có đủ 8 tài khoản, **TikTok tự động ẩn hoàn toàn nút "Thêm tài khoản"** khỏi bottom-sheet Switcher.
  - **Lý do ném 2 lỗi khác nhau**:
    - Bản TikTok cũ: Các node tài khoản mang resource-id cũ (`lli`, `n72`, `lkp`), hàm `_acc_count` đếm ra 8 -> raise `MACHINE_FULL_8_ACCOUNTS`.
    - Bản TikTok mới (46.x): Resource-id bị đổi obfuscated (`omm`, `omr`, `onj`, `oms`...), danh sách hardcode cũ đếm ra 0 nick. Nhưng vì nút "Thêm tài khoản" đã bị TikTok ẩn do đủ 8 nick, hàm tìm nút thất bại và ném `Không tìm thấy: ('Thêm tài khoản'...)`. Thực chất cả 2 lỗi đều do máy đã có đủ 8 nick.

---

## 3. Nguyên Nhân Gốc Reg Trùng Hàng Loạt & Không Ghi Excel
- **Nguyên nhân kiến trúc cũ (trước commit `fc80f09` ngày 17/09/2026)**:
  - `_run_all_targets.py` trước đây cấu hình chế độ "proof-only launcher":
    ```python
    for target in targets:
        if target.get('status') == "SUCCESS" and target.get('result_json'):
            target['workbook_write'] = "NOT_ATTEMPTED_BY_LOCAL_LAUNCHER"
    ```
  - Kết quả đăng ký chỉ được xuất ra file JSON tạm trên ổ cứng (`D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\...\tracking_result_*.json`) chứ không tự động đồng bộ vào `taikhoan_dat_v2_updated .xlsx`.
  - Do file Excel không được cập nhật, slot Row 8 vẫn hiển thị là `None`. Các lần chạy reg bù quét Excel thấy thiếu nick nên tiếp tục dispatch máy đi reg lại. Khi vào app, nick đã có sẵn từ đợt trước + 7 nick cũ = đủ 8 nick -> kẹt lỗi 8 tài khoản.
- **Các bản Git đã vá**:
  - `fc80f09` (17/09/2026): Tự động nạp `write_deferred_results_sequential` để sync thẳng toàn bộ kết quả SUCCESS từ JSON vào Excel sau khi kết thúc batch.
  - `7a50627` (17/09/2026): Tự động fallback sang slot trống tiếp theo nếu row dự kiến bị occupied/trôi.
  - `61181f4` (17/09/2026): Cập nhật đếm 8 account cho tap_add_account.

---

## 4. Quy Tắc Xử Lý Dữ Liệu Nick Ký Sinh / Reg Dở
- **Invariant Tài sản Farm**:
  - Mọi nick trên máy đều là tài sản user. CẤM tự ý xóa/logout khi chưa đối chiếu.
  - Tra cứu nick dư trên máy trong kho JSON deferred tracking (`D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all`).
  - Nếu nick có file JSON lưu info đầy đủ (email, password mail, password tiktok) và kiểm tra chỉ xuất hiện độc quyền trên đúng 1 máy đó (không trùng máy khác): **Tiến hành backfill trực tiếp vào Row 8 của máy trong Excel (`taikhoan_dat_v2_updated .xlsx` và `Tik8.xlsx`)**, tiết kiệm tài nguyên reg mới.
