# Silent Watchdog Safe Window vs Reporting Gate Contradiction (Deadlock Cửa Sổ Báo Cáo)

Ngày ghi nhận: 20/10/2026.
Phạm vi: Thiết kế logic silent watchdog kết hợp cửa sổ báo cáo định kỳ (periodic summary gate) và cửa sổ an toàn né ca (safe rolling window).

---

## 1. HIỆN TƯỢNG VÀ NGUYÊN NHÂN GỐC RỄ (ROOT CAUSE)

### 1.1 Hiện tượng
Watchdog tự động bật 2FA ban đêm (`cron_night_tiktok_2fa_watchdog.py`) chạy tuần hoàn mỗi 15 phút với `no_agent=True`. Dù batch thực thi vẫn chạy ngầm và xử lý hàng chục thiết bị, watchdog hoàn toàn im lặng trên nhóm Telegram đích (`-5468653590`) trong nhiều ngày liên tiếp.

### 1.2 Hai lỗi thiết kế logic tạo thành Deadlock

1. **Xung đột trực tiếp giữa Cửa Sổ Báo Cáo và Cửa Sổ An Toàn (Window Contradiction):**
   - Script định nghĩa cửa sổ báo cáo 6H:
     ```python
     is_6h_window = (now.hour in (0, 6, 12, 18) and now.minute < 30) or args.force or args.dry_run
     ```
   - Đồng thời, hàm an toàn `is_safe_rolling_window()` chặn chạy script trong 3 ca nuôi:
     - Ca 1: `05:15 - 09:30` (bao gồm toàn bộ giờ 6)
     - Ca 2: `11:45 - 15:30` (bao gồm toàn bộ giờ 12)
     - Ca 3: `17:45 - 21:30` (bao gồm toàn bộ giờ 18)
   - **Hậu quả:** Tại các mốc 6h, 12h, 18h, watchdog bị `is_safe_rolling_window()` chặn ngay tại đầu script (`return 0`). Do đó, **3/4 mốc báo cáo trong ngày (75%) vĩnh viễn không bao giờ có thể chạy hoặc in báo cáo ra stdout!**

2. **Lệch mốc thời gian do giữ biến `now` cũ trước batch dài (Time Skew on Long Batch):**
   - Mốc duy nhất không bị ca nuôi chặn là **00:00 - 00:30**.
   - Biến `now = datetime.now(HCMC)` được gán một lần duy nhất ở đầu hàm `main()`.
   - Nếu cron kích hoạt lúc 23:45, `now.hour = 23` $\rightarrow$ `is_6h_window` là False.
   - Khi batch chạy qua 2 cụm (Kibe 80 máy, Admin 80 máy qua SSH) mất 25–40 phút, script kết thúc lúc 00:15–00:25 nhưng `now` vẫn giữ giá trị cũ (23h) $\rightarrow$ `should_report = False` $\rightarrow$ không in stdout $\rightarrow$ Hermes không gửi tin nhắn.
   - Ngược lại, nếu cron kích hoạt lúc 00:15 và chạy đến 00:45 mới xong, nếu kiểm tra `end_dt.minute < 30` thì cũng bị trôi qua khỏi mốc 30 phút.

3. **Composite Pipeline giao thoa Repo:**
   - Trong các pipeline chuỗi như `post_noon_chain_watchdog.py` chạy lần lượt:
     - Phase 1: `run_gmail_batch` (thuộc repo `register gmail`)
     - Phase 2: `run_tiktok_2fa_batch` (thuộc repo `tiktok-add-bao-mat-f2a`)
   - Việc gán một đích đến duy nhất `deliver: telegram:-5373649734` (Farm Alerts) khiến cả hai nhóm chuyên biệt (`-5139245637` Gmai reg và `-5468653590` Tiktok add 2fa) đều bị thiếu báo cáo.

---

## 2. QUY TẮC CỨNG THIẾT KẾ SILENT WATCHDOG BÁO CÁO (BEST PRACTICES)

### Rule 1: Báo cáo theo sự kiện hoàn tất đợt (Event-Driven Milestone Reporting)
Thay vì trói cứng điều kiện báo cáo vào mốc giờ định kỳ (dễ xung đột với lịch vận hành farm), silent watchdog nên kích hoạt báo cáo khi:
1. Đợt chạy vừa hoàn tất có phát sinh khối lượng công việc mới (`success_count > 0`).
2. Hoặc phát sinh lỗi máy thật cần can thiệp (`failed_count > 0`).
3. Hoặc đợt chạy là mốc chốt ca cuối ngày (`is_final_shift_run`).

### Rule 2: Cập nhật thời gian tươi ngay trước khi đánh giá điều kiện báo cáo
Tuyệt đối không dùng biến `now` ở đầu script để đánh giá điều kiện sau khi một batch dài (từ vài phút đến hàng chục phút) đã hoàn tất:
```python
# SAI:
now = datetime.now(HCMC)
run_heavy_batch()  # Tốn 30 phút
if now.hour in (0, 6, 12, 18) and now.minute < 30:
    print(report)

# ĐÚNG:
run_heavy_batch()
finished_now = datetime.now(HCMC)
# Đánh giá bằng thời gian thực tế lúc hoàn thành
```

### Rule 3: Phân rã luồng Alert cho Pipeline đa Repo
Khi một watchdog chạy nhiều phase liên quan đến nhiều repo khác nhau, script cần:
- Tự động gọi API gửi alert chuyên biệt đến từng nhóm chat tương ứng (`_send_telegram_text(chat_id=REPO_GROUP_ID, ...)`).
- Hoặc tách hẳn các pha thành các cron độc lập trong `jobs.json` để tận dụng cơ chế `deliver` tự nhiên của scheduler.
