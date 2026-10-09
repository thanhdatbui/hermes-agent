# Kỷ Luật Điều Phối Đa Cron & Báo Cáo "Bỏ Qua An Toàn" Khi Nhường Tài Nguyên Trên Phone Farm

> 📌 **Chỉ thị cốt lõi của User:**  
> *"Cập nhật báo cáo đó cho all script khi phải nhường cho cron khác đi"*  
> *"Và các cron khi chạy đã lock lại tránh cron khác phá chưa. Và report có báo cáo kiểu bị skip vì cron khác k"*

---

## 1. Cơ Chế Khóa Thiết Bị 2 Tầng Chống Tranh Chấp Giữa Các Cron (Two-Tier Fleet Mutex)

Trên Farm có hàng chục cron chạy song song và cuốn chiếu (`post-evening-gpm-login-watchdog`, `post-noon-chain-watchdog`, `post-evening-avatar-watchdog`, `tiktok-runner`, `cron_clear_tiktok_cache`). Nếu không có khóa độc quyền, hai tiến trình cùng gõ lệnh ADB lên 1 điện thoại Galaxy S7 sẽ làm đứt phiên nuôi TikTok, văng tài khoản hoặc lỗi cấp OTP.

### Tầng 1: Khóa Độc Quyền Thiết Bị (Device Lock Lease)
- Mọi thao tác can thiệp thiết bị bắt buộc bọc trong `acquire_device_lock` từ `automation_core.device_lock`:
  ```python
  from automation_core.device_lock import acquire_device_lock

  with acquire_device_lock(machine=str(mid), serial=serial, project="gpm-login"):
      # Thực thi tác vụ can thiệp phần cứng ADB
      ...
  ```
- Thư viện tự động tạo file khóa tại `~/.codex/device-locks/machine_{mid}.{serial}.lock.json` ghi nhận: `pid`, `host`, `project`, `started_at`, `status: running`.
- Các cron khác trước khi bốc máy M phải kiểm tra thư mục lock (`LOCK_DIR` và `CODEX_LOCK_DIR`): nếu máy đang có trạng thái `active / running / queued / blocked` thì **lập tức bỏ qua, tuyệt đối không tranh chấp hay force-preempt mù quáng**.
- Watchdog `reap-dead-owner-locks` chạy mỗi 5 phút để thu hồi các lock mồ côi nếu tiến trình trước đó bị crash/kill bất ngờ.

### Tầng 2: Vùng Đệm Lịch Nuôi TikTok (Manifest Schedule Buffer)
- Nuôi TikTok Feed là **nhiệm vụ ưu tiên cao nhất của Farm**. Các tác vụ phụ trợ (Login GPM, Up Avatar, Đổi pass, Bật 2FA) bắt buộc phải né xa giờ nuôi.
- Trước khi khởi động worker phụ trợ, script gọi `is_machine_idle(mid)` đối soát file `assignment-v1-*.json` trong `D:/Taadaa/runtime/kibe/cron-state/manifests/`:
  ```python
  def is_machine_idle(mid: int) -> bool:
      # 1. Kiểm tra device locks hiện hữu
      if any(f.endswith(".lock.json") and f"machine_{mid}." in f for f in os.listdir(LOCK_DIR)):
          return False
      # 2. Kiểm tra slot manifest nuôi TikTok
      for e in manifest_entries:
          if e.get("machine") == mid:
              st = datetime.fromisoformat(e["slot_time"])
              et = datetime.fromisoformat(e["slot_end"])
              # Đang trong ca HOẶC cách ca tiếp theo < 10 phút
              if (st <= now < et) or (now <= st < now + timedelta(minutes=10)):
                  return False
      return True
  ```

---

## 2. Tối Ưu Lịch Cron Theo 2 Khoảng Rảnh Vàng Của Phone Farm

### Lịch Nuôi TikTok Feed (Cao điểm bận 100%):
- **Ca 1 (Sáng):** 06:00 – 09:25
- **Ca 2 (Trưa):** 11:35 – 15:25 (đợt 1: 11:35–13:25, đợt 2: 13:10–15:25)
- **Ca 3 (Tối):** 17:35 – 21:25

### 2 Khoảng Rảnh Vàng Bắt Buộc Khai Thác:
1. 🌅 **Khoảng Rảnh Vàng 1 (Sau Ca 1):** `09:30 – 11:20` (~2 tiếng cả Farm rảnh 100%).
2. ☀️ **Khoảng Rảnh Vàng 2 (Sau Ca 2):** `15:30 – 17:20` (~2 tiếng cả Farm rảnh 100%).
3. 🌙 **Khung Đêm (Sau Ca 3):** `21:30 – 23:45` (Toàn bộ 78 máy S7 kết thúc nuôi TikTok).

> ⚠️ **CẤM KỴ:** Tuyệt đối không xếp cron phụ trợ vào các khung `07:15–08:45` hay `12:00–13:45`. Vào các giờ này 100% máy báo bận (`idle=False`), candidates bị dồn ứ đến cuối ca chạm mốc `is_late` và bị hủy bỏ (force close), gây ảo giác cron bị liệt.

---

## 3. Tiêu Chuẩn Báo Cáo Bắt Buộc: Hiển Thị "Bỏ Qua An Toàn"

Khi một watchdog kết thúc ca hoặc hoàn tất chu kỳ chạy, **báo cáo gửi về Telegram BẮT BUỘC phải phân tách rạch ròi 3 cột số liệu**:

```text
[BÁO CÁO WATCHDOG TỔNG KẾT]
• Đã hoàn tất: X máy / accounts
• Bỏ qua an toàn: Y máy (nhường cron khác / lịch nuôi TikTok / lock đang chạy)
• Lỗi thực tế: Z máy (phân loại rõ Lỗi nền tảng vs Lỗi script)
```

### Quy Tắc Triển Khai Cho Từng Script:
1. **`post_evening_gpm_login_watchdog.py`**:
   - Khi `candidates` còn tồn đọng nhưng máy bận do TikTok hoặc avatar, truyền `skipped_busy` vào template báo cáo:
     `• Bỏ qua an toàn: {skipped_busy} acc nhường máy đang bận cron khác (TikTok/Avatar)`
   - Cấm im lặng thoát khi `total_success == 0` nếu có candidate bị hoãn vì nhường máy.

2. **`post_morning_gmail_2fa_watchdog.py`**:
   - Máy vướng `active_locks` hoặc `busy_feed` được gom vào `skipped_busy_machines`:
     `- Bỏ qua an toàn (N máy nhường cron khác): Mxx (nhường lịch nuôi TikTok / lock tiến trình khác)`

3. **`post_noon_chain_watchdog.py`**:
   - Tách biệt máy hoàn tất vs máy bỏ qua an toàn:
     `• Đã hoàn tất: N máy`
     `• Bỏ qua an toàn: M máy (đầy slot / nhường cron khác)`

4. **`post_evening_avatar_watchdog.py`**:
   - Trong `session_lines` của báo cáo ca tối, nếu còn máy chưa up do hết ca hoặc vướng lock:
     `• Bỏ qua an toàn: {tot_miss} máy (nhường lịch nuôi TikTok / lock tiến trình khác)`

5. **`cron_clear_tiktok_cache.py`**:
   - Máy bị `[LOCKED]` không được nuốt chửng hay tính vào lỗi, phải in dòng riêng:
     `• Bỏ qua an toàn: N máy (nhường lock tiến trình khác)`

---

## 4. Kỷ Luật Phòng Tránh State Bị Đóng Băng Qua Ngày (Date Drift Guard)

- Trong các cron feeder/reporter (`cron_gpm_oauth_full_pool.py`, `cron_gpm_oauth_pool_6h_report.py`):
- Khi chuyển sang ngày mới (`data.get("date") != today`):
  1. **Khởi tạo state mới và GHI NGAY XUỐNG ĐĨA:** Cấm chỉ reset trong RAM rồi `return 0` khi pool cạn ứng viên. Phải gọi `save_daily_state(new_state)` ngay lập tức.
  2. **Safe Date Guard khi đọc file báo cáo:** Script báo cáo BẮT BUỘC kiểm tra `state.get("date") == today`. Nếu khác ngày thì `used_proxies = {}` và `success_today = []`. Tránh hoàn toàn việc in lại số liệu ngày cũ nhiều ngày liên tiếp.
