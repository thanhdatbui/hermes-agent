# S7 Stuck Shell Rescue & Farm Rolling Reboot Throttle Architecture (15/10/2026)

## 1. Bản Chất Kỹ Thuật: Kẹt ADB Shell vs Reboot S7 Qua PC

### A. Tại sao Reboot PC hiệu quả nhưng Reboot đồng loạt 80 máy S7 là tử huyệt
- **Nút thắt USB 2.0 nằm 100% ở Host Controller PC (Intel X99 EHCI `8D26`, `8D2D`):**
  - Băng thông USB 2.0 trần ~35-40 MB/s gánh 80 máy. Khi chạy lâu dồn dập, thanh ghi phần cứng chip EHCI bị kẹt đệm (`HRESULT 0x8004100c` không thể live-reset).
  - Reboot PC kích hoạt xung **PCI System Bus Reset** từ BIOS POST, xả sạch điện và thanh ghi controller, kéo toàn bộ 80 máy xanh trở lại.
  - S7 không "tích tụ rác" trên đường truyền USB. Hiện tượng delay/timeout `adb shell` là do hàng đợi buffer trên PC, không phải do chip S7 truyền chậm đi.
- **Hiểm họa khi reboot đồng loạt 80 máy S7:**
  1. *USB Enumeration Storm:* 80 daemon `adbd` đồng loạt handshake làm tràn bộ đệm PnP của Windows EHCI, gây sập cả cụm Hub (Box 3, Box 4 rụng hàng loạt máy).
  2. *Sụt áp nguồn Box Hub:* 80 máy cùng ăn dòng sạc max + CPU 100% lúc boot dễ gây sụt áp VBUS.
  3. *Bão DHCP Wi-Fi:* 80 máy cùng kết nối lại Wi-Fi gây nghẽn hàng đợi DHCP trên MikroTik / Aruba AP.
  4. *Thermal Throttling & Đơ máy:* S7 Android 8 sau boot kích hoạt Knox, MediaScanner, Dexopt ngốn 100% CPU trong 5-10 phút đầu, máy nóng ran và lag hơn bình thường.

### B. Kẹt ADB Shell thì có reboot S7 từ PC được không?
Phân biệt rạch ròi 2 tầng kẹt:
1. **Kẹt tầng Process / Shell con (VẪN REBOOT ĐƯỢC TỪ PC):**
   - Trong ADB protocol, service `reboot:` độc lập hoàn toàn với `shell:...` (`/system/bin/sh`).
   - Lệnh `adb -s <serial> reboot` gửi packet trực tiếp tới daemon `adbd` gọi `property_set("sys.powerctl", "reboot")`.
   - Dù một lệnh shell (`dumpsys`, script treo, deadlock) đang chiếm pty/sh, `adb reboot` vẫn đưa máy khởi động lại bình thường.
2. **Kẹt tầng USB Transport / Linux Kernel Pipe (TÊ LIỆT TỪ PC):**
   - Khi pipe `/dev/android_adb` trên kernel S7 bị đứt do nghẽn buffer, máy rơi vào `device offline` hoặc `device not found`.
   - Mọi lệnh ADB (cả shell lẫn reboot) đều không thể truyền qua cáp.
   - Do nguồn 5V VBUS vẫn duy trì, S7 không phát sinh uevent ngắt cáp nên `adbd` không tự restart. Lúc này giải pháp duy nhất từ xa là Reboot PC để BIOS ngắt VBUS trong tích tắc.

---

## 2. Kiến Trúc Cứu Hộ Phân Tầng O(1) (`recover_stuck_s7.py`)

Công cụ triển khai tại `D:\Taadaa\tools\recover_stuck_s7.py`:
- **Level 1 (Soft Recovery — 1.5s):**
  - Chạy lệnh shell nhẹ với timeout cứng 3.0s: `am force-stop com.ss.android.ugc.trill` và `input keyevent 223` (tắt màn hình).
  - 95% trường hợp máy chỉ kẹt app hoặc cần đưa về sleep: hoàn tất trong <= 2s, **hoàn toàn không cần reboot**.
- **Level 2 (Daemon Direct Reboot — Bypass Shell):**
  - Chỉ kích hoạt khi Level 1 timeout > 3.0s (shell bị treo cứng).
  - Gửi thẳng packet `adb -s <serial> reboot` (timeout 5s) và chờ `wait_for_device_boot` (wait-for-device + get-state == 'device').
- **Level 3 (Transport Triage):**
  - Thử `adb reconnect <serial>`. Nếu vẫn không phản hồi, đánh dấu `failed_transport` và dừng ngay, không làm nghẽn hàng đợi farm.

---

## 3. Kiến Trúc Rolling Healer Toàn Farm (`batch_recover_s7.py`)

Công cụ triển khai tại `D:\Taadaa\tools\batch_recover_s7.py`:
- **Chốt an toàn 1 (Khống chế I/O đồng thời):** `max_workers = 8` qua ThreadPoolExecutor (an toàn cho trần 35 MB/s của EHCI USB 2.0).
- **Chốt an toàn 2 (Khóa chống bão Reboot qua Semaphore):**
  - Khởi tạo `reboot_sem = threading.Semaphore(max_reboots=2)`.
  - Level 1 chạy song song 8 luồng bình thường.
  - NẾU máy nào cần leo thang lên Level 2 (reboot), worker bắt buộc acquire `reboot_sem`.
  - **Tối đa chỉ 2 máy được reboot đồng thời trên toàn farm.** Máy thứ 3 phải xếp hàng chờ máy trước boot xong và online trở lại mới được cấp vé reboot.
- **Tự động lọc slot trống:** Tự động bỏ qua slot trống máy 255 trên Admin Farm.
- **Chống cướp focus:** Mọi lệnh subprocess đều dùng `creationflags = subprocess.CREATE_NO_WINDOW`.

---

## 4. Kỷ Luật Test Python Mock Semaphore
- Trong CPython, `with sem:` gọi `__enter__` và `__exit__` được tra cứu trên cấp **Class** (`type(sem)`), không tra cứu trên instance dict.
- Khi viết unit test mock semaphore context manager, dùng `mock_sem = MagicMock()` và assert `mock_sem.__enter__.called` thay vì `patch.object(sem, "acquire")` hay `patch.object(sem, "__enter__")`.
