# Canonical Sheet Isolation, Direct Switcher Selection & Closeout Gate Resolution (2026-09-25)

## 1. Bẫy Nạp Nhầm Sheet Phụ / Audit Trong Workbook Tracking (`taikhoan_dat_v2_updated .xlsx`)

### Triệu chứng
Khi chạy `tiktok_login_v1.py <STT> --email <target>`, script bị crash ngay ở bước preflight với lỗi:
```text
STOPPED: Khong tim thay Gmail live tren may khop local-part '<local_part>' de xac nhan domain
```
dù tài khoản mục tiêu trong sheet chính chủ `Tài Khoản` có đầy đủ ID, TikTok Pass, 2FA TOTP và full email `@gmail.com`.

### Root Cause
1. Hàm `load_tracking_accounts_for_stt` lặp qua toàn bộ `wb.worksheets`.
2. File Excel tracking thường có các sheet phụ như `Khong Co Trong GmailClean`, `Máy Thiếu Acc`, `Audit Pending`.
3. Trong sheet audit `Khong Co Trong GmailClean`, cùng tài khoản đó bị ghi dạng khuyết domain (VD: `duongthimyngoc190320011903`), khiến parser gắn cờ `email_missing_domain`.
4. Hàm `resolve_missing_domains_from_device` thấy cờ `email_missing_domain` nên cố kết nối thiết bị để đọc Gmail live. Do Gmail này không nằm trên máy, script raise `RuntimeError` crash luôn luồng login.

### Giải pháp (Fix)
- **Isolate Canonical Sheets**: Chỉ đọc sheet canonical (`"Tài Khoản"` hoặc `"Accounts"`), loại trừ 100% sheet audit/nháp:
  ```python
  if "Tài Khoản" in wb.sheetnames:
      worksheets = [wb["Tài Khoản"]]
  elif "Accounts" in wb.sheetnames:
      worksheets = [wb["Accounts"]]
  else:
      worksheets = [
          ws for ws in wb.worksheets
          if ws.title not in ("Khong Co Trong GmailClean", "Máy Thiếu Acc", "Audit Pending")
      ] or [wb.active]
  ```
- **Fail-soft Domain Inference**: Nếu tài khoản đã có sẵn `id` + `tiktok_pass` và không chạy `--otp-only`, tự động suy luận domain `@gmail.com` thay vì crash khi Gmail live không tìm thấy.

---

## 2. Bẫy Thiếu Nút "Thêm tài khoản" Khi Nick Đã Nằm Sẵn Trong Switcher

### Triệu chứng
Máy bị dừng ca với lỗi `missing-expected`, nhưng khi gọi login nạp bù thì script dừng ở:
```text
STOPPED: [04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account', 'Thêm tài khoản khác', ...)
```

### Root Cause
1. Máy đã có đủ 8 nick trên app (trong đó có nick cần login, nằm ở cuối danh sách Switcher, VD `m.ngc4624` ở bounds `[0,1788][1080,1920]`).
2. TikTok app tự động ẩn nút "Thêm tài khoản" khi danh sách đạt 8 nick.
3. Script login cố định quy trình `go_to_profile` -> `open_account_dropdown` -> `tap_add_account`. Do nút "Thêm tài khoản" biến mất, script quăng lỗi timeout không tìm thấy nút.

### Giải pháp (Fix)
- Trong `ensure_login_entry_screen`, ngay sau khi mở dropdown Switcher:
  Quét XML danh sách nick đang có trong Switcher. Nếu phát hiện nick mục tiêu (`id` hoặc `login_email` local-part) đã có sẵn trên máy:
  - Bấm trực tiếp vào node của nick đó để switch profile (`already_logged_in`).
  - Trả về thành công ngay lập tức, không cố bấm "Thêm tài khoản" hay mở form đăng nhập.
- Bổ sung resource-id `ng8` vào bộ nhận diện account node trong Switcher của `social_reg_v1.py`.

---

## 3. Kỷ Luật Closeout Gate: Staged Diff & Loop Sửa Đến Khi APPROVED

### Bài học Closeout Gate
- **Staging Diff**: Khi working tree có thay đổi, `closeout_gate.py` nếu không thấy staged files sẽ fallback quét full thư mục `tests`, có thể dẫn đến timeout 300s đối với các bộ test lớn. Bắt buộc `git add <target_files>` trước khi chạy gate để `closeout_gate.py` nhận diện đúng focused tests chạy <30s.
- **Vòng lặp sửa đến khi APPROVED**: Invariant chốt phiên là bắt buộc Reviewer độc lập (Sol Auditor :20129) chấm Score >= 85 và Exit code 0. Nếu gate trả về Rejected / Test Failed, Agent PHẢI tiếp tục sửa code/test và re-run gate cho đến khi APPROVED, tuyệt đối không được báo dừng hay bỏ cuộc.
