# Just-In-Time (JIT) Lock vs Bulk Pre-Reservation & An Toàn Khung Giờ Reboot (2026-10-25)

## 1. Bản chất sự cố xung đột Farm Alert (25/10/2026)
- **Hiện trường:** Batch Upload Video Ca 1 phát cảnh báo 44 máy cụm Admin dính lỗi script `[NEEDS_USER_DECISION] ACQUIRE_LOCKS`.
- **Nguyên nhân:**
  1. Cron phụ `night-tiktok-2fa-watchdog` có lịch chạy cả ngày `*/15 * * * *`.
  2. Khi quét trúng 44 máy cần bật 2FA, tiến trình cha `run_batch_live_2fa.py` gọi `acquire_device_lock(status="queued")` đồng loạt cho toàn bộ 44 máy và ghi 44 file `.lock.json` vào `C:\Users\Admin\.codex\device-locks\`.
  3. Dù chỉ có vài worker chạy song song theo `max_workers`, 40+ máy còn lại vẫn bị ghim lock ở trạng thái xếp hàng.
  4. Batch Upload Video khởi chạy song song thấy máy bị khóa bởi `tiktok-add-bao-mat-f2a`, tuân thủ fail-closed an toàn và dừng lại.

## 2. Kiến trúc giải pháp Just-In-Time (JIT) Lock
- **Quy tắc vàng:** Không lock máy khi còn đang chờ trong hàng đợi. Chỉ lock khi worker bắt đầu chạm vào thiết bị, và release ngay khi worker thoát.
- **Triển khai tại tiến trình cha:**
  ```python
  # 1. Bỏ toàn bộ vòng lặp acquire_device_lock(status="queued") ở main()
  # 2. Khử trùng lặp machine cho launch_plan (build_machine_launch_plan cấm duplicate)
  unique_machines = list(dict.fromkeys(target.machine for target in reserved_targets))
  launch_plan = build_machine_launch_plan(
      unique_machines,
      min_stagger_ms=2000,
      max_stagger_ms=8000,
      max_workers=cfg.max_workers,
  )

  # 3. Gom target theo machine bằng list để tránh ghi đè nếu một máy có nhiều account
  targets_by_machine: dict[str, list[BatchTarget]] = {}
  for target in reserved_targets:
      targets_by_machine.setdefault(target.machine, []).append(target)
  
  ordered_targets = []
  for machine in launch_plan.order:
      ordered_targets.extend(targets_by_machine.get(machine, []))

  # 4. Dispatch an toàn với launch_plan.delays_ms
  with ThreadPoolExecutor(max_workers=min(cfg.max_workers, len(ordered_targets))) as executor:
      futures = {}
      for i, target in enumerate(ordered_targets):
          delay_ms = launch_plan.delays_ms[i] if i < len(launch_plan.delays_ms) else 0
          if delay_ms:
              time.sleep(delay_ms / 1000.0)
          futures[executor.submit(run_target, target, cfg)] = target
  ```
- **Triển khai tại Worker con:**
  - Từng worker subprocess (`run_capture_phase_b.py`) tự gọi `acquire_device_lock(command="phase-b-live")`.
  - Khi worker xong hoặc gặp exception, lock được giải phóng ngay lập tức.

## 3. Quy chuẩn né khung giờ reboot & chuẩn bị ca cron
- Giữ lịch cron chạy cả ngày theo yêu cầu người dùng (`*/15 * * * *`), nhưng bọc bằng predicate `is_safe_rolling_window()`:
  - Khung dọn cache: `04:00 – 04:30`.
  - Khung đệm chuẩn bị ca trưa (sau giờ reboot 11:20): `11:05 – 11:35`.
  - Khung đệm chuẩn bị ca chiều (sau giờ reboot 17:20): `17:05 – 17:35`.
  - Khung hoạt động nuôi acc chính: `05:05–09:30`, `11:45–15:30`, `17:45–21:30`.
- Khi rơi vào các khung đệm này, watchdog lập tức skip để nhường thiết bị cho việc chuẩn bị ca cron mới và chu kỳ reboot máy.
