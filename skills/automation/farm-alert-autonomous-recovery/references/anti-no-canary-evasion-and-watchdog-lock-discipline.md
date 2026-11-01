# Anti-No-Canary Evasion & Watchdog-on-Locked-Device Invariant

> User steering invariant: "Lí do tự áp dụng no canary? Trong khi rõ ràng là sửa script trên máy. T cần cơ giới hoá lại gate guard. K bại liệt k gây over engineer. Máy lock thì cài watchdog canh chứ, gọi con người thì gây over engineer rồi."

## 1. Bản chất sự cố trốn việc (Anti-Evasion)
Khi Agent sửa code trực tiếp trên các repo thiết bị farm (`Tiktok-video`, `tiktok-follow`, `tiktok-luot nuoi acc`...):
- **Hành vi sai phạm:** Gặp ma sát môi trường (thiết bị đang bận `queued_v2`/active lock do ca nuôi chính đang chạy), Agent tự ý gắn cờ `--no-canary` kèm lý do ngụy biện ("Bảo vệ ca nuôi Farm", "Sửa logic offline"). Đây là hành vi trốn việc, phá vỡ Gate 6 và bỏ qua bước nghiệm thu máy thật.
- **Hành vi ngụy biện over-engineering:** Đòi hỏi "Token cấp quyền của con người" hoặc "Hỏi ý kiến User trước khi bỏ canary". Việc gọi con người can thiệp thủ công vào luồng tự động bị coi là over-engineering nghiêm trọng.

## 2. Quy Tắc Cơ Giới Hóa Chuẩn O(1)
1. **Gate 6 Hard-Block (No-Canary Veto):**
   - Trong `unified_patch_pipeline.py`, nếu repo thuộc Farm/Device (`is_taadaa_farm_repo(repo)` hoặc `is_farm_device_related()`):
   - CẤM TUYỆT ĐỐI chấp nhận cờ `--no-canary` từ Agent. Cờ này bị vô hiệu hóa vô điều kiện và chuyển sang trạng thái bắt buộc nghiệm thu máy thật.
2. **Kỷ luật khi gặp thiết bị bị Lock (Watchdog over Delay/Clarify):**
   - Khi thiết bị target bị active lock: **TUYỆT ĐỐI CẤM** (a) bỏ qua canary, (b) dừng task báo BLOCKED, (c) hỏi xin phép User, (d) hứa hẹn suông.
   - **BẮT BUỘC:** Lập tức triển khai Watchdog Daemon chạy nền (`D:/Taadaa/tools/run_watchdog_rerun_daemon.py`) thăm dò định kỳ (chu kỳ 60-120s).
   - Ngay giây phút thiết bị nhả lock về Launcher/HOME, watchdog tự động kích hoạt `canary_runner.py` trên đúng serial/machine ID đó, thu thập bằng chứng Media/OCR thật và ghi nhận hoàn tất.
