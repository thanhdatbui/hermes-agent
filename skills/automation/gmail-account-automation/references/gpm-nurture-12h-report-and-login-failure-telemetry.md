# GPM Nurture 12H Report, Daily Quota Reconciliation & Login Failure Telemetry

## 1. Daily Nurture Quota Reconciliation (Anti-Zero Reporting)
- **Vấn đề:** Runner `cron_gpm_gmail_nurture.py` đếm trần nuôi ngày (`MAX_DAILY_NURTURE = 30`) dựa vào `last_nurtured` timestamp của từng profile trong ngày, nhưng không ghi key `_daily_stats` vào state file. Script report đọc `state.get('_daily_stats', {})` dẫn đến báo `0/30 profile` dù thực tế đã hoàn thành đủ 30/30 profile.
- **Quy chuẩn sửa:**
  - Bổ sung hàm `count_nurtured_today(state: dict, now_ts: Optional[float] = None) -> int` duyệt toàn bộ profile hợp lệ và đếm timestamp `last_nurtured` có `date == today`.
  - Trong `build_report_lines`: Ưu tiên `_daily_stats` nếu có và khớp ngày hôm nay với `count > 0`; trường hợp còn lại fallback 100% sang `count_nurtured_today(state, now_ts)`.

## 2. Minh Bạch Hóa Danh Tính Acc Login Thất Bại (`post_evening_gpm_login_watchdog.py`)
- **Vấn đề:** Báo cáo tổng kết ca chỉ in số lượng `✓ 34 | ✗ 7` chung chung, không cho biết tài khoản nào bị fail và fail do loại lỗi gì.
- **Quy chuẩn sửa:**
  - Trong state file runtime (`post_evening_gpm_login_state.json`), lưu thêm mảng `failed_details: list[dict]`.
  - Mỗi khi một worker login thất bại:
    ```python
    failed_details.append({
        "email": res["email"],
        "mid": res.get("mid"),
        "fail_type": fail_type,  # PLATFORM vs SCRIPT
    })
    ```
  - Trong `_format_summary_report`, in danh sách chi tiết:
    ```text
    ⚠️ Chi tiết 2 acc thất bại:
      - example1@gmail.com (PLATFORM)
      - example2@gmail.com (SCRIPT)
    ```

## 3. Chuyển Đổi Nhịp Báo Cáo Sang 12H (`gpm-gmail-nurture-12h-report`)
- **Lịch cronjob:** `0 */12 * * *` (chạy lúc 00:00 và 12:00 hàng ngày), cập nhật qua `cronjob(action='update', job_id='96ea8cc3093b', schedule='0 */12 * * *', name='gpm-gmail-nurture-12h-report')`.
- **Logic Script:**
  - Đặt `WINDOW_HOURS = int(os.environ.get('GPM_NURTURE_WINDOW_HOURS', 12))`.
  - Cho phép truyền tham số `window_hours: Optional[int] = None` vào `build_report_lines` (fallback về `WINDOW_HOURS`).
  - Tiêu đề và nội dung format tự động co giãn theo `{window_hours}h`: `📊 [BÁO CÁO 12H: TIẾN ĐỘ NUÔI GMAIL GPM]`, bảo đảm tương thích ngược với các unit test cũ.

## 4. Kỷ Luật Dispatch Code-Edit Trên Farm (Cấm Freeze Khi User Giục)
- **Dispatch Gate Invariant:** `delegate_task` bị cấm cho tác vụ sửa code (`BLOCKED_BY_DISPATCH_GATE`). Tác vụ sửa code BẮT BUỘC dispatch qua Worker CLI:
  ```bash
  python D:/Taadaa/tools/dispatch_worker.py --workdir "D:/Taadaa/GPM auto" --file "<path>" "<contract>"
  ```
  *(Thang điều phối: Sol Tier 1 -> Agy CLI Tier 2 -> Haiku Tier 3 fallback).*
- **Phản ứng khi User giục "Làm đi":** CẤM phân trần, đóng băng hoặc hỏi lại xin phép. Kích hoạt Worker CLI ngay lập tức, hoàn thành sửa đổi và chạy pytest kiểm chứng.
