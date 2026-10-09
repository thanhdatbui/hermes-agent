# Cân bằng Outer Timeout, Concurrency và Inner Timing Budget trong Batch Cron Dọn Cache TikTok (2026-09-09)

## 1. Hiện tượng & Bối cảnh Sự cố (30/78 Máy Dính Timeout Hàng Loạt)
- **Log hiện trường:** `~/.hermes/cron/output/79021fa79d8b/2026-09-09_04-04-24.md`.
- **Thực trạng:** 48 máy thành công, 30 máy thất bại với nhãn đồng loạt `Máy XX: Timeout` lúc 04:04 sáng.
- **Nguyên nhân cốt lõi (Root Cause):**
  1. **Lệch pha ngân sách thời gian (Outer vs Inner Timing Budget):**
     - Outer subprocess timeout trong `cron_clear_tiktok_cache.py` đặt cứng **120s**.
     - Inner flow trong `clear-tiktok-cache.py` có cấu trúc 3 tầng: Path 1 (Deep Link) -> Path 2 (In-App Settings navigation) -> Path 3 (Widget probe).
     - Khi Deep Link thất bại (rất phổ biến sau cập nhật TikTok), kịch bản tự fallback về Path 2:
       * Wakeup + Monkey launch + Poll UI interactive (deadline 15s).
       * Chuyển tab Hồ sơ -> Mở menu 3 gạch -> Mở Cài đặt & riêng tư (mỗi bước tốn delay + dump UI = 3–5s).
       * Vòng lặp cuộn tìm "Giải phóng dung lượng" lặp tới 8 lần (mỗi lần swipe 1s + sleep 1.2s + dump UI ATX 2–3s = 4.5–6.5s/lần -> 35–45s).
       * Mở màn hình Giải phóng dung lượng -> Bấm Xóa -> Chờ dialog -> Bấm xác nhận -> Sleep 4s -> Dump UI verify 0,0MB (12–15s).
       * **Tổng thời gian thực tế của Path 2:** 85s – 140s trong điều kiện bình thường. Khi gặp trễ mạng/ATX, chắc chắn vượt 120s khiến tiến trình cha ngắt ngang (`subprocess.TimeoutExpired`).
  2. **Quá tải hàng đợi ADB Server do Concurrency quá cao (40 Workers không Stagger):**
     - Khác với batch upload video (có random stagger 2000–8000ms), cron dọn cache ban đầu chạy `MAX_WORKERS = 40` đồng loạt đẩy lệnh qua ADB daemon và cổng ATX TCP 7912.
     - 40 luồng uiautomator dump / TCP socket cùng lúc làm nghẽn daemon ADB trên Windows, đẩy độ trễ mỗi lệnh `dump_ui` từ 0.5s lên 5–15s.

## 2. Kỷ luật Cân chỉnh Tối thiểu (Anti-Overengineering)
Thay vì đập đi xây lại toàn bộ flow hoặc thêm các cơ chế phức tạp, áp dụng combo cân chỉnh tối thiểu vào đúng 2 file trong phạm vi Scope Lock:

### A. Tầng Cron Điều phối Ngoài (`cron_clear_tiktok_cache.py`)
1. **Hạ Worker Concurrency:** Giảm `MAX_WORKERS = 40` xuống `MAX_WORKERS = 20`. 78 máy chia thành ~4 đợt chạy tuần tự, triệt tiêu xung đột socket ADB và bảo toàn ổn định bus USB.
2. **Mở rộng Outer Timeout:** Nâng từ `120s` lên `300s` (5 phút). Đảm bảo đủ headroom an toàn (gấp 2.5x–3x thời gian chạy xấu nhất của Path 2).
3. **Phân loại mã lỗi chính xác trong báo cáo:**
   - Phân biệt rạch ròi giữa `Timeout` thật của subprocess cha (`[TIMEOUT]` / `timed out after 300s`) với các lỗi UI từ kịch bản con:
   ```python
   if "[TIMEOUT]" in msg or "timed out after" in msg:
       reason = "Timeout"
   elif "WIDGET_MISS" in msg:
       reason = "WIDGET_MISS"
   elif "UI_CHANGED" in msg:
       reason = "UI_CHANGED"
   elif "VERIFY_FAIL" in msg:
       reason = "VERIFY_FAIL"
   elif "ADB_ERROR" in msg:
       reason = "ADB_ERROR"
   elif "timed out" in msg.lower() or "timeout" in msg.lower():
       reason = "Timeout"
   ```

### B. Tầng Kịch bản Thao tác Trong (`clear-tiktok-cache.py`)
1. **Rút ngắn Delays an toàn:**
   - `PAGE_DELAY = 1.2` (từ 2.0s)
   - `AFTER_TAP_DELAY = 1.8` (từ 3.0s)
   - `AFTER_CONFIRM_DELAY = 2.5` (từ 4.0s)
2. **Siết trần Timeout ATX dump:**
   - Giảm timeout từ 15s/20s xuống 10s/12s để kịch bản không bị ngậm tới 85s khi ATX agent bị đơ, nhanh chóng kích hoạt fallback uiautomator shell.
3. **Thu hẹp Vòng lặp Cuộn Cài đặt (Swipe Loop):**
   - Giảm số vòng vuốt từ 8 xuống 6 (với màn 1080x1920 vuốt 1000px, 6 lần vuốt là đủ 6000px, bao phủ toàn bộ danh mục Cài đặt TikTok).
   - Rút ngắn `time.sleep(1.2)` sau swipe xuống `0.6s` (do hàm `swipe()` đã có sẵn delay 1.0s).

## 3. Checklist Đo đạc Thời lượng (Timing Budget Rule)
Trước khi đặt `subprocess.run(..., timeout=N)` cho bất kỳ tác vụ ADB/UI nào:
- **Tính Worst-Case Path:** `T_worst = T_fallback_1 + T_fallback_2 + (N_swipes * T_swipe) + T_verify + T_retries`.
- **Hệ số an toàn:** `Outer Timeout >= 2.0 * T_worst`.
- **Ngưỡng Worker an toàn:** Nếu không có random stagger khởi động, `MAX_WORKERS` tối đa cho các tác vụ UI dump đồng loạt là 20.
