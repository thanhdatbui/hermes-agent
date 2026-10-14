# Proxy Preflight Timeout and Cold-Launch Focus Triage (2026-10-14)

## 1. Triệu chứng lâm sàng (Symptoms)
- Phiên nuôi acc hàng loạt (Ca 1/2) văng 30-50% số máy ở cả 2 cụm (Kibe Local và Admin Remote).
- Báo cáo watchdog tổng kết hiển thị hàng loạt máy dính lỗi:
  + `[device-lock] machine N blocked by proxy VPN preflight` -> `device is offline or ADB/USB disconnected: adb command timed out: settings get global http_proxy`
  + `prepare-tiktok failed to focus TikTok after launch` (hoặc `focused package is unknown`)

## 2. Nguyên nhân kỹ thuật & Điểm mù (Root Cause Analysis)

### A. Proxy Preflight False Offline Trap
- **Vị trí:** `python_runner/core/vpn_preflight.py` tại hàm `require_proxy_connected`.
- **Cơ chế lỗi:** Lệnh `adb.shell(["settings", "get", "global", "http_proxy"], timeout=3.0, check=False)` đặt timeout cứng 3.0s không có retry.
- Khi 16-30 workers khởi động đồng loạt hoặc khi truy vấn cụm Admin qua socket mạng LAN TCP (`192.168.110.119:5037`), độ trễ hàng đợi ADB daemon vượt quá 3s, gây `subprocess.TimeoutExpired`.
- Ngoại lệ này bị hàm `is_connection_lost(err)` và kiểm tra `timed out` bắt trúng, tự động ném ra `ConsumerPreflightError: device is offline or ADB/USB disconnected`.
- Kết quả: Máy thật và proxy hoàn toàn bình thường nhưng bị hệ thống hiểu nhầm là rớt cáp/mất mạng và hủy phiên hàng loạt.
- **Biện pháp xử lý:** Tăng timeout lên 8.0s và bổ sung vòng lặp retry 2 lần với backoff 1.0s trước khi chấp nhận fail-closed.

### B. Samsung S7 Cold-Launch Delay vs Fast Fail-Closed
- **Vị trí:** `python_runner/flows/device_prepare.py` (`PREPARE_FOCUS_MAX_ATTEMPTS = 10`, `PREPARE_FOCUS_RETRY_DELAY_SECONDS = 1.5`).
- **Cơ chế lỗi:** Tổng thời gian chờ tối đa chỉ có 15s. Dòng Samsung Galaxy S7 (phần cứng Exynos 8890 cũ) khi khởi động nguội ứng dụng TikTok 47.0.3 nặng sau bước `am force-stop` thường mất từ 16–22s để nạp qua màn hình Splash.
- Bản vá Fast Fail-Closed đưa `failed to focus tiktok after launch` vào danh sách `_FATAL_DEVICE_ERROR_PATTERNS`, khiến worker cắt đứt toàn bộ phiên và giải phóng lease ngay khi chạm mốc 15s thay vì tiếp tục chờ.
- **Biện pháp xử lý:** Tăng `PREPARE_FOCUS_MAX_ATTEMPTS` lên 16 (tương đương 24s) để bao phủ độ trễ khởi động nguội trên thiết bị cũ.

## 3. Kinh nghiệm điều phối & Guard Contract Invariants
Khi Coordinator soạn contract cho Worker qua `delegate_task`:
1. **Giới hạn số file:** Tối đa $\le 2$ files (1 file nghiệp vụ + 1 file test). Cấm gộp 3 files trong 1 task.
2. **Fail-Fast Clause bắt buộc:** Bắt buộc có dòng:
   `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT) và trả về anchor + proposed contract, cấm đốt hết budget để mò file rồi fail im lặng.`
3. **Định dạng FOCUSED_TEST không khoảng trắng:**
   - Cú pháp chuẩn: `python -m pytest <file.py>::<test_node> -q` hoặc `python -m py_compile <file.py>`.
   - Lưu ý quan trọng: Parser regex guard dùng `[^\s]+\.py`, do đó đường dẫn chứa khoảng trắng (như `D:/Taadaa/tiktok-luot nuoi acc/...`) sẽ bị từ chối `INVALID_FOCUSED_TEST_FORMAT`. Bắt buộc dùng relative path không khoảng trắng như `python_runner/core/vpn_preflight.py`.
