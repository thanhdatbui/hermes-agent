# Watchdog Batch State Persistence & Anti-False-Completion Pitfalls (2026-09-11)

## 1. Bản chất sự cố "Chưa up sao dám báo ALL DONE"
- **Hiện tượng**: Agent thiết lập script watchdog tự động (chạy qua cron hoặc loop) để tải avatar/đăng video theo hàng đợi các Row: `[5, 6, 3, 4]`. Sau 1 vài tick, cronjob bắn thông báo về Telegram: `[ALL_DONE] Đã hoàn thành toàn bộ avatar cho các Row: [5, 6, 3, 4]`, trong khi thực tế trên đĩa và điện thoại chưa hề có máy nào được up avatar.
- **Root cause cấu trúc**:
  1. **Tăng state index vô điều kiện (Unchecked State Advance)**:
     ```python
     # CODE LỖI NGUY HIỂM:
     res = subprocess.run(cmd, ...)
     state["completed_tiks"].append(tik)
     state["current_index"] = idx + 1
     save_state(state)
     ```
     Khi `subprocess.run()` bị lỗi timeout, fail ADB, crash PowerShell, hoặc người dùng can thiệp ngắt giữa chừng (`exit code != 0`), watchdog không hề kiểm tra kết quả thực thi mà vẫn tăng `current_index`. Sau 4 lần timeout/fail, index chạm trần độ dài danh sách (`idx >= len(TARGETS)`).
  2. **Báo cáo "ALL_DONE" dựa trên biến đếm ảo thay vì Ground Truth**:
     Watchdog coi việc `idx >= len(TARGETS)` là đã hoàn thành tất cả và in ra `[ALL_DONE]`. Cron output bắt dòng này đẩy về Telegram khiến người dùng nhận thông báo hoàn thành giả mạo.

---

## 2. Các nguyên tắc bắt buộc khi viết Script Watchdog Batch

### Nguyên tắc 1: Kiểm tra Returncode và Ground Truth trước khi chuyển State
- Chỉ được chuyển sang task/row kế tiếp khi và chỉ khi:
  1. `res.returncode == 0`
  2. HOẶC đối soát trực tiếp ground truth (ví dụ kiểm tra số lượng máy còn thiếu trong workbook / summary batch run).
- Nếu lệnh chạy thất bại (`res.returncode != 0`), BẮT BUỘC giữ nguyên index, ghi nhận số lần retry thất bại (`failure_count += 1`), và ngắt chu kỳ để lần tick sau thử lại hoặc dừng hẳn nếu vượt ngưỡng retry (Circuit Breaker: max 3 lần fail liên tiếp thì dừng và báo lỗi thực tế).

### Nguyên tắc 2: Tách biệt Launch Subprocess vs Background Cronjob
- Các lệnh batch lớn (như `run_tiktok_upload_avatar.ps1` hoặc `run_tiktok_upload_batch.ps1`) chạy qua nhiều máy và có thể kéo dài 10–30 phút.
- **CẤM** gọi `subprocess.run()` đồng bộ chặn dòng (blocking) bên trong một cronjob tick ngắn (ví dụ mỗi 5p hoặc 10p), vì:
  - Cronjob sẽ bị timeout hoặc bị kill bởi watchdog hệ thống.
  - Tick tiếp theo có thể chồng lấn nếu không có file lock bảo vệ.
- Thay vào đó, watchdog chỉ làm nhiệm vụ:
  1. Kiểm tra điều kiện rảnh (`is_idle()`).
  2. Nếu rảnh: spawn tiến trình nền (`subprocess.Popen`) với file lock hoặc file PID ghi nhận `in_progress = True`.
  3. Các tick sau: chỉ monitor tiến trình đang chạy (`proc.poll()`). Khi tiến trình kết thúc sạch sẽ mới kiểm tra ground truth và cập nhật state.

### Nguyên tắc 3: Xác minh Ground Truth trước khi tuyên bố ALL DONE
- Tuyệt đối KHÔNG bao giờ in `[ALL_DONE]` hoặc báo user đã hoàn thành nếu chỉ dựa vào `idx >= len(...)`.
- Bắt buộc phải có hàm verify cuối cùng:
  ```python
  def verify_all_completed() -> bool:
      for tik in TARGET_TIKS:
          # Kiểm tra trực tiếp workbook TikN.xlsx hoặc cơ sở dữ liệu
          pending = get_pending_machines(tik)
          if len(pending) > 0:
              return False
      return True
  ```
  Nếu `verify_all_completed()` trả về `False`: Watchdog phải báo rõ: `"Đã duyệt hết hàng đợi nhưng vẫn còn X máy chưa đạt, dừng để kiểm tra"` thay vì báo càn `"ALL DONE"`.
