# Quy Tắc Chuỗi Đêm 3 Phase & Re-run Farm (Cập nhật 2026-09-07)

## 1. Chuỗi Đêm 3 Phase (01:00 - 02:00 Sáng)
- **Phase 1 (Reg Gmail):** Tạo Gmail mới, tự động mã hóa dấu cách `%s` cho tên nhiều từ, tự động đổi username ngẫu nhiên leo thang (3-4 số, salt) và retry tối đa 5 lần khi trùng.
- **Phase 2 (Reg TikTok):** Đăng ký TikTok bằng Gmail/Hotmail, tự động merge kết quả vào `taikhoan_dat_v2_updated .xlsx` và sync sang `taikhoan_run_safe.xlsx` (chuẩn 480 slot).
- **Phase 3 (Add 2FA TikTok):**
  - **Lọc đối tượng:** CHỈ chọn các nick **đã có ID TikTok** (cột C) nhưng **CHƯA CÓ 2FA** (cột E đang trống). Bỏ qua 100% tài khoản đã có 2FA.
  - **Lọc theo Ca hôm trước:** Quét các nick thuộc ca vừa chạy của ngày hôm trước (ngày ca lẻ -> slot 1, 3, 5; ngày ca chẵn -> slot 2, 4, 6) vì các nick này đang active sẵn trên thiết bị.
  - **Thực thi:** Chạy tối đa 40 worker song song qua `python_runner/run_batch_live_2fa.py`.
  - **Khởi chạy canonical từ pipeline:**
    ```python
    cmd = [
        PYTHON_EXE, "-u", str(runner_script),
        "--workbook-path", r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx",
        "--workbook-sheet", "Tài Khoản",
        "--max-workers", "40",
        "--adb-path", adb_arg,
        "--live",
    ]
    ```

## 2. Quy Tắc Giả Lập / Dry-Run Kiểm Chứng An Toàn (Simulation vs Live Test)
- **Phân biệt Lệnh User "Giả lập là [giờ/lịch] rồi kích hoạt chạy" vs "Dry-run":**
  - Khi user yêu cầu *"Giả lập là giờ là 1h đêm rồi kích hoạt chạy"* hoặc *"Giả định tới giờ chạy... lock lại chạy"*, ý user là **KÍCH HOẠT CHẠY THẬT (LIVE RUN)** chạm thiết bị thật trên tập máy mẫu nhỏ (ví dụ 2 hoặc 5 máy: `--live --limit 2` hoặc `--live --limit 5`), mô phỏng đúng hành vi ca chạy đêm tự động để kiểm tra thiết bị và runner thật có hoạt động bình thường hay không.
  - **BẮT BUỘC KHÓA THIẾT BỊ:** Luôn đảm bảo `user_authorized=True` để tạo file device lock vật lý (`machine_<N>.lock.json`) trong `.codex/device-locks`, bảo vệ độc quyền máy chống cron nuôi acc hoặc các batch khác xen ngang.
  - **TUYỆT ĐỐI CẤM:** Chỉ chạy dry-run/preview không chạm thiết bị khi user ra lệnh kích hoạt kiểu này.
- **Chế độ Dry-run (Chỉ preview, không chạm thiết bị):**
  - **Chỉ áp dụng khi:** User nói rõ "dry-run", "chỉ preview", hoặc "không chạm thiết bị".
  - **Thực thi:** Dùng `--limit <N>` không có cờ `--live` trên `run_batch_live_2fa.py`.
    + Script sẽ đọc snapshot workbook, freeze target list, xác thực proxy mapping và kiểm tra ADB path mà không chiếm lock thiết bị hay can thiệp điện thoại sống.
    + Kết quả trả về bảng máy với `status="frozen"` và `reason="dry-run"`, exit code `0`.
  - **Launcher chuyển tiếp CLI args:** `night_chain_reg_pipeline_launcher.py` forward `sys.argv[1:]` vào subprocess để cho phép test giả lập nhanh qua dòng lệnh.

## 3. Bộ 8 Pitfall Chuỗi Đêm & Phase 3 Batch 2FA (Sự cố 07/09/2026)
1. **P1: Thiếu ADB Path & PATH Environment:**
   - Host farm (kibe) không có `adb` trong global system PATH (`which adb` exit 1).
   - Subprocess pipeline bắt buộc truyền tường minh `--adb-path "C:\Program Files (x86)\xiaowei\tools\adb.exe"` và inject thư mục Xiaowei tools vào đầu `env["PATH"]`.
   - Trong `run_batch_live_2fa.py`, hàm `parse_config()` phải tự động fallback sang đường dẫn Xiaowei ADB nếu `shutil.which("adb")` là None.
2. **P2: Bóc tách dòng ngoại lệ thực tế trong `parse_summary_line`:**
   - Khi script con crash, `parse_summary_line` nếu chỉ lấy dòng header `"Traceback (most recent call last):"` sẽ che giấu hoàn toàn tên ngoại lệ thật trên cảnh báo Telegram.
   - Phải duyệt `reversed(lines)` để trích xuất dòng ngoại lệ thực tế ở cuối Traceback (ví dụ `FileNotFoundError: ...`, `AttributeError: ...`).
3. **P3: AttributeError `target.account`:**
   - Dataclass `BatchTarget` chỉ có trường `username`, không có `account`. Khi gọi hàm alert (`send_farm_machine_alert`) phải dùng `target.username` hoặc `getattr(target, "account", getattr(target, "username", ""))`.
4. **P4: Đảo thứ tự mapping Reservation Lock khi shuffle targets:**
   - Khi dùng `launch_plan.order` để xếp lịch chạy so le, bắt buộc map `reservations_by_machine = {target.machine: reservation for target, reservation in zip(reserved_targets, reservations)}` TRƯỚC khi gán lại `reserved_targets`. Nếu gán lại trước, `zip()` sẽ ghép target mới với reservation cũ, làm giải phóng sai lock của máy khác.
5. **P5: Bọc lỗi ngoại lệ cho Preflight per-target:**
   - Vòng lặp preflight từng target trong `run_batch_live_2fa.py` bắt buộc bọc `except Exception as exc:` bên cạnh `ConsumerPreflightError` để `reservation.release()` và đánh dấu máy là `skipped`, bảo đảm lỗi ADB lẻ của 1 máy không làm văng exception phá vỡ toàn bộ batch.
6. **P6: Thư mục report farm:**
   - Tránh trỏ vào các thư mục ảo như `runtime/kibe/reports`. Luôn trỏ log/report fallback về thư mục chuẩn của farm: `D:/Taadaa/reports` hoặc `D:/Taadaa/runtime/kibe`.
7. **P7: Lỗi DeviceLockReleaseError khi giải phóng reservation lock:**
   - Khi worker con (`run_capture_phase_b.py`) chạy, nó tiếp quản device lock (`allow_takeover=True`, tạo `lock_id` mới) và hoàn tất với `lease.finish()`.
   - Lệnh `reservation.release()` trong runner cha gọi `_release_lease_paths(strict=True)` sẽ văng ngoại lệ `DeviceLockReleaseError: DEVICE_LOCK_RELEASE_OWNERSHIP_MISMATCH` hoặc `PATH_MISSING` tại khối `finally:` hoặc preflight error, làm crash toàn bộ batch runner sau khi worker con đã xong việc.
   - **Khắc phục chuẩn:** Thay thế toàn bộ bằng `reservation.release_with_audit(reason="...")` (`strict=False`), chỉ giải phóng các lock file còn thuộc về lease này mà không quăng lỗi khi lock đã bị worker tiếp quản hoặc xóa; bọc an toàn trong `try...except Exception: pass`.
8. **P8: Giám sát batch runner khi chạy nền (Stdout buffer & dot-dir .codex):**
   - Batch runner `run_batch_live_2fa.py` thu thập kết quả và chỉ in stdout ở cuối `main()` sau khi toàn bộ workers trong `ThreadPoolExecutor` kết thúc. Trong lúc chạy, tiến trình cha không in stdout liên tục (không được nhầm là treo).
   - Thư mục `.codex` là dot-directory (hidden directory) nên `search_files` / ripgrep mặc định bỏ qua. Bắt buộc kiểm tra lock trực tiếp qua `read_file` đường dẫn tuyệt đối hoặc lệnh shell `ls -la ~/.codex/device-locks/`.

## 4. Quy Tắc Re-run Sau Lỗi
- **Chỉ chạy lại:** Các máy bị lỗi Script / Code logic (ví dụ lỗi ADB typing, lỗi syntax, lỗi selector, timeout cục bộ).
- **CẤM TUYỆT ĐỐI chạy lại:** Các máy bị Google chặn chủ động (bắt xác minh số điện thoại `PHONE_VERIFY`, chặn IP hoặc rate limit) để tránh nát thiết bị.

## 5. Quy Tắc Bắt Buộc Cho Coordinator
- Coordinator CẤM tự chạy terminal debug sâu, probe test, hay sửa code trực tiếp trong session chính.
- BẮT BUỘC dispatch `delegate_task(role=leaf)` cho worker subagent xử lý trọn gói trong context riêng.
