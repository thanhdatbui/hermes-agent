# GPM Nurture Daily Count Calculation & Login Failure Reporting

## 1. Nurture 6H Report Daily Quota Desync Pitfall
- **Vấn đề:** Runner nuôi (`cron_gpm_gmail_nurture.py`) giới hạn `MAX_DAILY_NURTURE = 30` bằng cách đếm số tài khoản có timestamp `last_nurtured` khớp ngày hôm nay. Nhưng nó không ghi key `_daily_stats` vào state file.
- **Bẫy thống kê:** Script báo cáo 6H (`cron_gpm_gmail_nurture_6h_report.py`) trước đây đọc `_daily_stats`, dẫn đến báo cáo `Tiến độ trần an toàn hôm nay: 0 [+0]/30 profile` dù thực tế đã nuôi đủ 30/30 profile hôm đó.
- **Giải pháp chuẩn:** Đồng bộ hàm `count_nurtured_today(state, now_ts)` vào script report:
  ```python
  def count_nurtured_today(state: dict, now_ts: Optional[float] = None) -> int:
      if now_ts is None:
          now_ts = time.time()
      today = datetime.fromtimestamp(now_ts).date()
      count = 0
      for k, info in state.items():
          if k.startswith('_') or not isinstance(info, dict):
              continue
          last_n = info.get('last_nurtured')
          if not last_n:
              continue
          try:
              if datetime.fromtimestamp(last_n).date() == today:
                  count += 1
          except Exception:
              continue
      return count
  ```
  Fallback: nếu `_daily_stats` có và `count > 0` thì dùng, ngược lại luôn gọi `count_nurtured_today(state, now_ts)`.

## 2. Minh bạch danh tính tài khoản Login thất bại
- **Vấn đề:** Watchdog đăng nhập (`post_evening_gpm_login_watchdog.py`) trước đây chỉ in số đếm tổng hợp `✓ 34 | ✗ 7`, giấu nhẹm danh tính email và lý do thất bại.
- **Giải pháp chuẩn:**
  1. State file duy trì mảng `failed_details: list[dict]`:
     ```python
     failed_details.append({
         "email": res["email"],
         "mid": res.get("mid"),
         "fail_type": fail_type,  # PLATFORM vs SCRIPT
     })
     ```
  2. Báo cáo tổng kết ca (`_format_summary_report`) bóc tách danh sách top acc thất bại gửi về Telegram:
     ```text
     ⚠️ Chi tiết 2 acc thất bại:
       - example1@gmail.com (PLATFORM)
       - example2@gmail.com (SCRIPT)
     ```

## 3. Quy chuẩn điều phối sửa code: Dispatch Gate & Worker CLI
- **Invariant:** `delegate_task` bị chặn bởi Dispatch Gate đối với tác vụ sửa code (`TASK_KIND: EDIT`).
- **Thực thi chuẩn:** Bắt buộc dispatch qua Worker CLI:
  ```bash
  python D:/Taadaa/tools/dispatch_worker.py --workdir "<repo_path>" --file "<target_file>" "<prompt_contract>"
  ```
  Thang leo thang tự động của `dispatch_worker.py`:
  - **Tier 1:** Sol (`gpt-web-sol` qua port `:20129`)
  - **Tier 2:** Antigravity CLI (`gemini-3.8-flash-medium`)
  - **Tier 3 Fallback:** Claude Haiku (`claude-haiku-5-5`)
- Khi user phát lệnh dứt khoát ("Làm đi"), Coordinator bắt tay thực thi ngay qua Worker CLI, cấm phân trần hoặc hỏi lại.
