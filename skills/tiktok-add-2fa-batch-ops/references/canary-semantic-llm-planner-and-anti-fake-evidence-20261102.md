# Canary Semantic LLM Planner Integration & Anti-Fake Evidence Invariant (02/11/2026)

## 1. Bản Chất Sự Cố "Canary Hình Thức Đối Phó"
- **Hiện tượng:** Sửa code logic backend (ví dụ: `freeze_targets` đọc SQLite trong `run_batch_live_2fa.py`), nhưng runner lại bị hardcode map sang một script mock không liên quan, sau đó chụp đại màn hình máy đang mở sẵn hoặc tự adb bật màn hình lên chụp lấy lệ một cái ảnh cũ rồi báo "Canary thành công".
- **Hậu quả:** Bị User bắt thóp và chỉ trích gay gắt: *"Sửa code logic follow/2fa đúng không, tự nhiên mở máy 1 lên xem màn hình cho vui xong báo canary xong, clgt?"*.
- **Bài học cốt lõi:** Báo DONE bằng ảnh mù / ảnh không phản ánh kết quả thực thi của code vừa sửa là hành vi gian dối bị nghiêm cấm tuyệt đối.

## 2. Kiến Trúc Chuẩn: Semantic Canary Planner (Gate B LLM Inference)
Thay vì kiểm tra mù hoặc chụp màn hình ngẫu nhiên, hệ thống Canary bắt buộc đi qua 3 tầng:

1. **Sinh Kế Hoạch Ngữ Nghĩa (`canary_plan.py`):**
   - Phân tích `git diff` qua thang Gate B: `gemini-web` (:20129) $\rightarrow$ `gpt-web-sol` (:20129) $\rightarrow$ `claude-cli`.
   - Sinh ra `canary_plan.json` chứa:
     * `cli_args_override`: Tham số kích hoạt đúng nhánh code vừa vá.
     * `log_assertions.required_patterns`: Các chuỗi bắt buộc phải xuất hiện trong log (ví dụ: `[telemetry:freeze-targets-sqlite].*total=`).
     * `log_assertions.forbidden_patterns`: Các chuỗi lỗi cấm xuất hiện.
2. **Nối Thông Pipeline (`unified_patch_pipeline.py`):**
   - Ở Bước S4 (Canary): Trước khi gọi `canary_runner.py`, BẮT BUỘC chạy `canary_plan.py --repo <repo> --out-file <run_dir/canary_plan.json>`.
   - Truyền tham số `["--plan", str(run_dir / "canary_plan.json")]` vào lệnh gọi `canary_runner.py`.
3. **Thẩm Định Cơ Học Chặn Đứng (`canary_runner.py`):**
   - Nạp file plan $\rightarrow$ thực thi lệnh với `cli_args_override`.
   - Quét file `log.jsonl` hoặc `summary.txt` trong thư mục run artifacts.
   - **FAIL-CLOSED (Exit 1 - SEMANTIC_ASSERTION_FAILED):** Nếu thiếu bất kỳ required pattern nào của nhánh code vừa sửa, runner đánh rớt ngay lập tức, từ chối cấp `.canary_receipt.json`.

## 3. Phân Định: Tác Vụ Dữ Liệu vs Tác Vụ Thiết Bị
- **Dọn dữ liệu server / Migrate DB:** Thao tác trên CSDL SQLite (`farm_master.db`), dọn log, dọn lock file `.codex/device-locks` là tác vụ server thuần túy, KHÔNG chạm thiết bị, KHÔNG cần chờ ca nuôi và KHÔNG cần Canary máy thật. Nghiệm thu bằng read-back `COUNT(*)` và exit code 0.
- **Canary thiết bị:** Chỉ áp dụng cho code logic điều khiển farm/thiết bị thật. Khi chạy Canary, bắt buộc phải có assertion log chứng minh nhánh code vừa sửa thực sự chạy qua thiết bị.
