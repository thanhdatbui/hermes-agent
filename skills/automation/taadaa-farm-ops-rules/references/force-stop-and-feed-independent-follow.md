# Quy trình Dừng Khẩn Cấp Thiết Bị & Follow Độc Lập Khỏi Trạng Thái Feed (30/08/2026)

## 1. Quy trình Dừng Thiết Bị Farm An Toàn (Anti-Lệnh Ảo / Lệnh Láo)

Khi người dùng yêu cầu **"Tạm dừng all máy"** hoặc **"Dừng toàn bộ thiết bị"**:

1. **Kill tiến trình chủ trên PC trước:**
   - Dùng `psutil` hoặc `taskkill` quét và kill toàn bộ process `python_runner`, `multi_machine_feed_session`, `run_tiktok`, `tiktok_workflow`, `tiktok_runner`, `pytest`.
2. **Gửi lệnh dừng kép song song tới toàn bộ thiết bị ADB:**
   - Lấy danh sách serial online từ `adb devices`.
   - Dùng `ThreadPoolExecutor(max_workers=30)` gửi lệnh gộp:
     ```bash
     adb -s <serial> shell "am force-stop com.ss.android.ugc.trill; am force-stop com.zhiliaoapp.musically; input keyevent 3"
     ```
3. **BẮT BUỘC Hậu Kiểm Hiện Trường Thật (Proof of Stopped State):**
   - Quét lại toàn bộ máy qua `dumpsys window windows` để lấy `mCurrentFocus`.
   - Kiểm tra `is_tiktok = "com.ss.android.ugc.trill" in focus or "com.zhiliaoapp.musically" in focus`.
   - **Chỉ khi `total_running_tiktok == 0` (100% máy về Home/Launcher) mới được báo cáo hoàn tất cho người dùng.** Tuyệt đối không báo cáo khi chưa có kết quả dump focus thực tế.

---

## 2. Quy tắc Follow Hook Độc Lập Khỏi Trạng Thái Feed

- **Quy tắc vận hành:** Kể cả khi phiên lướt Feed gặp lỗi (swipe limit, drift, timeout, degraded...), máy vẫn được phép chuyển sang hook Follow chéo `_run_follow_hook` (miễn là thỏa mãn điều kiện Gate $\ge 5$ video và không dính `follow-released-daily-cooldown`).
- **Phân loại Watchdog chuẩn:**
  - Watchdog chỉ tính lỗi Follow (`fl_error`) hoặc Upload (`up_error`) khi máy đã hoàn tất bước Feed thành công (`status == "success"`) mà hook bị lỗi.
  - Các máy fail ở Feed / bị lock thiết bị không có kết quả follow/upload **tuyệt đối không được tính vào "Lỗi script/xác minh" của Follow/Upload**.
