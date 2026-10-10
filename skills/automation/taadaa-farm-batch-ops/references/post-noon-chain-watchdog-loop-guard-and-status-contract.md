# Post Noon Chain Watchdog (Reg Gmail -> Add 2FA TikTok) Loop Guard & Status Contract

## 1. Bản chất sự cố chạy lặp (Repeated Execution Loop)
- Watchdog chạy theo lịch cron mỗi 5-10 phút để kiểm tra điều kiện chạy chuỗi sau ca trưa (14:30 - 18:30).
- Idempotency dựa vào `already_ran_today`:
  ```python
  def already_ran_today(today_str: str) -> bool:
      data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
      return data.get("last_success_date") == today_str and data.get("details", {}).get("lane_status") == "success"
  ```
- Nếu `lane_status` bị đánh giá là `"failed"`, `save_state` sẽ **không cập nhật `last_success_date` hôm nay**.
- Kết quả: Lần cron tick kế tiếp (sau 5 phút) thấy `already_ran_today == False` -> Tiếp tục kích hoạt lại toàn bộ batch 1 tiếng -> Gây lặp 2-3 lần trong ngày.

## 2. Contract Exit Code của Gmail Batch (`run_all.ps1`)
- Khi chạy batch Reg Gmail (`run_gmail_batch`), PowerShell `run_all.ps1` trả về exit code 1 (`g_code = 1`) nếu có máy dính lỗi nền tảng Google (`phone_verify`, `account_creation_error`).
- Đây là kết quả **bình thường của batch reg** trong thực tế vận hành farm khi tổng số máy đã xử lý `g_tot > 0`.
- **Contract chuẩn**:
  ```python
  gmail_ok = (g_code == 0) or (g_code == 1 and g_tot > 0)
  t2fa_ok = t2fa_code in (0, 4)

  lane_status = "success" if (
      (gmail_ok if args.lane in ("gmail", "all") else True) and
      (t2fa_ok if args.lane in ("tiktok", "all") else True)
  ) else "failed"
  ```

## 3. Cooldown Guard chống Cron Re-trigger
- Bên cạnh `already_ran_today`, watchdog cần có **cooldown guard 45 phút** dựa trên `last_run_at`:
  ```python
  def is_in_cooldown(threshold_minutes: int = 45) -> bool:
      if not STATE_FILE.is_file():
          return False
      try:
          data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
          last_run_str = data.get("last_run_at")
          if not last_run_str:
              return False
          last_run_dt = datetime.fromisoformat(last_run_str)
          now_dt = datetime.now(HCMC)
          elapsed_seconds = (now_dt - last_run_dt).total_seconds()
          return 0 <= elapsed_seconds < (threshold_minutes * 60)
      except Exception:
          return False
  ```
- Bỏ qua cooldown khi có `--force` hoặc `--dry-run`.
- Đảm bảo ngay cả khi batch kết thúc có lỗi thật sự, cron không spam chạy lại chuỗi nặng liên tục mỗi 5 phút.

## 4. Các vị trí file runtime cần đồng bộ
Khi chỉnh sửa `post_noon_chain_watchdog.py`:
1. Repo gốc / test: `D:/Taadaa/Hermes/deploy/hermes-home/scripts/post_noon_chain_watchdog.py`
2. Hermes runtime script: `C:/Users/Kibe/AppData/Local/hermes/scripts/post_noon_chain_watchdog.py`
3. Tools fallback: `D:/Taadaa/tools/post_noon_chain_watchdog.py`
