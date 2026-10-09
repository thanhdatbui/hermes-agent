# Case UI-98: Mode 2 Anchor Mining Min-Following Gate & Single-Source Quota Lock

## Bối cảnh & Hiện tượng (Symptom)
Trong các phiên chạy Follow của farm, nhiều máy (như M17, M18, M23) kết thúc phiên chỉ follow được rất ít nick (2-8 nick/phiên) dù cấu hình budget là 10-20.
Khi soi log Module 2 (`mode2_follow_followers.py`), Module 2 kết thúc sớm chỉ sau đúng 2 lượt follow và nhường cho Module 1, hoặc dừng hẳn phiên.

## Nguyên nhân gốc rễ (Root Cause)

### 1. Nghịch lý "Mỏ rỗng" trong hàm chọn Anchor (`anchor_uids`)
- **Thiết kế ban đầu:** Anchor Mode 2 chỉ chọn các nick Tik1/Tik2 (hàng 1-2 trên máy 1-80) và có `video_count >= 10`. Giả định rằng nick cội rễ lâu năm sẽ có danh sách Following dày đặc để bot đào mỏ follow chéo nội bộ.
- **Thực tế cơ sở dữ liệu:** Trong 145 nick Tik1/Tik2 đạt tiêu chuẩn video, có tới **47 nick có Following < 10** (nhiều nick chỉ có 0, 1, 3, 4 following do reg tự động nhưng chưa được phân phối follow sâu).
- **Hệ quả runtime:** Khi bot chọn trúng Anchor có 0-4 following:
  1. Bot bấm follow bản thân Anchor đó (tính được 1 follow).
  2. Bot mở tab "Đang follow" của Anchor ra: Tab trống hoặc chỉ có 1-2 nick đã follow từ trước.
  3. Cuộn 5 lần không thấy ai mới (`idle_scrolls >= 5`) -> Thoát Anchor.
  4. Duyệt qua 2-3 Anchor rỗng -> Mode 2 dừng lại với vỏn vẹn 2 lượt follow (chính là 2 lượt bấm vào bản thân 2 cái Anchor).

### 2. Quota bị re-roll ngẫu nhiên giữa chừng
- `FollowEngine`, `mode2_follow_followers`, và `mode1_search_follow` đều gọi độc lập `state.session_budget()`.
- Hàm này sinh số ngẫu nhiên `_random.randint(min, max)` mỗi lần gọi. Khi Mode 2 chuyển giao cho Mode 1 bù quota, việc re-roll làm lệch pha budget phiên, khiến Mode 1 tính sai số lượng cần bù.

## Giải pháp chuẩn hóa (Pattern & Patch)

### 1. Min-Following Gate trên Anchor Selection & Telemetry Hardening
Trong `follow_engine.py::anchor_uids()`:
- **Đường dẫn DB linh hoạt:** Không hardcode tuyệt đối. Ưu tiên `os.environ.get("TIKTOK_TRACKER_DB")` -> `cfg.tracker_db_path` -> fallback `D:/Taadaa/data/tiktok_tracker.db`. Kiểm tra `Path(_db_path).exists()` trước khi kết nối để an toàn trên các môi trường CI/test/khác.
- **SQLite URI an toàn:** Đọc snapshot mới nhất qua SQLite URI read-only (`mode=ro`, timeout ngắn <= 3.0s), dùng `COALESCE(following, 0)` để xử lý triệt để giá trị NULL.
- **Ngưỡng lọc:** Lọc bỏ mọi Anchor có `following < MIN_ANCHOR_FOLLOWING` (ngưỡng chuẩn: `30`).
- **Telemetry định lượng (Audit & Observability):** Ghi nhận chi tiết vào `self._last_anchor_telemetry` và log cụ thể từng lý do bị loại: `excluded_active`, `excluded_not_tik12`, `excluded_machine`, `excluded_low_videos`, `excluded_low_following`, `tracker_db_active`.
- **Fallback an toàn:** Nếu DB bị thiếu, lock hoặc hỏng file, log cảnh báo và fallback graceful sang danh sách Tik1/Tik2 theo video count (không làm sập engine).
- **Kết quả:** Từ 144 anchor lẫn nhiều mỏ rỗng -> tinh lọc còn 82 anchor chất lượng cao (100% có `following >= 30`), đảm bảo Mode 2 luôn khai thác được 8-15 nick mỗi phiên.

### 2. Single-Source Session Budget Locking
Trên `FollowEngine`:
- Bổ sung `effective_session_budget()`: Tính toán quota ngẫu nhiên đúng **1 lần duy nhất** ở đầu phiên, cache vào `_effective_session_budget`.
- Cả Mode 2 và Mode 1 đều đọc qua method này để đảm bảo đồng nhất 100% quota xuyên suốt vòng đời session.
- Mode 1 bù chính xác: `rem_budget = effective_session_budget() - len(res.followed)`.
- Giảm `reserve_seconds` từ 180s xuống 90s khi check deadline trong Mode 1 để tránh dừng sớm khi còn đủ thời gian follow bù.
