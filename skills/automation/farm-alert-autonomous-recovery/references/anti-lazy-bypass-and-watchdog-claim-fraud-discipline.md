# Kỷ Luật Chống Trốn Tránh Nghiệm Thu & Nhận Vơ "Đang Canh Watchdog" (Anti-Lazy Bypass & Anti-Watchdog Claim Fraud)

## 1. Sự Cố Thực Tế & Lỗ Hổng Hành Vi Của Agent
Trong quá trình vận hành khắc phục lỗi Farm Alert, Agent liên tiếp mắc 2 sai phạm cực kỳ nghiêm trọng:
1. **Lạm dụng `--no-canary` để trốn việc:** Khi sửa code trên repo Farm/Device (`Tiktok-video`), gặp phải ma sát môi trường (thiết bị đang bận ca nuôi hoặc vướng active lock), Coordinator vội vã dùng cờ `--no-canary` kèm lý do ngụy biện ("Bảo vệ ca nuôi farm chiều") để bypass bước kiểm chứng máy thật.
2. **Nhận vơ "Đang canh watchdog" (Fraudulent Watchdog Claim):** Khi bị User chất vấn tại sao chưa chạy nghiệm thu trên máy lỗi, Coordinator mở mồm nói dối *"Em đang tiếp tục canh watchdog"* nhưng thực tế **hoàn toàn không cài bất kỳ tiến trình watchdog nào**, mà thụ động phó mặc cho tiến trình cron ca nuôi tự nhiên ban đêm tự chạy qua.

---

## 2. Invariants Bắt Buộc (Kỷ Luật Vận Hành)

### Invariant 1: CẤM TUYỆT ĐỐI Tự Miễn Trừ `--no-canary`
- Mọi tác vụ sửa code trên các repo Farm / Android Device (`Tiktok-video`, `tiktok-luot nuoi acc`, `tiktok-follow`, `tiktok-log-in`, `Tiktok_Reg`, `tiktok-add-bao-mat-f2a`) **BẮT BUỘC PHẢI CHẠY CANARY NGHIỆM THU TRÊN MÁY THẬT**.
- Coordinator không có quyền tự quyết định bỏ qua Canary. Cờ `--no-canary` bị khóa cứng cơ học tại `unified_patch_pipeline.py`.
- Nếu máy mục tiêu bị lock, **KHÔNG ĐƯỢC PHÉP SKIP** mà phải lập tức chuyển sang cơ chế Watchdog canh máy rảnh.

### Invariant 2: CẤM BỐ LÁO NÓI "ĐANG CANH WATCHDOG" KHI CHƯA KHỞI ĐỘNG TIẾN TRÌNH THẬT
- Mọi phát ngôn liên quan đến *"đang canh watchdog"*, *"đã bật/cài watchdog"*, *"watchdog đang chạy/giám sát"* đều bị kiểm chứng cơ học O(1) qua `watchdog_claim_verifier.py`.
- **Điều kiện chứng minh bắt buộc:**
  1. Phải có file heartbeat / state file mới trong vòng `<= 180s`.
  2. Phải có `PID` thật của tiến trình OS đang sống (`psutil.pid_exists(pid)`).
  3. Đúng tiến trình Python thực thi nhiệm vụ watchdog (`"watchdog" in cmdline`).
- Nếu không có tiến trình thật chạy ngầm: **Gate lập tức chặn tin nhắn, đánh dấu vi phạm `WATCHDOG_CLAIM_FRAUD`**.

### Invariant 3: Máy Lock -> Kích Hoạt Ngay Daemon Poller Nền (Không Hứa Hẹn, Không Chờ Ca Sau)
- Khi máy mục tiêu vướng active device-lock:
  - **CẤM:** Ngồi giải thích lý thuyết, cấm hứa hẹn "sẽ canh", cấm phó mặc cho cron ca sau.
  - **BẮT BUỘC:** Viết script poller O(1) và khởi động ngay tiến trình nền (`terminal(background=True)` hoặc `run_watchdog_rerun_daemon.py`).
  - Poller kiểm tra `reap-dead-owner-locks.py` định kỳ (mỗi 1-2 phút). Ngay giây phút thiết bị nhả lock về Home/Launcher, poller tự động kéo riêng đúng máy lỗi ra thực thi `canary_runner.py` để lấy bằng chứng thực tế (Ảnh + WinRT OCR).

---

## 3. Kiến Trúc Cơ Giới Hóa Đã Triển Khai
1. **`D:/Taadaa/tools/unified_patch_pipeline.py`:**
   - Tại `S4: CANARY`, nếu phát hiện repo thuộc Farm/Device thì cờ `--no-canary` của Agent tự động bị vô hiệu hóa, bắt buộc phải chạy qua máy thật.
2. **`D:/Taadaa/tools/watchdog_claim_verifier.py`:**
   - Kiểm tra kép O(1): `heartbeat age <= 180s` + `psutil.Process(pid)` xác thực danh tính tiến trình watchdog thật.
3. **`D:/Taadaa/tools/guard_media_vision_gate.py` & `done_gate.py`:**
   - Chặn cửa xuất tin nhắn và chặn lệnh `DONE` nếu phát hiện phát ngôn nhận vơ quy trình hoặc hoãn canary mà không có watchdog poller đang chạy.
