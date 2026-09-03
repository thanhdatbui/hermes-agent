# Feed Session Common Errors & Handling

## 1. manual-needed:account-switcher-not-open
- **Triệu chứng**: `manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`.
- **Nguyên nhân**: Quá trình chuyển tài khoản trên TikTok chạm vào anchor header (tên tài khoản ở màn hình Profile) nhưng popup / bottom sheet danh sách tài khoản không bật lên hoặc bị miss tap do độ trễ UI/animation.
- **Hành vi an toàn**:
  1. Giữ hiện trường, không tự ý clear app data hay tap mù liên tục.
  2. Screencap hiện trạng màn hình và gửi ảnh thật `MEDIA:<path>` cho user.
  3. Báo cáo rõ trạng thái hiện tại (máy đang ở Profile hay Feed, nick hiện tại).
  4. Chờ chỉ thị từ user trước khi thực hiện hành động tiếp theo.
