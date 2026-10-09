# Ensure Row Accounts Positional Syntax, False-Positive Exit 0, & Gmail Clean Purge Invariant (2026-10-04)

## 1. Cú pháp gọi bắt buộc: Positional Argument `row`
- **Vấn đề**: `python D:/Taadaa/tools/ensure_row_accounts.py --row 8 --machines 3` sẽ văng lỗi ngay do argparse: `unrecognized arguments: --row 8` (exit 2).
- **Nguyên nhân**: Trong `ensure_row_accounts.py`, `row` được định nghĩa là positional argument (`choices=range(1, 9)`), không phải option flag.
- **Cú pháp chuẩn**:
  ```bash
  python D:/Taadaa/tools/ensure_row_accounts.py <row> --machines <M> [--dry-run]
  # Ví dụ cho Row 8 Máy 3:
  python D:/Taadaa/tools/ensure_row_accounts.py 8 --machines 3 --dry-run
  python D:/Taadaa/tools/ensure_row_accounts.py 8 --machines 3
  ```

---

## 2. Bẫy False-Positive Exit 0 ("Khong co tracking result moi de merge")
- **Hiện tượng**:
  ```text
  [ensure_row] Row 8: Phat hien 1 may chua co tai khoan: [3]
  [ensure_row] Toan bo 1 may thieu acc da co san mail hop le.
  [ensure_row] Khoi dong TikTok Reg batch cho 1 may: 3
  [ensure_row] Batch Reg ket thuc voi exit code 0
  [ensure_row] Khong co tracking result moi de merge.
  ```
  Quá trình chỉ mất ~20s, exit code 0, nhưng không có tài khoản TikTok nào được tạo!
- **Nguyên nhân cốt lõi**:
  1. `ensure_row_accounts.py` gọi subprocess `_run_all_targets.py`.
  2. `_run_all_targets.py` kích hoạt `_detect_clean.py` để tìm target email cho các máy.
  3. `_detect_clean.py` kiểm tra `device-locks` tập trung tại `C:/Users/Kibe/.codex/device-locks`.
  4. Nếu máy đang có lock active (ví dụ: ca nuôi `tiktok-luot nuoi acc` giữ lock `status=queued_v2` hoặc `status=running`), `_detect_clean.py` ghi nhận:
     `Skipped by device lock before selection cap: STT=M: DEVICE_LOCK_PRESENT status=queued_v2`
  5. Khi đó `Targets: 0`. File `_clean_targets.json` ghi ra `[]`.
  6. `_run_all_targets.py` không có target nào để spawn worker, thoát bình thường với exit code 0 (`all_results.json: []`).
- **Kỷ luật kiểm chứng (Verification Invariant)**:
  - Exit code 0 của `ensure_row_accounts.py` **KHÔNG ĐỒNG NGHĨA VỚI THÀNH CÔNG**.
  - Bắt buộc kiểm tra `all_results.json` có entry thành công không và readback trực tiếp cả 2 file:
    `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` và `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx`.
  - Phải có ảnh Account Switcher (`MEDIA:...`) chứng minh nick mới đã xuất hiện trên app.

---

## 3. Kỷ Luật Purge DIE Kho Mail & Làm Sạch Slot Safe Workbook (User Directive 2026-10-04)
- **Quy chuẩn `gmail_clean_v2.xlsx`**:
  - `gmail_clean_v2.xlsx` **TUYỆT ĐỐI CHỈ ĐƯỢC PHÉP LƯU GMAIL / HOTMAIL LIVE**.
  - Khi mail bị DIE (bao gồm checkmail.live báo DIE hoặc Google Challenge Phone `challenge/iap` đòi số điện thoại), **CẤM TUYỆT ĐỐI** chỉ đổi cột 11 thành "DIE" rồi để lại dòng trong file.
  - **Bắt buộc**: Xóa hoàn toàn dòng chứa email đó (`ws.delete_rows(r, 1)`). Toàn bộ lịch sử DIE chỉ được lưu tại `D:/OneDrive/TaadaaData/kibe/gmail_die_tong.txt`.
- **Quy chuẩn làm sạch slot `taikhoan_run_safe.xlsx`**:
  - Khi nick bị khai tử, phải gán ô ID thành rỗng `""` (kèm xóa video count và ngày tạo), **CẤM để lại chuỗi `<id>_DIE`**.
  - Nếu để lại `<id>_DIE`, hàm `get_missing_machines_for_row` trong `ensure_row_accounts.py` sẽ coi ô đó có dữ liệu và kết luận *"Toan bo may da day du tai khoan"*, bỏ qua việc reg bù!
- **Đồng bộ `taikhoan_dat_v2_updated .xlsx`**:
  - Phải xóa trắng trường `ID` tương ứng trong sheet `Tài Khoản` để tránh script `sync-safe-workbook.py` nhặt lại chuỗi cũ và điền ngược lại vào `taikhoan_run_safe.xlsx`.

---

## 4. Allowlist Coordinator Cho `ensure_row_accounts.py`
- Trong file `D:/Taadaa/tools/hooks/guard_dispatch_contract.py`, hàm `coordinator_terminal_gate` áp dụng cơ chế default-deny cho terminal session chính.
- Allowlist Case C regex hợp lệ:
  ```python
  re.match(r"^(?:python(?:\.exe)?\s+(?:-m\s+pytest\b|D:/Taadaa/tools/(?:inspect_machine|closeout_gate|done_gate|cage_gate|ensure_row_accounts)\.py\b|[\w\-/:\\\.]+\.py\b)|pytest(?:\.exe)?\b)", ...)
  ```
