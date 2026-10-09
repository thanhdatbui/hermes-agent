# Cơ Chế Tăng Tần Suất Đăng Cho Nick Cắn Đề Xuất (BOOST) & Bypass Dưỡng Sinh

## 1. Bản Chất "Dưỡng Sinh" (Organic Rest) vs "Lướt Feed"
- **Lướt Feed (100%):** Mọi nick khi đến phiên nuôi **BẮT BUỘC ĐỀU LƯỚT FEED** để giữ Trust Score và nuôi IP proxy.
- **Dưỡng Sinh (1/3 ngày):** `= Lướt feed + (0 Follow + 0 Upload)`.
- Xác định theo công thức hash ngày/máy/row: `(int(hashlib.md5(f"{date_str}:{m}:{r}").hexdigest()[:8], 16) % 3) == 0`.

---

## 2. Quy Tắc Tần Suất Đăng Video (Posting Cadence)
- **Nick Thường / Flop (`NORMAL`):** 
  - Giữ nguyên ngày nghỉ upload 1/3.
  - Nhịp đăng tự nhiên giãn ra **2.5 – 3 ngày / video** (tiết kiệm tài nguyên render và kho video, không nhồi video cho kênh flop).
- **Nick Đang Cắn Đề Xuất (`BOOST`):** 
  - **Gỡ bỏ lệnh cấm upload ngày dưỡng sinh!**
  - Đăng cố định **48h / lần (2 ngày 1 video)** liên tục theo sóng đề xuất của TikTok.

---

## 3. Cơ Chế Nhận Diện & Khóa Giữ Trạng Thái (Hold Window 5 Ngày)
- **Tiêu chí Trending:** 
  $$\Delta \text{Follower} \ge 20 \quad \mathbf{HOẶC} \quad \Delta \text{Heart} \ge 50 \quad \mathbf{HOẶC} \quad (\text{Follower} \ge 1000 \;\mathbf{VÀ}\; \text{LIVE})$$
- **Bẫy Flapping ("Hôm nay cắn mai mất"):** 
  - Video viral phân phối theo chu kỳ 3–5 ngày. Nếu dùng delta 24h làm công tắc ON/OFF thì lịch đăng bị giật cục.
  - Giải pháp: Khóa giữ trạng thái `BOOST` trong **5 ngày liên tiếp** (`boost_until = event_date + 5 days at 23:59:59`).
- **Bảng lưu trữ SQLite:** `account_boost_state` trong `D:/Taadaa/data/tiktok_tracker.db` với index `(machine, row)`.

---

## 4. Kiến Trúc Thực Thi Trong Code
- **Module quản lý:** `python_runner/flows/account_boost.py`:
  - `update_account_boost_states(db_or_conn, hold_days=5)`: Quét snapshots 7 ngày gần nhất, gom group theo ngày, tính delta và upsert vào `account_boost_state`.
  - `is_account_boosted(machine, row, username)`: Tra cứu nhanh với thread-safe in-memory cache TTL 60s, fail-safe trả về `False` khi DB bận.
- **Điểm tích hợp Hook Upload:** `python_runner/flows/multi_machine_feed_session.py`:
  - Trong `_run_upload_hook`: nếu `is_account_boosted` trả về `True` $\rightarrow$ set `_is_account_boosted = True`, ghi log telemetry `organic_rest_upload_permitted`, và **bỏ qua rào cản `is_organic`** để tiếp tục tiến trình upload preflight.
- **Tự động làm mới:** `D:/Taadaa/tools/tiktok_account_tracker.py` sau khi lưu snapshots lúc 07:00 sáng tự động gọi `update_account_boost_states`.

---

## 5. Closeout Gate & Test Execution Pitfalls
- **Import file mismatch:** Khi repo có cả `tests/test_<stem>.py` và `test_<stem>.py`, pytest sẽ báo lỗi import mismatch. Closeout Gate phải ưu tiên file trong `tests/` và loại bỏ file trùng tên ở root.
- **Tránh chạy test suite Monolithic:** Với các file flow lớn như `multi_machine_feed_session.py` có 110+ tests chạy > 120s gây timeout, Closeout Gate cần cấu hình chạy các companion tests tập trung (`test_organic_rest_upload_gate.py`, `test_account_boost.py`) < 30s.
