# GPM Nurture Report Observability & Worker CLI Dispatch

## 1. Kỷ luật Điều phối Sửa Code (Worker CLI Dispatch vs delegate_task)
- **Cấm dừng lại hỏi khi user phát lệnh hành động:** Khi User ra lệnh "Làm đi", "Sửa đi", Coordinator BẮT BUỘC thực thi ngay lập tức. CẤM dừng lại tóm tắt kế hoạch hay phân trần về gate.
- **Dispatch Gate Invariant:** `delegate_task` bị chặn đối với tác vụ sửa code (`⛔ [DISPATCH GATE - BLOCKED_BY_DISPATCH_GATE]: delegate_task bị cấm cho tác vụ sửa code. Phải dispatch qua worker CLI.`).
- **Lệnh điều phối chuẩn (Canonical Worker CLI):**
  ```bash
  python D:/Taadaa/tools/dispatch_worker.py --workdir "D:/Taadaa/GPM auto" --file "<target_file>" "<structured_contract>"
  ```
  Thang giải cứu tự động của `dispatch_worker.py`:
  - **Tier 1:** Sol Worker (`gpt-web-sol` qua port 20129)
  - **Tier 2:** Antigravity CLI (`gemini-3.8-flash-medium`)
  - **Tier 3:** Claude Haiku (`claude-haiku-5-5`)

## 2. Bẫy Thống kê Trần Nuôi Ngày (Daily Quota Calculation Trap)
- **Hiện tượng:** Report báo `Tiến độ trần an toàn hôm nay: 0 [+0]/30 profile` dù thực tế đã nuôi hoàn tất 30/30 profile.
- **Nguyên nhân gốc rễ:** Runner chính `cron_gpm_gmail_nurture.py` kiểm tra trần qua timestamp `last_nurtured` của từng profile trong ngày, không ghi key `_daily_stats` vào state file. Script report đọc cứng `_daily_stats` sẽ luôn nhận 0.
- **Chuẩn hóa:** Luôn dùng hàm đếm timestamp `count_nurtured_today(state, now_ts)` đọc trực tiếp các bản ghi trong state, chỉ fallback sang `_daily_stats` khi có dữ liệu hợp lệ.

## 3. Cấu hình Cửa sổ Báo cáo Linh hoạt (6H vs 12H)
- Cấu hình cửa sổ thời gian qua biến môi trường với mặc định 12h:
  ```python
  WINDOW_HOURS = int(os.environ.get("GPM_NURTURE_WINDOW_HOURS", 12))
  ```
- Hàm `build_report_lines(...)` bắt buộc nhận `window_hours: Optional[int] = None`:
  - Mặc định dùng `WINDOW_HOURS` (12h cho lịch chạy `0 */12 * * *`).
  - Cho phép unit test truyền tường minh `window_hours=6` để đảm bảo tương thích ngược (regression safe).

## 4. Minh bạch Lỗi Login Thất bại (Actionable Failure Observability)
- **Quy tắc chống ẩn lỗi:** Không được chỉ in con số tổng quát `✓ 34 | ✗ 7`. Người vận hành không thể khắc phục nếu không biết nick nào chết và chết vì lý do gì.
- **Cơ chế:**
  - Lưu mảng `failed_details` vào state file: `[{"email": ..., "mid": ..., "fail_type": "PLATFORM" | "SCRIPT"}]`.
  - Format tin nhắn Telegram tóm tắt ca bắt buộc trích xuất danh sách top acc thất bại:
    ```text
    ⚠️ Chi tiết 2 acc thất bại:
      - example1@gmail.com (PLATFORM)
      - example2@gmail.com (SCRIPT)
    ```

## 5. Thẩm định Closeout Gate Repo Desktop (GPM auto)
- Repo `GPM auto` là automation trên Windows browser (GPMLogin/Chrome), không nằm trong danh mục thiết bị của `canary_runner.py` (Android Phone Farm).
- Lệnh chạy kiểm chứng Closeout Gate chuẩn:
  ```bash
  python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/GPM auto" --files <files_modified> --base HEAD --json-output
  ```
- Yêu cầu Sol Auditor (`:20129` model `review`) đạt `Score >= 85/100` và `Verdict: APPROVED` trước khi commit.
