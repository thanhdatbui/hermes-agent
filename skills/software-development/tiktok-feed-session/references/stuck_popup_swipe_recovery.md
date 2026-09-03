# Swipe Recovery on Stuck Screens / Popups (TikTok Feed Session)

## Quy tắc cốt lõi:
- Khi gặp popup lạ, overlay quảng cáo (Shopee, sự kiện, CTA, Đóng/Xem ngay, v.v.) hoặc màn hình không rõ ràng:
  - **Không thuộc nhóm nhạy cảm**: Login, Captcha, OTP, Security challenge.
  - **Hành động bắt buộc**: Chạy `_swipe_recovery_on_stuck` (thực hiện vuốt lên tối đa 2 lần swipe bằng ADB `input swipe 540 1600 540 400 300`) để lướt qua video tiếp theo và tiếp tục phiên nuôi.

## Pitfall kiến trúc code:
1. **Thứ tự thực thi**: Khối `_swipe_recovery_on_stuck` PHẢI đặt **TRƯỚC** `manual_guard.record(...)`.
   - Nếu `manual_guard.record(...)` đặt trước, khi gặp 2 nhịp capture liên tiếp có cùng lý do `manual-needed:popup` (ví dụ sau bước BACK recheck), `manual_guard` sẽ kích hoạt dừng phiên ngay lập tức trước khi luồng kịp gọi swipe recovery.
2. **Quản lý cờ trạng thái**: Sau khi swipe recovery thành công và chuyển sang video mới, reset lại cờ `ctx.config["_swipe_recovery_used"] = False` để các video kế tiếp trong phiên nếu tiếp tục gặp popup lạ vẫn được quyền vuốt cứu kẹt.
3. **Kiểm tra foreground package trước khi vuốt**: Khi gặp `unexpected popup/dialog marker detected` hoặc kẹt feed, nếu TikTok bị crash/mất focus văng về Launcher (`com.sec.android.app.launcher`), việc thực hiện `input swipe` chỉ vuốt các trang màn hình chính Android. `_swipe_recovery_on_stuck` cần kiểm tra `focused_package`; nếu là launcher/systemui thì phải kích hoạt relaunch TikTok (`monkey -p com.ss.android.ugc.trill ...`) thay vì vuốt mù trên desktop dẫn đến lỗi `swipe recovery (2 swipes) still stuck`.
