# USB Concurrency vs Schedule Window Budget & Launch Stagger Tuning (2026-10-14)

## 1. Bối cảnh & Bài học điều phối (User Correction)
- **Sự cố:** Sau đợt văng hàng loạt 44 máy (26 máy offline USB + 10 máy kẹt focus TikTok), Coordinator từng đề xuất và thử hạ `MaxWorkers` từ `25` xuống `16` để bảo vệ bus USB.
- **Phản hồi chỉnh đốn của User:** *"T sợ k đủ time chạy á chứ. Lúc giảm worker 40 xuống 25 đã gây tănh time cả phiên lên bn r"*.
- **Bài học cốt lõi:** Tuyệt đối không được hạ `MaxWorkers` dưới `25` một cách cơ học mà không tính toán ngân sách thời gian (time budget) của lịch nuôi acc.

---

## 2. Phân tích số liệu thực tế từ hệ thống (Hard Evidence)

### 2.1. So sánh thời lượng theo mức concurrency:
* **`MaxWorkers = 40` (giai đoạn trước 10/10):**
  * Số batch: $\lceil 80 / 40 \rceil = 2$ đợt chạy.
  * Thời gian hoàn thành 1 phiên: **45 – 65 phút**.
* **`MaxWorkers = 25` (từ 11/10):**
  * Số batch: $\lceil 80 / 25 \rceil = 4$ đợt chạy (25 + 25 + 25 + 5 máy).
  * Thời gian hoàn thành 1 phiên: **75 – 90 phút** (chạm mốc tối đa 120 phút nếu có máy lỗi ngâm timeout).
* **Nếu hạ xuống `MaxWorkers = 16`:**
  * Số batch: $\lceil 80 / 16 \rceil = 5$ đợt chạy (16 x 5).
  * Thời gian hoàn thành sẽ vượt ngưỡng **130 phút**.

### 2.2. Ngân sách khung giờ (Schedule Window Budget):
* Chu kỳ nuôi 3 Ca/ngày gồm 2 Phiên/ca:
  * Ca 1: Phiên 1 lúc **06:00**, Phiên 2 lúc **08:00** (cửa sổ 120 phút).
  * Ca 2: Phiên 1 lúc **12:00**, Phiên 2 lúc **14:00** (cửa sổ 120 phút).
  * Ca 3: Phiên 1 lúc **18:00**, Phiên 2 lúc **20:00** (cửa sổ 120 phút).
* **Hậu quả nếu phiên > 120 phút:** Phiên 1 chưa chạy xong đã đến giờ cron kích hoạt Phiên 2 $\rightarrow$ Watchdog buộc phải dập cưỡng bức hoặc xung đột tài nguyên/lock hàng loạt.
* **Quy tắc bất biến:** `MaxWorkers = 25` là **ngưỡng sàn cứng (hard floor)** để bảo toàn tiến độ toàn farm.

---

## 3. Giải pháp chuẩn: Giãn nhịp khởi động (Launch Stagger) thay vì bóp Concurrency

### 3.1. Bản chất điểm nghẽn của Bus USB
* Bus USB Intel X99 bị nghẽn không phải do số lượng máy lướt web nền, mà do **bão lệnh (command storm)** tại thời điểm khởi động:
  * 25 máy cùng lúc gửi lệnh `monkey -p com.ss.android.ugc.trill` và `dumpsys window` qua daemon ADB.
  * Việc này làm bão hòa hàng đợi socket ADB và gây sụt áp tạm thời tại các hub USB.

### 3.2. Cấu hình Stagger chuẩn hóa
* Thay vì giảm số worker đồng thời, thực hiện giãn cách thời điểm kích hoạt từng worker:
  * Tăng `MachineStartStaggerMs` từ `2000,8000` (2s–8s) lên **`3000,10000` (3s–10s)**.
  * Áp dụng đồng bộ tại 3 vị trí:
    1. `scripts/run-feed-session.ps1`: `$effectiveMachineStartStaggerMs = "3000,10000"`
    2. `scripts/hermes_cron/tiktok_runner.py`: `-MachineStartStaggerMs "3000,10000"`
    3. `run_74machines.bat`: `-MachineStartStaggerMs 3000,10000`
* **Hiệu quả:**
  * Giải tỏa triệt để bão socket lúc launch.
  * Giữ nguyên thông lượng 25 workers song song trong suốt 60-70 phút lướt feed tiếp theo.
  * Tổng thời gian phiên không đổi, hoàn thành an toàn trong < 85 phút.

---

## 4. Triage Phục hồi sau Host Auto-Reboot (Uptime Verification)
* Khi nhận alert sụt hàng loạt thiết bị (20+ máy offline), trước khi can thiệp thủ công:
  * Kiểm tra Uptime của PC Host:
    ```python
    import psutil, time
    uptime = time.time() - psutil.boot_time()
    ```
  * Nếu máy vừa reboot gần đây (< 30-40 phút), System Bus Reset từ BIOS đã tự động giải phóng các thanh ghi EHCI USB bị treo.
  * Kiểm tra lại toàn bộ fleet qua `python D:/Taadaa/tools/inspect_machine.py`. Các máy rớt do nghẽn transport mềm sẽ tự động chuyển về trạng thái `device`.
  * Chỉ những máy vẫn báo `device not found` sau reboot (ví dụ M10) mới là lỗi tiếp xúc vật lý cần kiểm tra dây cáp.
