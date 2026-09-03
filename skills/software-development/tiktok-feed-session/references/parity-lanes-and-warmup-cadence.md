# Cấu Hình Parity LANES & Lộ Trình Warmup Nick Mới (Row 5 & Row 6)

## 1. Parity LANES (Ngày Chẵn / Ngày Lẻ) - Cập nhật 2026-09-01
- **Nguyên tắc**: Tách bạch ca nuôi và chia đều tải cho 6 hàng nick (Row 1..6) trên 80 máy:
  + **Ngày Lẻ (Lane B)**:
    - Ca 1 (06:00): **Row 1** (Phiên 3 Đăng video + Follow chéo).
    - Ca 2 (12:30): **Row 3** (Nuôi feed + Đăng video).
    - Ca 3 (19:00): **Row 5** (Warmup lướt feed thuần).
  + **Ngày Chẵn (Lane A)**:
    - Ca 1 (06:00): **Row 2** (Phiên 3 Đăng video + Follow chéo khi đủ $\ge 5$ video).
    - Ca 2 (12:30): **Row 4** (Nuôi feed + Đăng video).
    - Ca 3 (19:00): **Row 6** (Warmup lướt feed thuần).
- **Quy tắc giờ cố định**: Nick Row 1 và Row 2 chỉ chạy buổi sáng (Ca 1). Buổi tối dành trọn vẹn cho dàn nick mới Row 5 và Row 6.

## 2. Lộ Trình Nuôi Warmup 20 Ngày Chuẩn cho Dàn Nick Mới
- **Giai đoạn 1: Warmup Lướt Feed Thuần (Ngày 1..10 lịch - 5 ngày chạy thực tế)**:
  + 15 phiên lướt feed (3 phiên/ngày chạy).
  + **0 đăng video, 0 follow**.
  + Tích lũy cookie tự nhiên, xây dựng sở thích video (niche) và trust score cho nick.
- **Giai đoạn 2: Đăng 5 Video Đầu Tiên (Ngày 11..20 lịch - 5 ngày chạy thực tế tiếp theo)**:
  + Đăng 1 video/ngày chạy ở Phiên 3 $\rightarrow$ đạt mốc 5 video/nick sau 5 ngày chạy.
  + **Vẫn chặn follow chéo** (Gate $< 5$ video).
- **Giai đoạn 3: Mở Follow Chéo Tự Động (Từ Ngày 21 lịch trở đi)**:
  + Nick đạt 10 ngày tuổi thực tế và có $\ge 5$ video.
  + Hệ thống tự động kích hoạt Hook Follow chéo ngoài farm (Module 2), bắt đầu từ hạn mức an toàn 5-10 follow/ngày rồi tăng dần lên trần 40 follow/ngày.

## 3. Đồng Bộ Nguồn Dữ Liệu Tự Động (Auto-Sync to Cron Source)
- `taikhoan_run_safe.xlsx` là nguồn sự thật duy nhất cho toàn bộ 80 máy.
- `hermes_taikhoan_sync_cron.py` tự động xuất dữ liệu sang `hermes_cron_source_config.json`, `feed_state.json` và `post_state.json`, đảm bảo scheduler luôn tạo manifest đủ 80 máy (không bị thiếu dải máy 75..80 hoặc kẹt ID rác).
