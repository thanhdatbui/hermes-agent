# Case UI-78: Kiến Trúc Pool Follow Gộp 2 Cụm (Kibe + Admin), Gating & Cơ Chế Xác Thực Nhả Follow

## 1. Bối cảnh & Yêu cầu vận hành (30/09/2026)
- **Vấn đề đặt ra:**
  - Farm vận hành 2 cụm độc lập: Cụm Kibe (Máy 1–80, 638 accounts) và Cụm Admin (Máy 201–280, 613 accounts).
  - Nếu chỉ chạy follow nội bộ trong từng cụm: Cụm Kibe sẽ nhanh chóng bão hòa follow lẫn nhau, tạo thành đồ thị đóng kín (dense closed graph) rất dễ bị TikTok quét pattern bot.
  - Tuy nhiên, nếu gộp chung file Excel vận hành vật lý (`taikhoan_run_safe.xlsx`): Sẽ xảy ra xung đột đồng bộ OneDrive lock (`dwShareMode=0`) và race condition giữa 2 máy chủ.
- **Giải pháp kiến trúc:**
  - **Giữ nguyên 2 sổ cái độc lập:** `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` và `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx`.
  - **View gộp Read-Only:** Tạo file `D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx` (1.251 UIDs) bằng script `D:/Taadaa/tools/sync_combined_safe_workbook.py`.
  - Tự động hook vào cron `taikhoan-run-safe-sync` (`hermes_taikhoan_sync_cron.py`), cập nhật mỗi 5 phút khi có thay đổi.

---

## 2. Các quy tắc Invariant cốt lõi của Follow Pool

### A. Hard Gate Anchor Mode 2 (`1 <= machine <= 80`)
- Trong `follow_engine.py` (`anchor_uids()`):
  ```python
  filtered = [
      u for u in uids
      if row_uids.get(str(u).casefold(), 99) <= 2
      and row_video_counts.get(str(u).casefold(), 0) >= 10
      and 1 <= uid_to_machine.get(str(u).casefold(), 999) <= 80  # Chỉ Tik1/Tik2 Kibe (1-80)
      and str(u).strip().lstrip("@").casefold() != active
  ]
  ```
- **Mục đích:** Chỉ có Tik1 & Tik2 của máy Kibe ($\ge 10$ video) mới được dùng làm Anchor mồi để mở tab Following.
- Toàn bộ 613 nick Admin chỉ tham gia làm Target (được follow) hoặc tham gia bù ở Mode 1, tuyệt đối không bị bốc làm Anchor.

### B. Bộ 4 Lớp Preflight Gates trong Hook Post-Feed (`multi_machine_feed_session.py`)
Trước khi một máy lướt feed xong được phép gọi subprocess `run_follow.py`, bắt buộc vượt qua 4 chốt chặn:

1. **Gate 1 - Trạng thái phiên Feed & Warm Telemetry:**
   - **Lỗi nặng tài khoản (`_SENSITIVE_ACCOUNT_WORDS`):** Gặp `checkpoint`, `banned`, `suspended`, `logged_out`, `logout`, `captcha`, `manual_challenge`, `otp`, `2fa`, `account_locked`, `account_mismatch` $\rightarrow$ **SKIP NGAY** để bảo vệ nick.
   - **Lỗi script / Timeout:** Nếu phiên feed đã lướt được $\ge 3$ video (`completed_swipes >= 3`, Warm Telemetry) HOẶC nick đã có phiên lướt thành công trước đó trong cùng ca (`has_prior_success_in_shift`) $\rightarrow$ **VẪN CHO PHÉP CHẠY FOLLOW HOOK** vì tài khoản đã có hành vi tự nhiên.
2. **Gate 2 - Ngày Dưỡng Sinh Độc Lập (`organic-rest-day-pure-feed`):**
   - Băm MD5: `(int(hashlib.md5(f"{date_str}:{m_num}:{r_num}").hexdigest()[:8], 16) % 3) == 0` (xác suất ~33% ngẫu nhiên).
   - Vào ngày dưỡng sinh: Máy vẫn lướt feed và upload video bình thường, nhưng **TẮT HOÀN TOÀN FOLLOW HOOK** để giữ hành vi tự nhiên.
3. **Gate 3 - Trust Gate Video Count (`under-6-videos-follow-disabled`):**
   - Nick phải có `video_count >= 6`.
   - Nick mới có $< 6$ video (0–5 video) bị cấm đi follow để tránh bị TikTok nhả follow ngay tức thì do trust mỏng.
4. **Gate 4 - Bảo Vệ Nhả Follow & Cooldown (`follow-released-daily-cooldown`):**
   - Nếu nick đang trong thời gian phạt `now_utc < cooldown_until_at` $\rightarrow$ Tự động bỏ qua follow hook (`status: skipped, reason: follow-released-daily-cooldown`).

---

## 3. Thuật Toán Cooldown Nhả Follow & Invariant Lưu Trạng Thái

### A. Thuật toán Progressive Backoff Cooldown (`follow_state.py`)
Khi runner phát hiện TikTok nhả follow (`FOLLOW_FAILED`), hàm `set_follow_failed()` kích hoạt cơ chế giãn cách lũy tiến:
- **Streak 1 (Bị nhả lần đầu trong ngày):** Cooldown đến hết ngày hôm nay (`23:59:59 local`). Sang ca của ngày hôm sau (`00:00:00`), hàm `_check_and_sync_cooldown_expiry()` tự động mở lại.
- **Streak 2 (Bị nhả 2 cữ liên tiếp):** Tự động khóa nghỉ **4 ngày** (`today_end_local + timedelta(days=4)`).
- **Streak $\ge 3$ (Tài khoản yếu, nhả liên tục):** Tự động khóa nghỉ **7 ngày (1 tuần)** (`today_end_local + timedelta(days=7)`).
- **Post-Cooldown Warmup:** Khi mãn hạn cooldown (`is_post_cooldown_warmup`), nick không chạy full quota mà chỉ được cấp quota mồi **3 – 5 follow/phiên** để thăm dò. Nếu chạy êm thì mới xóa chuỗi lỗi (`fail_streak = 0`).

### B. Invariant Deduplication State (Bảo Vệ Không Mất Target Khi Bị Nhả)
- `is_followed(uid)` chỉ đọc trong `self._data["followed"]`.
- Khi follow bị thất bại hoặc bị TikTok nhả:
  - Hệ thống gọi `mark(uid, STATUS_FAILED)`.
  - Dữ liệu chỉ ghi vào `self._data["failed"][uid] = now_iso`, **TUYỆT ĐỐI KHÔNG GHI VÀO `followed`**.
  - **Ý nghĩa:** Nick mục tiêu không bị đánh dấu là "đã follow". Khi tài khoản mãn hạn phạt, nó hoàn toàn có thể được chọn để follow lại bình thường, không bị loại vĩnh viễn.

---

## 4. Chi Tiết Xác Thực Nhả Follow Trên Giao Diện

### A. Mode 2: Mô Phỏng Người Thật Khi Follow Anchor (`_ensure_anchor_followed`)
Trước khi mở tab Following của Anchor, nếu tài khoản hiện tại chưa follow Anchor:
1. **Tìm video:** Quét lưới video trên Profile của Anchor (các node có `cover`, `tv_play_count`, `aweme`).
2. **Xem video (Dwell):** Tap vào cover video đầu tiên, giữ xem ngẫu nhiên **8.0 đến 15.0 giây** (`dwell = random.uniform(8.0, 15.0)`).
3. **Thả tim ngẫu nhiên:** Xác suất **65%** tìm nút Like (`content-desc="thích"` hoặc `like_icon`) để tap.
4. **Tap Follow:** Bấm nút Follow trên video overlay (dấu `+` đỏ bên cạnh avatar hoặc content-desc `Follow`).
5. **Chờ máy chủ:** Chờ **2.0 đến 4.0 giây** để server TikTok đồng bộ.
6. **Back & Vuốt Reload (Bust Optimistic UI Cache):** Bấm Back về Profile Anchor $\rightarrow$ Thực hiện **Kéo vuốt làm mới trang Profile (`pull_to_refresh_profile`, sleep 3.5s)**.
7. **Đọc trạng thái thật:** Nếu sau khi vuốt reload mà nút quan hệ bị nhảy ngược về `Follow` đỏ $\rightarrow$ Báo lỗi `FOLLOW_FAILED: anchor @... bị nhả sau vuốt — dừng session` và đưa nick vào Cooldown ngay.

### B. Mode 2: Quy Trình Path B Verify & Back Về Danh Sách Following (`_path_b_verify`)
1. Từ danh sách Following của Anchor, tap username node của nick con $\rightarrow$ Vào Profile nick con.
2. Kiểm tra quan hệ trên Profile (xác nhận nút chuyển thành `Đã follow`/`Bạn bè`/`Nhắn tin`).
3. Gọi `adapter.back()` quay lại danh sách Following.
4. **Restore Verification:** Dump lại UI để kiểm tra `_on_follower_list`.
5. **Anti-Drop Back Recovery:** Nếu bị rớt lệnh back (màn hình vẫn ở Profile nick con), runner tự tìm nút Back icon góc trên bên trái (`_find_top_left_back_button`) để bấm lại. Nếu vẫn không phục hồi được danh sách Following, dừng ngay với `MANUAL_REVIEW` để bảo vệ vị trí màn hình.

### C. Mode 1: Xác Thực Nhả Follow Qua Search (`verify_after_tap` & `_reload_profile`)
1. Search UID $\rightarrow$ Mở Profile mục tiêu $\rightarrow$ Dwell 6.0 – 12.0s $\rightarrow$ Tap Follow.
2. Khi nút đổi sang trạng thái thành công lần 1, runner **KHÔNG TIN NGAY** vì TikTok có cơ chế Optimistic UI (hiển thị thành công cục bộ trước khi server từ chối).
3. Runner gọi `_reload_profile(engine, uid)` theo cơ chế phối hợp tự nhiên:
   - **80% trường hợp:** Kéo vuốt làm mới Profile tại chỗ (Pull-to-refresh có jitter, sleep 3.0 – 4.5s).
   - **20% trường hợp:** Bấm Back ra màn hình Search results rồi tap lại vào card nick để Re-entry.
4. Kiểm tra nút quan hệ sau khi reload:
   - Nếu VẪN LÀ `Đã follow` / `Nhắn tin` $\rightarrow$ Ghi nhận `SUCCESS`.
   - Nếu BỊ TRẢ LẠI thành `Follow` / `Follow lại` $\rightarrow$ Báo `FOLLOW_FAILED: follow bị nhả sau re-entry — dừng session`.

---

## 5. Lệnh kiểm tra và đối soát vận hành nhanh (Operational Auditing)

### Kiểm tra phân bổ Follow Kibe vs Admin qua State:
```bash
python -c "
import glob, json, openpyxl

wb = openpyxl.load_workbook('D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx', read_only=True)
kibe_uids = {str(r[2]).strip().lower() for r in wb.active.iter_rows(values_only=True) if r and len(r)>=3 and r[0] and int(r[0])<=80}
admin_uids = {str(r[2]).strip().lower() for r in wb.active.iter_rows(values_only=True) if r and len(r)>=3 and r[0] and int(r[0])>80}

state_files = glob.glob('D:/Taadaa/tiktok-follow/runs/state/follow_state_*.json')
k_cnt, a_cnt = 0, 0
for sf in state_files:
    try:
        with open(sf, 'r', encoding='utf-8') as f:
            for uid in json.load(f).get('followed', {}).keys():
                u = uid.strip().lower()
                if u in kibe_uids: k_cnt += 1
                elif u in admin_uids: a_cnt += 1
    except: pass
print(f'Followed: Kibe={k_cnt}, Admin={a_cnt}')
"
```

### Kiểm tra Breakdown trạng thái phiên chạy gần nhất trên toàn fleet:
```bash
python -c "
import glob, json
files = glob.glob(r'D:\Taadaa\runtime\kibe\live\*\row-*\*\machines\machine_*\*\follow_result.json')
reasons = {}
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fp:
            d = json.load(fp)
            k = f\"{d.get('status')}: {d.get('reason', '')}\"
            reasons[k] = reasons.get(k, 0) + 1
    except: pass
for k, v in sorted(reasons.items()):
    print(f'{k} -> {v}')
"
```

### Kiểm tra phân bố chuỗi lỗi `fail_streak` và các nick đang trong Cooldown:
```bash
python -c "
import glob, json
files = glob.glob('D:/Taadaa/tiktok-follow/runs/state/follow_state_*.json')
streaks = {}
in_cd = 0
for f in files:
    with open(f, 'r', encoding='utf-8') as fp:
        d = json.load(fp)
        s = d.get('fail_streak', 0)
        streaks[s] = streaks.get(s, 0) + 1
        if d.get('follow_failed'):
            in_cd += 1
print('Fail streaks:', sorted(streaks.items()))
print(f'Total accounts currently in cooldown: {in_cd}')
"
```
