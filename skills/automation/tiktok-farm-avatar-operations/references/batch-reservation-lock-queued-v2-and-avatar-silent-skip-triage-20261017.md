# Bẫy Khóa Đặt Chỗ Hàng Loạt (Batch Reservation Lock `queued_v2`) & Ngộ Nhận Exit Code 0 Khi Nạp Avatar (17/10/2026)

## 1. Bối Cảnh Thực Tế & Hiện Trường Sự Cố
- **Tình huống**: Operator gửi ảnh Profile TikTok nick `@yobi1965` trên Máy 34 (Tik 6, F_src=434, F_out=270, Niche Yoga) yêu cầu chuẩn hoá và *"Đổi ava"*.
- **Chuẩn bị hoàn tất**: Coordinator đã trích xuất frame huấn luyện viên Yoga nữ từ `F_src=434`, crop chuẩn vuông $512 \times 512$, headroom cân đối, soi mắt qua `browser_vision`, đồng bộ file vào cả 2 đầu thư mục kèm marker `.manual_avatar_locked`, cập nhật Excel `Tik6.xlsx` sang `PENDING` và SQLite `avatar_replace_queue`.
- **Sự cố 1 - Bẫy Exit Code 0 nhưng không nạp được (False-Success Trap)**:
  - Khi gọi launcher:
    ```bash
    python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik 6 --machine 34
    ```
  - PowerShell kết thúc trả về `ExitCode: 0`.
  - Nếu Coordinator chỉ căn cứ vào `ExitCode: 0` mà báo "Đã đổi avatar thành công" thì sẽ là **VI PHẠM BÁO ẢO NGHIÊM TRỌNG**.
  - Kiểm tra kỹ `summary.csv` và stdout thực tế:
    ```text
    Hoàn tất batch: 0/40 target verified-success
    Target bị bỏ qua trước/đầu launch: 40
    Máy 34: SKIPPED_LOCKED (reason: device lock active)
    ```
  - Thực tế không có bất kỳ worker nào được kích hoạt để đổi avatar.

---

## 2. Bản Chất Cơ Chế Khóa Đặt Chỗ Hàng Loạt (`queued_v2`)
- **Nguyên nhân gốc rễ**:
  - Tiến trình batch lớn ban đêm (ví dụ: `run_batch_live_2fa.py`, PID 6332) điều phối 15 worker xử lý 2FA cho toàn farm.
  - Để đảm bảo không bị xung đột máy giữa chừng, tiến trình này tạo file lock tại `~/.codex/device-locks/machine_<M>.lock.json` cho TẤT CẢ các máy trong danh sách chờ với trạng thái:
    ```json
    {
      "status": "queued_v2",
      "pinned": true,
      "user_authorized": true,
      "command": "batch-live-2fa-reservation"
    }
    ```
  - Trong module `automation_core.device_lock` và `machine_inventory._filter_locks`, trạng thái `queued_v2` nằm trong `_WIRE_ACTIVE_DEVICE_LOCK_STATUSES` $\to$ Hệ thống coi đây là active lock và lập tức skip máy mục tiêu (`SKIPPED_LOCKED`).
  - Dù tại thời điểm đó Máy 34 đang rảnh rỗi (màn hình tắt, chưa có worker con nào kết nối ADB), launcher avatar vẫn từ chối can thiệp để bảo vệ toàn vẹn cho batch 2FA.

---

## 3. Quy Trình Điều Tra O(1) & Vận Hành Khắc Phục Chuẩn Xác
1. **Kiểm tra liveness của Process cha sở hữu Lock**:
   ```python
   import json, psutil
   lock = json.load(open(r"C:\Users\Kibe\.codex\device-locks\machine_34.lock.json"))
   pid = lock.get("pid")
   is_alive = psutil.pid_exists(pid)
   ```
2. **Kiểm tra Worker con có đang chiếm thiết bị thực tế hay không**:
   ```python
   p = psutil.Process(pid)
   active_children = [c for c in p.children(recursive=True) if "<serial>" in " ".join(c.cmdline())]
   ```
3. **Kỷ luật Coexistence (Không cướp lock - Không phá vỡ hàng đợi)**:
   - TUYỆT ĐỐI CẤM tự ý xóa file `.lock.json` của tiến trình đang sống.
   - Báo cáo rõ ràng cho Operator: Dữ liệu avatar và hàng đợi đã sẵn sàng (`PENDING`), máy đang nằm trong hàng đợi đặt chỗ của batch bảo mật.
4. **Kích hoạt nạp ngay khi nhả lock**:
   - Khi master batch hoàn tất xử lý và giải phóng máy (`machine_<M>.lock.json` tự động bị xóa):
   - Chạy lại launcher đơn máy qua background terminal:
     ```bash
     python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik 6 --machine 34
     ```
   - Xác nhận kết quả thật từ stdout:
     ```text
     Máy 34: THÀNH CÔNG (exit=0, verified=True)
     Hoàn tất batch: 1/1 target verified-success
     ```
5. **Nghiệm thu thị giác Gate 6 bắt buộc**:
   - Chụp ảnh màn hình live của máy bằng ADB O(1).
   - Soi mắt qua `browser_vision` để đối soát khuôn mặt trên Profile đã thực sự cập nhật mới trước khi gửi `MEDIA:` cho Operator.
