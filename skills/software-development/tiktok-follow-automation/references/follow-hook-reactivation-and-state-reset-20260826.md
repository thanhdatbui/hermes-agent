# Tái Kích Hoạt Follow Hook & Quy Trình Kiểm Tra Nhả Follow (2026-08-26)

## 1. Bối cảnh & Yêu Cầu Vận Hành
Sau thời gian tạm dừng follow để nuôi trust cho dàn tài khoản sau sự cố IP collision, tiến trình đi follow chéo được kích hoạt lại theo yêu cầu operator để kiểm tra thực tế xem TikTok còn nhả follow hay không.

## 2. Các Bước Kích Hoạt An Toàn

### Bước 1: Gỡ Bypass Trong Feed Session Runner (`multi_machine_feed_session.py`)
- Gỡ bỏ early-return bypass `follow-disabled-by-operator` trong hàm `_run_follow_hook`.
- Giữ nguyên các chốt an toàn:
  - **Cổng Video**: Chỉ nick đã đăng $\ge 1$ video (`video_count >= 1`) mới được gọi follow runner. Nick 0 video tự động bỏ qua (`zero-video-follow-disabled`).
  - **Cổng Sensitive Stop**: Bỏ qua follow nếu phiên feed dừng vì lỗi nhạy cảm (captcha, 2FA, OTP, checkpoint).
  - **Cổng Cooldown Ngày**: Tự động bỏ qua follow nếu nick đó đã bị dính cờ nhả follow (`FOLLOW_FAILED`) trong ngày hôm nay.

### Bước 2: Cấu Hình Follow Runner Hybrid (`tiktok-follow`)
- File config: `follow_runner/config.example.yaml` (commit `af56b2a`).
- **Chế độ chạy**: `mode: "both"` (Ưu tiên Mode 2' duyệt danh sách Following nội bộ của anchor Tik1/Tik2; nếu thiếu lượt tự động gọi Mode 1 tìm kiếm để bù đủ budget).
- **Budget phiên**: `budget_per_session_min: 4`, `budget_per_session_max: 6`, `budget_per_session: 6`.
- **Cơ chế xác thực nhả-follow**: `_confirm_not_released()` thực hiện kéo vuốt từ trên xuống (*Pull-to-refresh*) sau khi tap follow. Nếu nút bị nhả về "Follow" đỏ $\rightarrow$ kích hoạt `FOLLOW_FAILED`, dừng phiên và khóa follow nick đó trong 24h.

### Bước 3: Dọn Dẹp State Cooldown Cũ
- Trước khi bắt đầu đợt đo kiểm mới, xóa sạch các file state cũ tại `D:\Taadaa\tiktok-follow\runs\state\follow_state_*.json` để tránh bị cờ phạt của những ngày trước chặn nhầm.

### Bước 4: Nguyên Tắc In-Flight Protection
- Nếu có phiên feed đang chạy dở giữa chừng khi kích hoạt code: **Tuyệt đối không force-stop hay can thiệp ngắt ngang máy**. Để các phiên đang chạy hoàn tất tự nhiên, phiên kế tiếp sẽ tự động bắt đầu chu trình đi follow mới.
