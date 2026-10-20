# Antigravity CLI Pool Timeout Cascade & Closeout Test Pairing (2026-10-20)

## 1. Hiện Tượng: Cascade Timeout 180s Làm Đơ Toàn Bộ Pool Antigravity (`ag_cli.py`)
- **Triệu chứng:** Khi điều phối Strike 3 Reviewer Handoff hoặc task sửa code sang `ag_cli.py fix`, toàn bộ 22 profile trong `pool_state.json` lần lượt bị khóa cooldown `1200s` (20 phút) với lý do:
  ```json
  "reason": "TimeoutExpired (180s)",
  "cooldown_seconds": 1200
  ```
  Tạo cảm giác toàn bộ pool bị "treo" hay đứng im.
- **Nguyên nhân gốc rễ:**
  - Binary `agy.exe` (Antigravity Headless CLI) hoạt động trên nền tảng Gemini Code Assist.
  - Khi chạy trong repo có các file chỉ dẫn lớn (như `AGENTS.md` > 140KB) và prompt sửa code nhiều yêu cầu, `streamGenerateContent` phải stream qua nhiều turns (`I1020 05:08:51`, `05:09:17`, `05:09:48`, `05:10:07`, `05:10:27`, `05:11:09`, `05:11:42`).
  - `ag_cli.py` thiết lập tham số `--timeout` mặc định là 180s (`subprocess.Popen` timeout 180s).
  - Khi thời gian streaming vượt qua 180s, `TimeoutExpired` kích hoạt, tiến trình bị `taskkill /F /T`, profile bị phạt cooldown 1200s.
  - Vòng lặp failover tự động nhảy sang profile kế tiếp trong pool (`acc_02`, `acc_04`...) và tiếp tục bị timeout 180s, dẫn đến hiệu ứng domino (cascade failure) làm cạn kiệt toàn bộ pool.
- **Giải pháp & Kỷ luật vận hành:**
  1. Khi dispatch task sửa code cho `ag_cli.py fix`, **BẮT BUỘC chỉ định `--timeout` tối thiểu từ 300s đến 600s** nếu repo có context lớn hoặc nhiều rule files.
  2. Không để timeout mặc định 180s nuốt chửng các profile đang hoạt động bình thường.
  3. Ưu tiên Tier 1 (Claude CLI với `claude_worker.py --role reviewer`) cho pha Strike 3 Reviewer Handoff khi quota của Claude vẫn còn trong ngưỡng an toàn.

## 2. Bẫy Điểm Phạt `test_evidence` Khi Tách File Test Khỏi `--files` (30KB Ceiling)
- **Triệu chứng:** Điểm Closeout Gate bị kẹt ở mức 73–76/100 dù toàn bộ 26 unit test pass 100%. Reviewer ghi nhận:
  *"Việc thay đổi đáng kể hành vi watchdog mà không cung cấp diff của test hoặc coverage report khiến chưa thể xác nhận không có regression đối với logic báo cáo và lịch chạy trước đó."*
- **Nguyên nhân:**
  - Nhằm tránh ngưỡng fail-fast `MAX_DIFF_BYTES_GATE = 30_000` (30KB), Coordinator chỉ truyền file triển khai vào `--files` (`cron_night_tiktok_2fa_watchdog.py`) mà bỏ qua file test (`test_cron_night_tiktok_2fa_watchdog.py`).
  - Khi Reviewer đọc payload diff không thấy mã nguồn test tương ứng với các thay đổi nghiệp vụ mới (như file locking, status check Telegram, idempotency), cột điểm `test_evidence` bị trừ nặng (chỉ đạt 20–21/30 điểm), kéo tổng điểm xuống dưới ngưỡng 80/85.
- **Quy tắc giải quyết:**
  1. **Không tách rời Implementation và Test:** `--files` bắt buộc phải chứa cả file triển khai và file test tương ứng.
  2. **Gọt dũa mã nguồn O(1):** Cả file triển khai và file test phải được viết ngắn gọn, súc tích, tái sử dụng fixture và helper, loại bỏ docstring thừa hay các khối test trùng lặp để **TỔNG DIFF CẢ HAI FILE LUÔN <= 28,000 BYTES**.
  3. Đảm bảo Reviewer nhìn thấy bằng chứng kiểm thử trực tiếp trong diff candidate mà không làm tràn trần 30KB.
