# Retirement of uiautomator.md & Multi-Source Cooldown Invariants (2026-10-05)

## 1. Retirement of `docs/uiautomator.md` Across All Farm Repos
- **Bối cảnh & Lệnh User:** User chỉ đạo khai tử hoàn toàn `docs/uiautomator.md` trên 16 repo farm tại `D:/Taadaa/`.
- **Nguyên nhân:**
  - `uiautomator.md` là alias lịch sử trùng lặp với `docs/farm-automation-cases.md`.
  - Tài liệu markdown thụ động không thể ngăn ngừa hồi quy mã nguồn, nhưng lại bắt buộc mỗi task sửa farm code phải cập nhật cả hai file docs, làm tăng số lượng file và gây phình to diff (`diff bloat`).
- **Quy chuẩn mới:**
  - **Regression Gate là nguồn chân lý duy nhất chống hồi quy:** Mọi lỗi farm phải được kiểm chứng bằng Focused Unit/Integration Tests tự động trong test suite và thẩm định qua `closeout_gate.py`.
  - Toàn bộ 16 file `uiautomator.md` đã bị xóa bỏ hoàn toàn. `AGENTS.md` đã gỡ bỏ alias `uiautomator.md`.
  - Chỉ duy trì `docs/farm-automation-cases.md` cho các Anti-Pattern và kiến trúc lớn, không bắt buộc cập nhật song song tài liệu trùng lặp.

## 2. Multi-Source Cooldown Precedence Invariant (Fail-Closed)
- **Lỗ hổng phát hiện bởi Reviewer Sol/Terra:**
  - Trong `_is_account_follow_cooldown`, nếu chỉ kiểm tra file theo row (`follow_state_{machine}_row_{row}.json`) và thấy không có cooldown, code cũ lập tức bỏ qua file cấp máy (`follow_state_{machine}.json`).
  - Hậu quả: Một row state mới "sạch" có thể che giấu hoàn toàn lệnh cooldown cấp máy đang còn hiệu lực, dẫn đến việc tài khoản bị follow trái phép.
  - Ngoài ra, nếu `cooldown_until_at` (timestamp UTC) đã hết hạn nhưng `cooldown_until_date` hoặc `follow_failed` streak vẫn còn hiệu lực trong cùng 1 JSON state, việc return sớm `False` sẽ bỏ qua các tín hiệu cooldown còn lại.
- **Quy tắc bất biến (Invariant):**
  - **Hợp nhất đa nguồn (OR semantics):** BẮT BUỘC kiểm tra cả 2 file candidate (cấp row và cấp máy). Nếu BẤT KỲ nguồn nào còn cooldown hiệu lực $\to$ `return True`.
  - **Đánh giá toàn diện các trường cooldown:** Hết hạn timestamp không được phép short-circuit các trường date hoặc streak còn hiệu lực trong cùng payload.
  - **Fail-Closed khi lỗi:** Nếu bất kỳ file nào bị lỗi cú pháp, JSON hỏng, hoặc non-dict $\to$ `return True` (chặn follow an toàn).

## 3. Cấm Tự Ý Đảo Ngược Safety Defaults (Opt-in Protection)
- **Bài học từ Reviewer Sol:**
  - Việc sửa đổi cờ `allow_network_force_stop_recovery` từ `False` sang `True` làm mặc định đã bị Reviewer đánh rớt điểm Farm Safety từ 14 xuống 8 (kéo tổng điểm xuống 73/100).
  - Lý do: Biến cơ chế force-stop/relaunch TikTok khi lỗi mạng từ opt-in thành mặc định bật tiềm ẩn nguy cơ văng session/cookie hàng loạt trên farm mà không có guard chống lặp.
- **Quy tắc:** CẤM TUYỆT ĐỐI đảo ngược các cờ bảo vệ an toàn (safety flags) từ `False` sang `True` trong các task sửa bug thông thường. Mọi thao tác có tính hủy diệt/kill process/force-stop bắt buộc phải là strict opt-in.

## 4. Telemetry Anomaly Invariant trong Watchdog
- Khi phát hiện số liệu bất thường (`like_count > 0` nhưng `valid_swipes <= 0`, hoặc `already_liked >= swipes`):
  - Watchdog BẮT BUỘC phát cảnh báo `[LIKE_RATE_TELEMETRY_ANOMALY]`.
  - Tỷ lệ thả tim BẮT BUỘC gán là `"INVALID"` (hoặc `None`), TUYỆT ĐỐI CẤM xuất ra `0.0%` hay tỷ lệ `> 100%` (như `150.0%`) làm sai lệch và che giấu dữ liệu lỗi trong báo cáo vận hành.

## 5. Whitespace/Empty-String Path Fallback Trap
- **Bẫy:** Viết `state_root = Path(state_dir) if state_dir is not None else DEFAULT_PATH`.
  Khi caller truyền `state_dir=""` hoặc `"   "`, `Path("")` trỏ vào thư mục hiện hành (`cwd`) thay vì fallback về thư mục mặc định của repo.
- **Quy chuẩn:** Bắt buộc sanitize độ dài chuỗi:
  `state_root = Path(state_dir) if (state_dir is not None and str(state_dir).strip()) else DEFAULT_PATH`.

## 6. Fallback Event Parsing: Truthiness & Non-Dict `extra` Trap
- **Bẫy 1 - Substring không đồng nghĩa với Truthy:** Trong fallback `log.jsonl`, kiểm tra `'"already_liked"' in line` nhưng khi đọc `event` lại tăng biến đếm mà không kiểm tra `bool(event.get("already_liked"))`. Log mang giá trị `already_liked: false` vẫn bị đếm, làm sai lệch telemetry. Bắt buộc: kiểm tra truthy rõ ràng.
- **Bẫy 2 - `extra` là None hoặc non-dict:** Gọi `event.get("extra", {}).get(...)` sẽ văng `AttributeError: 'NoneType' object has no attribute 'get'` khi `event["extra"]` tồn tại nhưng mang giá trị `None`. Bắt buộc chuẩn hóa:
  `extra = event.get("extra") if isinstance(event.get("extra"), dict) else {}`.
- **Bẫy 3 - Per-line JSON parsing:** Không bọc cả vòng lặp đọc file trong một khối `try...except` duy nhất vì một dòng JSON hỏng sẽ làm dừng toàn bộ quá trình quét. Bắt buộc đặt `try...except` quanh `json.loads(line)` của từng dòng riêng biệt.

## 7. MagicMock Property Trap trong Test Gate Evaluator
- **Bẫy:** Trong test fixture dùng `MagicMock` cho kết quả session (`child_result`), nếu không gán rõ `child_result.status = "success"` và `child_result.final_status = "success"`, các hàm chuẩn hóa chuỗi như `_normalize_token(getattr(child_result, "final_status", None))` sẽ biến mock thành chuỗi `"<magicmock_name='mock.final_status' ...>"`. Chuỗi này kích hoạt early exit `sensitive-skip-...` thay vì đi vào nhánh test mong muốn.
- **Quy chuẩn:** Luôn mock tường minh các trường status kết thúc (`status="success"`, `final_status="success"`).

## 8. Account-Switcher Bounds Clamping: Lệch Tâm Tap trên Samsung
- **Bẫy:** Tự ý kẹp cứng bounds của account-switcher row rộng $\ge 600$ thành `(x1, y1, x1+600, y2)` làm tâm tap bị dịch từ x=540 sang x=300 trên màn hình 1080x1920, khiến nút chuyển tài khoản trên Samsung bị hụt hoặc tap nhầm.
- **Quy chuẩn:**
  - Nếu row container là clickable (`node.attributes.get("clickable") == "true"`), giữ nguyên bounds đầy đủ (tâm x=540).
  - Nếu row container không clickable, tìm phần tử con TextView clickable tương ứng bên trong. Khôi phục nguyên vẹn hành vi baseline `HEAD`.
