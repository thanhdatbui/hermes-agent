# SQLite Master DAL OTP Resolution & Gate B Context Invariants (31/10/2026)

## 1. Kỷ Luật Cơ Giới Hoá Thay Thế Lời Nhận Lỗi (Anti-Apology Invariant)
- **Tuyệt đối cấm dài dòng nhận lỗi / giải thích thanh minh:** Khi gặp trục trặc hoặc bị nhắc nhở ("Đừng có nhận lỗi clg hết t cần sửa hoặc cơ giới hoá"), Coordinator BẮT BUỘC bỏ qua mọi văn mẫu xin lỗi hay phân bua, tập trung 100% vào việc:
  1. Phân tích nguyên nhân kỹ thuật tận gốc (root cause).
  2. Sửa code hoặc cơ giới hóa dứt điểm cơ chế (patch ngay trong pipeline / script).
  3. Báo cáo bằng số liệu và kết quả thực thi kiểm chứng thật.

---

## 2. Toàn Diện SQLite Master DAL — Cấm Tái Lập Đọc Excel (`farm_db.py`)
- **Dữ liệu farm đã chuyển dịch 100% sang SQLite:**
  Mọi thông tin tài khoản (TikTok, Hotmail/Mailbox, Machine, Proxy, Token Graph API) đều nằm tập trung tại `D:/Taadaa/data/farm_master.db`.
- **Cấm tuyệt đối dùng `openpyxl` / đọc file Excel:**
  * Mọi luồng đọc OTP Graph API (`_try_read_tiktok_otp_graph` trong `flows/hotmail_login.py`), lấy thông tin tài khoản theo máy (`canary_runner.py`), đối soát token hoặc mật khẩu: BẮT BUỘC gọi qua DAL `D:/Taadaa/tools/farm_db.py`:
    ```python
    from farm_db import get_mailbox_credentials, get_accounts_by_machine, get_account
    # Trả về tức thì O(1) oauth_refresh_token, oauth_client_id, password
    cred = get_mailbox_credentials(email)
    ```
  * Không dùng `openpyxl.load_workbook()` trên các file Excel cũ (`gmail_clean_v2.xlsx`, `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`) để tránh kẹt I/O, lock file và lệch đồng bộ giữa các cụm.

---

## 3. Ngữ Cảnh Code Cho Gate B Planner (`gate_b_planner.py`)
- **Vấn đề đã khắc phục:** Cắt cứng 100 dòng hay 800 dòng đầu file khiến các file dài (>800 dòng như `live_phase_b_adapter.py`) bị mất đoạn hàm mục tiêu (ví dụ `ensure_account_password_saved()` ở dòng 807). Hệ quả là `gemini-web` không thấy code thật, tự suy diễn và sinh `old_string` ảo giác.
- **Chuẩn nạp context:**
  * File $\le 1.500$ dòng: BẮT BUỘC nạp toàn bộ file code thật.
  * File monolith $> 1.500$ dòng: Trích xuất 200 dòng đầu kết hợp các cửa sổ $\pm 60$ dòng quanh các keyword/function name bóc tách từ task prompt, giúp `gemini-web` nhìn thấy chính xác anchor thật (`count == 1`).

---

## 4. Chuẩn Lệnh Canary Runner & Pipeline CLI
- `canary_runner.py` chỉ chấp nhận cờ:
  * `--machine <N>`: Cho test hotfix đơn máy.
  * `--auto-device`: Tự chọn máy rảnh an toàn ngoài khung ca nuôi.
  * `--dry-run`: Chạy kiểm tra focused test offline không chiếm máy thật.
- Trong `unified_patch_pipeline.py`, cấm truyền cờ `--device`; bắt buộc map `--canary-device auto` sang `--auto-device` và `--canary-device <N>` sang `["--machine", str(N)]`.
