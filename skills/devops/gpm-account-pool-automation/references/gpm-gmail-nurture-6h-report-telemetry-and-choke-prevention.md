# GPM Gmail Nurture 6H Report Telemetry & Selection Choke Prevention

Tài liệu chuẩn hóa kỷ luật báo cáo định kỳ 6h nuôi Gmail GPM, chống báo cáo ảo văng cookie (Phantom Cookie-Drop Alert) và giải tỏa bẫy nghẽn vĩnh viễn (Selection Choke) trong luồng nuôi cuốn chiếu.

---

## 1. Bẫy Báo Cáo Ảo Văng Cookie (Phantom Cookie-Drop Alert Trap)

### Hiện tượng thực tế
Báo cáo 6h gửi về Telegram in dòng cảnh báo:
```
• Tổng số profile Group 10 (Google Live Ready): 77
⚠️ Acc phát hiện văng cookie (79 acc, đã đẩy re-login miễn trừ cooldown):
  - quyphuoc090565@gmail.com
  ... và 74 acc khác
```
Nghịch lý toán học: Toàn bộ Group 10 chỉ có 77 profile, nhưng lại báo có tới 79 tài khoản văng cookie!

### Nguyên nhân gốc rễ (Root Cause)
1. **Không lọc theo phạm vi nhóm (Group Scope Blindness):** Script báo cáo duyệt toàn bộ key trong `gpm_gmail_nurture_state.json`. Trong 79 acc bị đếm, có 29 acc thuộc các nhóm cũ/đã xóa từ lịch sử tháng trước, hoàn toàn không nằm trong Group 10.
2. **Không lọc theo cửa sổ thời gian (Window Hours Ignored):** Script gom toàn bộ tài khoản từng bị gán cờ `NEEDS_LOGIN` từ đầu lịch sử (ví dụ từ ngày 08/10) mà không kiểm tra xem sự cố có phát sinh trong 6h qua (`now_ts - last_checked <= 6 * 3600`) hay không. Trong 6h thực tế, 0 acc nào bị văng cookie mới (100% lượt nuôi thành công).
3. **Mất đồng bộ trạng thái thực tế trên đĩa (Disk Cookie Desync):** Nhiều tài khoản đã được watchdog re-login hoặc người dùng đăng nhập thành công (file SQLite cookies trên đĩa có đủ `SID, SSID, HSID, SAPISID >= 2`), nhưng state file chưa được xóa cờ `NEEDS_LOGIN`.

### Chuẩn hóa báo cáo minh bạch (Anti-Hallucination Reporting)
Bắt buộc tách bạch 2 chỉ số độc lập:
1. **Acc mới văng cookie trong 6h qua (`needs_login_recent`):**
   ```python
   # Chỉ tính các profile Group 10 có last_checked trong vòng WINDOW_HOURS
   if status == "NEEDS_LOGIN" and (now_ts - last_checked) <= (WINDOW_HOURS * 3600):
       recent_dropped.append(em)
   ```
   - Nếu bằng 0: In rõ `• Cookie 6h qua: ✓ 100% không có acc mới văng`.
   - Nếu > 0: In cảnh báo đỏ kèm danh sách acc mới bị văng để điều phối.
2. **Tổng số acc đang chờ khôi phục session trong Group 10 (`pending_relogin`):**
   - Chỉ đếm các email thực sự tồn tại trong Group 10 (`GroupId == 10`).
   - Báo cáo rõ: `• Đang chờ re-login (Group 10): X/77 acc (miễn trừ cooldown, ưu tiên ca rảnh)`.

---

## 2. Giải Tỏa Bẫy Nghẽn Tuyển Chọn Vĩnh Viễn (Selection Choke Trap)

### Vấn đề
Trong script nuôi `cron_gpm_gmail_nurture.py`:
```python
# Sai lầm: Bỏ qua vĩnh viễn không bao giờ nuôi lại
for p in candidates:
    em = p["email"]
    info = state.get(em, {})
    if info.get("status") == "NEEDS_LOGIN":
        continue
```
Khi 47-50 tài khoản bị đánh dấu `NEEDS_LOGIN`, chúng bị `continue` vĩnh viễn. Dù 10-15 ngày trôi qua hoặc cookie đã được hồi sinh, các tài khoản này không bao giờ được bốc vào `due_profiles`.

### Giải pháp Cooldown 24h
Áp dụng cooldown 24h tính từ mốc `last_checked`:
```python
if status == "NEEDS_LOGIN":
    last_checked = info.get("last_checked", 0)
    # Trong vòng 24h: Tạm bỏ qua để nhường watchdog login chuyên trách xử lý
    if (now_ts - last_checked) < 86400:
        continue
    # Quá 24h: Cho phép đưa vào due_profiles để kiểm tra lại session
```

---

## 3. Kỷ Luật Đồng Bộ 2 Chiều: Watchdog Login ➔ Nurture State

Khi `post_evening_gpm_login_watchdog.py` thực hiện re-login thành công một tài khoản:
```python
# BẮT BUỘC cập nhật ngay vào gpm_gmail_nurture_state.json
if res.get("status") == "SUCCESS":
    try:
        if NURTURE_STATE.exists():
            n_data = json.loads(NURTURE_STATE.read_text(encoding="utf-8"))
            em_k = email.lower()
            if em_k in n_data and n_data[em_k].get("status") == "NEEDS_LOGIN":
                n_data[em_k]["status"] = "LOGIN_RECOVERED"
                n_data[em_k]["recovered_at"] = datetime.now().isoformat()
                n_data[em_k]["recovered_date"] = datetime.now(HCMC).strftime("%Y-%m-%d")
                NURTURE_STATE.write_text(json.dumps(n_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e_rec:
        log(f"Lỗi cập nhật NURTURE_STATE: {e_rec}")
```
Quy tắc này đảm bảo tài khoản vừa cứu xong sẽ:
1. Được xóa khỏi danh sách cảnh báo văng cookie ở báo cáo 6h tiếp theo.
2. Sẵn sàng cho cron nuôi cuốn chiếu nhận diện `LOGIN_RECOVERED` để chăm sóc duy trì session ấm.
