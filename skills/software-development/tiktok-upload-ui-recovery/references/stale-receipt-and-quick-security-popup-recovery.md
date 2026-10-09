# Quy trình xử lý lỗi Stale Idempotency Receipt, Quick Security Popup & Tự động kích hoạt Login Recovery

## 1. Stale Post Intent Receipt (`COMPAT-POST-VERIFY-004`)
- **Triệu chứng**: Máy báo lỗi `POST_SUBMISSION_UNKNOWN` hoặc `MANUAL_REVIEW`, không thể đăng video dù tài khoản chưa từng đăng bài (`Video_Đã_Đăng = 0`).
- **Nguyên nhân**: Trong thư mục `D:\CodexRuntime\tiktok-video\idempotency\post-attempts`, tồn tại file receipt cũ (ví dụ: tạo từ các đợt test nhiều tuần trước) với `status: intent_pending`, `post_tapped_at: null`.
- **Cách xử lý an toàn**:
  1. Kiểm tra timestamp và thuộc tính `post_tapped_at`: nếu `post_tapped_at is null` và thời gian cách hiện tại > 24h, xác nhận video chưa từng được bấm Đăng.
  2. Backup và đổi đuôi sang `.bak-stale-intent-<date>`.
  3. Giải phóng khóa media fingerprint tương ứng nếu cần.
  4. Chạy lại workflow đăng video.

## 2. Popup Bảo Mật Mới của TikTok (`quick_security`)
- **Triệu chứng**: Script bị kẹt ở `ACCOUNT_READY` hoặc `ACCOUNT_SWITCHER` với lỗi `ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account`.
- **Màn hình thực tế**: Modal popup xuất hiện có text *"Hãy cùng kiểm tra bảo mật nhanh nhé"* (`quick_security_title`) và nút đóng X không nhãn (unlabeled) ở góc trên bên phải `[936,857][1056,989]`.
- **Bản vá cốt lõi**:
  - Trong `automation-core/src/automation_core/tiktok/benign_popup.py`: Bổ sung `or detect_quick_security_popup(root)` vào hàm `detect_allowed_generic_popup()`.
  - Kiểm chứng bằng pytest: `pytest test_tiktok_benign_popup.py -k "quick_security"`.

## 3. Khôi phục tự động đăng nhập khi thiếu Nick trên App
- **Triệu chứng**: Switcher quét danh sách tài khoản nhưng không thấy nick cần chạy (`ACCOUNT_MISSING`).
- **Cạm bẫy**:
  - Không được suy đoán sai serial hoặc nhầm lẫn giữa log chạy song song của nhiều máy. Luôn kiểm tra trực tiếp qua ADB (`screencap` hoặc dump XML) trên chính serial của máy đó.
  - Khi app có đủ 8 tài khoản, nút "Thêm tài khoản" bị ẩn. Bắt buộc kiểm tra kỹ số tài khoản thực tế trên máy trước khi kết luận nick bị thiếu hay máy đã đầy.
- **Công cụ cầu nối chuẩn**:
  - Sử dụng `D:/Taadaa/tools/recover_missing_tiktok_login.py --machine <N> --account <user>`.
  - Cần truyền cờ `--allow-parent-lock` khi kế thừa lock từ các phiên điều phối mẹ.
