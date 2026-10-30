# Quy chuẩn Đối soát & Phân tích Sức khỏe Đàn Nick TikTok Farm (Age & Provider Cohort)

## 1. Nguyên Tắc Cốt Lõi: Phân Tách Cohort Tuổi & Loại Mail (Reg Date & Provider Strictness)
- **CẤM TUYỆT ĐỐI gom chung acc khác loại mail / nguồn tạo:** Khi so sánh sức khỏe follow (tỷ lệ nhả / cắn follow), bắt buộc phải phân tách:
  * **Gmail chính chủ:** Được đăng ký tay, có ngày sinh thật, có 2FA, trust cao, ít bị shadow drop follow.
  * **Hotmail / Outlook farm:** Được tạo hàng loạt bằng tool, trust thấp, chịu sự kiểm soát chống bot và rate-limit cực gắt từ thuật toán TikTok.
- **Biên độ cùng độ tuổi (±15 ngày):** Khi đối soát đàn nick "cùng đợt", chỉ được so sánh các nick có ngày tạo (`Ngày Tạo` / `NGÀY TẠO` trên workbook `taikhoan_run_safe.xlsx` hoặc `taikhoan_dat_v2_updated .xlsx`) trong khoảng biên độ ±15 ngày. Cấm gom nick tạo từ tháng 6-7 đem so sánh với đợt tháng 8-9.

## 2. Bản Chất Cơ Chế Chặn Follow Của TikTok: Quyền "Cho Đi" (Following)
- **Không có chuyện cấm "nhận follow" (Follower):** Mạng xã hội chỉ kiểm duyệt chiều **CHO ĐI** (`Following` của tài khoản trên máy). Anchor (tài khoản mồi) không có khái niệm "khó tính" hay "từ chối nhận follow".
- **Lý do nhả follow thật:** Quyết định nhả hay giữ follow nằm 100% ở việc thuật toán TikTok backend đánh giá tài khoản đang bấm follow:
  * Nếu phát hiện hành vi tự động hoặc trust tài khoản chưa đạt ➔ Server âm thầm từ chối (reject) lệnh follow.
  * Cơ chế kiểm tra của script farm là **BẮT BUỘC vuốt kéo reload (Pull-to-refresh) + sleep 3.5s**. Nếu sau khi reload nút nhảy đỏ lại `Follow` thì đó là **NHẢ THẬT (backend drop)**, không phải do lag mạng hay false-positive.

## 3. Khâu Xem Video Anchor & Tỷ Lệ Dwell Time
- **Ở khâu Anchor:** 100% các máy đều vào xem video đầu tiên của Anchor từ 8–15s (`dwell = random.uniform(8.0, 15.0)`), thả tim 50–70% rồi mới bấm follow trên video, sau đó back ra profile vuốt reload kiểm tra.
- **Ở khâu Followers sau Anchor:** Tỷ lệ xem lướt video profile đối phương được quy định theo xác suất ngẫu nhiên 30–35% (`chance_range = (0.30, 35%)`). Chỉ ~1/3 nick được bot ghé xem video trước khi bấm follow.

## 4. Tình Trạng Thực Tế Của Đàn Nick Hotmail Tháng 8/2026
- Đàn nick Hotmail (reg ngày 25/08/2026) có hơn 60% đang nằm ở mốc 0 Following do bị TikTok siết nhả follow.
- Khoảng 38% chỉ giữ được 1–5 follow nhỏ giọt.
- Các nick giữ được >15 follow như Máy 17 (`lyhoan.music`) là nhóm thiểu số rất hiếm (~1%) lọt qua được nhiều đợt quét thuật toán. Để đánh giá thực chất đàn nick cần dữ liệu tích lũy chạy phân nhóm Chẵn/Lẻ trong ít nhất 15 ngày.
