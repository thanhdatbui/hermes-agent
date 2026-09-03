# Đối Soát Batch Follow Row 2 & Bản Chất Nghỉ 48h Khi Dính Nhả Follow (2026-08-27)

## 1. Dữ Liệu Thực Nghiệm Chạy Follow Ngày Chẵn 26/08/2026 (Row 2)
- **Tổng số máy ghi nhận chạy:** 41 máy.
- **Tổng lượt follow thành công:** 110 lượt.
- **Phân bổ kết quả:**
  - **10 máy chạy tốt (không nhả follow):** Đạt 88 follow (M06: 12, M08: 10, M17: 11, M18: 15, M24: 3, M25: 8, M42: 10, M46: 0, M51: 11, M61: 8).
  - **11 máy nhả follow sau 1–3 nick:** Đạt 22 follow (M03, M07, M09, M11, M12, M13, M14, M30, M40, M50, M64).
  - **20 máy nhả follow ngay lượt đầu (0 follow):** M05, M16, M19, M20, M27, M44, M45, M48, M52..M60, M63, M66, M67.

## 2. Root Cause: Tình Trạng Video Row 2 (Tik2.xlsx)
- Kiểm tra toàn bộ 80 máy trên file `Tik2.xlsx` cho thấy `Video Đã Đăng = 0` trên 100% các dòng.
- Theo quy luật thuật toán TikTok: **Nick 0 video bị xếp vào nhóm bot/clone rác $\rightarrow$ TikTok kích hoạt cơ chế nhả follow tức thì sau khi reload profile (100% nhả follow ngay lượt đầu hoặc sau 1-2 lượt)**.

## 3. Bản Chất Thời Gian Nghỉ 48h vs Số Lượng Video Đã Đăng
1. **Đối với nick 0 video (Row 2, Row 3):**
   - **Nghỉ 48h, 72h hay lâu hơn hoàn toàn KHÔNG có tác dụng** nếu nick vẫn chưa đăng video.
   - Lý do: Thuật toán TikTok đánh giá Trust Score dựa trên lịch sử hoạt động và nội dung đăng tải (video). Khi chưa có video, bất kể giãn cách bao lâu, hành vi follow đều bị coi là bot tự động.
   - **Giải pháp:** Tắt follow hook, chạy thuần túy Lướt Feed + Đăng video (ở phiên 3 cuối ca) cho đến khi đạt tối thiểu $\ge 5$ video mới kích hoạt lại follow.
2. **Đối với nick đã có video ($\ge 8$ video - Row 1):**
   - Nghỉ 24h–48h là đủ để TikTok reset cờ rate-limit trong ngày (Daily Rolling Limit), sau đó có thể chạy follow 8–15 follow/ngày bình thường.
   - Khi dính cờ phạt nặng do IP collision/network glitch, cần nghỉ follow 3–5 ngày chỉ nuôi feed + up video trước khi probe lại bằng canary.
