# Bất Biến Độ Tuổi Tài Khoản, Cơ Chế Cách Ly Follow (Zero-Follow Quarantine) & Nuôi Thụ Động

## 1. Dữ Liệu Đối Soát Thực Tế Farm (Account Age vs Follow Retention)
Đối soát trên toàn bộ 500+ state file và database `tiktok_tracker.db` của farm:
- **Dưới 30 ngày:** 0.0% follow thành công (100% dính block/fail ngay phiên đầu).
- **30 – 59 ngày:** 12.0% có follow được (TB chỉ 1.8 follow/acc), 42.3% bị gắn cờ `follow_failed = True`.
- **60 – 89 ngày:** Chỉ vỏn vẹn 4.9% follow bền vững (>=5 lượt), nhưng tới 82.9% tài khoản dính cờ `follow_failed = True` và fail streak kéo dài.
- **90 – 119 ngày (~3 đến 4 tháng):** Tỷ lệ follow bền vững bật tăng lên 22.2%, tỷ lệ có follow đạt 38.1%, fail streak giảm sâu.
- **Trên 120 ngày (Dàn Tik 1 & 2):** 83.0% follow thành công, 68.8% follow bền vững (>=5 lượt), đóng góp hơn 10.300 lượt follow (TB 73.7 follow/acc).

➡️ **Mốc tới hạn (Critical Threshold):** Mốc an toàn để tài khoản TikTok bắt đầu đi follow ổn định là **từ 90 ngày tuổi (~3 tháng) trở lên**.

---

## 2. Phân Tích Bản Chất Thuật Toán: "Ngâm Chết" vs "Nuôi Thụ Động (Zero-Follow)"
Khi tài khoản còn non (< 90 ngày), xuất hiện đề xuất sai lầm: *"Cho nghỉ hoàn toàn, không lướt feed, không đăng video, ngâm chết trên máy đủ 3 tháng rồi mới nuôi và follow"*. Đây là nhận thức sai về thuật toán TikTok Risk Control.

### A. Rủi ro chí tử của "Ngâm Chết" (Dormant / Ghost Account):
1. **Xếp loại Zombie Account:** TikTok không chỉ đo thời gian tạo tài khoản (`created_at`) mà đo điểm uy tín qua hành vi (`behavioral telemetry`, `watch time`, `interest tags`). Một nick 3 tháng không phát sinh telemetry bị xếp vào nhóm Inactive/Zombie.
2. **Flag Bot Reactivation:** Khi một nick ngủ đông 3 tháng bất ngờ "thức dậy", lướt qua loa rồi bấm follow hàng loạt, hệ thống chống gian lận của ByteDance lập tức nhận diện là tài khoản farm được kích hoạt lại để đi spam $\implies$ Ăn action block hoặc shadowban vĩnh viễn.
3. **Mất Token & Rớt Session:** Sau 30-90 ngày không mở app, refresh token của TikTok app hết hạn. Khi mở lại sẽ bị văng phiên (force logout), bắt xác minh OTP mail (Hotmail dễ chết token Graph), dính captcha khó.
4. **Mất nhịp tích lũy nội dung:** Sau 3 tháng vẫn là kênh 0 video hoặc 1-2 video cũ, không có trust score của Creator.

### B. Ưu thế vượt trội của "Nuôi Thụ Động Không Bấm Follow" (Passive Nurture / Zero-Follow Warm-up):
1. **Tích lũy Trust Score an toàn:** Mỗi phiên nuôi lướt FYP giúp tài khoản tích lũy thời gian xem, tạo profile sở thích (interest tags), nhận diện là người tiêu dùng nội dung thật (Active Consumer).
2. **Giữ Session luôn sống:** Token và cookie đăng nhập được refresh liên tục trong các phiên nuôi định kỳ, không bị văng đăng nhập.
3. **Tích lũy Video & View tự nhiên:** Vẫn đăng video đều đặn giúp kênh có 10–15 video, có lượt xem và tim tự nhiên.
4. **Tỷ lệ sống tối đa sau 90 ngày:** Khi đạt 90 ngày tuổi và video count >= 10, tài khoản đã là "Veteran Consumer" có độ trust cao, mở quyền follow sẽ không bị nhả follow hay dính án phạt.

---

## 3. Quy Tắc Vận Hành Bất Biến Cho Farm
1. **Tách bạch hành động Nuôi vs Follow:** Lỗi nhả follow/action block là do **hành động bấm Follow**, hoàn toàn **không liên quan đến việc lướt feed hay đăng video**.
2. **CẤM ngâm chết hoặc tắt ca nuôi của Row 7 & 8:** Toàn bộ các nick trong Pool `{1, 2, 7}` (Ca 1) và `{3, 4, 8}` (Ca 2) vẫn tham gia vòng xoay Shift-Pool bình thường để tích lũy session và giữ đều tải máy.
3. **Cách ly quyền Follow bằng Age Gate (90 ngày):**
   - Với tài khoản có `account_age_days < 90`: Khi chạy feed session, hook follow tự động bỏ qua:
     `status: "skipped", reason: "under-age-90d-quarantine"`.
   - Vẫn cho phép lướt feed, xem video, tương tác tự nhiên và đăng video theo lịch.
   - Khi tài khoản chạm mốc $\ge 90$ ngày và $\ge 10$ video: Tự động tốt nghiệp (graduated) và cấp budget follow theo phễu sức khỏe.
