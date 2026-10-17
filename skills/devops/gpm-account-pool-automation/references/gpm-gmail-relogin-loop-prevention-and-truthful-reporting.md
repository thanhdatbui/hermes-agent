# Khắc phục lỗi Re-login Vô tận (Infinite Re-login Loop) & Báo cáo Sai số trong GPM Login Watchdog

## 1. Bản chất sự cố (Root Cause)
1. **Lỗ hổng Bypass State trong Candidate Selector:**
   - Khi cron nuôi (`cron_gpm_gmail_nurture.py`) phát hiện mất session cookie Google, nó đánh dấu `status: NEEDS_LOGIN` vào `gpm_gmail_nurture_state.json`.
   - Script login (`post_evening_gpm_login_watchdog.py`) cho phép các tài khoản có `NEEDS_LOGIN` được bypass danh sách đã chạy (`seen_emails`) với cờ `is_relogin = True`.
   - **Lỗi chí mạng:** Sau khi login thành công, script không xóa trạng thái hoặc không đóng dấu ngày phục hồi (`recovered_date`). Cứ mỗi 5 phút cron chạy lại, 5 tài khoản này lại tiếp tục được chọn làm candidate ưu tiên số 1, dẫn đến việc bị login lại 7-9 lần trong một buổi sáng.
2. **Spam nát Proxy 4G:**
   - Script tự cấp cơ chế *"MIỄN TRỪ proxy limit 2/ngày"* cho các acc re-login, làm các port proxy bị băm tới 9 lần/cổng trong 2 tiếng, vi phạm nghiêm trọng ngưỡng an toàn IP.
3. **Báo cáo láo / Văn mẫu bịa đặt:**
   - Báo cáo đếm `processed` bị lặp (5 acc x 9 lần = "✓ 44 acc"), gây hiểu lầm là đã login được 44 tài khoản khác nhau.
   - Báo cáo in cứng câu khẩu hiệu `proxy_limit 2/port/ngày` che mắt trong khi thực tế vi phạm nặng.
   - In dòng văn mẫu bịa đặt: `"• Bỏ qua an toàn: ... acc nhường máy đang bận cron khác (TikTok/Avatar)"` trong khi GPM chạy Chrome trên PC độc lập, không liên quan thiết bị Android farm.

---

## 2. Quy tắc Khắc phục Bắt buộc (Rules of Engagement)

### A. Khóa cứng chốt chặn `seen_emails` tuyệt đối
- Mỗi tài khoản Google/GPM chỉ được phép xử lý **DUY NHẤT 1 LẦN/NGÀY**, kể cả khi tài khoản bị văng session cần re-login:
  ```python
  # CẤM TUYỆT ĐỐI: if (em_l in seen_emails and not is_lost_session) or em_l in excluded_emails: continue
  # BẮT BUỘC:
  if em_l in seen_emails or em_l in excluded_emails:
      continue
  ```

### B. Cắt đứt vòng lặp qua `recovered_date`
- Khi login thành công, bắt buộc ghi nhận dấu mốc ngày:
  ```python
  nurture_data[email]["status"] = "LOGIN_RECOVERED"
  nurture_data[email]["recovered_at"] = datetime.now().isoformat()
  nurture_data[email]["recovered_date"] = datetime.now(HCMC).strftime("%Y-%m-%d")
  ```
- Khi quét `NEEDS_LOGIN` trong candidate selector, nếu `info.get("recovered_date") == today_str`: **Bỏ qua ngay lập tức**.

### C. Khóa trần cứng Proxy 4G (Hủy bỏ cờ "Miễn trừ")
- Tuyệt đối không cho phép miễn trừ proxy limit vô tội vạ.
- Trường hợp re-login khẩn cấp chỉ được phép tối đa `MAX_LOGINS_PER_PROXY + 1` trên cổng đó, vượt quá phải hoãn sang ca/ngày kế tiếp:
  ```python
  if not is_relogin:
      if port and current_run_proxy_count.get(port, 0) >= MAX_LOGINS_PER_PROXY:
          continue
  else:
      if port and current_run_proxy_count.get(port, 0) >= MAX_LOGINS_PER_PROXY + 1:
          log(f"[CANDIDATE-FILTER] {email} skipped: re-login proxy port {port} hit max safety cap")
          continue
  ```

### D. Chuẩn hóa Báo cáo Thực tế (Anti-Fabrication & Anti-Template)
- **Deduplicate danh sách:** Luôn lưu `processed = list(dict.fromkeys(processed))` để số liệu `total_success` là số tài khoản duy nhất (distinct accounts).
- **Phản ánh đúng tải Proxy:** In giá trị cổng cao nhất thực tế (`max_proxy {max_p}/cổng`) thay vì in khẩu hiệu suông.
- **Xóa văn mẫu:** Bỏ triệt để các câu từ bịa đặt "nhường máy TikTok/Avatar". Nếu có acc chưa chạy trong ca do hết worker, báo đúng bản chất: `"• Còn lại trong hàng đợi: X acc chờ ca tiếp theo (tối đa 5 workers/lần)"`.
