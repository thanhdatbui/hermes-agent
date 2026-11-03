# SQLite SSOT Dual-Cluster Isolation & 2FA Recovery (2026-11-03)

## 1. Căn Nguyên Sự Cố 2FA Ban Đêm (126 Lỗi)
- **POST_SUCCESS_VERIFICATION_FAILED (69 máy Admin):**
  - Worker `--password-only` không mở TikTok/điều hướng nhưng in `status: success`; Parent runner hậu kiểm thấy mật khẩu trên workbook Excel vẫn rỗng nên đánh fail giả tạo.
- **WorkbookError (43 máy Kibe):**
  - Hàm `freeze_targets_from_sqlite()` nạp toàn bộ danh bạ không lọc cụm (lấy cả máy $\ge 200$) và đồng nhất sai `a.rowid` SQLite với số dòng Excel $\rightarrow$ `SOURCE_ROW_IDENTITY_MISMATCH_USERNAME`.

---

## 2. Giải Pháp Chuẩn Hóa Kiến Trúc
1. **Phân Vùng Cụm Máy Tuyệt Đối (Zero Overlap):**
   - Kibe quản lý máy $1 - 80$ ($640$ nick).
   - Admin quản lý máy $201 - 280$ ($640$ nick).
   - `freeze_targets_from_sqlite()` lọc cứng dải máy theo tham số `is_admin`.
2. **Loại Bỏ Phụ Thuộc Excel Trong Verification:**
   - Hậu kiểm 2FA đọc trực tiếp trên `farm_master.db` SQLite SSOT.
   - Chấp nhận `target.blank_pass = True` là hợp lệ, không ép kiểm tra mật khẩu đối với tài khoản chỉ cần bật 2FA.
3. **Fail-Safe Fallback:**
   - Trong `run_batch_live_2fa.py`, nếu file SQLite bị lỗi hoặc chưa sẵn sàng, runner tự động bắt ngoại lệ `(sqlite3.Error, OSError, WorkbookError)` và fallback an toàn sang `freeze_targets()` từ workbook mà không văng crash.

---

## 3. Quy Chuẩn Cơ Học Về Timeout (Gate G15)
- CẤM TUYỆT ĐỐI Coordinator truyền cờ `timeout < 300` khi gọi Advisor / Planner / Pipeline.
- Toàn bộ hằng số trong `gate_b_planner.py` và `consult_advisor.py` bắt buộc neo cứng $\ge 300\text{s}$.
