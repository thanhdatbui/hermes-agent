# Tần Suất Đăng Video & Cơ Chế Dưỡng Sinh (BOOST vs NORMAL) Trên Taadaa Farm

## 1. Bản Chất Cốt Lõi: Lướt Feed vs Dưỡng Sinh (User Invariant)

Tránh hiểu nhầm thuật ngữ (từng xảy ra với các LLM ngoài):
- **Lướt feed (Feed Session)**: Là **nền tảng 100% của farm**. Mọi tài khoản khi đến lượt mở máy trong các ca nuôi ĐỀU PHẢI lướt feed, xem video tự nhiên và thả tim theo tỷ lệ an toàn để nuôi IP proxy và tích lũy Trust Score.
- **Chế độ Dưỡng sinh (Organic Rest 1/3)**: Là thao tác **TẮT ĐĂNG VIDEO + TẮT FOLLOW** trong ngày nuôi đó. Không có nghĩa là tắt lướt feed!

---

## 2. Hai Tầng Nhịp Đăng Video Cho Toàn Farm

Nhằm cân bằng giữa việc đón sóng đề xuất (viral momentum) và tiết kiệm tài nguyên kho video / chống spam, farm áp dụng 2 tầng nhịp:

| Trạng thái | Điều kiện nhận diện | Nhịp đăng Video | Cơ chế Dưỡng sinh Upload |
| :--- | :--- | :--- | :--- |
| **`NORMAL`** *(Nick thường / Flop)* | View/tim bình thường, chưa có đà tăng trưởng | **2.5 – 3 ngày / video** | **Bật dưỡng sinh 1/3** (0 follow + 0 upload) theo hash ngày:máy:row. |
| **`BOOST`** *(Đang cắn đề xuất)* | $\Delta \text{Follower} \ge 20$ HOẶC $\Delta \text{Heart} \ge 50$ (hoặc Follower $\ge 1000$ LIVE) | **Cố định 48h / video** (2 ngày 1 lần) | **GỠ BỎ cấm upload ngày dưỡng sinh** (vẫn lướt feed 100%). |

---

## 3. Cơ Chế Khóa Giữ 5 Ngày (5-Day Hold Window) Chống Flapping

- **Vấn đề "Hôm nay cắn mai mất"**: 
  TikTok phân phối video theo từng đợt sóng (24h - 72h đầu). Nếu chỉ nhìn delta 24h:
  - Ngày 1 tăng $+60$ tim $\to$ bật cờ cắn đề xuất $\to$ ép đăng.
  - Ngày 2 video cũ vẫn có view âm ỉ nhưng delta hạ còn $+20$ tim $\to$ mất cờ $\to$ quay về dưỡng sinh.
  - Ngày 3 bùng tiếp $\to$ lại bật cờ.
  $\implies$ Scheduler bị giật cục liên tục, thuật toán TikTok đánh giá hành vi nick thất thường.
- **Giải pháp**:
  - Khi phát hiện 1 đợt cắn đề xuất $\implies$ Gắn nhãn **`BOOST` và KHÓA GIỮ TỐI THIỂU 5 NGÀY** (`boost_until = event_date + 5 days`).
  - Trong suốt 5 ngày này, nick được phép đăng đều đặn nhịp 48h (trọn vẹn 2–3 video) để đón hết toàn bộ cửa sổ vàng phân phối.
  - Sau 5 ngày nếu không còn tín hiệu mới $\to$ Tự động hạ về `NORMAL`.

---

## 4. Bảng Trạng Thái `account_boost_state` Trong SQLite `tiktok_tracker.db`

- **Đường dẫn**: `D:/Taadaa/data/tiktok_tracker.db`
- **Cấu trúc bảng**:
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
- **Module thực thi (`python_runner/flows/account_boost.py`)**:
  - `update_account_boost_states(db_path, hold_days=5)`: Quét snapshot 7 ngày, tính delta, cập nhật bảng `account_boost_state`.
  - `is_account_boosted(machine, row, username, db_path)`: Kiểm tra nhanh trạng thái BOOST với in-memory cache TTL 60s, fail-safe trả về `False` khi DB bận/lỗi, tuyệt đối không crash runner.
  - Hook tích hợp trong `multi_machine_feed_session.py`:
    ```python
    if is_organic and not is_boosted:
        payload = {"status": "skipped", "reason": "organic-rest-day-upload-disabled"}
    ```
- **Tự động đồng bộ**: Script `D:/Taadaa/tools/tiktok_account_tracker.py` tự động gọi `update_account_boost_states()` sau mỗi lần lưu snapshots vào 07:00 sáng hàng ngày.

---

## 5. Kỷ Luật Điều Phối Subagent (`delegate_task`) Cần Lưu Ý

1. **Gate Multi-file (`[HARD GATE #3 - MULTI-FILE BLOCKED]`)**:
   - Cấm gộp $\ge 2$ file code nghiệp vụ trong 1 task delegate.
   - Bắt buộc chẻ nhỏ: Mỗi task chỉ được sửa đúng **1 file code nghiệp vụ** ($+$ file test tương ứng).
2. **Gate Investigate (`[HARD GATE #3 - INVESTIGATE ROUTE]`)**:
   - Task điều tra / khảo sát bắt buộc phải có câu:
     `BUDGET: <= 5 tool calls, thời gian < 3 phút. Trả về kết luận/anchor rồi THOÁT NGAY` trong `context`.
