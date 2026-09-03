# Quy Luật Hạn Mức Follow TikTok & Chiến Lược Lịch Chẵn/Lẻ Closed Graph (19/08/2026)

## 1. Bản Chất Hạn Mức Follow Theo Thực Nghiệm (19/08)
- **Hạn mức tính theo Ngày (Calendar Day / 24h)**: Khi tài khoản bị TikTok gắn cờ rate-limit (`FOLLOW_FAILED` — nhả follow sau vuốt reload), nick đó **bị khóa trọn vẹn theo chu kỳ 24h**. Thử nghiệm cho nick nghỉ 10-12 tiếng tối cùng ngày test lại vẫn bị nhả ngay từ lượt đầu tiên. Phải qua ngày hôm sau mới hết cờ phạt.
- **Tài khoản 0 Video (Row 3, 4, 5, 6) TUYỆT ĐỐI KHÔNG FOLLOW**: Nick chưa đăng video bị TikTok xếp vào nhóm clone/bot rác, 100% bị nhả ngay từ cú tap follow đầu tiên. Nhóm này chỉ chạy thuần túy Lướt Feed làm ấm (warm-up) + Đăng tối thiểu $\ge 8$ video trước khi bật follow.
- **Tài khoản Đã Có Video (Row 1, 2 - có 8-12 video)**: TikTok cấp Trust Score cho phép follow 15-18 nick/ngày. Tuy nhiên **CẤM DỒN VÀO 1 BUỔI SÁNG** (dồn 4 phiên liên tiếp sẽ bị gắn cờ spam lúc 09:45). BẮT BUỘC chia đều 2 cữ: **Sáng 7-8 follow + Tối 7-8 follow** (mỗi cữ cách nhau 8-10 tiếng).

## 2. Chiến Lược Lịch Farm Ngày Chẵn / Ngày Lẻ (Lane A / Lane B)
- **Ngày Lẻ (1, 3, 5, 7, 9...) — Tập trung Row 1**:
  - Ca 1 (06:00 - 10:00): **Row 1** (Lướt Feed + Follow Cữ 1: 7-8 nick)
  - Ca 2 (12:30 - 16:30): **Row 3 & 5** (12h30-14h30 Row 3 nuôi+up video; 14h30-16h30 Row 5 lướt warm-up; 0 follow)
  - Ca 3 (19:00 - 23:00): **Row 1** (Lướt Feed + Follow Cữ 2: 7-8 nick)
  - *Tổng kết*: Row 1 ăn 15-16 follow/ngày an toàn; Row 3 & 5 cứng nick.
- **Ngày Chẵn (2, 4, 6, 8, 10...) — Tập trung Row 2**:
  - Ca 1 (06:00 - 10:00): **Row 2** (Lướt Feed + Follow Cữ 1: 7-8 nick)
  - Ca 2 (12:30 - 16:30): **Row 4 & 6** (12h30-14h30 Row 4 lướt; 14h30-16h30 Row 6 lướt; 0 follow)
  - Ca 3 (19:00 - 23:00): **Row 2** (Lướt Feed + Follow Cữ 2: 7-8 nick)
  - *Tổng kết*: Row 2 ăn 15-16 follow/ngày an toàn; Row 4 & 6 cứng nick.

## 3. Toán Học Mạng Lưới Follow Chéo (Closed Graph)
- Trong mạng follow chéo nội bộ, **Tổng số nick trong Farm chính là "TRẦN FOLLOWER TỐI ĐA" mà 1 nick có thể nhận được**.
- Farm hiện tại (~200 nick) $\rightarrow$ Kéo chéo tối đa chỉ lên được ~200 Follower.
- Farm mở rộng **160 máy $\times$ 6 nick = 960 nick**:
  - Bể tài khoản nội bộ có 960 nick.
  - Mỗi nick follow 16 người/ngày (Sáng 8 + Tối 8).
  - Phép toán khớp lệnh: $960 \div 16 = \mathbf{60 \text{ ngày (đúng tròn 2 tháng)!}}$
  - Đúng sau 60 ngày, toàn bộ 960 tài khoản đồng loạt đạt 1.000 Follower mở giỏ hàng TikTok Shop.
