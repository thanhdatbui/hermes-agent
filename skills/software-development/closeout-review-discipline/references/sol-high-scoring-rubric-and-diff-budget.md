# Sol High Closeout Gate: Scoring Rubric Optimization & Diff Payload Guard

## 1. Cơ Chế Sol Payload Guard (Ngưỡng 21.299 Bytes Clean Diff)
- **Cơ chế:** Khi tổng `clean_diff` vượt quá ngân sách `diff_b` (~21.299 bytes trong `SOL_TARGET_BYTES = 32768`), `sol_payload_guard.py` tự động kích hoạt `level=L4` và cắt tỉa `(partial)` các file code thực thi (`omitted: ['.../script.py(partial)']`).
- **Bẫy đo kích thước clean_diff:** `clean_diff = normalize_diff(diff_text)` có thể dài hơn `diff_text` thô khoảng 50 - 100 bytes do chuẩn hóa header. Luôn kiểm tra trực tiếp qua `normalize_diff(diff_text) <= diff_b` trước khi chạy gate.
- **Tác động điểm số:** Khi có `(partial)` truncation, Sol Reviewer bị che khuất các nhánh xử lý lỗi và logic dọn dẹp cốt lõi, ngay lập tức trừ điểm nặng (điểm bị kẹt ở mức 76 - 79/100, không thể đạt threshold 85).
- **Chiến thuật tinh gọn diff để giữ L0 (0 truncation):**
  1. **Test Parametrization:** Thay thế các chuỗi decorator `@pytest.mark.parametrize` dài dòng bằng vòng lặp gọn nhẹ `for val, exp in [...]`, tiết kiệm 400 - 600 bytes.
  2. **Gộp Assertion:** Loại bỏ các lần `capsys.readouterr()` trung gian không cần thiết, gộp đếm sự kiện qua `count()`.
  3. **Tận dụng Fixture:** Dùng `@pytest.fixture(autouse=True)` để reset trạng thái dùng chung (cache, metrics), loại bỏ các dòng `reset()` lặp lại ở đầu mỗi test function.

## 2. Các Trụ Cột Đạt Điểm >= 85/100 từ Reviewer Sol High

### A. Logic Correctness (35 điểm)
- **Fail-Closed Semantics:** Khi kiểm tra trạng thái tiến trình gặp lỗi hoặc ngoại lệ, bắt buộc trả về `True` (coi như đang chạy) để tuyệt đối không kill nhầm tiến trình đang hoạt động.
- **Backoff trên Retry:** Khi retry `_query_*`, thêm backoff tối thiểu (`time.sleep(0.1)`) thay vì retry tức thì.
- **Tránh Subprocess Redundancy:** Lưu kết quả vào biến cục bộ (ví dụ: `is_running = is_xiaowei_running()`) thay vì gọi lại liên tiếp trong cùng một khối `if/else`.
- **DRY_RUN Guard Tại Từng Hàm Hành Động:** Đặt kiểm tra `if DRY_RUN_MODE: return ...` ngay đầu các hàm phá hủy (`close_*`, `cleanup_*`), không chỉ ở `main()`, tránh việc các hàm bị gọi trực tiếp ngoài entrypoint gây side-effect không mong muốn. Bắt buộc có test assertion trực tiếp: `assert close_func() is False and "DRY_RUN_SKIP" in capsys.readouterr().out`.
- **CIM Timeout Tuning:** Cấu hình mặc định cho các lệnh WMI/CIM trên máy farm nên là <= 10s (thay vì 15-30s) để tránh làm nghẽn chu kỳ cron watchdog khi WMI service phản hồi chậm.
- **Fresh Race-Check Bỏ Qua Cache:** Trong các hàm guard an toàn đa tầng (như `_xiaowei_started_before` kiểm tra trước mỗi bước kill destructive), BẮT BUỘC dùng `use_cache=False` (truy vấn fresh). Dùng cache TTL 2s ở các bước race-check tạo ra khoảng trống TOCTOU nguy hiểm cho farm.

### B. Code Architecture (10 điểm)
- **Giảm Cyclomatic Complexity:** Phân rã các hàm dài (>30 dòng) có nhiều tầng lồng `try/except` và fallback thành các hàm đơn nhiệm rõ ràng (ví dụ: `_try_kill_server()`, `_try_cim_terminate()`).
- **Lock Scope Tối Ưu (Chống Deadlock):** TUYỆT ĐỐI KHÔNG bọc `subprocess.run` hay `time.sleep` bên trong `with _CACHE_LOCK:` vì nguy cơ deadlock dưới tải cao. Chỉ giữ lock khi đọc cache (`if use_cache: with _CACHE_LOCK: return cache`) và khi cập nhật cache (`with _CACHE_LOCK: _CACHE = result; _CACHE_TS = time.time()`).
- **Configurable Cache TTL:** Không hardcode `CACHE_TTL_SECONDS = 2.0`. Bắt buộc đọc từ biến môi trường có fallback: `CACHE_TTL_SECONDS = float(os.environ.get("..._CACHE_TTL", "2.0"))`.
- **Cache Invalidation Tường Minh:** Tách helper `_invalidate_cache()` thread-safe; bắt buộc gọi invalidation ngay sau khi tiến trình được đóng thành công trước khi chuyển sang bước cleanup tiếp theo, triệt tiêu khoảng trống TOCTOU giữa `close` và `cleanup`.
- **Zombie Escalation Delay:** Khi phát hiện zombie (taskkill rc=0 nhưng tiến trình vẫn còn chạy), thêm khoảng chờ ngắn `time.sleep(0.5)` trước khi gọi CIM terminate để tránh race condition với tiến trình đang trong quá trình thoát dở dang.

### C. Test Evidence & Edge Cases (25 điểm)
- **Double-None Retry:** Bắt buộc có test mock `side_effect=[None, None]` để chứng minh nhánh fail-closed hoạt động đúng khi retry cả 2 lần đều lỗi.
- **Dynamic Env Parsing Clamp:** Test đầy đủ các ca biên khi đọc biến môi trường: giá trị âm ép về min, giá trị vượt ngưỡng ép về max, chuỗi chữ/rỗng fallback về mặc định.
- **Cache Expiry Test:** Bắt buộc có test case chứng minh TTL hết hạn: gán `_CACHE_TS = xw.time.time() - 5.0` (> 2s TTL) và kiểm chứng `is_xiaowei_running(use_cache=True)` gọi lại subprocess thay vì trả cache.
- **Zombie-to-CIM Success Path:** Mô phỏng `taskkill` báo 0 nhưng tiến trình sống (`iter([True, False])`), sau đó CIM terminate thành công trả về `close_xiaowei() is True` và `call_count == 2` (gọi đúng `powershell`).
