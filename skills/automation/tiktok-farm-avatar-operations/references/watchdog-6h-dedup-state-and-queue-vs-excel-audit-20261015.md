# Watchdog 6H Dedup State Key Mismatch & Queue vs Excel Discrepancy Audit

## 1. Sự cố Spam Báo Cáo 6H do Lệch State Key (State Key Mismatch)

### Hiện tượng & Triệu chứng
- Cron watchdog chạy tần suất cao (ví dụ `*/5 * * * *` cho `post_evening_avatar_watchdog.py` hoặc `*/15 * * * *` cho `cron_night_tiktok_2fa_watchdog.py`).
- Trong khung giờ báo cáo 6H (`00:00, 06:00, 12:00, 18:00` với `now.minute < 30`), hàm `is_after_evening_window` hoặc `is_6h_window` trả về `True`.
- Thay vì chỉ gửi 1 tin nhắn duy nhất, watchdog bắn liên tục 6 tin nhắn (mỗi 5 phút 1 lần) trong suốt 30 phút.

### Nguyên nhân gốc rễ
- **Lệch Key kiểm tra và Key ghi lại**:
  - Đoạn kiểm tra trùng lặp đọc key:
    ```python
    if not all_done and state.get("last_reported_6h") == sess_key:
        return
    ```
  - Nhưng sau khi gửi báo cáo, hàm lưu state lại chỉ ghi:
    ```python
    state["last_reported_session"] = sess_key
    state["last_reported_date"] = sess_key
    # QUÊN GHI: state["last_reported_6h"] = sess_key
    ```
  - Kết quả là `state.get("last_reported_6h")` luôn trả về `None`, vô hiệu hóa hoàn toàn cơ chế chặn trùng lặp.

### Quy tắc Chuẩn Hóa
1. **Ghi đồng bộ (Multi-key Write-Through):** Luôn ghi đồng thời cả 3 key để đảm bảo tương thích ngược:
   ```python
   state["last_reported_6h"] = sess_key
   state["last_reported_session"] = sess_key
   state["last_reported_date"] = sess_key
   if all_done:
       state["last_reported_all_done"] = True
   ```
2. **Kiểm tra đa tầng (Defensive Preflight Check):**
   ```python
   if not all_done and (
       state.get("last_reported_6h") == sess_key
       or state.get("last_reported_session") == sess_key
       or state.get("last_reported_date") == sess_key
   ):
       return
   ```
3. **Áp dụng cho mọi script có chế độ báo cáo 6H:** Bao gồm cả watchdog 2FA đêm (`cron_night_tiktok_2fa_watchdog.py`) và watchdog avatar.

---

## 2. Bẫy Đối Soát: Hàng Đợi SQLite `avatar_replace_queue` vs Sổ Cái Excel `Tik1..8.xlsx`

### Hiện tượng
- Báo cáo 6H hiển thị một máy (ví dụ Máy 213 trên Admin) xuất hiện ở cả 8 Tik trong danh sách chưa up avatar.
- Coordinator vội vàng kết luận máy bị hỏng trắng cả 8 nick hoặc rớt mạng gây lỗi 8 acc.

### Thực tế Kỹ thuật (Ground Truth Triage)
1. **Quy tắc ưu tiên của hàm `get_tik_avatar_stats`:**
   ```python
   # SQLite query join:
   LEFT JOIN avatar_replace_queue q ON m.username = q.username AND m.may = q.may AND m.tik = q.tik

   # Phân loại trạng thái:
   if queue_status == "PENDING":
       unuploaded.append(may)
   elif queue_status == "DONE":
       uploaded_count += 1
   elif has_avatar == 1:
       uploaded_count += 1
   else:
       unuploaded.append(may)
   ```
   - Cờ `queue_status == 'PENDING'` có độ ưu tiên cao hơn `has_avatar == 1`.
   - Nếu trong `avatar_replace_queue`, nick bị gán `PENDING` (chưa chạy runner hoặc runner thất bại), máy sẽ bị liệt kê vào `unuploaded` dù nick trên TikTok đã có avatar hoặc trên Excel đã ghi `Avatar = OK`.

2. **Quy trình đối soát 3 lớp bắt buộc khi phân tích Farm Report:**
   - **Lớp 1 (Sổ cái Excel):** Đọc cột `Avatar` trong `admin/Tik1..Tik8.xlsx` hoặc `kibe/Tik1..Tik8.xlsx`. (Ví dụ M213 đã có `OK` ở Tik 1, Tik 2, Tik 8).
   - **Lớp 2 (Hàng đợi DB `avatar_replace_queue`):** Kiểm tra `status` và `last_error` của từng Tik slot để biết chính xác nick nào đang kẹt thật sự và nguyên nhân lỗi (ví dụ M213 vướng Switcher / Open TikTok từ sáng).
   - **Lớp 3 (Trạng thái phần cứng ADB):** Kiểm tra danh sách `attached devices` để phân biệt rõ máy đang online (bị kẹt phần mềm, có thể auto-retry) vs máy offline vật lý (rớt cáp, cần can thiệp phần cứng).
