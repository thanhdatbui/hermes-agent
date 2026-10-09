# Khai Tử Case Docs Thủ Công vs Regression Gate Tự Động & Bằng Chứng Thị Giác Avatar Crop

## 1. Khai tử `farm-automation-cases.md` chuyển sang Regression Gate tự động (08/10/2026 Operator Correction)
- **Chỉ thị của Operator:** Hệ thống farm đã khai tử và bỏ hoàn toàn việc ghi chép case tài liệu thủ công (`docs/farm-automation-cases.md` từ thời uiautomator cũ).
- **Cơ chế thay thế chuẩn:** Toàn bộ việc chống hồi quy (Anti-Regression) được giao phó 100% cho **Regression Gate tự động**:
  * Chạy test suite offline chuyên biệt của từng repo (`tests/test_avatar_edit_and_milestone.py`, `tests/test_profile_golden.py` trên `Tiktok-video`; `python_runner/tests/` trên `tiktok-luot nuoi acc`; `follow_runner/tests/` trên `tiktok-follow`).
  * Thẩm định độc lập qua `closeout_gate.py` (Sol Reviewer chấm $\ge 85/100$).
- **Bẫy Pre-Commit Hook cũ chặn Commit (Rule R2):**
  * Trong repo `Tiktok-video`, hook vật lý `.git/hooks/pre-commit` vẫn có thể đang gọi `tools/guard_selector_change.py`.
  * Guard cũ này còn sót Rule R2: bắt buộc mọi thay đổi trong `profile_layouts/` phải cập nhật `docs/farm-automation-cases.md` và sinh golden dump.xml.
  * **Xử lý chuẩn:** Tuyệt đối KHÔNG tự ý bịa thêm case mới vào docs (như Case 105)! Dùng `git commit --no-verify` để bỏ qua hook cũ, đảm bảo test hồi quy offline đạt 34/34 PASS và đưa thẳng qua Closeout Gate để thẩm định.

## 2. Bẫy Ảnh Teardown Launcher vs Ảnh Crop Screen Trong Avatar Smoke (`avatar-uploaded-confirmed.png`)
- **Hiện tượng:** Runner `state_machine.py` trong chế độ Avatar Smoke sau khi upload thành công sẽ gọi dọn dẹp:
  ```text
  [INFO] [ENSURE_AVATAR] Da force-stop TikTok va dua may ve Home
  [INFO] [CONNECT_DEVICE] Portrait rotation enforced: True
  [INFO] Recent apps đã đóng sạch và được automation-core xác nhận
  ```
- **Hậu quả:** File ảnh nghiệm thu cuối cùng `avatar-uploaded-confirmed.png` được chụp sau khi TikTok đã bị force-stop, nên ảnh chụp thực chất là màn hình **Launcher / Home** của Android (WinRT OCR đọc ra: *Danh bạ, Cài đặt, Điện thoại, Chrome, TikTok*).
- **Nhận diện bằng chứng đúng:**
  * File `avatar-save-surface-guard.png` trong thư mục run (`run_<serial>_<timestamp>/`) mới chính là ảnh chụp in-app lúc thực hiện thao tác cắt ảnh avatar trên TikTok (*"Cắt", "Đăng ảnh này lên Nhật ký", "Xem trước", nút Lưu [792, 1794]*).
  * Nếu cần screencap màn hình Profile sau upload để OCR username và avatar mới: BẮT BUỘC mở lại TikTok (`monkey -p com.ss.android.ugc.trill ...`), chờ app render Profile rồi mới screencap. Tránh nhầm lẫn màn hình Launcher sau teardown là lỗi mất phiên.

## 3. Phân Định Phạm Vi Regression Gate Giữa Các Repo
- Mỗi repo chịu trách nhiệm bộ test hồi quy của riêng mình:
  * `Tiktok-video`: `tests/test_avatar_edit_and_milestone.py` (34 tests), `tests/test_profile_golden.py` (18 tests).
  * `tiktok-luot nuoi acc`: `python_runner/tests/` (100+ tests).
  * `tiktok-follow`: `follow_runner/tests/` (17 tests).
  * `automation-core`: `tests/` (65 tests).
- `closeout_gate.py` tự động phát hiện đường dẫn test của repo mục tiêu để chạy và chấm điểm, không dùng test suite của repo này để đánh giá repo khác.
