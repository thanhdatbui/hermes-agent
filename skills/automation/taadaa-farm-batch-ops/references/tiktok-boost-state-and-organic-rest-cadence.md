# Cơ chế Cắn Đề Xuất (BOOST State) & Nhịp Đăng Video Dưỡng Sinh Farm TikTok

## 1. Định nghĩa Chuẩn Về "Dưỡng Sinh" (Organic Rest) vs "Lướt Feed"
- **Lướt feed (Feed Session):** 100% tài khoản khi đến cữ nuôi ĐỀU PHẢI LƯỚT FEED. Lướt feed là nền tảng mặc định cho toàn bộ 80-160 máy trên farm để duy trì trust score, giữ active session và nuôi IP proxy.
- **Dưỡng sinh (Organic Rest):** Là trạng thái phiên nuôi chỉ lướt feed thuần túy:
  $$\text{Dưỡng sinh} = \text{Lướt feed} + (\mathbf{0\ Follow} + \mathbf{0\ Upload})$$
- Mặc định toàn farm: Mỗi nick có xác suất rơi vào ngày nghỉ dưỡng sinh là 1/3:
  $$\text{hash}(\text{ngày}:\text{máy}:\text{row}) \pmod 3 == 0$$

---

## 2. Nhịp Đăng Video Theo Trạng Thái Tài Khoản

| Trạng thái | Điều kiện nhận diện | Nhịp đăng Video | Quy tắc Dưỡng sinh |
| :--- | :--- | :--- | :--- |
| **`NORMAL`** *(Mặc định / Flop)* | Nick mới hoặc view/tim bình thường, chưa có đà tăng trưởng | **2.5 – 3 ngày / video** | **Bật dưỡng sinh 1/3:** Trúng ngày dưỡng sinh thì dừng up và dừng follow để tiết kiệm kho video và dưỡng kênh flop. |
| **`BOOST`** *(Cắn đề xuất)* | $\Delta \text{Follower} \ge 20$ **HOẶC** $\Delta \text{Heart} \ge 50$ **HOẶC** ($\text{Follower} \ge 1000$ & status LIVE). Khóa giữ **5 ngày** (`boost_until`). | **Cố định 48h / video** (2 ngày 1 lần) | **Vẫn lướt feed 100%**, nhưng **GỠ BỎ CẤM UPLOAD** (bypass ngày nghỉ upload) để giữ nhịp đăng liên tục đón sóng view. |

---

## 3. Kiến Trúc Kỹ Thuật (SQLite + Runner)

### Bảng Lưu Trữ SQLite (`D:/Taadaa/data/tiktok_tracker.db`):
```sql
CREATE TABLE IF NOT EXISTS account_boost_state (
    username TEXT PRIMARY KEY,
    machine INTEGER,
    row INTEGER,
    is_boost INTEGER DEFAULT 1,
    boost_since TEXT,
    boost_until TEXT,
    follower_delta INTEGER DEFAULT 0,
    heart_delta INTEGER DEFAULT 0,
    follower_count INTEGER DEFAULT 0,
    heart_count INTEGER DEFAULT 0,
    reason TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_boost_machine_row ON account_boost_state(machine, row);
```

### Module Hỗ Trợ: `python_runner/flows/account_boost.py`
- `update_account_boost_states(db_or_conn, hold_days=5)`: Quét snapshot 7 ngày gần nhất, nhận diện đà tăng và cập nhật `boost_until` giữ 5 ngày. Tự động gọi sau mỗi lần quét daily của `tiktok_account_tracker.py`.
- `is_account_boosted(machine, row, username, db_path)`: Kiểm tra nhanh trạng thái `BOOST` còn hạn với in-memory cache 60s và fail-safe chống treo DB.
- `get_boosted_accounts(db_path)`: Lấy danh sách các tài khoản đang trong diện `BOOST`.

### Điểm Can Thiệp Runner: `multi_machine_feed_session.py`
- Trong hàm `_run_upload_hook`:
  ```python
  if is_organic and not is_boosted:
      payload = {
          "machine": account.machine,
          "row": upload_row,
          "status": "skipped",
          "reason": "organic-rest-day-upload-disabled",
      }
      _write_upload_result(child_ctx, payload)
      return payload
  ```
- Nếu `is_boosted == True`: Runner ghi nhận `child_ctx.config["_is_account_boosted"] = True`, bypass cờ bỏ qua ngày dưỡng sinh và tiếp tục tiến trình upload bình thường.

---

## 4. Kỷ Luật Vận Hành Chống Over-Engineering
1. **Tuyệt đối không dùng "Quarantine bất tử" hay bắt kiểm tra tay:** Video mới đăng 0-view hay ít view là hiện tượng bình thường của thuật toán TikTok (chờ index). Cấm bắt nick dừng đăng và cấm bắt người vận hành kiểm tra tay.
2. **Không khóa 1 chiều phức tạp:** Giữ cơ chế phân loại tự động 100%. Khi hết hạn 5 ngày mà không có thêm đà tăng mới, nick tự động về lại `NORMAL` mà không cần can thiệp thủ công.
3. **Lướt feed là bất biến:** Dù nick ở trạng thái nào, việc mở TikTok lướt feed có tương tác tự nhiên ở đầu phiên nuôi là bắt buộc 100%.
