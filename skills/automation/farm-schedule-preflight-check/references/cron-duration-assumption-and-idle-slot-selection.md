# Cạm Bẫy Tính Toán Giờ Lịch Nuôi Acc & Cơ Chế Canh Máy Thật (Real Runtime vs Static Guessing)

## 1. Cạm Bẫy Tính Thời Lượng Ca Nuôi Tĩnh (Static Duration Assumption Trap)
- **Sai lầm phổ biến:**
  - Giả định ca nuôi 18:00 chỉ mất 40 phút (`18:00 + 40m = 18:40`), nên cài đặt cron task on-demand / canary chạy lúc `19:35` với suy nghĩ "cách ca 20:00 hẳn 25 phút là máy đã rảnh 100%".
- **Thực tế vận hành trên Phone Farm 80 máy:**
  - Một ca nuôi (`row-X`) không chỉ là thời gian swipe video thuần túy.
  - Tổng thời lượng thực tế bao gồm:
    1. Giãn cách khởi động giữa các máy (`MachineStartStaggerMs: 2000, 8000`).
    2. Độ trễ tải video trên proxy 4G Mobi.
    3. Thao tác dọn dẹp teardown, đóng TikTok, release lock.
    4. Thao tác upload video ở Phiên 2 (nếu có hook).
  - Do đó, một ca nuôi có thể kéo dài **từ 60 đến 90+ phút**.
  - Hậu quả: Khi cron on-demand chạy lúc 19:37, máy vẫn đang ở trạng thái `mCurrentFocus = SplashActivity` (TikTok đang chạy). Chốt an toàn buộc phải `SKIP`, làm mất cơ hội chạy task và gây khó chịu cho user ("cài cron canh giờ ngu").

## 2. Giải Pháp Chuẩn Bắt Buộc (Adaptive / Event-Driven / Idle Slot Selection)
1. **Tuyệt đối không đoán giờ tĩnh khi máy có lịch nuôi:**
   - Nếu cần chạy on-demand hoặc test canary trên một máy, không hẹn giờ mù dựa vào phép cộng trừ thời gian.
2. **Chọn máy không có tài khoản trong ca hiện tại (Zero-Account Slot Selection):**
   - Thay vì chọn máy đang bận nuôi (như M19 có acc ở Row 6 đang chạy), hãy rà soát workbook `taikhoan_run_safe.xlsx`:
     - Tìm máy có `Row X = None` (ví dụ: M71 không có acc ở Row 6, 7, 8).
     - Máy này hoàn toàn không được phân bổ tài khoản trong ca nuôi hiện tại $\rightarrow$ Máy ở `LauncherActivity` (rảnh 100%), có thể chạy test ngay lập tức mà không sợ đụng độ cron nuôi acc.
3. **Mô hình Watchdog động (Adaptive Watchdog Pattern):**
   - Nếu bắt buộc phải chạy trên đúng máy đó: Cài đặt watchdog quét chu kỳ 3-5 phút kiểm tra trạng thái thực tế:
     - `mCurrentFocus != com.ss.android.ugc.trill`
     - Không có file lock tại `~/.codex/device-locks/machine_<M>.lock.json`
     - Sau khi thỏa mãn cả hai điều kiện mới kích hoạt tác vụ và tự hủy watchdog.
