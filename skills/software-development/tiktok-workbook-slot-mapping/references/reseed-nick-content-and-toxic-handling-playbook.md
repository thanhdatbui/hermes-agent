# Playbook: Reseed Nick Content & Xử lý Kênh Bị Vi phạm / Dính Toxic Comment

Áp dụng khi một nick TikTok trên Farm cần đổi toàn bộ chủ đề / content (do dính vi phạm, dính chủ đề nhạy cảm chính trị/CSGT, bị phe độc hại vào chửi hoặc reup nhầm niche).

## 1. Nguyên tắc cốt lõi & Tư vấn an toàn cho User
- **BẮT BUỘC ẨN (Chuyển sang "Chỉ mình tôi" / Private), TUYỆT ĐỐI CẤM XÓA VIDEO HÀNG LOẠT**:
  - Xóa video hàng loạt sẽ kích hoạt thuật toán bất thường của TikTok $\rightarrow$ nick bị shadowban hoặc tụt trust chết hẳn.
  - Chuyển sang "Chỉ mình tôi" vừa bảo toàn toàn bộ Follower + Lượt thích cũ, vừa ngắt lập tức luồng phân phối công khai tới đối tượng toxic.
- **Trình tự thực thi không được đảo lộn**:
  1. Tư vấn user ẩn video trên app trước.
  2. Backup workbooks liên quan (`TikN.xlsx`, `taikhoan_run_safe.xlsx`).
  3. Dọn dẹp destructive đúng phạm vi: Xóa toàn bộ file trong thư mục nguồn cũ (`D:\video goc\<video_goc>`) và thư mục render cũ (`D:\TIKTOK-videonuoinick\<Folder Video>`).
  4. Dọn dẹp cache post-attempts idempotency (`D:\CodexRuntime\tiktok-video\idempotency\post-attempts\*<machine>_*`) để tránh xung đột cursor.
  5. Cấp nguồn mới: CUT (không COPY) từ thư mục spare có $\ge 45$ mp4 sạch chưa gán cho nick nào, hoặc download nguồn mới.
  6. Đồng bộ Workbooks: Reset `Video Đã Đăng = 0` ở cả `TikN.xlsx` và `taikhoan_run_safe.xlsx`, cập nhật Keyword/Hashtag theo niche mới.
  7. Render thay thế: Chạy `random_batch_render.py` với preset chuẩn `presets\preset_owner.json`, parallel 1, render đủ $\ge 30-45$ video `1.mp4..N.mp4` + `avatar.jpg`.
