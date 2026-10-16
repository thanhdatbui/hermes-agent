# Continuous Rolling Avatar Operations & Anti-False-Yield Reporting (2026-10-15)

## 1. Context: 3-Ca Farm Schedule (Bỏ Ca 4 Đêm)
- TikTok feed schedule is now strictly 3 Ca x 2 Sessions (06:00, 12:00, 18:00).
- Night Ca 4 (00:00 - 05:30) is completely abolished.
- This unlocks a continuous 6.5-hour idle window ban đêm: `21:30 → 04:00` (before 04:00 cache clear).
- Farm also has daytime idle windows: `09:30 → 11:45` and `15:30 → 17:45`.

## 2. Pitfall: Legacy 23:45 Evening Truncation & False "Nhường Lịch Nuôi"
- **Legacy truncation:** `is_after_evening_window` triggered at 23:45, stopping batch launches for the entire night and forcing an incomplete report.
- **Reporting bug (Slot vs Distinct Machine):**
  - Summing `unuploaded` across Tik 1..8 yields unuploaded account slots (`tot_miss`), NOT unique machines.
  - Example: M10 and M30 offline in 6 Tiks each = 12 slots, but only 2 physical machines.
- **Reporting bug (False "Nhường lịch"):**
  - Unconditionally labeling `tot_miss` as "Bỏ qua an toàn: {tot_miss} máy (nhường lịch nuôi TikTok / lock tiến trình khác)" falsely blamed the feed schedule during midnight hours when no feed ca was running, while obscuring genuine errors (DEVICE_OFFLINE, SWITCHER_FAILED).

## 3. Standard Continuous Rolling Protocol
- Run continuous rolling batches across all farm idle windows until 100% DONE.
- Stop conditions:
  * Only when feed runner is actively running (`is_feed_runner_active()`).
  * Within 30 minutes before next scheduled feed ca.
  * During 04:00 - 04:45 daily cache-clear window.
- Periodic cadence reporting (every 6h: 00:00, 06:00, 12:00, 18:00 or 12h) to avoid fragmented spam.
- Explicit report breakdown:
  * Total DONE % (accounts / target).
  * New SUCCESS in window.
  * Real Technical Failures (distinct machines grouped by error).
  * Pending Queue (machines waiting for next batch).
  * NEVER claim "nhường lịch nuôi" unless verified active feed lock exists.

## 6. Cạm Bẫy Báo Cáo 6H Chạy Trên Cron 5m/15m: Lệch State Key Gây Spam Liên Tục ("Clg report này gửi liên tục spam v")
- **Hiện tượng sự cố:**
  - Watchdog chạy theo lịch cron định kỳ cao (mỗi 5 phút `*/5 * * * *` hoặc mỗi 15 phút `*/15 * * * *`).
  - Hàm kiểm tra khung giờ 6H mở trong 30 phút: `is_6h_window = (now.hour in (0, 6, 12, 18) and now.minute < 30)`.
  - Trong suốt 30 phút đó, mỗi tick cron (5 phút) đều kích hoạt và bắn báo cáo vào Telegram, gây ra chuỗi spam 6 tin nhắn giống hệt nhau liên tiếp.
- **Nguyên nhân gốc rễ (Lệch Key State Guard):**
  - Trong logic chặn trùng (dedup), script kiểm tra:
    ```python
    slot_6h = (now.hour // 6) * 6
    sess_key = f"{now.strftime('%Y-%m-%d')}_{slot_6h:02d}"
    if not all_done and state.get("last_reported_6h") == sess_key:
        return
    ```
  - Nhưng ở đoạn `save_state` sau khi gửi báo cáo, script lại lưu vào key cũ:
    ```python
    state["last_reported_session"] = sess_key
    state["last_reported_date"] = sess_key
    # ❌ QUÊN GHI: state["last_reported_6h"] = sess_key
    ```
  - Hậu quả: `state.get("last_reported_6h")` vĩnh viễn là `None`. Guard bị vô hiệu hoá hoàn toàn, watchdog bắn lặp mỗi 5 phút cho đến khi hết phút 30.
- **Quy tắc chuẩn hóa Dedup 6H bắt buộc:**
  1. Kiểm tra bao quát cả key mới lẫn key kế thừa (fallback):
     ```python
     if not all_done and (
         state.get("last_reported_6h") == sess_key
         or state.get("last_reported_session") == sess_key
         or state.get("last_reported_date") == sess_key
     ):
         return
     ```
  2. Ghi đầy đủ và đồng bộ cả 3 key khi phát báo cáo:
     ```python
     state["last_reported_6h"] = sess_key
     state["last_reported_session"] = sess_key
     state["last_reported_date"] = sess_key
     if all_done:
         state["last_reported_all_done"] = True
     ```
  3. BẮT BUỘC viết unit test kiểm chứng idempotency (gọi 2 lần liên tiếp trong cùng window 6H chỉ gửi đúng 1 lần alert duy nhất).

## 4. Cạm Bẫy Cột Avatar Excel `OK` vs Kích Hoạt Watchdog (`FORCE_UPLOAD`)
- **Nguyên nhân bỏ sót máy cần đổi avatar:**
  - `post_evening_avatar_watchdog.py` sử dụng `resolve_avatar_pending_machines.py <Tik>` để lập danh sách máy cần upload.
  - Script chỉ lọc các dòng có cột `Avatar != 'OK'`. Nếu nick đã từng up avatar thành công trong quá khứ (`Avatar: OK`), watchdog sẽ **bỏ qua hoàn toàn** mà không upload lại.
- **Quy tắc bắt buộc khi đổi/chuẩn hoá avatar theo lệnh User:**
  1. CẤM TUYỆT ĐỐI hứa "watchdog sẽ tự đổi" khi chưa sửa Excel.
  2. BẮT BUỘC cập nhật cột `Avatar` thành **`FORCE_UPLOAD`** trong `Tik<N>.xlsx`.
  3. BẮT BUỘC kiểm chứng lại bằng lệnh:
     ```bash
     python D:/Taadaa/Tiktok-video/scripts/resolve_avatar_pending_machines.py <Tik>
     ```
     Xác nhận output có chứa đúng số máy mục tiêu trước khi báo cáo.

## 5. Hiện Tượng Ca Nuôi Nhiều Phiên (Phiên 1 $\to$ Phiên 2) & Cửa Sổ Giờ Của Watchdog
- **Bẫy "Ca trưa kết thúc tưởng máy rảnh":**
  - Mỗi ca nuôi (ví dụ Ca trưa 12:00) thường gồm nhiều phiên liên tiếp:
    * Phiên 1 (Session 1): bắt đầu ~12:02, kết thúc ~13:58.
    * Phiên 2 (Session 2): tự động spawn ngay lập tức ~14:03 (`run_tiktok.py --session-index 2`), tái khóa toàn bộ Device Locks (`status: running`/`queued_v2`).
  - Coordinator nhìn thấy Phiên 1 vừa exit mà vội kết luận "máy đã rảnh" hoặc thắc mắc tại sao watchdog chưa chạy là sai hiện trường.
- **Khung giờ cứng của `is_post_evening_window` trong watchdog:**
  - Code của `post_evening_avatar_watchdog.py` chặn cứng chỉ chạy trong 3 khung giờ an toàn:
    * Khung sáng: `08:30 → 11:05` (sau Ca 1 P2, né reboot 11:20)
    * Khung tối: `20:15 → 23:45` (sau Ca 3 P2)
    * Khung đêm: `03:15 → 05:05` (sau Ca 4 P2, né reboot 05:20)
  - Khung giờ trưa/chiều (12:00 → 20:00) watchdog **CHỦ ĐỘNG KHÔNG CHẠY** để bảo vệ ca nuôi và các tác vụ GPM.
- **Quy tắc điều phối khi User yêu cầu "Làm đi" vào ban ngày:**
  1. Phải giải thích rõ: Giữa ngày đang là Phiên 2 ca nuôi (khóa máy), và watchdog chỉ tự kích hoạt ở khung an toàn tối (sau 20:15).
  2. CẤM NẰM IM CHỜ USER NHẮC ("Tại sao tao phải nhắc mày mới làm"): Khi máy kẹt lock ca nuôi (P1 hoặc P2), Coordinator BẮT BUỘC phải đặt tiến trình background watcher (event-driven wakeup) hoặc hẹn giờ kiểm tra tự động giải phóng lock lúc ~15:20. Ngay khi lock vừa nhả, agent phải tự động kích hoạt làm tiếp dứt điểm ngay lập tức, tuyệt đối không được im lặng để user phải giục.
  3. Khi máy rảnh hoàn toàn mới chạy lệnh đơn máy cưỡng chế (`run_tiktok_upload_avatar.ps1` hoặc `pin_top_videos.py`), không được ngồi chờ watchdog tự kích hoạt lúc 14h.

## 7. Quy Trình Vượt Layout TikTok v47 Có Bong Bóng Note Đè Avatar & Remote Admin (M >= 200)
- **Bẫy bong bóng Note ("Thì thầm to nhỏ", "Bạn có nghĩ gì?"):**
  - Trên TikTok v47, nếu avatar bị gắn bong bóng status Note, bấm vào avatar sẽ mở popup tạo/xem Note chứ KHÔNG mở đổi ảnh đại diện.
  - Phải vào màn hình "Sửa hồ sơ" (Edit Profile): cuộn trang tìm nút "Sửa hồ sơ" hoặc mở qua menu cài đặt.
  - Trong "Sửa hồ sơ": Bấm "Thay đổi ảnh" -> Hiện bottom sheet -> Bấm "Tải ảnh lên" (`input tap 540 1616`) -> Vào Gallery Picker -> Chọn ảnh đầu tiên -> Bấm "Tiếp" -> Vào màn Crop -> Bấm "Lưu" (`input tap 900 1800`) -> Hoàn tất.
- **Bẫy host thực thi Admin Remote (M >= 200):**
  - Thiết bị M >= 200 cắm USB trực tiếp vào máy Admin (`192.168.110.119`), không cắm vào máy local Kibe.
  - Chạy launcher local mà không cấu hình đúng ADB host sẽ bị lỗi `[DEVICE_OFFLINE] device not found`.
  - Phải dùng `python D:/Taadaa/tools/remote_admin_adb.py -s <serial>` hoặc chạy runner trực tiếp trên host Admin qua `admin_ssh.py` với `-HostConfigPath D:\Taadaa\machine-config\admin.yaml`.

