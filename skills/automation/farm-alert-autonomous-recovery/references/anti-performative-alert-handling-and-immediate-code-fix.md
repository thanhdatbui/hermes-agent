# Anti-Performative Farm Alert Handling: Immediate Code-Fix Contract

> User steering invariant: "Mày phải thiết kế lại alert để t gửi là mày biết nhiệm vụ vào điều tra tìm cách fix, không phải ngồi làm đối phó".
> Detailed Case 82 Reference: `references/feed-watchdog-alert-threshold-and-keyguard-recovery.md`.

## 1. Bản chất sự cố "Token Compliance / Báo Cáo Đối Phó"
Khi User gửi một tin nhắn `🚨 [FARM ALERT]` hoặc `🚨 [BATCH ALERT]` vào chat:
- **Hành vi sai (Bị nghiêm cấm):** Chỉ chạy đúng lệnh `inspect_machine.py <N>`, thấy màn hình tắt hoặc Launcher là phán ngay: `"Canary chưa thành công, batch bị khóa, BLOCKED"` rồi ngồi im giải thích lý thuyết suông chờ User nhắc nhở.
- **Hành vi đúng (Bắt buộc):** Alert là một **Yêu cầu nhiệm vụ khẩn cấp (Direct Task Assignment)** giao quyền toàn diện cho Coordinator tự động điều tra, đọc log, tìm lỗi code, dispatch worker sửa và chạy canary nghiệm thu.

## 2. Quy Trình 4 Pha Thực Thi Bắt Buộc (End-to-End Pipeline)

Mỗi khi nhận Alert, Coordinator BẮT BUỘC thực thi liên tục 4 pha không gián đoạn:

### Pha 1: Hiện trường O(1)
- Lấy thông tin serial, pin, và trạng thái màn hình:
  ```bash
  python D:/Taadaa/tools/inspect_machine.py <N>
  ```
- Nếu màn hình sleep hoặc ở Launcher, đây là trạng thái sau khi script crash/văng, **tuyệt đối KHÔNG được coi là lý do để báo BLOCKED**. Lập tức chuyển sang Pha 2.

### Pha 2: Đọc Log & Trích Xuất Traceback
- Đọc file log phiên chạy được chỉ định trong alert hoặc theo artifact ca gần nhất:
  - Tra cứu log tại: `D:/Taadaa/runtime/<cluster>/live/<date>/row-<N>/log.jsonl`
  - Đọc `run_manifest.json` và `summary.txt`.
- Tìm chính xác: Tên hàm, dòng code, và ngoại lệ (Exception / Error Signature).

### Pha 3: Dispatch Worker Vá Lỗi (Cơ Học O(1))
- Không tự sửa lan man, sử dụng Single Dispatch Gateway cơ học:
  ```bash
  python D:/Taadaa/tools/dispatch_worker.py --workdir "<repo_path>" --file "<target_file>" "In <target_file>: <exact error fix description>"
  ```
- Cổng điều phối tự động fallback: `Sol Worker (:20129) -> Agy CLI (29 Pro) -> Haiku CLI -> Coordinator L2`.
- Timeout mặc định >= 180s, cấm đặt timeout ngắn.

### Pha 4: Chạy Lệnh Canary Nghiệm Thu Trên Máy Thật & Qua Protection Regression Gate
- Chạy toàn diện bộ Protection Regression Gate trước khi nghiệm thu:
  1. `pytest D:/Taadaa/tools/guardgate` (đảm bảo 100% mechanical rules & regression vectors pass).
  2. Focused unit test của module đã vá (`pytest <repo>/tests/test_<module>.py`).
- Chạy lệnh Canary chính thức qua `canary_runner.py`:
  ```bash
  python D:/Taadaa/tools/canary_runner.py --repo <repo_name> --machine <id>
  ```
- Kiểm tra Gate chốt chặn `done_gate.py`:
  ```bash
  python D:/Taadaa/tools/done_gate.py --task-type automation --repo "<repo_path>"
  ```
- Nghiệm thu Gate 6 (Soi mắt đọc ảnh): Dùng `browser_vision` hoặc WinRT OCR mở ảnh screencap xác nhận đúng màn hình đích thật, không lỗi/đen/popup trước khi gửi `MEDIA:<path>`.

### Pha 5: Báo Cáo Có Bằng Chứng Thực Tế
Báo cáo cho User gồm đủ 4 phần:
1. **Root cause:** Hàm / module cụ thể gây ra crash trong log (ví dụ bẫy Keyguard SystemUI hay auto-healing timeout).
2. **Code diff:** Chi tiết đoạn code đã vá và giải pháp chuẩn hóa vào `farm-automation-cases.md`.
3. **Regression & Alert fix evidence:** Kết quả pass của GuardGate / Unit tests và bằng chứng đã cập nhật cơ chế bắn Farm Alert đúng ngưỡng.
4. **Canary evidence:** Kết quả lệnh test máy thật pass và xác nhận nội dung soi mắt qua Vision.
