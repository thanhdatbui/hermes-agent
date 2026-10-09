# Device Lock Auto-Reap, Watchdog Threshold & Teardown-to-Home Standard

## 1. Bản chất sự cố Race Condition giữa Watchdog & Reaper (13/09/2026)

### Vấn đề thực tế:
- Cả **Reaper** (`reap-dead-owner-locks.py`) và **Watchdog** (`watch_device_locks.py`) đều chạy chu kỳ 15 phút.
- Ngưỡng TTL tự động nhả lock `blocked` (giữ hiện trường) là 60 phút (3600s).
- Khi các máy chạm 60-70 phút, Watchdog quét trước và bắn cảnh báo Telegram: *"VƯỢT NGƯỠNG 60P"*, trong khi chỉ 1-2 phút sau Reaper tự động kích hoạt dọn sạch sẽ vào quarantine và nhả máy cho ca chạy mới.
- Người dùng đặt câu hỏi chính đáng: *"Ủa sắp được quét nhả lock tự động rồi còn báo Telegram làm gì?"*.

### Chuẩn hóa thiết kế mới:
1. **Tần suất Reaper:** Rút ngắn lịch cron `reap-dead-owner-locks` xuống `*/5 * * * *` (5 phút/lần). Đảm bảo lock vừa hết hạn TTL 60p là được dọn ngay trong vòng 1-5 phút.
2. **Ngưỡng Watchdog cảnh báo (Fail-safe Alert):** Nâng ngưỡng cảnh báo Telegram từ 60p lên **90 phút** (`ALERT_THRESHOLD_MINUTES = 90`, `ALERT_THRESHOLD_BLOCKED_MINUTES = 90`).
   - 0 - 60 phút: Máy chạy hoặc giữ hiện trường cho operator/dev.
   - 60 - 65 phút: Reaper tự động dọn âm thầm, dọn lock và đưa máy về HOME sạch sẽ mà KHÔNG spam Telegram.
   - Chỉ khi nào lock kẹt **> 90 phút** (Reaper đã qua nhiều chu kỳ mà không thể dọn do lỗi file/tiến trình bất tử) thì Watchdog mới phát báo động khẩn cấp lên nhóm.

---

## 2. Quy chuẩn Giữ Hiện Trường vs Bằng Chứng Số Hóa (Digital Evidence)

### Có cần ngâm màn hình máy thật để fix lỗi không?
- **KHÔNG.** Chỉ cần bộ 3: **`Dump XML + Screencap (ảnh) + Log`** là đủ 95-100% để debug, viết detector, selector, dismisser popup và unit test.
- **Màn hình máy thật chỉ có 1 tác dụng duy nhất:** Chạy Live Canary sau khi fix xong.
- **Tác hại khi ngâm máy thật quá lâu:**
  - TikTok sau 10-15 phút tự reload feed, màn hình tắt, hoặc app bị OS kill làm mất hiện trường thực tế.
  - Làm nghẽn hàng đợi (1 máy gánh 8 nick theo ca), làm lỡ ca chạy của đàn tài khoản phía sau.
- **Quy tắc:** Bắt sự kiện lỗi -> Chụp screencap + dump XML lưu vào `artifacts/` -> Đưa máy về HOME hoặc cho phép Reaper nhả lock sau tối đa 30-60 phút.

---

## 3. Quy chuẩn Teardown bắt buộc về HOME (`_force_stop_and_home`)

Mọi script tự động hóa trên farm (dù chạy THÀNH CÔNG hay THẤT BẠI/EXCEPTION) **bắt buộc phải có teardown trong khối `finally:`** để:
1. Force-stop ứng dụng (`am force-stop <package>`).
2. Gửi keyevent HOME (`input keyevent 3`).

### Matrix kiểm tra các repo:
- `tiktok-luot nuoi acc`: Đã chuẩn hóa trong `finally:` của `multi_machine_feed_session.py` (`_force_stop_tiktok_and_home`).
- `Tiktok_Reg`: Đã chuẩn hóa trong `finally:` của `social_reg_v1.py` (`_post_reg_cleanup`).
- `reap-dead-owner-locks.py`: Đã chuẩn hóa qua `_cleanup_device_screen` khi dọn lock.
- `tiktok-follow`: Cần đảm bảo `cleanup_after_result` bọc trong `finally:` của runner cả khi gặp ngoại lệ.
- `Tiktok-video`: Cần loại bỏ nhánh cố tình không dọn app khi lỗi trong `state_machine.py`, chuyển sang bắt buộc về HOME sau khi đã lưu xong XML/screencap bằng chứng.
