# S7 Hung Shell Triage & Rolling Healer Governance (2026-10-15)

## 1. Bản Chất Kỹ Thuật: Reboot PC vs Reboot S7 Khi Nghẽn Bus USB

- **Nút thắt cổ chai phần cứng nằm tại Host Controller PC (Intel C610/X99 EHCI USB 2.0):**
  * 80 máy cắm dồn qua các hub vào 2 controller EHCI (`8D26`, `8D2D`), trần băng thông thực tế ~35–40 MB/s.
  * Sau nhiều giờ chạy auto (screencap, dumpsys, streaming), thanh ghi phần cứng và hàng đợi buffer của chip EHCI bị kẹt cứng (lỗi phần cứng `HRESULT 0x8004100c` không thể reset mềm qua PnP).
  * Reboot PC phát xung **PCI System Bus Reset** từ BIOS/UEFI xả sạch điện và thanh ghi controller, kéo 100% ADB xanh tươi trở lại.
- **Reboot S7 không giải quyết được nghẽn bus USB mà còn gây thảm họa nếu chạy đồng loạt:**
  * Chip USB PHY trên S7 không tích tụ rác theo thời gian; độ trễ truyền dữ liệu là do nghẽn buffer trên PC.
  * **Bão USB Enumeration:** 80 máy S7 reboot cùng lúc sẽ kích hoạt 80 daemon `adbd` gửi gói kết nối USB về PC trong 1-2 phút, làm sập hoàn toàn 2 chip EHCI, gây rụng cả Box hub.
  * **Sụt áp VBUS & Bão Wi-Fi DHCP:** Đồng loạt khởi động lại gây sụt áp nguồn Box Hub và nghẽn hàng đợi DHCP trên MikroTik / Aruba AP.
  * **Warmup CPU Throttling:** 5–10 phút đầu sau boot, S7 chạy ngầm MediaScanner, Knox, dexopt khiến CPU 100%, máy nóng ran và lag hơn rất nhiều so với máy đang chạy bình thường.

## 2. Phân Tầng Kẹt Lệnh Shell: Khi Nào Reboot Được Qua PC?

- **Kịch bản A — Kẹt ở tầng Process/Shell con (VẪN REBOOT ĐƯỢC TỪ PC):**
  * Trong giao thức ADB, `shell:...` và `reboot:...` là 2 service hoàn toàn độc lập do daemon `adbd` quản lý.
  * Lệnh `adb reboot` **KHÔNG** chạy qua `/system/bin/sh`. Gói tin đi thẳng vào daemon `adbd` $\rightarrow$ gọi `property_set("sys.powerctl", "reboot")`.
  * Khi `dumpsys` hay script bị deadlock trong Android, shell bị treo nhưng daemon `adbd` vẫn sống $\rightarrow$ `adb -s <serial> reboot` vẫn khởi động lại máy tức thì từ PC.
- **Kịch bản B — Kẹt ở tầng USB Transport / Kernel pipe (TÊ LIỆT HOÀN TOÀN TỪ PC):**
  * Đường ống `/dev/android_adb` trên nhân Linux của S7 bị gãy socket pipe (máy báo `device offline` hoặc `device not found`).
  * Mọi lệnh ADB (cả shell lẫn reboot) đều không truyền được dữ liệu.
  * **Bẫy nguồn 5V VBUS:** Do cáp sạc vẫn cấp điện 5V, S7 không nhận biết được cáp đã mất dữ liệu nên không kích hoạt uevent để reset daemon `adbd`. Chỉ có thể giải phóng khi rút cáp, reset cổng từ BIOS khi reboot PC, hoặc smart power-cut.

## 3. Kiến Trúc Cứu Hộ 3 Cấp Độ O(1) (`recover_stuck_s7.py`)

- **Cấp 1 — Soft Recovery (<= 3.0s timeout):**
  * Gửi lệnh shell nhị phân nhẹ: `am force-stop com.ss.android.ugc.trill` và `input keyevent 223` (sleep).
  * Nếu thành công: Cứu app ngay lập tức trong 1.5s, không cần reboot.
- **Cấp 2 — Daemon Direct Reboot (5.0s timeout + 60s wait-for-boot):**
  * Chỉ kích hoạt khi Cấp 1 gặp `TimeoutExpired` hoặc kẹt shell.
  * Bắn trực tiếp `adb -s <serial> reboot` ở tầng daemon (bypass shell).
  * Chờ `wait-for-device` và kiểm tra `get-state == 'device'`.
- **Cấp 3 — Transport Triage & Isolation:**
  * Nếu Cấp 2 thất bại: Thử `adb reconnect <serial>`. Nếu vẫn unresponsive $\rightarrow$ ghi nhận `failed_transport`, dừng ngay để không làm nghẽn hàng đợi.

## 4. Quy Chuẩn Rolling Healer Toàn Farm (`batch_recover_s7.py`)

- **Khống chế I/O:** `ThreadPoolExecutor(max_workers=8)` tuân thủ Heavy-IO gate của farm.
- **Khóa trần Reboot (Hard Throttle):** `reboot_sem = threading.Semaphore(2)`. Bắt buộc tối đa **2 máy được reboot cùng một thời điểm**. Máy thứ 3 phải chờ 1 trong 2 máy trước boot xong mới được cấp vé. Triệt tiêu hoàn toàn bão PnP và nghẽn Wi-Fi DHCP.
- **Thực nghiệm toàn farm (~160 máy):** 155/159 máy vật lý (97.5%) hoàn tất Cấp 1 trong 33 giây; cách ly 3 máy lỗi tiếp xúc cáp vật lý (M10, M30 trên Kibe; M228 trên Admin) mà không gây gián đoạn hệ thống.
- **Testing Pitfall (Python C-level Semaphore):** Trong CPython, câu lệnh `with sem:` gọi trực tiếp `__enter__` và `__exit__` ở cấp độ C của class `type(sem)`. Khi viết unit test mock, việc dùng `patch.object(sem, "acquire")` hoặc `patch.object(sem, "__enter__")` trên instance `sem` sẽ không được gọi. Bắt buộc truyền `mock_sem = MagicMock()` để mock đánh chặn chính xác `__enter__` và `__exit__`.
