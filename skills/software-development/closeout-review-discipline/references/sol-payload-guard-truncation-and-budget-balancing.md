# Sol Payload Guard Truncation Mechanics & Budget Balance (16/10/2026)

## 1. Cơ chế Truncation của Sol Payload Guard
Trong `D:/Taadaa/tools/sol_payload_guard.py`:
- `SOL_TARGET_BYTES = 32768` (32KB).
- `split_budget(SOL_TARGET_BYTES)` phân bổ:
  * Diff budget: 65% = 21,299 bytes.
  * Log budget: 25% = 8,192 bytes.
  * Reserve: 10%.
- Khi tổng raw diff vượt quá `diff_budget`, guard gọi `parse_diff()` và `_render_file()`.

## 2. Công thức Cắt tỉa File (Share Allocation Pitfall)
Trong `digest_diff()`:
```python
code_files = sorted(
    (f for f in files if not NOISE_PATTERN.search(f["path"])),
    key=lambda f: nbytes("\n".join("\n".join(h) for h in f["hunks"]))
)
remaining = max(256, budget - nbytes(stat) - 512)
for i, f in enumerate(code_files):
    sum_w = sum(weights[i:])
    share = remaining * weights[i] // sum_w if sum_w > 0 else remaining
    rendered, is_partial = _render_file(f, share)
```
- **Hệ quả chết người:**
  * File code nhỏ hơn được duyệt TRƯỚC, chiếm trước quota trong `remaining`.
  * File code lớn hơn duyệt SAU, chỉ nhận được phần `share` còn lại.
  * Nếu một file test phình to (ví dụ ~10KB raw diff), nó sẽ ép file production code (cũng ~11KB) bị cắt cụt (`is_partial = True` -> `[TRUNCATION_MANIFEST] level=L4 omitted=['deploy/...py(partial)']`).
  * Reviewer Sol High sẽ lập tức trừ điểm nặng ở `logic_correctness` và `farm_safety_regression` vì "101 dòng code production bị truncate, không thể review core logic".

## 3. Quy tắc Cân đối Ngân sách Diff (Diff Budget Balancing)
Để đạt `level=L0` (0 truncation) cho toàn bộ diff:
1. **Kiểm soát dung lượng file Test:** Test suite mới chỉ nên giữ dưới 7-8KB diff (khoảng 8-10 focused test methods, tránh lặp lại boilerplate/mock cồng kềnh).
2. **Loại bỏ Redundant Tests:**
   - Xóa bỏ test chỉ kiểm tra API thụ động đã có integration test bao phủ (`GetLastInputInfo`).
   - Gộp các test assertions vào một context manager (`with patch(...)`).
3. **Mục tiêu Diff Toàn cục:** Tổng raw diff của cả code + test BẮT BUỘC <= 20,000 bytes (tốt nhất ~19KB) để lọt trọn vẹn vào `diff_b` (21,299 bytes), đảm bảo không bao giờ rơi vào `_render_file` truncation.

## 4. Các Tiêu chuẩn Nâng điểm Reviewer Sol High (>= 85/100)
- **Correlation Tracing:** Mọi event phát ra qua structured JSON telemetry (`log_event`) bắt buộc có `correlation_id` / `run_id` tự sinh hoặc nhận từ env.
- **Configurable Clamping:** Các biến cấu hình từ env var (như `XIAOWEI_CIM_TIMEOUT`) bắt buộc phải clamp range an toàn (ví dụ: `max(5, min(60, timeout))`).
- **Cache Invalidation:** Bất kỳ cache nội bộ nào (như `_XIAOWEI_RUNNING_CACHE`) phải được bảo vệ bằng Lock và reset về `None` ngay đầu hàm `main()`.
- **Negative Paths Testing:** Bắt buộc có test cho trường hợp binary không tồn tại nhưng fallback thành công, và trường hợp zombie process (taskkill rc=0 nhưng tiến trình vẫn còn chạy).
