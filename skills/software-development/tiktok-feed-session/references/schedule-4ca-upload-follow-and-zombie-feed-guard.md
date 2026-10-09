# Quy tắc Vận hành 4 Ca × 2 Phiên & Bảo vệ Trust Score Feed (2026-09-12)

## 1. Lịch 4 Ca × 2 Phiên & Upload Hook Linh Hoạt (Case 150 & 152)

- **Lịch 8 slot chuẩn:**
  - Ca 4 (Đêm): P1: `00:00`, P2: `01:30` (Chẵn Row 8 / Lẻ Row 7).
  - Ca 1 (Sáng): P1: `06:00`, P2: `08:00` (Chẵn Row 2 / Lẻ Row 1).
  - Ca 2 (Trưa): P1: `12:00`, P2: `14:00` (Chẵn Row 4 / Lẻ Row 3).
  - Ca 3 (Tối): P1: `18:00`, P2: `20:00` (Chẵn Row 6 / Lẻ Row 5).
  - Dead zone bảo trì: `02:30 -> 05:59`.
- **Cơ chế Upload Video (Case 152):**
  - Mở upload hook ở **CẢ Phiên 1 và Phiên 2** (luôn truyền `--allow-upload-hook`).
  - Mỗi ca tối đa chỉ đăng 1 video / nick.
  - Sổ cái `_ShiftUploadLedger` kiểm soát nguyên tử:
    - Phiên 1: Lướt feed xong kiểm tra có video thì đăng ngay.
    - Phiên 2: Nếu Phiên 1 đã đăng thành công -> Safe-skip ngay trong 0.1s (`already_uploaded_in_shift`). Nếu Phiên 1 bị lỗi hoặc chưa có video -> Phiên 2 tự động đăng bù!
  - Tuyệt đối không bao giờ đăng trùng 2 lần / ca / ngày.

## 2. Quy Tắc Follow Hook Gate (Case 151)

- **Điều kiện duy nhất:** Nick có **tối thiểu 5 video (`video_count >= 5`)** mới được đi follow.
- **Xóa bỏ chặn cứng warmup theo Row:** Trước đây Row 3..6 bị chặn bởi `tik{row}-warmup-feed-only`. Hiện tại đã gỡ bỏ hoàn toàn: **Mọi Row (1 đến 8)**, cứ có $\ge 5$ video là sau khi lướt feed sẽ tự động đi follow chéo.
- Nick $< 5$ video: Safe-skip an toàn (`under-5-videos-follow-disabled`) để tránh bị TikTok nhả follow.

## 3. Kỷ Luật Báo Cáo Chốt Phiên

- Mọi báo cáo ca, chốt phiên của watchdog và coordinator **BẮT BUỘC** phải thống kê đầy đủ 3 trụ cột:
  1. **Lướt Feed**: số máy success, fail, manual-needed, blocked-proxy-vpn.
  2. **Đăng Video (Upload Hook)**: số video đăng thành công ở phiên này, số máy đã đăng ca trước skip.
  3. **Follow Chéo (Follow Hook)**: số máy follow, số nick followed, số máy skip do chưa đủ 5 video hoặc đang cooldown.

## 4. Cảnh Báo "Zombie Feed" (Nguy cơ phá hỏng Trust Score)

- **Dữ liệu cảnh báo:** Phiên sáng 12/09 chạy 80 máy với 556 lượt vuốt nhưng **0 lượt like (thả tim)** và `watch_seconds` chỉ 2–3s.
- **Nguy cơ:** Lướt feed không có tương tác khiến TikTok gắn cờ bot, dẫn đến việc 40 máy bị nhả follow hàng loạt và ngâm cooldown bao nhiêu ngày cũng không tự hết nhả.
- **Biện pháp khắc phục:** Bắt buộc duy trì tỷ lệ like ngẫu nhiên **15% – 25%** khi lướt feed và kéo giãn thời gian xem video **6s – 15s** để tích lũy Trust Score người thật.
