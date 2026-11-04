# Case Study: Phục Hồi 9/10 Hotmail ChatGPT Pool & Bẫy Fail-Closed Proxy Port Desync

## 1. Hiện Tượng & Diễn Biến Thực Tế
Trong phiên vận hành ngày 04/11/2026:
- Script `cron_auto_feed_chatgpt_pool.py` trước đây gặp hiện tượng bế tắc 0/10 do bốc 10 Gmail cũ văng Auth Google.
- Sau khi đổi thứ tự ưu tiên sang Hotmail (`cand_h + cand_g`) và nạp cơ chế Rolling Cooldown 12h:
  - 5 worker GPMLogin đồng loạt mở 10 profile Hotmail lên `chatgpt.com`.
  - Kết quả bóc cookie session thành công rực rỡ: **9/10 tài khoản Hotmail lấy được session-token hợp lệ** (độ dài 6.800 - 10.300 chars).
  - Duy nhất 1 tài khoản thất bại do văng Auth được đưa vào cooldown 12h và báo cáo Telegram.

## 2. Bẫy Nguy Hiểm: Fail-Closed Proxy Port Desync
Tuy nhiên, khi hàm `sync_to_omniroute()` chạy, cả 9 tài khoản vừa cứu thành công suýt chút nữa **bị bỏ qua sạch sẽ (0 account được nạp vào OmniRoute)** vì một lỗi khởi tạo ngớ ngẩn:
```python
# Trong rescue_single_account(acc):
email = acc["email"]
pid = acc["pid"]
port = acc.get("port")
res = {"email": email, "pid": pid, "success": False, "token_len": 0, "screenshot": None, "error": None}
# THIẾU KHỞI TẠO trường "port": port vào dict res!
```
- Khi chạy tới `sync_to_omniroute(results)`:
  ```python
  port = r.get("port")
  if not port:
      logger.error(f"[SKIP FAIL-CLOSED] {email}: không có port trong kết quả -> không bật is_active")
      continue
  ```
- **Hậu quả:** Dù bóc được token xịn nhưng do dict trả về không mang theo `port`, cơ chế fail-closed của database chặn không lưu.
- **Bài học khắc phục:**
  - Bắt buộc phải gắn đầy đủ metadata nguồn (`port`, `host`, `pid`, `proxy_id`) xuyên suốt từ lúc bốc ứng viên đến lúc trả kết quả của worker.
  - Sau khi sửa `res["port"] = port`, 9/10 tài khoản lập tức được ghi nhận vào `provider_connections` của OmniRoute (`storage.sqlite`) với `is_active=1, test_status='active'`.
