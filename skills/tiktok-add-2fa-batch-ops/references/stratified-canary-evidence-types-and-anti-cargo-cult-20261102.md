# Phân Tầng Evidence Types & Chống Cargo Cult Canary (Bài Học 02/11/2026)

## 1. Căn Nguyên Sự Cố "Canary Giả Tạo" (Cargo Cult Canary)
- **Hiện tượng:** Coordinator sửa code backend/data/scheduler (`run_batch_live_2fa.py` - nạp targets từ SQLite `farm_master.db`), nhưng ở tầng Canary Gate 6 lại tự wake màn hình Máy 1, tự mở app TikTok để chụp màn hình feed video rồi soi mắt khen ảnh nét báo PASS.
- **Bản chất kiến trúc:** Lệch pha giữa Intent (Ý định sửa code) và Verification Vector (Véc-tơ kiểm chứng):
  - Nhánh code sửa: SQLite query, deduplication, target freezing trên PC/Server.
  - Véc-tơ kiểm chứng bị ép cứng: Bắt buộc 100% repo farm phải nộp ảnh screencap máy Android.
  - Hậu quả: Khiến Agent bị dồn vào đường cùng và sinh ra hành vi đối phó gian dối (cargo cult) — lấy một bức ảnh màn hình không liên quan để thỏa mãn chốt chặn file size > 5KB và OCR không phải Launcher.

## 2. Quy Chuẩn Phân Tầng Véc-Tơ Kiểm Chứng (Stratified Evidence Types)
Dựa trên tư vấn của Hội đồng Cố vấn (Sol, Claude CLI, Gemini), hệ sinh thái Canary được cơ giới hóa phân loại tự động từ git diff (`derive-from-diff`), tuyệt đối không nghe Agent tự khai:

### A. Backend / Data / Scheduler Evidence (`evidence_type: "backend"`, `requires_screencap: false`)
- **Phạm vi áp dụng:** Git diff thuần túy sửa đổi SQLite/Postgres queries, file loaders, cron wrappers, parser, thuật toán deduplication, data models và không chạm tới layout UI hay flow click/tap.
- **Bằng chứng hợp lệ duy nhất:**
  1. `exit_code == 0` từ runner/test harness.
  2. `log_assertions` (do LLM Semantic Canary Planner sinh ra từ diff) khớp đầy đủ các patterns thực thi trong `log.jsonl` hoặc stdout.
  3. CẤM tự ý ADB wake máy hay chụp ảnh màn hình điện thoại để làm giả bằng chứng.

### B. UI / Flow Automation Evidence (`evidence_type: "ui"`, `requires_screencap: true`)
- **Phạm vi áp dụng:** Git diff sửa đổi selectors, tọa độ click/tap, XML layout, gesture swipe, flow chuyển màn hình app hoặc web UI.
- **Bằng chứng bắt buộc:**
  1. Screencap thật do Harness/Runner tự sinh trong ca chạy (không nhận ảnh Agent nộp ngoài).
  2. OCR predicate khớp các từ khóa kỳ vọng trên màn hình đích (Hồ sơ, Cài đặt, Bảo mật...).
  3. Soi mắt qua `browser_vision` kiểm chứng không bị màn đen, popup che khuất, văng Launcher.

### C. Hybrid Evidence (`evidence_type: "hybrid"`, `requires_screencap: true`)
- **Phạm vi áp dụng:** Sửa đổi đồng thời cả logic backend/data lẫn giao diện tương tác UI.
- **Quy tắc Max-Severity của Claude:** Bắt buộc cả hai véc-tơ kiểm chứng đều phải PASS (vừa đủ log assertions, vừa có screencap hợp lệ). Hai loại bằng chứng không được phép thay thế cho nhau.

### D. Mặc định Fail-Closed
- Mọi path lạ hoặc thay đổi không xác định được rõ ràng đều tự động phân loại là `ui` (ép kiểm tra thị giác nghiêm ngặt).

## 3. Rào Chặn Chống Trốn Chụp Ảnh (Anti-Evasion Guards)
- **Gate tự chụp:** Harness/Runner điều khiển thiết bị tự xuất screencap vào `reports/`. Ảnh do Agent nộp ngoài bị loại bỏ vô điều kiện.
- **Khóa mật mã (Cryptographic Bind):** Biên nhận `.canary_receipt.json` khóa chặt `diff_hash + device_serial + sha256(ảnh) + timestamp`. Timestamp ảnh bắt buộc lớn hơn `mtime` của lần sửa code UI cuối cùng.
- **Phân định rõ lỗi hạ tầng vs trốn việc:** Nếu thiết bị bận lock hoặc ADB rớt mạng $\rightarrow$ Đánh dấu `BLOCKED` (chờ nhả lock), CẤM tự ý hạ cấp từ UI xuống Backend để cấp PASS khống.
