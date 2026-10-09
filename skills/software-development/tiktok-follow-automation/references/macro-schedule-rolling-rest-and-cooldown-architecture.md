# Chu Kỳ Điều Phối 6 Ngày, Nghỉ Xả Trắng & State Cooldown Khép Kín (2026-09-15)

## 1. Bản chất thuật toán & Tại sao cần Ngày Nghỉ Xả Trắng
- Thuật toán TikTok không bao giờ phạt nick chỉ vào lướt xem video và thả tim dạo. TikTok chỉ tích lũy điểm nghi vấn (Anomaly Score) khi phát sinh tương tác ngoại vi (Outbound Follow/Comment).
- Cày liên tục 30 ngày/tháng dù delay kỹ đến đâu vẫn tạo ra Anomaly Score lũy tiến -> Dẫn tới phạt nhả follow dây chuyền.
- **Ngày dưỡng sinh (Lướt feed thuần túy, 0 follow)** đóng vai trò kích hoạt cơ chế Decay Penalty, đưa điểm nghi vấn về 0, giúp nick hồi phục trust score 100%.

## 2. Chu kỳ vận hành 6 ngày (xoay tua 4 acc/ngày)
Khung giờ farm chia làm 4 Ca tiêu chuẩn: Ca 1 (Sáng), Ca 2 (Trưa), Ca 3 (Tối), Ca 4 (Đêm) — mỗi ca chạy đúng 1 slot:

| Chu kỳ | Ca 1 (Sáng) | Ca 2 (Trưa) | Ca 3 (Tối) | Ca 4 (Đêm) | Tính chất ngày chạy |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **Ngày 0** | Row 1 | Row 3 | Row 5 | Row 7 | **CÀY CHÍNH:** 2 phiên follow (10–20 follow/phiên) + Up video. |
| **Ngày 1** | Row 2 | Row 4 | Row 6 | Row 8 | **CÀY CHÍNH:** 2 phiên follow (10–20 follow/phiên) + Up video. |
| **Ngày 2** | Row 1 | Row 3 | Row 5 | Row 7 | **DƯỠNG SINH (RỬA TRUST):** 100% **CHỈ LƯỚT FEED NUÔI, TUYỆT ĐỐI 0 FOLLOW**. |
| **Ngày 3** | Row 2 | Row 4 | Row 6 | Row 8 | **CÀY CHÍNH:** 2 phiên follow + Up video. |
| **Ngày 4** | Row 1 | Row 3 | Row 5 | Row 7 | **CÀY CHÍNH:** 2 phiên follow + Up video. |
| **Ngày 5** | Row 2 | Row 4 | Row 6 | Row 8 | **DƯỠNG SINH (RỬA TRUST):** 100% **CHỈ LƯỚT FEED NUÔI, TUYỆT ĐỐI 0 FOLLOW**. |

- **Thời gian hồi phục**: Mỗi slot sau khi cày 1 ngày sẽ có trọn vẹn 48h nghỉ ngơi hành vi follow (1 ngày không đụng tới + 1 ngày vào app chỉ lướt xem video).

## 3. Ngân sách & Định mức Follow
- `budget_per_session`: 10 – 20 follow / phiên.
- `budget_per_day`: 40 follow / ngày / slot.
- Tỷ lệ vàng: 2 phiên follow kẹp 1 phiên upload video mới.
- Hard Gate móng tài khoản: Bắt buộc $\ge 10$ video mới được cấp budget đi follow chéo. Khi $< 10$ video: 0 follow.

## 4. Quy tắc Clear Cache & Bảo trì Phần cứng S7
- Dọn dẹp cache app định kỳ cuối ngày hoặc cuốn chiếu theo batch bằng cron để chống tràn bộ nhớ máy Samsung S7 (32GB).
- **CẤM TUYỆT ĐỐI** xóa cache trước mỗi lần switch nick (gây lặp lại hành vi máy móc và lộ signature bot).

## 5. Kiến trúc State Cooldown & Auto-Expiry (Sol Review 9.3/10)
- **Chuẩn hóa UTC 100%**: So sánh thời gian tuyệt đối theo UTC (`datetime.now(timezone.utc)` và `until_dt.astimezone(timezone.utc)`), loại bỏ lỗi lệch ngày giữa Windows local và UTC server.
- **Cách ly cấp Slot/Row**: Bỏ hẳn fallback `follow_state_{machine}.json`, chỉ match chính xác theo cặp `(machine, row)`.
- **Auto-Sync Expiry diệt Zombie State**: Khi `now_utc >= until_dt`, hàm kiểm tra phải tự động xóa cờ `follow_failed = False`, dọn sạch các trường timestamp cũ và ghi đè an toàn qua file tạm `.json.tmp` -> `os.replace` (atomic replace) để tự động mở lại cờ follow khi lướt feed và popup.
