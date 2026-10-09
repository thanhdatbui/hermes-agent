# Case UI-83: Dual Gate Tuổi Nick (account_age_days >= 21) Khiến Budget = 0 & Nguy Cơ Lệch Pha Follow Tự Nhiên

## 1. Hiện tượng & Triệu chứng
- Trong phiên nuôi feed (ví dụ Row 8), báo cáo hiển thị:
  - `Follow chéo (0 lượt follow) [Module 2 (Anchor): 0 | Module 1 (Bù): 0]`
  - Các nick Row 8 đều có `video_count >= 6` (đủ điều kiện video).
  - File `follow_result.json` trả về: `status: OK, followed: [], mode2_followed_count: 0, mode1_followed_count: 0, details: {"mode2_zero_following_fix": "zero-following-skip-v2"}`.
  - Đồng thời, khi lướt Feed lại lòi ra các lượt "Follow tự nhiên", nhưng khi đối soát Web thì Following thật tăng +0 (bị lệch âm so với script báo).

## 2. Pitfall Phân Tích Nghiêm Cấm
- **CẤM TUYỆT ĐỐI** nhìn tag code `"mode2_zero_following_fix": "zero-following-skip-v2"` trong `res.details` mà suy diễn cẩu thả là "anchor có 0 following" hay "anchor rỗng list".
- Các anchor Tik1/Tik2 của Farm Kibe luôn có hàng chục/hàng trăm following nội bộ.
- Chuỗi `zero-following-skip-v2` chỉ là version identifier của logic bảo vệ, luôn được gán vào `res.details` ở cuối `run_mode2`, không phản ánh profile anchor bị 0 following.

## 3. Nguyên nhân Gốc rễ: Dual Gate (25/09) Cấp Budget = 0
Trong `follow_runner/core/follow_state.py` (hàm `session_budget`):
```python
if account_age_days is not None:
    if account_age_days < 21 or video_count is None or video_count < 6:
        budget = 0
```
- Điều kiện hợp lệ để cấp budget đi follow: **`account_age_days >= 21` VÀ `video_count >= 6`**.
- Các tài khoản Row 8 (ví dụ tạo 15-16/09/2026) tính đến 02/10/2026 mới đạt **16-17 ngày tuổi (< 21 ngày)**.
- Do đó `session_budget` trả về **0**.
- Cả Mode 2 (anchor) và Mode 1 (search bù) đều nhận `budget = 0` nên vòng lặp thoát ngay lập tức (`used >= budget` khi used=0), không thực hiện bất kỳ hành động follow nào và trả về danh sách rỗng.

## 4. Lệch pha (Desync) Giữa Feed Session và Follow Runner
- Repo `tiktok-follow` áp dụng Dual Gate (`account_age_days >= 21` và `video_count >= 6`).
- Nhưng trong repo `tiktok-luot nuoi acc` (`feed_swipe_smoke.py`), nhánh follow tự nhiên khi lướt feed chỉ mới gate `video_count >= 6`, **chưa gate `account_age_days >= 21`**.
- Hậu quả: Nick mới 16 ngày tuổi vẫn bấm follow tự nhiên trên app, nhưng TikTok server đánh giá trust thấp và shadow-revert (web tăng +0), tạo ra độ lệch âm khi đối soát.
- **Quy tắc:** Cần đồng bộ kiểm tra `account_age_days >= 21` sang cả flow lướt feed trước khi cho phép roll follow tự nhiên.

## 5. Kỷ luật Báo cáo Watchdog Đối Soát Web
- Trong watchdog session (`feed_session_watchdog.py`), danh sách chi tiết đối soát Web:
  - **CHỈ ĐƯỢC IN** các nick có độ lệch (`diff != 0`) hoặc lỗi đọc snapshot / thiếu baseline (UNPROVEN).
  - **CẤM IN** các dòng nick khớp 100% (`diff == 0` / chênh lệch +0) để tránh làm loãng nội dung report của User.
