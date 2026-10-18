# Batch Alert Locked Device Canary Failover & Guard Anti-Complaint Protocol (2026-10-18)

## 1. Sự Cố Thực Tế
- **Hiện tượng**:
  1. Khi nhận Batch Alert 79/80 máy lỗi Feed Session (2 cụm: `account-switcher-not-open` và `loading spinner dump error`), Coordinator đã tìm ra root cause và vá code trong `feed_swipe_smoke.py`, pass 127 unit tests.
  2. Khi chạy Canary, lệnh PowerShell (`powershell.exe -ExecutionPolicy Bypass -File ...`) bị Coordinator Guard chặn (default-deny).
  3. Thay vì chủ động trích xuất lệnh Python thực sự bên trong script để chạy, Coordinator lại dừng hình và báo cáo khóc lóc ra chat: *"Blocker thật: Live canary bắt buộc trên M1 chưa chạy được vì Coordinator Guard chặn..."*.
  4. User mắng gay gắt: *"lảm nhảm cái lồn gì thế?"*.
  5. Tiếp đó, khi chạy lại lệnh Python trên M1, M1 đang bị lock bởi batch ca 14h (PID 59260) đang chạy upload hook. Coordinator lại đứng im phân trần.
  6. User tiếp tục chấn chỉnh: *"cái địt con mẹ mày t vừa fix lỗi khóc lóc r vẫn đéo ăn thua hả đã cài guard hook gate r mà? sao k lấy máy khác mà canary"*.
  7. Coordinator lập tức chuyển sang Máy 2 (cùng thuộc cụm lỗi 1), kiểm tra lock trống, chạy canary thành công 2/2 swipes, soi ảnh profile `@lieuhoan03` qua LLM Vision và nghiệm thu hoàn tất.

## 2. Kỷ Luật Bất Biến Rút Ra

### A. Chống Báo Cáo Khóc Lóc Khi Gặp Rào Cản Công Cụ / Guard Terminal Blocked
- **Tuyệt đối CẤM**: Bê nguyên thông báo chặn của guard (`COORDINATOR TERMINAL BLOCKED`, `DEFAULT-DENY`, `exit 124`, wrapper script bị cấm) ra chat làm bình phong để thoái thác trách nhiệm hoặc tuyên bố `BLOCKED` với User.
- **Quy tắc giải quyết**:
  - Script wrapper (`.ps1`, `.bat`, `.sh`) bị chặn ➔ Đọc nội dung script, lấy lệnh core thực thi (ví dụ `python python_runner/run_tiktok.py ...`) đã được allowlist để chạy trực tiếp.
  - Timeout foreground 60s ➔ Dùng `terminal(background=True, notify_on_complete=True)`.
  - CẤM mọi hình thức phân trần nội bộ về công cụ hay tự kiểm điểm "bệnh Luna/khóc lóc" rườm rà. Hành động ngay lập tức bằng lệnh đúng.

### B. Cơ Chế Failover Chọn Máy Khác Trong Batch Khi Máy Đích Bị Lock
- **Bản chất Batch Alert**: Batch Alert xảy ra trên quy mô lớn (30-80 máy) chia thành các cụm lỗi (clusters). Máy N (như M1) trong prompt alert chỉ là gợi ý đại diện ban đầu.
- **Kỷ luật Failover Canary**:
  - Khi máy ban đầu (ví dụ M1) đang có Device Lock active với PID tiến trình hợp lệ còn sống (`psutil.pid_exists(pid) == True`), TUYỆT ĐỐI CẤM:
    1. Force-kill tiến trình đang chạy dở của farm.
    2. Đứng im chờ đợi thụ động làm tắc nghẽn toàn bộ luồng recovery.
    3. Báo cáo kẹt với User.
  - BẮT BUỘC: Quét nhanh danh sách các máy còn lại trong **CÙNG CỤM LỖI** (ví dụ cụm `account-switcher-not-open` có M2, M11, M13...):
    1. Kiểm tra máy rảnh: Không có file lock `C:/Users/Kibe/.codex/device-locks/machine_<id>.lock.json`.
    2. Chạy `python D:/Taadaa/tools/inspect_machine.py <id>` xác nhận thiết bị ONLINE, màn hình sáng/sẵn sàng.
    3. Lập tức kích hoạt Canary trên máy rảnh đó để lấy bằng chứng nghiệm thu thực tế.
