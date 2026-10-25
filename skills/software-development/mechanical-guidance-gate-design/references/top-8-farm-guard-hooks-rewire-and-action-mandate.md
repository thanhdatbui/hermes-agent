# Top 8 Farm Guard Hooks Rewire & Action Mandate

## Bối Cảnh
Báo cáo đối soát 6h từ watchdog tuân thủ gate ghi nhận 1.750 dòng log với 8 quy tắc bị Guard chặn nhiều nhất. Các vi phạm xảy ra do Agent/Subagent thiếu Action Mandate cụ thể, dẫn đến lặp lại các hành vi bị cấm thay vì đi theo lộ trình hợp lệ.

## Chi Tiết 8 Hook & Cơ Chế Auto-Rewire / Guidance

### 1. Worker Dispatch: Chặn sửa file hệ thống
- **Hiện tượng:** Worker subagent cố sửa các file hệ thống được bảo vệ hoặc sửa các file ngoài hợp đồng được giao.
- **Root Cause:** Prompt dispatch Worker để scope mở hoặc không chỉ định chặt danh sách file được phép chỉnh sửa.
- **Action Mandate / Rewire:**
  - Coordinator BẮT BUỘC khai báo rõ ràng mảng target_files O(1) trong prompt dispatch.
  - Inject quy tắc cứng vào Worker: Cấm sửa bất kỳ file nào ngoài target_files. Nếu phát hiện cần sửa thêm file khác -> BẮT BUỘC ABORT ngay trong <= 3 turns đầu để Coordinator cấp hợp đồng mới.

### 2. Worker Dispatch: Chặn dispatch mở (investigate)
- **Hiện tượng:** Dispatch Worker với mục tiêu mở (tìm hiểu/điều tra lỗi) bị Gate 2 chặn thẳng thừng.
- **Root Cause:** Vi phạm Gate 2 (Patch Contract cho Monolith / Code lớn).
- **Action Mandate / Rewire:**
  - Coordinator KHÔNG ĐƯỢC PHÉP dispatch Worker khi chưa có anchor duy nhất (wc -l == 1).
  - Dispatch bắt buộc chứa Patch Contract O(1): old_string -> new_string kèm lệnh test focused < 30s.

### 3 & 4. Anti-Scan & Terminal: Chặn quét đĩa diện rộng
- **Hiện tượng:** Agent chạy script Python quét đĩa diện rộng để tìm file log/script.
- **Root Cause:** Thói quen dò dẫm đĩa thay vì dùng kiến trúc định danh canonical.
- **Action Mandate / Rewire:**
  - Tra cứu qua file chỉ mục có sẵn (skills_index.json, cron_registry.yaml, hoặc danh mục canonical tool).
  - Sử dụng đường dẫn tuyệt đối hoặc relative có anchor rõ ràng.

### 5. Anti-Scan & Terminal: Yêu cầu JIT Device Lock
- **Hiện tượng:** Chạy lệnh ADB hoặc script can thiệp điện thoại Farm mà không giữ lock thiết bị.
- **Root Cause:** Chạy trực tiếp script điều khiển device mà không qua bulkhead lock.
- **Action Mandate / Rewire:**
  - Luôn bọc qua công cụ khóa JIT: with_device_lock.py.
  - Nghiêm cấm bulk pre-reserve giữ lock hàng loạt trong hàng đợi.

### 6. Anti-Scan & Terminal: Chặn Timeout Foreground Quá 60s
- **Hiện tượng:** Lệnh shell terminal foreground chạy không khai báo tham số timeout hoặc timeout > 60s, kích hoạt Bulkhead Gate 5.
- **Root Cause:** Coordinator block luồng điều phối chính quá 60s chờ thiết bị thật hoặc tác vụ nặng.
- **Action Mandate / Rewire:**
  - Quick probe foreground: BẮT BUỘC đặt rõ timeout <= 60 (ví dụ: timeout=30).
  - Tác vụ dài/batch/canary thiết bị: BẮT BUỘC chuyển sang chạy nền (background=True, notify_on_complete=True).

### 7. Anti-Scan & Terminal: Kỷ Luật Closeout Gate
- **Hiện tượng:** Agent tự ý git commit, push hoặc báo DONE khi chưa có thẩm định từ reviewer độc lập.
- **Root Cause:** Vi phạm Hard Invariant Closeout Gate.
- **Action Mandate / Rewire:**
  - Khi user phát lệnh chốt/đóng phiên hoặc hoàn tất code: BẮT BUỘC chạy closeout_gate.py với cờ json-output.
  - Chỉ được phép push khi Verdict là APPROVED (Overall Score >= 85/100).

### 8. Cronjob Window: Khung Giờ Cấm / Reboot
- **Hiện tượng:** Kích hoạt script can thiệp vào khung giờ cấm / reboot window định kỳ của Farm.
- **Root Cause:** Thiếu predicate kiểm tra khung giờ an toàn.
- **Action Mandate / Rewire:**
  - Các cron/watchdog chạy định kỳ phải bọc predicate né khung giờ reboot/đệm trước ca cron.
