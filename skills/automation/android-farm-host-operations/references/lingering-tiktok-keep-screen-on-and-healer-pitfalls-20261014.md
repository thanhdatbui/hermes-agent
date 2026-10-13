# Bẫy TikTok Sáng Đèn Xuyên Đêm (FLAG_KEEP_SCREEN_ON), Nhầm Lẫn Ca Đêm & Ranh Giới Phóng Vệ vs Healer Cron

## 1. Hiện Tượng (Đêm 13/10/2026 - Rạng Sáng 14/10/2026)
- Người dùng mở Phóng Vệ (XiaoWei / JiWei) lúc 00:49 đêm thấy hơn 30 máy điện thoại vẫn đang sáng đèn và phát video TikTok liên tục.
- Câu hỏi đặt ra: "0h49 đêm còn chạy ca nào thế? Nhớ bỏ ca đêm rồi mà!" và "Có văng như làm gì tới mức như report (Phóng Vệ chỉ có 9 ô cam)?".

## 2. Bản Chất Kỹ Thuật

### A. Tại sao TikTok phát xuyên đêm dù không có ca đêm
1. Ca 3 kết thúc lúc 21:26 tối. Các máy chạy dưỡng sinh (32 máy) chạy trọn vẹn và được cleanup tắt màn hình đen.
2. Các máy bị lỗi giữa chừng (timeout ADB lệnh shell hoặc mất focus) bị runner ngắt ngang, bỏ qua bước `cleanup_close_all_after_session`.
3. Player video của TikTok trên Android (`com.ss.android.ugc.trill`) luôn kích hoạt cờ `WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON`.
4. Vì cờ này giữ màn hình luôn sáng, bộ đếm `screen_off_timeout` (10 phút) của Android bị bypass hoàn toàn và không bao giờ đếm lùi để tắt màn hình. Video/livestream tự động cuộn phát suốt đêm.

### B. Ranh giới hiển thị Phóng Vệ (XiaoWei) vs ADB Command Shell
1. Phóng Vệ truyền nhận khung hình qua luồng USB bulk endpoint / minicap driver nhẹ. Miễn là máy chưa ngắt điện hoàn toàn thì video stream vẫn chạy (chỉ 9 máy mất hẳn kết nối mới báo cam).
2. Automation runner nuôi acc bắt buộc thực thi qua ADB Command Shell (`settings get`, `dumpsys window`, `input swipe`). Khi chip USB EHCI bị nghẽn đệm, lệnh shell bị treo >25s timeout khiến runner đánh dấu thất bại toàn bộ máy.

### C. Lỗ hổng của cron `farm_idle_screen_and_app_healer.py`
1. **Chỉ quét `adb devices`:** Script lấy danh sách thiết bị từ `adb devices`. Các máy đã rớt ADB bị bỏ qua hoàn toàn.
2. **Không gọi tắt màn hình chủ động:** Code chỉ chạy `settings put system screen_off_timeout 600000` mà không gọi `input keyevent 26` (Power). Khi TikTok giữ wake lock, thiết lập này vô tác dụng.
3. **Timeout `dumpsys window` quá ngắn:** Đặt 4s khiến Samsung S7 thường xuyên TimeoutExpired và bị khối `except Exception: pass` nuốt chửng, không thể kích hoạt `am force-stop`.

## 3. Quy Trình Cứu Hộ & Khắc Phục Chuẩn Xác
- **Cứu hộ tức thời:** Dùng nút "Đóng tất cả ứng dụng" và "Tắt màn hình" trên thanh công cụ của Phóng Vệ (XiaoWei) vì driver USB của XiaoWei vẫn gửi được signal tới các máy đang nghẽn ADB.
- **Bẫy tử huyệt `input keyevent 26` (Power toggle) vs Giải pháp chuẩn `input keyevent 223` (KEYCODE_SLEEP):**
  * Nút Power (keyevent 26) là phím đảo trạng thái (toggle). Nếu thiết bị đã ngủ sẵn (như các máy dưỡng sinh), gửi 26 sẽ **BẬT SÁNG MÀN HÌNH TRỞ LẠI**.
  * BẮT BUỘC dùng **`input keyevent 223` (KEYCODE_SLEEP)**: Lệnh này có tính chất idempotent tuyệt đối — nếu màn hình đang sáng (`Display Power: state=ON` / `mWakefulness=Awake`) thì đưa về sleep; nếu màn hình đã ngủ sẵn thì **giữ nguyên ngủ 100%**, không bao giờ bị bật sáng ngược.
- **Thay thế `dumpsys window` bằng `pidof` (<0.1s):**
  * Lệnh nhị phân `pidof com.ss.android.ugc.trill com.zhiliaoapp.musically` phát hiện tức thì app TikTok còn sót trên máy nhàn rỗi (không có active lock trong `~/.codex/device-locks/`).
  * Khi phát hiện PID: chạy `am force-stop` cả 2 package, gửi `input keyevent 3` (Home) và `input keyevent 223` (Sleep).
- **Bộ kiểm thử tự động (Unit Test Regression):**
  * File test: `D:/Taadaa/tools/tests/test_farm_idle_screen_and_app_healer.py`.
  * Bao phủ 7 nhánh kiểm thử: `test_is_near_reboot_window`, `test_heal_device_locked`, `test_heal_device_lingering_tiktok_and_screen_off`, `test_heal_device_clean_idle`, `test_heal_device_adb_timeout`, `test_get_online_devices_failure`, `test_concurrent_healing` (100% passed).
  * Xử lý ngoại lệ tường minh: Thay vì nuốt `pass`, mọi lỗi lệnh ADB (`subprocess.TimeoutExpired`, runtime failure) đều được bắt vào danh sách `errors` và tính thời gian `duration_ms` cho từng thiết bị.
  * Xuất structured telemetry cuối phiên: `[TELEMETRY_METRIC] {"event": "idle_healer_done", "online": N, "healed": N, "stopped": N, "off": N}`.

## 4. Cơ Chế 3-Strike Closeout Remediation & Reviewer Hand-off
- **Quy trình Closeout Gate khi nghiệm thu tool farm:**
  * Strike 1 & 2: Sol High (:20129) tạo proposal O(1) qua `sol_repair.py`. Nếu Sol Repair không thể xử lý (exit != 0 / no findings), fallback dispatch Worker Gemini qua `delegate_task`.
  * Strike 3 Hand-off: Khi Sol High từ chối 3 lần liên tiếp trên cùng `scope_hash`, Closeout Gate in tín hiệu `[REVIEWER_HANDOFF_TRIGGERED: ...]`.
  * **Hành động bắt buộc:** CẢ Coordinator, Worker và Sol Repair DỪNG LẠI, chuyển giao quyền can thiệp cho Reviewer (Claude Code CLI) tự sửa theo tiêu chuẩn riêng của nó:
    ```bash
    claude -p "<Prompt bàn giao phạm vi allowlist và tiêu chí nghiệm thu>" --dangerously-skip-permissions
    ```
    Chạy nền với `notify_on_complete=True` để hoàn tất chốt phiên an toàn.
