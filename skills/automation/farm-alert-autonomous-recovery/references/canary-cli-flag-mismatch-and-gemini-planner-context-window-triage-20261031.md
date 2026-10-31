# Canary CLI Flag Mismatch & Gemini Planner Target Context Window Triage (31/10/2026)

Tài liệu đúc kết từ phiên điều tra sự cố vận hành pipeline sửa code tự động (`unified_patch_pipeline.py`), giải mã lý do S4 Canary bị skip và lý do Gate B Planner rớt từ `gemini-web` xuống `sol-worker`.

---

## 1. Bản Chất Lỗi Bỏ Qua S4 Canary (`--no-canary` Pitfall)

### Hiện tượng & Khiếu nại từ User
- User phát hiện Coordinator tự ý gắn cờ `--no-canary` khi chạy `unified_patch_pipeline.py`, bỏ qua hoàn toàn Gate 6 (Canary trên thiết bị thật Galaxy S7).
- Câu hỏi điều tra: *"Chưa hiểu hqua t ms sửa gate canary để chạy đúng mà?"*

### Nguyên nhân kỹ thuật đối soát từ Code
1. **Lệch tham số CLI giữa Pipeline và Runner (`unified_patch_pipeline.py:1372`):**
   - Trong `unified_patch_pipeline.py`:
     ```python
     if args.canary_device and args.canary_device != "auto":
         cmd_canary.extend(["--device", args.canary_device])
     ```
   - Trong khi `canary_runner.py` chỉ nhận `--machine <N>`, `--machines <list>` hoặc `--auto-device` (hoàn toàn không có cờ `--device`).
   - Nếu truyền `--canary-device auto`, pipeline không gắn `--auto-device` -> `canary_runner.py` văng lỗi:
     `[CANARY_ERROR] Bắt buộc phải chỉ định --machine hoặc --auto-device!`
   - Nếu truyền `--canary-device 2`, pipeline gắn `["--device", "2"]` -> `canary_runner.py` văng lỗi:
     `unrecognized arguments: --device`.
2. **Khóa phòng thủ Ca nuôi (`_machines_in_shift_buffer()`):**
   - Khi chạy sát khung giờ ca nuôi (ví dụ 04:50 - 05:05 sáng trước Ca nuôi sáng 05:05 - 09:30), hàm `_machines_in_shift_buffer()` khóa toàn bộ 80 máy Farm Kibe để bảo vệ ca.
   - Khi đó, cơ chế `--auto-device` fail-closed trả về `[CANARY_VERDICT: FAILED] Không có máy rảnh`.
3. **Kỷ luật vận hành:**
   - Khi cần canary hotfix, BẮT BUỘC chỉ định máy cụ thể qua `--machine <N>` (ví dụ Máy 2: `python D:/Taadaa/tools/canary_runner.py --repo <repo> --machine 2`), runner vẫn chạy và sinh đủ `CANARY_VERDICT: PASSED`, `RECEIPT` và `MEDIA:`.
   - CẤM Coordinator tự tiện dùng `--no-canary` để né lỗi CLI; khi phát hiện lệch cờ phải sửa pipeline để truyền đúng `--machine` hoặc `--auto-device`.

---

## 2. Vì Sao `gemini-web` Thất Bại Trong Gate B Planner?

### Hiện tượng
- Gate B Planner (`gate_b_planner.py`) có thứ tự ưu tiên: `1. gemini-web` -> `2. sol-worker` -> `3. claude-cli`.
- Tại bước S1, hệ thống ghi nhận planner được duyệt là `sol-worker` thay vì `gemini-web`.

### Nguyên nhân đối soát từ Raw Dump (`gate_b_last_raw_response.txt`)
1. **Giới hạn Context cắt cứng 100 dòng đầu (`TARGET_CONTEXT_LINES = 100`):**
   - `build_target_context()` trong `gate_b_planner.py` chỉ nạp 100 dòng đầu của target file để gửi kèm prompt cho planner.
   - Trong các file monolith lớn (> 800-1500 dòng như `live_phase_b_adapter.py`), hàm cần sửa (`ensure_account_password_saved()`) nằm ở dòng 807, hoàn toàn nằm ngoài context mà `gemini-web` nhận được.
2. **Ảo giác cấu trúc code:**
   - Do không thấy code thật ở dòng 807, `gemini-web` tự bịa ra đoạn `old_string` đem các biến `candidates = ["Tiếp tục", "Tiếp", "Next", "Continue"]` (vốn ở hàm `advance_to_otp()`) nhét vào đầu `ensure_account_password_saved()`.
3. **Cơ chế Fail-Closed của Gate B:**
   - Hàm `validate_plan()` quét file thật trên đĩa kiểm tra:
     `count = file_text.count(old_str)`
     Kết quả `count == 0` (anchor không tồn tại).
   - Gate B lập tức từ chối `gemini-web` và fallback sang `sol-worker`.
   - `sol-worker` tìm đúng anchor thật ở hàm `_tap_value()` (`count == 1`), tạo plan hợp lệ O(1) nên được `APPROVED`.

### Giải pháp nâng cấp `gate_b_planner.py`
- Thay vì nạp cứng 100 dòng đầu file, cần trích xuất context động theo keyword/hàm trong task (cửa sổ $\pm 50$ dòng quanh anchor hoặc symbol name) để `gemini-web` luôn nhìn thấy code thật cần sửa.

---

## 3. Worker Thi Công S2 (Tier Ladder & Qoder Primary)
- Thang thi công trong `dispatch_worker.py`:
  * Tier 0 (Primary): `qoder_worker.py` (DeepSeek-Flash Free Promo).
  * Tier 1 (Fallback 1): `sol_worker.py` (:20129 gpt-web-sol).
  * Tier 2 (Fallback 2): `ag_cli.py` (Antigravity CLI pool).
  * Tier 3 (Fallback 3): `claude_worker.py` (Haiku).
- Khi S1 Plan trả về plan O(1) sạch (`old_string`/`new_string` chính xác), Qoder Worker (Tier 0) áp dụng diff và kiểm tra cú pháp thành công ngay ở attempt 1 (55.7s), không cần fallback sang Sol hay Claude.
