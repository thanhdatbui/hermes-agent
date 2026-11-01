# Triage & Reconciliation: Lệch Chỉ Số Following Giữa Bot vs Web Trên TikTok Farm Dashboard

## 1. Bối Cảnh Hiện Trường
Trên giao diện **TikTok Farm Dashboard** (`tiktok_dashboard.py`), thẻ KPI **👥 Tổng Đã Follow (Following)** hiển thị dòng đối soát:
- `📊 Đối soát hôm qua: Bot +A ➔ Web Tổng tăng: +B`
- `⚡ Tiến độ hôm nay: Bot +X lượt (Web Tổng tăng: +Y)`

Khi $X \neq Y$, người dùng thường yêu cầu điều tra nguyên nhân lệch giữa số liệu Bot ghi nhận và số liệu Web cào được.

---

## 2. Kiến Trúc Dữ Liệu & Nguồn Gốc 2 Chỉ Số

### A. Chỉ Số "Bot +X lượt"
- **Nguồn:** Bảng `session_action_stats` trong SQLite `D:/Taadaa/data/tiktok_tracker.db`.
- **Cơ chế ghi:** Cuối mỗi phiên nuôi/follow chéo (Ca 1/2/3, Phiên 1/2), script `feed_session_watchdog.py` thu thập số lượt click follow thành công từ các máy trong cụm và ghi vào:
  ```sql
  SELECT COALESCE(SUM(internal_follows), 0)
  FROM session_action_stats
  WHERE target_date = 'YYYY-MM-DD'
  ```
- **Ý nghĩa:** Tổng số lượt action follow mà bot đã thi công trong các phiên có watchdog ghi nhận ngày hôm đó.

### B. Chỉ Số "Web Tổng tăng: +Y"
- **Nguồn:** Bảng `snapshots` trong SQLite `D:/Taadaa/data/tiktok_tracker.db` kết hợp `daily_account_actions`.
- **Cơ chế tính trong `dashboard/queries.py` (`get_farm_data`):**
  1. `snapshots` lưu lịch sử cào thông số thực tế từ web/API TikTok của các nick theo từng thời điểm.
  2. Hệ thống tính `delta_following = following_hiện_tại - following_ngày_hôm_trước`.
  3. Lọc danh sách tài khoản có `internal_followed > 0` trong bảng `daily_account_actions` của ngày hôm đó:
  ```python
  if has_active_follow:
      if internal_followed > 0:
          total_delta_following += delta_following
  ```
- **Ý nghĩa:** Tổng mức tăng following thực tế trên profile TikTok của các tài khoản có phát sinh hoạt động follow hôm nay.

---

## 3. Các Nguyên Nhân Cốt Lõi Gây Lệch (Root Causes)

1. **Lệch Lệch Cửa Sổ Thời Gian (Time Window Drift & Off-Shift Runs):**
   - Tài khoản phát sinh follow ngoài ca nuôi chính thức (ví dụ: ca chạy đêm, bù rạng sáng trong `follow_state_<may>_row_<tik>.json`).
   - Các lượt này làm tăng following thực tế trên web TikTok. Khi scraper cào `snapshots` ca sáng, số Following đã tăng từ trước.
   - Nhưng `session_action_stats` chỉ tính các lượt được bàn giao trong các phiên chạy ban ngày của watchdog $\rightarrow$ **Web tăng nhiều hơn Bot**.

2. **Lỗi Lọc / Bị TikTok Nhả Follow (Shadow Unfollow / Verification Lag / Anchor Rollback):**
   - Bot bấm nút Follow thành công trên app và ghi nhận +1 vào state.
   - Khi dính lỗi anchor rollback (`FOLLOW_FAILED: anchor @... bị nhả sau vuốt — dừng session`), lượt bấm follow trước đó bị TikTok shadow-revert hoặc không cộng vào profile. 
   - **Cạm bẫy code cũ trong `feed_session_watchdog.py`:**
     Code cũ viết `reset = failed and cnt == 0`, tức chỉ reset về 0 khi máy fail ngay lượt đầu. Nếu máy đã follow 1 nick (`cnt = 1`) rồi mới phát hiện anchor bị nhả, code vẫn đếm `m_to_reported = cnt` (+1) ➔ Bot ghi nhận +1 nhưng Web Following delta = 0 ➔ Lệch -1 lượt.
   - **Quy chuẩn sửa đúng (Fix Invariant):**
     Bắt buộc sửa thành:
     ```python
     reset = failed
     m_to_reported[str(m)] = natural_cnt if reset else cnt + natural_cnt
     ```
     Khi `failed is True` (bị nhả follow), toàn bộ lượt follow chéo `cnt` trong phiên đều bị hủy bỏ khỏi `m_to_reported`, chỉ giữ `natural_cnt` (nếu có).

3. **Đứt Gãy Tiến Trình Tổng Nuốt Chửng Kết Quả Follow (Parent Session Crash / Truncation Trap):**
   - Phiên chạy tổng (`multi_machine_feed_session.py`) gặp sự cố dừng đột ngột (thiếu file `summary.txt` và `run_manifest.json` ở root folder `row-X-HHMMSS`).
   - Mặc dù tiến trình con trên máy (`run_follow.py --machine M`) đã kịp bấm follow thật trên TikTok và ghi vào file state `follow_state_M_row_R.json`, nhưng do tiến trình mẹ bị đứt, stdout không được thu hoạch để ghi file `follow_result.json` vào thư mục máy.
   - Watchdog quét thư mục không tìm thấy `follow_result.json` nên ghi nhận `0 lượt` cho toàn bộ phiên đó vào `session_action_stats`.
   - Kết quả: Web scraper đọc trực tiếp trên TikTok profile thấy Following tăng vọt, trong khi Bot bị mất trắng số liệu của phiên bị đứt $\rightarrow$ **Web tăng nhiều hơn Bot (+N lượt)**.

---

## 4. Kỷ Luật Phản Hồi: Không Dừng Lại Ở Số Liệu Khơi Khơi
Khi User yêu cầu điều tra lệch số liệu ("Sao lệch", "Điều tra kĩ cho tao", "Thì điều tra lí do lỗi đi"):
- **CẤM** chỉ dừng lại ở việc báo cáo: "Nick A web tăng X, bot tăng Y". Đó chỉ là bề nổi của hiện tượng!
- **BẮT BUỘC** phải đào sâu xuống tận tầng tiến trình: Kiểm tra thư mục runtime `D:/Taadaa/runtime/<cluster>/live/<date>/row-*`, xác minh sự tồn tại của `summary.txt`, `log.jsonl`, `follow_result.json`, và đối soát log `follow_state_*.json` để chỉ ra chính xác phiên nào bị đứt gãy hoặc nick nào bị TikTok nhả anchor.

---

## 5. Quy Trình Triage O(1) Để Tìm Đúng Nick Lệch

Khi nhận yêu cầu điều tra, Coordinator BẮT BUỘC thực hiện truy vấn bóc tách O(1) theo các bước:

### Bước 1: Đối soát tổng hợp theo từng tài khoản qua Python/SQLite
```python
import sys
sys.path.insert(0, r"D:/Taadaa/tools")
from dashboard.queries import get_farm_data

data = get_farm_data(r"D:/Taadaa/data/tiktok_tracker.db")
items = data["items"]

print(f"{'Username':<20} | {'May':<4} | {'Tik':<4} | {'DeltaWeb':<8} | {'BotInt':<8} | {'Diff':<6}")
for it in items:
    df = it.get("delta_following", 0)
    int_fl = it.get("internal_followed", 0)
    if df != int_fl:
        print(f"{it['username']:<20} | {str(it.get('may')):<4} | {str(it.get('tik')):<4} | {df:<8} | {int_fl:<8} | {df - int_fl:<+6}")
```

### Bước 2: Kiểm tra lịch sử snapshot của các nick bị lệch
```sql
SELECT timestamp, following
FROM snapshots
WHERE username = '<outlier_username>'
ORDER BY timestamp DESC LIMIT 10;
```

### Bước 3: Kiểm tra timestamp từng lượt follow trong file state máy
Đọc file `D:/Taadaa/tiktok-follow/runs/state/follow_state_<may>_row_<tik>.json`:
Trích xuất `followed` dictionary để xem chính xác các mốc giờ UTC/VN mà máy đã bấm follow. So khớp timestamp bấm máy với các mốc giờ lưu `session_action_stats` để chứng minh lượt follow phát sinh ở phiên nào.
