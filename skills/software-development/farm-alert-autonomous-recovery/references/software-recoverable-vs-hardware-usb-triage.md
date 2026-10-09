# Phân Định & Tự Động Phục Hồi Phần Mềm vs Can Thiệp Phần Cứng (Software Healer vs Hardware Hub Outage)

## 1. Ma Trận Phân Định Khả Năng Xử Lý (Triage Matrix)

| Lớp sự cố | Triệu chứng kỹ thuật | Khả năng tự cứu bằng phần mềm | Cơ chế khắc phục phần mềm chuẩn |
| :--- | :--- | :---: | :--- |
| **1. Kẹt Socket Transport (I/O Deadlock / Hang)** | `adb devices` báo `device`, nhưng lệnh shell (`echo 1`, `screencap`) bị hang > 2.5s (do nghẽn pipe video XiaoWei/JiWei hoặc dump UI). | **CÓ (100%)** | Gửi `adb -s <serial> reconnect` để ngắt transport socket cũ mà không làm rớt adb server; phát tiếp `keyevent 224` để kích thích GPU render frame mới cho stream. |
| **2. ADB Daemon Desync (Offline logic)** | Thiết bị rơi vào trạng thái `offline` do adbd phía điện thoại bị lag/desync kết nối sau khi máy tải nặng hoặc chuyển ca. | **CÓ (~80%)** | Gửi `adb -s <serial> reconnect` kết hợp `adb reconnect offline`. Nếu server local Kibe kẹt, restart canonical `adb server` (`xiaowei/tools/adb.exe`). Tuyệt đối cấm kill-server trên Admin remote! |
| **3. ATX-Agent / UIAutomator Stub Crash** | ADB phản hồi tốt nhưng click/dump XML trên port 7912 văng `ATX_SESSION_UNAVAILABLE` hoặc `UI_XML_TIMEOUT`. | **CÓ (100%)** | Hạ sạch tiến trình uiautomator cũ: `am force-stop com.github.uiautomator*` rồi khởi động lại daemon: `/data/local/tmp/atx-agent server -d`. |
| **4. Mất kết nối Wi-Fi (Drop Carrier)** | Máy online ADB nhưng mất IP Wi-Fi nội bộ (`192.168.110.x`), không ra được proxy hoặc rớt mạng. | **CÓ (100%)** | Tự động toggle Wi-Fi radio: `svc wifi disable` ➔ chờ 1.5s ➔ `svc wifi enable` ➔ kiểm tra lại IP `wlan0`. |
| **5. Treo App / ANR / Màn hình sáng liên tục** | Máy nhàn rỗi (idle) nhưng app TikTok bị crash, kẹt popup ANR ("Ứng dụng không phản hồi") hoặc màn hình không chịu tắt. | **CÓ (100%)** | Gửi phím HOME (`keyevent 3`), force-stop app lỗi, đặt lại timeout tắt màn hình (`settings put system screen_off_timeout 600000`) và tắt màn hình (`keyevent 223`). |
| **6. Lỗi phần cứng Hub USB / Sụt áp nguồn** | Windows Device Manager báo `Unknown USB Device (Port Reset Failed)`, `Descriptor Request Failed` (chip điều khiển QinHeng/WCH bị kẹt). | **KHÔNG THỂ** | **Fail-Safe & Escalation**: Cô lập máy, không spam lệnh gây nghẽn bus, phân loại chính xác lỗi phần cứng và Hub InstanceId để báo đích danh vị trí Hub cần rút cắm lại nguồn. |

---

## 2. Bẫy Tử Huyệt: Báo Cáo Ảo "Healed" Khi Chỉ Mới Gửi Lệnh Reconnect (False Healing Trap)
- **Sai lầm phổ biến**: Nhiều script/watchdog khi thấy máy offline chỉ chạy `adb reconnect offline` rồi lập tức ghi nhận `healed_list.append(f"M{m} (offline -> reconnect)")` và báo cáo hoàn tất trong khi thiết bị thực tế vẫn `offline` do kẹt phần cứng!
- **Kỷ luật Two-Phase Verification Gate bắt buộc**:
  1. **Pre-check**: Ghi nhận trạng thái ban đầu (`offline`, `hung`, `atx_dead`...).
  2. **Execute Remedy**: Thực thi lệnh khắc phục tương ứng với timeout <= 4s.
  3. **Post-check (Kiểm chứng thực tế)**: Chờ 1–2s, gọi lại `adb devices` và chạy test shell ping (`adb shell echo 1`, timeout 2.5s).
  4. **Kết luận**:
     - CHỈ KHI trạng thái chuyển thành `device` VÀ shell ping trả về `1` mới được xác nhận `RECOVERED`.
     - Nếu sau khi thử các biện pháp phần mềm mà post-check vẫn `offline` / `not found` -> Gắn cờ `HARDWARE_FAULT_SUSPECTED`, đưa vào danh sách sự cố phần cứng, CẤM báo hoàn tất ảo.

---

## 3. Kiến Trúc Kịch Bản Tự Cứu Phần Mềm Đa Tầng (`farm_software_auto_healer.py`)

Kịch bản chuẩn hóa tự động vận hành theo 5 nguyên tắc:
1. **Device Lock Guard**: Bỏ qua các máy đang có lock hợp lệ (`.codex/device-locks`) để bảo vệ ca nuôi/upload đang chạy.
2. **Dual-Cluster Support**: Xử lý song song Kibe Local và Admin Remote (`192.168.110.119:5037`).
3. **Strict Timeout**: Mỗi lệnh ADB giới hạn <= 3–5s, chạy đa luồng `ThreadPoolExecutor(max_workers=25)`.
4. **Silent Watchdog Pattern**: Giữ `stdout` rỗng khi bình thường hoặc tự sửa xong, xuất telemetry qua `stderr`.
5. **Hardware Isolation**: Khi phát hiện chùm máy cùng Hub dính `Port Reset Failed`, script tự động nhóm theo Hub ID và báo cáo rõ cần thao tác nguồn vật lý cho Hub nào.
