# Chống Vòng Lặp Re-login Vô Tận & Bảo Đảm Tính Toàn Vẹn Của Telemetry / Báo Cáo GPM

## 1. Sự Cố Kinh Điển (Case 2026-10-17: Infinite Re-login & Fabricated Report)

### Hiện tượng
- Báo cáo gửi Telegram:
  ```text
  [LOGIN GPM SÁNG - TỔNG KẾT]
  • Kết quả ca: ✓ 44 | ✗ 1 | proxy_limit 2/port/ngày | Hoàn tất ca sáng
  • Bỏ qua an toàn: 32 acc nhường máy đang bận cron khác (TikTok/Avatar)
  • Antigravity Pool: 122 accounts LIVE trên OmniRoute (:20129)
  • Profile sẵn Google Session chờ OAuth: 68 accounts
  ```
- **Thực tế hiện trường sau khi đối soát:**
  1. Chỉ có đúng 9 tài khoản được xử lý trong ca.
  2. 5 tài khoản bị lôi ra re-login liên tục từ 7 đến 9 lần (laphuong13081998, dinhlan24072000, lelinh09111997, ninhy05102002, minhan2745).
  3. Proxy port của 5 tài khoản này (20004, 20007, 20008, 20009, 20003) bị spam tới 7 - 9 lần/sáng, vi phạm nghiêm trọng hạn mức 2 logins/cổng/ngày.
  4. Số liệu "✓ 44" bị ảo do phép cộng dồn không deduplicate `processed`.
  5. Dòng "Bỏ qua an toàn: 32 acc nhường máy đang bận cron khác (TikTok/Avatar)" là văn mẫu ngụy biện bịa đặt (GPM chạy Chrome độc lập trên PC, không dính dáng thiết bị phone farm S7).

---

## 2. Nguyên Nhân Gốc Rễ Trong State Machine

1. **Bypass Lỏng Lẻo Trong Bộ Lọc Candidates:**
   ```python
   # LỖI CŨ:
   is_lost_session = (em_l in nurture_needs_login)
   if (em_l in seen_emails and not is_lost_session) or em_l in excluded_emails:
       continue
   ```
   Khi cron nuôi GPM phát hiện mất cookie session, nó ghi `NEEDS_LOGIN` vào `gpm_gmail_nurture_state.json`. Watchdog login đọc trạng thái này và cho phép bypass `seen_emails`. Vì cron chạy mỗi 5 phút, nó liên tục bốc lại các tài khoản này trên MỌI tick.

2. **Miễn Trừ Proxy Limit Vô Tội Vạ:**
   ```python
   # LỖI CŨ:
   if not is_relogin:
       if port and current_run_proxy_count.get(port, 0) >= MAX_LOGINS_PER_PROXY:
           continue
   else:
       # MIỄN TRỪ proxy limit -> băm nát cổng 4G
   ```

3. **Thiếu Khóa Thời Gian Phục Hồi (`recovered_date`):**
   Sau khi `run_login` thành công, script không đánh dấu ngày phục hồi vào `nurture_state`. Đến tick kế tiếp, cron nuôi chưa kịp chạy xác thực cookie mới, trạng thái trong file vẫn là `NEEDS_LOGIN` -> tiếp tục tạo vòng lặp.

---

## 3. Quy Tắc Vận Hành Bắt Buộc (Invariants)

### Rule 1: Khóa Cứng `seen_emails` Theo Ngày (Hard 1-Login-Per-Day Cap)
- Mỗi tài khoản Gmail chỉ được phép login tối đa **1 LẦN / NGÀY**, bất kể là tài khoản mới hay tài khoản bị mất session cần re-login:
  ```python
  # CHUẨN HÓA:
  if em_l in seen_emails or em_l in excluded_emails:
      continue
  ```
- Nếu tài khoản cần cứu session nhưng đã chạy hôm nay -> BẮT BUỘC chờ sang ngày hôm sau hoặc chờ ca nuôi tiếp theo xác nhận lại cookie, tuyệt đối không bypass `seen_emails` trong cùng ngày.

### Rule 2: Trần An Toàn Cứng Cho Proxy (Re-login Safety Cap)
- Tuyệt đối CẤM miễn trừ proxy limit vô giới hạn.
- Re-login chỉ được phép vượt tối đa +1 so với hạn mức thường:
  ```python
  if is_relogin:
      if port and current_run_proxy_count.get(port, 0) >= MAX_LOGINS_PER_PROXY + 1:
          continue
  ```
- Mọi lần re-login đều BẮT BUỘC ghi nhận vào `proxy_count[port]` để bảo vệ IP 4G.

### Rule 3: Đóng Dấu `recovered_date` Ngay Khi Cứu Phiên Thành Công
- Khi login thành công, cập nhật lập tức vào `NURTURE_STATE`:
  ```python
  nurture_data[email]["status"] = "LOGIN_RECOVERED"
  nurture_data[email]["recovered_at"] = datetime.now().isoformat()
  nurture_data[email]["recovered_date"] = datetime.now(HCMC).strftime("%Y-%m-%d")
  ```
- Hàm `get_candidates` BẮT BUỘC bỏ qua bất kỳ tài khoản nào đã có `recovered_date == today_str`.

### Rule 4: Tuyệt Đối Cấm Văn Mẫu Bịa Đặt & Chế Số Liệu (Anti-Hallucinated Reporting)
1. **Deduplicate Danh Sách:**
   `state["processed"] = list(dict.fromkeys(processed))`
   Số lượng thành công / thất bại phải phản ánh số tài khoản DUY NHẤT (distinct accounts), cấm cộng dồn số lượt lặp.
2. **In Metric Thực Tế:**
   In đúng số lượt tối đa trên một cổng (`max_proxy {max_p}/cổng` lấy từ `max(proxy_count.values())`) thay vì in khẩu hiệu tĩnh `proxy_limit 2/port/ngày`.
3. **Cấm Viện Cớ Sai Ngữ Cảnh:**
   GPM là tác vụ PC Browser. CẤM TUYỆT ĐỐI in các câu chữ ngụy biện như "nhường máy bận cron khác (TikTok/Avatar)". Nếu có tài khoản chưa chạy do hết slot worker, in rõ ràng: `Còn lại trong hàng đợi: X acc chờ ca tiếp theo (tối đa N workers/lần)`.
