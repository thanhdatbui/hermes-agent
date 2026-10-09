# Midnight Rollover & Fast Fail-Closed with Lock Retention

## 1. Sự Cố Chốt Non Báo Cáo Khi Phiên Vắt Qua Nửa Đêm (Midnight Rollover Pitfall)

### Hiện Tượng
- Ca 3 - Phiên 3 (cuối ngày) thường khởi chạy lúc ~22:15 - 22:35 và kéo dài 45-55 phút do vừa lướt feed vừa chạy upload video cho 74 máy.
- Thời điểm kết thúc vắt qua nửa đêm (00:00:00 sang ngày hôm sau).
- Khi watchdog chạy ở tick 00:00:33, `today = "YYYY-MM-DD (mới)"` trong khi `target_date = "YYYY-MM-DD (cũ)"` $\rightarrow$ `is_today = False`.
- **Cạm bẫy:** Nếu watchdog chỉ có điều kiện:
  ```python
  if is_today:
      return (completed >= expected and not runner_busy) or (now >= window_end)
  return True  # ⛔ LỖI NGHIÊM TRỌNG: Khi qua ngày, return True vô điều kiện!
  ```
  Watchdog sẽ chốt báo cáo ngay lập tức tại 00:00:33 khi mới chỉ có 1-2 máy hoàn thành sớm, phát cảnh báo sai lệch ("Tổng máy xử lý: 2 máy") và khóa state không bao giờ báo cáo 72 máy còn lại.

### Khắc Phục Bắt Buộc
1. **Runner Active Gate:** Nếu `runner_busy == True`, **TUYỆT ĐỐI KHÔNG** cho phép báo cáo (`return False`) dù `is_today` là True hay False.
2. **Nhận diện đầy đủ Runner Processes:**
   - Lệnh spawn thực tế có thể dùng `--mode multi-machine-feed-session` (gạch nối), `run_tiktok.py`, `hermes_cron_runner.py`, `tiktok_runner.py`.
   - CẤM chỉ so khớp cứng chuỗi `multi_machine_feed_session` (gạch dưới).
   - Loại trừ PID của chính tiến trình watchdog (`p.pid == os.getpid()`).
3. **Grace Period cho Ngày Cũ:**
   - Với ngày hôm trước (`not is_today`): Chỉ cho phép report khi `not runner_busy` VÀ (`completed_expected >= expected` HOẶC `now >= 02:00`).

---

## 2. Fast Fail-Closed vs Giữ Lock Thiết Bị (Device Lock Retention)

### Yêu Cầu Sống Còn Của Operator
- User phản hồi: *"Nhưng như v thì k bị lock và t k detect lỗi đc"*.
- Nếu khi lỗi mà giải phóng lock ngay, màn hình điện thoại sẽ bị phiên sau đè hoặc mất dấu vết, operator không thể chạy `python D:/Taadaa/tools/inspect_machine.py <N>` để điều tra hiện trường.
- Do đó: **MỌI MÁY LỖI BẮT BUỘC PHẢI GIỮ LOCK `blocked` ĐỦ 1 GIỜ (TTL 3600s)**.

### Vấn Đề Ngâm Threadpool
- Nếu một máy gặp lỗi vật lý (rớt cáp USB, `device not found`, `router proxy unreachable`, `ping probe failed`), việc retry lặp lại hoặc chờ default timeout 35 phút (2100s) sẽ giam lỏng 1 worker slot trong `ThreadPoolExecutor(max_workers=40)`.
- 34 máy đợt 2 phải xếp hàng chờ, khiến toàn bộ phiên bị kéo dài từ 40 phút lên gần 2 tiếng.

### Giải Pháp Chuẩn: Fast Fail-Closed + Lock Retention
1. **Phát hiện sớm (Fast Fail):**
   - Khi gặp các lỗi fatal unrecoverable (USB disconnect, device offline, router proxy chết), ngắt ngay lập tức trong vòng <= 1 phút, không retry vô vọng.
2. **Khóa cứng hiện trường (Lock Retention):**
   - Lập tức chuyển lock sang `status: "blocked"` (`lease.set_status("blocked")`).
   - Ghi nhận `final_status: "blocked"` và mã blocker rõ ràng.
   - Bắn ngay Farm Alert Telegram kèm ảnh hiện trường.
3. **Giải phóng Thread Slot:**
   - Worker thread kết thúc ngay sau khi set `blocked`, nhả slot trong threadpool cho các máy khác tiếp tục thực thi.
   - Operator vừa nhận được alert sớm hơn 30 phút, vừa giữ trọn vẹn hiện trường `blocked` trên điện thoại đủ 1 tiếng để inspect.

---

## 3. Quy Chuẩn Triển Khai Kỹ Thuật (Claude CLI Review Hardening)

Khi triển khai Fast Fail-Closed trên các flow đa luồng thiết bị:
1. **Cô Lập Hook Phụ Thuộc ADB:**
   - Khi thiết bị dính lỗi fatal (`_is_fatal_device_error` = True) hoặc ADB validation fail, **BẮT BUỘC bỏ qua toàn bộ các hook phụ thuộc ADB** (follow hook, upload hook, clear cache hook) và `return child_result` ngay lập tức.
   - Tránh việc thiết bị đã tuột cáp/offline mà runner vẫn tiếp tục spawn subprocess upload/follow khiến thread bị ngâm thêm 15–20 phút.
2. **Không Gây Side-Effect Cho Upload Ledger:**
   - Việc bỏ qua upload hook khi thiết bị offline là an toàn 100% vì `_ShiftUploadLedger` chỉ ghi nhận upload khi process upload thật hoàn tất thành công (`post_verified = True`). Thiết bị offline không thể đăng bài, không bị tính là đã upload.
3. **Double-Wrap Bảo Vệ Lock Trong `finally:`:**
   - Lệnh `lease.set_status("blocked")` bên trong khối `finally:` phải được bọc trong `try...except Exception: pass` riêng biệt, độc lập với các bước ghi file evidence (`_write_recovery_handoff_evidence`). Tránh trường hợp lease throw exception làm đứt gãy luồng ghi log/evidence hiện trường.
4. **Tuple Nhận Diện Chống False Positive:**
   - CẤM so khớp chuỗi ngắn thô như `"offline"` vì dễ dính false positive từ log nội bộ app ("user went offline", "cache offline").
   - BẮT BUỘC dùng cụm từ định danh thiết bị chính xác (`"device offline"`, `"device is offline"`, `"adb/usb disconnected"`, `"not found in adb devices"`, `"required router proxy is unreachable"`, `"ping probe failed"`, `"adb transport lost"`) kết hợp `.lower()` và compound check `("device" in lower and "not found" in lower)`.
5. **Đồng Bộ Core Package Import Integrity:**
   - Khi `automation-core` khai báo các hàm ném ngoại lệ ADB (`raise ADBError(...)`), bắt buộc module đó phải `from .adb import AdbClient, ADBError`. Tránh lỗi runtime `NameError: name 'ADBError' is not defined` làm crash tiến trình và biến lỗi thiết bị thành lỗi code unhandled.

