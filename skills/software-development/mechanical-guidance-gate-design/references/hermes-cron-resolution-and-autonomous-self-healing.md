# Cron Script Resolution & Autonomous Self-Healing Pipeline Activation

## 1. Cron Script Path Resolution on Windows (Chống Lỗi Script Not Found & Policy Block)

### Hiện Tượng và Nguyên Nhân:
Khi đăng ký cronjob trong Hermes với `no_agent: true` trên hệ điều hành Windows:
1. **Pre-Tool Hook Denial (Script Resolution Check):**
   - Hook an toàn cron kiểm tra đường dẫn qua hàm đối chiếu các roots: `cwd`, `D:/Taadaa`, và thư mục scripts runtime.
   - Trong phiên làm việc của Coordinator, `cwd` mặc định là `C:\Users\Kibe`. Nếu script mới viết chỉ nằm trong `D:/Taadaa/tools` mà chưa có trong `cwd` hoặc thư mục scripts runtime, lệnh tạo cronjob bị chém văng ngay với thông báo script không tồn tại.
2. **Runtime Execution Denial (`Script not found`):**
   - Khi cron daemon thực sự chạy (runner execution tick), engine của Hermes tự động nối đường dẫn: `<runtime_dir>\<script>`.
   - Nếu Coordinator cố tình lách hook bằng cách truyền `scripts/<script>.py`, engine sẽ tìm kiếm tại `<runtime_dir>\scripts\<script>.py` -> Crash với lỗi `Script not found` và `last_status: error`.

### Quy Chuẩn Cơ Học 3 Bước Bắt Buộc:
1. **Đặt script tại gốc deploy:** Đặt script trong `D:/Taadaa/Hermes/deploy/hermes-home/scripts/<script>.py`.
2. **Đồng bộ đa tầng qua cron sync watchdog:**
   - Chạy đồng bộ tự động để file được phân phối nguyên tử tới cả 3 nơi:
     * Thư mục scripts của runtime Kibe (cho Cron runner engine).
     * `C:\Users\Kibe\<script>.py` (cho resolver kiểm tra khi cwd là user home).
     * `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\<script>.py` (cho sao lưu phân tán).
3. **Khai báo tên file trần:** Chỉ truyền `script: "<script_name>.py"` (không có tiền tố thư mục).

---

## 2. Closed-Loop Autonomous Self-Healing Activation (Kích Hoạt Tự Động Hóa Tự Lành 100%)

### Vấn Đề "Hạ Tầng Ngủ Quên" (Dormant Engine):
Dù các khối lõi đã được xây dựng và pass test 100% (`incident_envelope`, `incident_lock`, `incident_auto_harness`), hệ thống vẫn không tự sửa lỗi nếu thiếu 2 dây nối sống:
1. **Thiếu Dispatcher Cron:** Không có tiến trình định kỳ quét thư mục `pending/` để kéo Harness vào chạy.
2. **Thiếu Envelope Emitter:** Các watchdog ca chạy chỉ ghi log/alert ra console mà không đóng gói sự cố.

### Mô Hình Vận Hành Khép Kín 4 Pha:
1. **Pha 1 (Catch & Envelope):**
   - Watchdog ca chạy (ví dụ watchdog ca nuôi) khi phát hiện máy lỗi UI/kẹt màn hình:
     * Chụp ảnh `.png` + dump cây UI `.xml` + trích xuất 3 frames stack trace.
     * Khởi tạo `IncidentEnvelope(...)` và gọi `.save_pending()` (ghi nguyên tử tempfile -> rename vào `runtime/incidents/pending/<id>.json`).
     * Đưa điện thoại về HOME và nhả device-lock ngay lập tức để không ngâm máy kẹt ca nuôi.
2. **Pha 2 (Dispatcher Sweep - 15m Cron):**
   - Cronjob `incident-auto-heal-dispatcher` chạy mỗi 15 phút với `cron_incident_auto_heal.py` (`no_agent: true`).
   - Tuân thủ **Watchdog Silent Pattern:** Nếu `pending/` không có file -> Thoát im lặng exit 0 (zero token).
   - Nếu có file -> Kích hoạt `process_queue()` duyệt qua từng sự cố.
3. **Pha 3 (Autonomous 6-Gate Harness):**
   - Khóa file bằng `IncidentLock` (chống xung đột branch/git diff giữa các incident).
   - Chạy tuần tự 6 Gate:
     * Gate 0: Chấm điểm Telemetry (Score = 2 khi đủ cả XML lẫn Screenshot).
     * Gate 1: Dispatch Claude Sonnet (hoặc Sol) lên plan kỹ thuật O(1).
     * Gate 2: Dispatch Worker sửa code theo contract.
     * Gate 3: Quét Invariant GuardGate Step 2.5 chống sửa ngược hằng số an toàn.
     * Gate 4: Bắt buộc Canary Gate máy thật xác nhận kết quả.
     * Gate 5: Sol Reviewer chấm độc lập >= 85 điểm.
4. **Pha 4 (Atomic Resolve & Report):**
   - Pass 100% các cổng -> Chuyển file sự cố sang `runtime/incidents/resolved/<id>.json`.
   - Bắn thông báo nghiệm thu kèm MEDIA/Screenshot và điểm review về Telegram Farm Alert (`-5373649734`).
