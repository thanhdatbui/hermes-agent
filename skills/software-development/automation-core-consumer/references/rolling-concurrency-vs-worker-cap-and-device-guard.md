# Rolling Concurrency vs Worker Cap and Device Lock Gate Guard

## 1. Sai Lầm Cốt Lõi: Nhầm Lẫn "Cuốn Chiếu" Với "Bóp Nghẹt Worker"

### Sự cố thực tế & Bài học phản hồi từ User
- **Ngữ cảnh:** Khi User yêu cầu: *"Và ưu tiên cho cron chạy dạng cuốn chiếu"*, AI Coordinator và Claude Planner đã suy diễn máy móc rằng "cuốn chiếu" đồng nghĩa với việc hạ trần `MAX_WORKERS` từ 25 xuống 3 và đặt chặn cứng `max_workers <= 5` trong Gate Guard.
- **Phản hồi của User:** *"Tao đéo hề yêu cầu hạ wofker 25 xuống 3?"* — Làm bóp nghẹt 88% thông lượng xử lý của dàn farm 80–280 thiết bị.

### Định nghĩa chuẩn xác về "Chạy Cuốn Chiếu" (Rolling Execution) trên Farm
- **Thông lượng song song (Concurrency):** Duy trì số lượng worker lớn phù hợp quy mô farm (15–25–40 workers song song tùy tác vụ rename, dọn cache, bật 2FA).
- **Khóa & Nhả theo từng thiết bị (`release: per_device`):**
  - Mỗi worker khi bốc 1 máy sẽ gọi `acquire_device_lock` riêng cho máy đó.
  - **Không bao giờ khóa đồng loạt cả cụm:** Máy nào xong thì nhả lock ngay lập tức trong context manager/finally để máy đó rảnh tay nhận việc khác, worker bốc tiếp máy kế tiếp trong hàng đợi (Sliding Window / Queue).
  - Không chờ cả cụm 15–25 máy cùng hoàn tất mới nhả lock.
- **Bỏ qua an toàn khi có tranh chấp (`SAFE_SKIP`):**
  - Nếu máy đang bận ca nuôi hoặc có tiến trình khác giữ lock, worker bắt bộ 3 ngoại lệ: `(DeviceLockUnavailable, DeviceLockNeedsUserDecision, DeviceLockReadinessError)`.
  - Ghi log `SAFE_SKIP` và thoát sạch sẽ với exit code 0, không throw traceback, không force-stop app và không đá nick của tiến trình đang chạy.

---

## 2. Chuẩn Triển Khai Runner Cuốn Chiếu An Toàn

```python
from automation_core.device_lock import (
    acquire_device_lock,
    DeviceLockUnavailable,
    DeviceLockNeedsUserDecision,
    DeviceLockReadinessError
)

def run_single_device(machine_id, serial, ...):
    try:
        with acquire_device_lock(
            machine=machine_id,
            serial=serial,
            project="farm-batch-task",
            command=sys.argv,
            release_on_terminal=True
        ):
            return _execute_device_actions()
    except (DeviceLockUnavailable, DeviceLockNeedsUserDecision, DeviceLockReadinessError) as e:
        print(f"SAFE_SKIP: May {machine_id} ({serial}) dang ban hoac co lock: {e}")
        return 0
```

---

## 3. Quy Chuẩn Gate Guard Kiểm Soát Cron Thiết Bị (`guard_cronjob_safety.py`)

Khi kiểm tra tĩnh (AST Analysis) các cronjob mới can thiệp vào thiết bị Android (`monkey`, `am force-stop`, `input tap`, `com.ss.android.ugc.trill`):

1. **Bắt buộc AST Lock:**
   - Import phải trỏ chính xác vào `automation_core.device_lock` (chặn định nghĩa hàm giả mạo local hoặc import module không được kiểm chứng).
   - Khối `with acquire_device_lock(...)` bắt buộc phải có thân lệnh thực thi thiết bị thực chất (chặn `with lock: pass` hoặc thân rỗng).
2. **Hợp đồng `farm_contract`:**
   - Bắt buộc khai báo `touches_device: true`, `device_lock: required`, `mode: rolling`, `release: per_device`.
   - Chống lách luật (Anti-bypass): Dù khai báo `touches_device: false`, guard vẫn quét chéo mã nguồn script; nếu phát hiện lệnh thiết bị ➔ Chặn lập tức (`FARM_CONTRACT_MISMATCH`).
3. **Ngưỡng Worker Cap cho Farm:**
   - Ngưỡng giới hạn worker của guard phải được cấu hình rộng cho quy mô phone farm (cho phép đến **50 workers**), tuyệt đối không áp đặt các trần nhỏ hẹp (như 3–5) làm tê liệt năng lực xử lý hàng loạt.
