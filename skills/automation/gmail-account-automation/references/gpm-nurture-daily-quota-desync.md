# GPM Gmail Nurture Daily Quota Metric Desync Pitfall

## Vấn đề (Desync Pattern)
Trong hệ thống tự động nuôi profile Gmail trên GPMLogin (`GPM auto`):
- Runner chính (`cron_gpm_gmail_nurture.py`) xác định số lượt nuôi trong ngày bằng cách quét timestamp `last_nurtured` của từng profile trong state file:
  ```python
  def count_nurtured_today(state: dict, now_ts: Optional[float] = None) -> int:
      today = datetime.fromtimestamp(now_ts).date()
      return sum(1 for info in state.values() if info.get("last_nurtured") and datetime.fromtimestamp(info["last_nurtured"]).date() == today)
  ```
- Script báo cáo định kỳ (`cron_gpm_gmail_nurture_6h_report.py`) lại truy vấn qua key cache `_daily_stats`:
  ```python
  daily_stats = state.get("_daily_stats", {})
  daily_count = daily_stats.get("count", 0) if daily_stats.get("date") == today_str else 0
  ```
- Do runner không ghi `_daily_stats` vào `gpm_gmail_nurture_state.json`, báo cáo 6H sẽ hiển thị sai `Tiến độ trần an toàn hôm nay: 0 [+0]/30 profile` mặc dù thực tế hệ thống đã nuôi đủ 100% trần an toàn (`30/30` profile).

## Giải pháp chuẩn hóa (Best Practice)
1. **Kiểm tra hiện trường:** Luôn đọc trực tiếp timestamp `last_nurtured` của các profile trong state file để xác minh số lượng tài khoản thực tế đã nuôi hôm nay.
2. **Đồng bộ logic đếm:** Script báo cáo và watchdog BẮT BUỘC dùng chung hàm tính toán `count_nurtured_today` dựa trên `last_nurtured` thay vì phụ thuộc vào key phụ `_daily_stats` chưa được đồng bộ hóa.
