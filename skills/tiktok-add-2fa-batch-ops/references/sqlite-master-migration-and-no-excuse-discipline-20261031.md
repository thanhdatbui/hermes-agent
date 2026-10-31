# Chuyển Đổi Dứt Điểm Farm Master Sang SQLite & Kỷ Luật Không Nhận Lỗi Suông (31/10/2026)

## 1. Kỷ Luật Ứng Xử: "Đừng nhận lỗi clg hết, t cần sửa hoặc cơ giới hoá"
- **Triệt tiêu văn phong xin lỗi, nhận khuyết điểm suông:** Khi có trục trặc hoặc user phát hiện điểm thiếu sót, TUYỆT ĐỐI KHÔNG xin lỗi dài dòng, không giải thích lý do cá nhân.
- **Hành động ngay:** Tập trung 100% trí lực vào việc:
  1. Xác định chính xác root cause kỹ thuật.
  2. Viết patch sửa triệt để ngay lập tức.
  3. Cơ giới hóa vào pipeline/gate để lỗi đó không bao giờ lặp lại.

## 2. Di Căn Legacy Excel Sang SQLite Master (`farm_master.db` & `farm_db.py`)
- **Bản chất vấn đề:** Dù Sổ Cái đã chuyển đổi 100% sang `D:/Taadaa/data/farm_master.db`, các repo/script cũ vẫn còn sót rải rác `openpyxl.load_workbook()` gây chậm (1-3s), dễ nghẽn I/O và lệch dữ liệu giữa Excel với SQLite.
- **Quy chuẩn chuyển đổi toàn diện:**
  - **Đọc OTP Hotmail:** Trong `flows/hotmail_login.py`, hàm `_try_read_tiktok_otp_graph()` bắt buộc gọi `farm_db.get_mailbox_credentials(email)` lấy `oauth_refresh_token` & `oauth_client_id` trong 0.01s, chỉ dùng Excel làm fallback cuối.
  - **Đọc Target & Preflight:** Trong `python_runner/core/workbook.py`, các hàm `inspect_target()`, `password_is_blank()`, `read_pass_value()`, `read_email_value()` ưu tiên đọc trực tiếp từ `farm_db.get_account(username)`.
  - **Ghi Kép Đồng Bộ (Write-Through):** Tại hàm `_write_cell()`, sau khi ghi Excel tracking bắt buộc gọi `farm_db.update_tiktok_credentials(username, password=..., twofa_secret=...)` để đồng bộ song song ngay lập tức vào SQLite.
  - **Canary Runner:** `canary_runner.py` nạp tài khoản kiểm chứng qua `farm_db.get_accounts_by_machine(m)` thay vì load workbook.

## 3. Khắc Phục Lỗi Gate B Planner & Canary CLI Mismatch
- **Cơ giới hóa Gate B Planner (`gate_b_planner.py`):**
  - Cắt cứng `TARGET_CONTEXT_LINES = 100` khiến model (Gemini Web) không nhìn thấy các hàm nằm ở dòng sâu (>500-800) $\rightarrow$ sinh ra ảo giác anchor sai $\rightarrow$ `count == 0` bị reject.
  - Giải pháp cơ giới hóa: Nạp toàn bộ file nếu $\le 1.500$ dòng; nếu lớn hơn thì bóc tách từ khóa từ prompt và nạp các cửa sổ $\pm 60$ dòng quanh code thật.
- **Sửa lệch tham số Canary Runner:**
  - `unified_patch_pipeline.py` từng truyền cờ `--device <serial>` (không tồn tại trong `canary_runner.py`).
  - Chuẩn hóa: map `--canary-device auto` sang `--auto-device`, và `--canary-device <N>` sang `["--machine", "<N>"]`.
