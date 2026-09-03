# Chiến Lược Lịch Ca Chẵn/Lẻ & Toán Học Follow Chéo Farm 160 Máy (19/08/2026)

## 1. Bản Chất Cooldown Follow Limit TikTok
- **Chu kỳ 24h (Calendar Day)**: Khi nick bị nhả follow (`FOLLOW_FAILED`), TikTok giữ cờ hạn mức suốt 24h (nghỉ 10-12h cùng ngày vẫn bị nhả). Phải qua ngày kế tiếp mới hồi.
- **Phân tầng Video**:
  - *Nick 0 video (Row 3, 4, 5, 6)*: CẤM BẬT FOLLOW (100% nhả ngay). Chỉ lướt feed + up $\ge 8$ video.
  - *Nick có video (Row 1, 2)*: Follow tối đa 15-18/ngày, nhưng CẤM dồn vào 1 ca sáng. Phải chia 2 cữ: Sáng 7-8 + Tối 7-8 (cách nhau $\ge 8$h).

## 2. Lịch Vận Hành Ngày Chẵn / Ngày Lẻ (3 Ca)
- **Ngày Lẻ (Tập trung Row 1)**:
  - Ca Sáng (06h-10h): Row 1 (Follow Cữ 1: 7-8)
  - Ca Trưa (12h30-16h30): Row 3 (12h30-14h30) & Row 5 (14h30-16h30) (Lướt feed, 0 follow)
  - Ca Tối (19h-23h): Row 1 (Follow Cữ 2: 7-8)
- **Ngày Chẵn (Tập trung Row 2)**:
  - Ca Sáng (06h-10h): Row 2 (Follow Cữ 1: 7-8)
  - Ca Trưa (12h30-16h30): Row 4 (12h30-14h30) & Row 6 (14h30-16h30) (Lướt feed, 0 follow)
  - Ca Tối (19h-23h): Row 2 (Follow Cữ 2: 7-8)

## 3. Bản Chất Toán Học Closed Graph Farm 160 Máy
- Trong follow chéo nội bộ, tổng nick trong farm là trần follower tối đa 1 nick nhận được.
- Khi farm đủ 160 máy $\times$ 6 = 960 nick $\rightarrow$ Mỗi nick follow 16 người/ngày $\rightarrow 960 \div 16 = \mathbf{60 \text{ ngày (đúng 2 tháng)}}$ đồng loạt 960 nick cán mốc 1.000 Follower mở TikTok Shop!
