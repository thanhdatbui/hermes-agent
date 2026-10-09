# Persistent Device Lock Keeper & Cron Preemption Guard

## 1. Anatomy Sự Cố: Write-and-Forget Lock & Cron Preemption (2026-10-06)
Khi Coordinator hoặc Operator can thiệp thiết bị thủ công (Ad-hoc Inspection, Test APK, Canary, Debug UI):
- **Cạm bẫy chết người:** Dùng lệnh one-shot kiểu `python -c "import json, os; ... os.getpid() ..."` để ghi đè file lock `machine_<M>.lock.json`.
- **Hậu quả:** Lệnh `python -c` là một subprocess ngắn hạn — chạy 0.1s ghi file xong là PID chết ngay lập tức. Lock file lúc đó chứa PID của một tiến trình đã không còn tồn tại từ giây thứ 0.
- **Cơ chế Stale-Lock Reclaim của Cron:** Khi Cronjob định kỳ (ví dụ `run_tiktok.py --mode multi-machine-feed-session`) thức dậy quét farm, nó kiểm tra `psutil.pid_exists(pid)`. Thấy PID đã chết (`pid_exists == False`), nó xác định đây là "stale lock" sót lại từ runner bị crash và tự động chiếm máy, bật app nuôi acc đè lên màn hình thử nghiệm của Coordinator.
- **Bài học cốt lõi:** Lock thiết bị KHÔNG PHẢI là một hành động ghi file tĩnh (write-and-forget), mà là một **Reservation có vòng đời gắn chặt với một tiến trình nền CÒN SỐNG THỰC SỰ** nuôi nhịp tim (heartbeat) liên tục.

## 2. Giải Pháp Kỹ Thuật Chuẩn: `device_lock_keeper.py`
Để ngăn chặn hoàn toàn việc Cron cướp máy giữa chừng, toàn bộ các thao tác can thiệp thủ công / canary BẮT BUỘC sử dụng công cụ chuẩn:
`D:/Taadaa/tools/device_lock_keeper.py`

### Các tính năng an toàn cốt lõi:
1. **Living Daemon PID:** Lệnh `start` spawn tiến trình nền detached (`_worker`) sống xuyên suốt toàn bộ thời gian thao tác (`psutil.pid_exists(pid) == True`), Cron tuyệt đối không thể coi là stale lock.
2. **Heartbeat & TTL Dynamic (`expires_at`):** Cứ mỗi 10 giây, daemon tự động gọi `lease.heartbeat()` gia hạn `last_heartbeat` và cập nhật `expires_at = now + ttl`.
3. **Hard Max-Duration (Fail-Safe chống treo vĩnh viễn):** Cờ `--max-duration` (mặc định 1800s = 30 phút). Nếu Coordinator quên stop hoặc phiên làm việc bị ngắt đột ngột, daemon tự động nhả máy sau max-duration.
4. **Sentinel Graceful Release trên Windows:** Khi gọi `stop`, script gửi tín hiệu qua sentinel file `machine_<M>.stop`. Daemon con bắt tín hiệu và thực thi khối `finally: lease.release()` của `automation_core` trước khi kết thúc.
5. **Ownership Guard Fail-Closed 100%:** Lệnh `stop` bắt buộc đối soát `owner["lock_id"] == keeper_data["lock_id"]`. Nếu file lock trên đĩa thuộc sở hữu của người khác (ví dụ cron đang chạy) hoặc thiếu keeper file: **TỪ CHỐI XÓA, in cảnh báo, fail-closed**.
6. **Anti-Prefix Collision:** Nhận diện daemon process bằng token exact match `--machine <N>` trong danh sách argv, tránh lỗi substring match (`--machine 4` trùng `--machine 42`).
7. **Tri-State Status (AccessDenied handling):** Phân biệt `True` (sống), `False` (chết), `None` (AccessDenied). Nếu `None` $\to$ fail-closed, cấm xóa file lock.

## 3. Workflow Vận Hành Chuẩn Trước Khi Chạm Vào Thiết Bị
Trước khi gửi bất kỳ lệnh ADB hoặc thao tác UI nào vào máy <N>:

```bash
# Bước 1: Khởi động keeper nền giữ máy (chống mọi cron cướp máy)
python D:/Taadaa/tools/device_lock_keeper.py start --machine <N> --project "<ten_task>" --ttl 120

# Bước 2: Kiểm tra trạng thái xác nhận keeper đã sống và giữ lock thành công
python D:/Taadaa/tools/device_lock_keeper.py status --machine <N>

# Bước 3: Thực hiện thao tác thử nghiệm (cài app, mở màn hình, test flow)
adb -s <serial> ...

# Bước 4: Sau khi hoàn tất và chụp ảnh nghiệm thu, giải phóng máy an toàn
python D:/Taadaa/tools/device_lock_keeper.py stop --machine <N>
```

Hoặc sử dụng wrapper tự động heartbeat trong 1 lệnh duy nhất:
```bash
python D:/Taadaa/tools/device_lock_keeper.py run --machine <N> --project "<ten_task>" -- <command...>
```
