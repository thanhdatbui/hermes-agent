# Phân Biệt Thực Thi Nuôi Acc (Runner) vs Giám Sát Cứu Hộ (Watchdog)

## 1. Bản Chất Kiến Trúc Hai Trục

Trong hệ thống vận hành nuôi TikTok trên farm 80-160 thiết bị (`D:/Taadaa/tiktok-luot nuoi acc`), hai file `multi_machine_feed_session.py` và `feed_session_watchdog.py` đóng hai vai trò hoàn toàn tách biệt:

| Tiêu Chí | `multi_machine_feed_session.py` (Thợ Thi Công) | `feed_session_watchdog.py` (Giám Sát Cứu Hộ) |
| :--- | :--- | :--- |
| **Bản chất** | **Execution Engine** (Bộ máy thực thi nuôi acc trực tiếp) | **Supervisor Watchdog** (Cơ chế giám sát ngoài băng) |
| **Vị trí file** | `python_runner/flows/multi_machine_feed_session.py` | `scripts/feed_session_watchdog.py` (kèm `scripts/watchdog/`) |
| **Nhiệm vụ chính** | - Mở TikTok, kiểm tra proxy/VPN, điều khiển AdbKeyboard.<br>- Phân bổ luồng For You (75%), Following (15%), Friends (10%).<br>- Thực hiện tương tác xem, thả tim, follow, lướt video theo slot. | - Quét heartbeat kiểm tra các máy có bị đơ/treo quá 30 phút không.<br>- Dọn dẹp tiến trình zombie/mồ côi (`parasite`).<br>- Gỡ device lock bị kẹt (`stale locks`).<br>- Gửi cảnh báo Telegram và tự động kích hoạt auto-resume. |
| **Vòng đời / Tần suất** | Chạy theo **Ca nuôi cố định** (Ca sáng 6h, Ca trưa 12h, Ca tối 18h), kéo dài 1 - 2 tiếng/ca. | Chạy **liên tục mỗi 15 phút** (`*/15 * * * *`) trong cron suốt 24/7. |

---

## 2. Cron Nuôi Acc Thực Tế Dùng File Nào?

Cấu hình Cronjob chính thức của hệ thống (trong `setup_admin_cron.py` & `%LOCALAPPDATA%/hermes/cron/jobs.json`):

### A. Cron Nuôi Acc Chính: `phase9-runner-tiktok-feed`
* **Lịch chạy:** `*/15 * * * *`
* **Lệnh kích hoạt:** Gọi `tiktok_runner.py` (hoặc `scripts/run-feed-session.ps1`).
* **Chuỗi gọi thực tế:**
  `tiktok_runner.py` $\to$ `run-feed-session.ps1` $\to$ `python_runner/run_tiktok.py --mode multi-machine-feed-session` $\to$ **Thực thi `flows/multi_machine_feed_session.py`**.
* **Ý nghĩa:** Đây là luồng thực sự điều khiển điện thoại vuốt màn hình và nuôi tài khoản.

### B. Cron Giám Sát: `tiktok-feed-session-watchdog`
* **Lịch chạy:** `*/15 * * * *`
* **Lệnh kích hoạt:** Chạy script `feed_session_watchdog.py`.
* **Ý nghĩa:** Không đụng vào ADB lướt video của máy, chỉ đứng ngoài đọc file log/JSON trạng thái, nếu thấy ca nuôi bị crash hoặc máy đơ thì phát tín hiệu cứu hộ.

---

## 3. Cơ Chế Bắt Buộc Khi Viết Script Mới (Chống Đẻ Monolith)

Để ngăn chặn việc AI hoặc lập trình viên tiếp tục viết các file script khổng lồ > 1.500 dòng:

1. **Phanh cơ học vật lý ở Closeout Gate (`MAX_DIFF_BYTES_GATE = 30_000` bytes):**
   Mọi commit có diff candidate vượt quá 30 KB sẽ bị Closeout Gate ngắt cầu dao ngay lập tức (`[Gate Fail-Fast: DIFF_TOO_LARGE]`), cấm push lên GitHub. Bắt buộc người viết phải chia nhỏ tính năng thành các package/module mỏng (100 - 300 dòng/file).
2. **Bộ Test Gác Cổng Kiến Trúc (`test_*architecture_gate.py`):**
   Mọi module mới đều phải có unit test gác trần số dòng (`assertLess(len(lines), MAX_BUDGET)`). Nếu cố tình nhồi nhét code vượt trần, CI test suite sẽ đánh trượt ngay lập tức.
3. **Quy tắc Single Responsibility:**
   Phân tách tuyệt đối 3 tầng:
   - `core/`: Data models & logic thuần túy (không dính giao diện hay network).
   - `flows/` hoặc `services/`: Điều phối luồng nghiệp vụ.
   - `tests/`: Bộ test tương ứng.
