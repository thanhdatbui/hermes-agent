# Case 124: Tự Động Nhận Diện Candidate Placeholder `user...` Trong Account Switcher & Hạ Modal Khi Thiếu Tài Khoản (06/09/2026, Sự Cố Máy 5 - Nick `stevemgjqec`)

## 1. Hiện Tượng & Triệu Chứng Lỗi
- **Thiết bị:** Máy 5 | Serial: `9885e64b4a434a3037` | Nick: `stevemgjqec` (Row 2, Ca 1 06/09/2026).
- **Quy trình:** Feed Session Smoke (`multi-machine-feed-session` / `feed-session-smoke` trong repo `tiktok-luot nuoi acc`).
- **Triệu chứng báo cáo:** Dừng phiên với lỗi `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.
- **Hiện trường thực tế khi inspect:** Màn hình hiện popup / bottom-sheet "Chuyển đổi tài khoản" đang mở. Danh sách có 7 tài khoản nhưng không có handle `stevemgjqec`, chỉ có một tài khoản hiển thị dạng `user1196792370966` và nút "+ Thêm tài khoản".

---

## 2. Nguyên Nhân Cốt Lõi (3 Anti-Patterns)
1. **Placeholder Username (`user\d+`):** TikTok đôi khi hiển thị username tạm dạng placeholder `user\d+` (do lag cache tên người dùng hoặc tài khoản chưa cập nhật display handle trên switcher). Script chỉ tìm kiếm exact match theo `expected_account` nên trả về `None` và dừng phiên `manual-needed`, không nhận diện được tài khoản thực sự đã có trên máy.
2. **Kẹt Modal Account Switcher:** Khi không tìm thấy tài khoản trong switcher, script không gửi lệnh hạ modal (phím Back `keyevent 4`) trước khi chuyển sang nhánh recovery login hoặc trước khi thoát flow, khiến modal switcher che khuất giao diện và kẹt luồng recovery.
3. **PowerShell Scoped Variable Trap:** Cú pháp chuỗi `${m}:` trong `run-feed-session.ps1` bị lỗi cú pháp biến phạm vi drive trên PowerShell (`$m:` gây `InvalidVariableReferenceWithDrive`).

---

## 3. Giải Pháp Chuẩn Hóa
1. **Helper Quét Candidate Placeholder (`_find_user_placeholder_switch_option`):**
   - Quét danh sách node trong UI XML, nhận diện các ứng viên có `text` hoặc `content_desc` khớp regex `^user\d+$` (không phân biệt hoa thường).
   - Tính toán `bounds` và `center` hợp lệ từ XML.
2. **Fallback Chọn Placeholder Trong `verify_and_switch_profile`:**
   - Khi `_find_account_switch_option` trả về `None`, kích hoạt nhánh fallback tìm `_find_user_placeholder_switch_option`.
   - Nếu tìm thấy: tự động chọn candidate này (`action="try_user_placeholder_account"`), tap chuyển sang và điều hướng vào Profile để đọc, xác thực lại username/display name thực tế.
   - Nếu profile khớp với nick mục tiêu, coi như switch thành công và tiếp tục session.
3. **Hạ Modal Switcher Bằng Keyevent 4 (Back):**
   - Bổ sung gửi phím Back `keyevent 4` kèm log `dismiss_switcher_on_missing_account` để hạ modal switcher khi phát hiện thiếu account trước khi kích hoạt recovery login hoặc trước khi thoát flow.
4. **Sửa Cú Pháp PowerShell:**
   - Thay thế `${m}:` bằng cú pháp an toàn `$($m):` hoặc `${m}` tách rời để tránh lỗi scope drive trên PowerShell.

---

## 4. Kiểm Thử & Verification
- Unit test suite: `python_runner/tests/test_user_placeholder_switcher.py` pass 3/3 tests.
- Live Canary Test B4: Chạy thực tế trên Máy 5 Row 2 (`run-feed-session.ps1 -Machines 5 -Row 2 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`) hoàn thành 2/2 swipes thành công với `exit code 0`, `status: success`. Log xác nhận chọn `user1196792370966`, verify profile khớp `@stevemgjqec` (Display name: `Linh Chau1`), artifacts `20260906-111303`.
