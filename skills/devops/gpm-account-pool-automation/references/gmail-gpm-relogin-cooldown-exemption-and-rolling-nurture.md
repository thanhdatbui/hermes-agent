# Gmail GPM Re-login Proxy Cooldown Exemption & Rolling Nurture Protocol

## 1. Quy tắc Phân Định Cooldown Proxy 24h: Acc Mới vs Acc Bị Văng (Re-login)

> 📌 **Chỉ thị vận hành bất biến từ User:**  
> *"Log in acc bị văng thì k tính cooldown 24h. Chỉ acc mới log lên ms bị tính."*

### 1.1. Acc mới tạo / Login lần đầu lên GPM
- **Định nghĩa:** Tài khoản chưa từng đăng nhập trên GPM, hoặc profile mới tạo chưa từng lưu Google session thành công.
- **Ràng buộc:** BẮT BUỘC áp trần nghiêm ngặt **tối đa 2 tài khoản / port proxy / ngày** (cooldown 24h giữa các mẻ mới trên cùng một cổng proxy).
- **Mục đích:** Bảo vệ dải IP 4G của farm khỏi danh sách đen (Blacklist / Sentinel) của Google khi phát hiện nhiều danh tính đăng nhập mới từ cùng một endpoint.

### 1.2. Acc cũ bị văng session (Re-login / Refresh Cookie)
- **Định nghĩa:** Tài khoản đã có sẵn profile GPM, đã gán cổng proxy cố định 1:1, nhưng bị hết hạn cookie hoặc bị Google bắt đăng nhập lại (`status: NEEDS_LOGIN`).
- **Quy tắc:** **MIỄN TRỪ HOÀN TOÀN COOLDOWN 24H**.
- **Thực thi:** Cho phép đăng nhập lại ngay lập tức mà không phải chờ 24h, nhằm khôi phục cookie sống cho Group 10 (`Google_Live_Ready`) và cung cấp session cho các downstream pool (ChatGPT-Web, Codex, OAuth).

### 1.3. Cảnh Báo Chí Mạng: Bẫy Vòng Lặp Re-login Vô Tận (Infinite Re-login Loop Trap)
- **Sai lầm ngộ nhận chết người:** Nhầm lẫn giữa "Miễn trừ cooldown 24h" với việc "Cho phép bypass `seen_emails` trên mọi tick cron (5 phút/lần)".
- **Hiện tượng thực tế từng xảy ra:**
  - Cron nuôi đánh dấu acc là `NEEDS_LOGIN`.
  - Cron login thấy `is_relogin` liền cho bypass `seen_emails` liên tục mỗi 5 phút, đè đúng 5 tài khoản ra login lặp lại 7–9 lần trong một ca sáng, băm nát cổng proxy 4G (đạt 9 lượt/cổng thay vì trần 2 lượt).
  - Báo cáo tổng kết đếm cộng dồn thành "✓ 44" (ảo), in khẩu hiệu "proxy_limit 2/port/ngày" (dối trá) và bịa ra lý do "nhường máy TikTok/Avatar" (gây bức xúc cực độ cho User).
- **Quy tắc Bất Biến khắc phục:**
  1. **Khóa cứng `seen_emails` theo ngày:** Bất kể acc mới hay acc re-login, một khi đã chạy trong ngày (thành công hoặc thất bại) BẮT BUỘC ghi vào `seen_emails` và cấm chạy lại ở các tick kế tiếp trong cùng ngày (`if em_l in seen_emails or em_l in excluded_emails: continue`).
  2. **Ghi nhận `recovered_date`:** Khi login thành công, cập nhật ngay `recovered_date = today_str` vào `gpm_gmail_nurture_state.json`. Hàm bốc candidate phải loại bỏ các acc có `recovered_date == today_str`.
  3. **Trần an toàn proxy cho Re-login:** Re-login chỉ được phép tối đa `MAX_LOGINS_PER_PROXY + 1` trên cổng đó. Vượt quá lập tức skip để bảo vệ IP 4G, cấm miễn trừ vô tội vạ.
  4. **Kỷ luật báo cáo trung thực (Anti-Hallucination Reporting):**
     - Luôn deduplicate `processed`: chỉ báo cáo số tài khoản duy nhất thực tế (`len(set(processed))`).
     - Báo cáo chỉ số proxy thực tế (`max_proxy {max_p}/cổng`), cấm in khẩu hiệu tĩnh che mắt.
     - CẤM TUYỆT ĐỐI văn mẫu bịa đặt đổ lỗi cho thiết bị khác ("nhường máy TikTok/Avatar" trong khi GPM chạy PC). Nếu còn acc chờ thì ghi đúng: *"Còn lại trong hàng đợi: X acc chờ ca tiếp theo"*.

### 1.4. Mẫu Code Chuẩn Cho Chốt Chặn Re-login & Báo Cáo Không Bịa Đặt
```python
# 1. Chốt chặn candidate: không cho phép bất kỳ email nào chạy lặp lại trong ngày
if em_l in seen_emails or em_l in excluded_emails:
    continue

# 2. Hard cap proxy cho re-login (tối đa limit + 1)
if is_relogin:
    if port and current_run_proxy_count.get(port, 0) >= MAX_LOGINS_PER_PROXY + 1:
        continue
    current_run_proxy_count[port] = current_run_proxy_count.get(port, 0) + 1

# 3. Đánh dấu recovered_date tránh cron nuôi đánh dấu NEEDS_LOGIN lại ngay
if email in nurture_data and nurture_data[email].get("status") == "NEEDS_LOGIN":
    nurture_data[email]["status"] = "LOGIN_RECOVERED"
    nurture_data[email]["recovered_at"] = datetime.now().isoformat()
    nurture_data[email]["recovered_date"] = datetime.now(HCMC).strftime("%Y-%m-%d")

# 4. Báo cáo trung thực: Distinct accounts, real max proxy, không văn mẫu
max_p = max(proxy_count.values()) if proxy_count else 0
lines = [
    f"[LOGIN GPM {shift_label} - TỔNG KẾT]",
    f"• Kết quả ca: ✓ {total_success} | ✗ {total_fail} | max_proxy {max_p}/cổng | Hoàn tất ca {shift_desc}",
]
if skipped_busy > 0:
    lines.append(f"• Còn lại trong hàng đợi: {skipped_busy} acc chờ ca tiếp theo (tối đa {MAX_WORKERS} workers/lần)")
```

### 1.5. Hai Cạm Bẫy Logic Giờ Giấc & Điều Kiện Ca Chạy (Shift & Is_Late Pitfalls)
1. **Lỗi lọt ranh giới thời gian `is_late` (Compound Hour/Minute Bug):**
   - *Viết sai:* `hour >= 11 and minute >= 15`. Khi đồng hồ điểm `12:05`, điều kiện này trả về `False` vì `5 < 15`, khiến watchdog tưởng ca sáng chưa hết giờ và tiếp tục chờ!
   - *Viết đúng:* Bắt buộc dùng `hour > 11 or (hour == 11 and minute >= 15)` cho mốc `11:15` (tương tự cho `17:15` và `23:30`).
2. **Lỗi lệch tập hợp ca (Set Parity Drift):**
   - Khi hệ thống đã chuyển từ ca `TRƯA` sang ca `CHIỀU`, toàn bộ các nhánh kiểm tra hoàn tất cả ngày BẮT BUỘC đồng nhất dùng `{"SANG", "CHIEU", "TOI"}`. Nếu sót lại `{"SANG", "TRUA", "TOI"}` thì cờ `all_day_finished` không bao giờ đạt `True`.
3. **Cạm bẫy Unit Test dữ liệu tĩnh (Synthetic Assertion Trap):**
   - Đừng chỉ viết test assert trên một dict tự tạo (`{"status": "LOGIN_RECOVERED"}`). Test có giá trị cao nhất phải gọi trực tiếp `get_candidates()` với file state thật/mocked để chứng minh:
     - Account có `recovered_date == today_str` bị bỏ qua.
     - Account đã nằm trong `seen_emails` bị bỏ qua 100%.
     - Account re-login bị chặn khi cổng proxy chạm trần `MAX_LOGINS_PER_PROXY + 1`.

---

## 2. Kiến Trúc Nuôi Cuốn Chiếu (Rolling Concurrency = 5)

### 2.1. Hạn chế của mô hình nuôi theo mẻ ngắt quãng (Periodic Batch)
- Mô hình cũ chạy `--concurrency 2 --limit 6` mỗi giờ 1 lần (`0 * * * *`) khiến 77+ tài khoản mất nhiều ngày mới quay vòng xong một lượt, đồng thời tài nguyên RAM/CPU bị bỏ phí giữa các khung giờ rảnh.

### 2.2. Chuẩn hóa Worker Pool 5 Profiles Cuốn Chiếu
- **Độ rộng song song:** Duy trì đồng thời tối đa **5 profile GPM** (`concurrency = 5`).
- **Khởi động so le (Staggered Launch):** Giãn cách 30s giữa các lượt mở profile để tránh nghẽn cổng CDP 19995 và sốc CPU.
- **Cơ chế cuốn chiếu (Rolling Queue):**
  1. Profile A hoàn thành kịch bản nuôi (xem YouTube 90-120s hoặc Google News/Search 45-60s).
  2. Đóng trình duyệt (`Context.close()`, `Browser.close()`, GPM stop API).
  3. Kiểm tra dọn dẹp triệt để tiến trình Chrome zombie qua `psutil`.
  4. Ngay lập tức bốc Profile B trong danh sách Group 10 vào thế chỗ.
- **Độ phủ & Nhịp độ chuẩn hóa (User Approved):**
  * **Chu kỳ giãn cách profile (NURTURE_INTERVAL_SECONDS):** **2 ngày (48 giờ)** thay vì 5 ngày (120h là quá lâu khiến session nguội và Google tự thu hồi cookie; 1 ngày là quá dày gây pattern máy móc và hao data 4G).
  * **Trần an toàn nuôi hàng ngày (MAX_DAILY_NURTURE):** Giới hạn tối đa **25 – 30 profile / ngày** để bảo vệ băng thông data proxy 4G (tránh nghẽn làm drop điện thoại S7 đang chạy TikTok/Upload) và giải phóng RAM/CPU máy chủ.
  * Với kho ~77 profile Group 10, nhịp độ 30 acc/ngày sẽ xoay vòng trọn vẹn 100% kho sau đúng 2.5 – 3 ngày.

---

## 3. Kỷ Luật Báo Cáo: Silent Hàng Giờ vs Tổng Kết Mỗi 6H

### 3.1. Silent Watchdog hàng giờ (Chống Spam Telegram)
- Cron nuôi chạy hàng giờ hoặc liên tục **CẤM in stdout** khi vận hành bình thường.
- Tuyệt đối không gửi tin nhắn báo *"Hoàn tất nuôi X/Y profiles"* mỗi giờ lên kênh Telegram của User (tránh bão 24 tin/ngày làm loãng thông điệp).
- Mọi chỉ số được ghi âm thầm vào `LOG_FILE` và telemetry JSON trên đĩa.

### 3.2. Báo cáo gộp định kỳ mỗi 6h (`00:00, 06:00, 12:00, 18:00`)
- Tích hợp số liệu nuôi vào bản tin báo cáo định kỳ 6h (`cron_gmail_gpm_2fa_6h_report`):
  - Tổng số lượt tương tác thành công / thất bại trong 6h qua.
  - Tỷ lệ phân bổ hành vi: YouTube vs Google News/Search.
  - Danh sách tài khoản phát hiện văng session (`NEEDS_LOGIN`) để bàn giao cho ca login xử lý.
- **Alert khẩn cấp:** CHỈ bắn tin cảnh báo ngay lập tức khi phát hiện proxy toàn farm sập hoặc tiến trình Chromium bị treo hàng loạt.
