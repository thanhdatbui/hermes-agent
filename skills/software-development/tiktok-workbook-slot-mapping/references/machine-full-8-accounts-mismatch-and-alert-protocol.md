# Incident & Invariant: Machine Full 8 Accounts Mismatch & Alert Telegram Protocol (2026-09-21)

## Bối cảnh & Hiện tượng (Incident Context)
Khi chạy Preflight Reg bù tài khoản TikTok theo ca (ví dụ `ensure_row_accounts.py 7`), một số máy (như M27, M37) liên tục báo lỗi:
`[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`

## Nguyên nhân gốc rễ (Root Cause)
1. **App TikTok đã đạt trần 8 tài khoản**:
   - Trên thiết bị thật, app TikTok đã lưu đủ 8 tài khoản (trần tối đa của ứng dụng). Do đó, TikTok ẩn hoàn toàn nút "Thêm tài khoản" trong dropdown switcher.
2. **Lệch pha dữ liệu Excel (Data Drift / Phantom Empty Slot)**:
   - Dù trên thiết bị đã đủ 8 nick, file Excel tracking (`taikhoan_dat_v2_updated .xlsx`) vẫn còn dòng trống (do đợt reg trước bị ghi đè nhầm hàng, hoặc chưa backfill nick cũ vào).
   - Bộ chọn target (`_detect_clean.py`) chỉ đọc Excel thấy thiếu slot nên tiếp tục cử máy đi reg.
3. **Bẫy Obfuscated Resource-ID mới của TikTok**:
   - TikTok cập nhật phiên bản mới đổi resource-id avatar/node trong switcher sang `ndk` (thay vì các ID cũ như `n72`, `lkp`, `l9b`...).
   - Script không đếm được node `ndk`, tưởng app chưa đủ 8 nick nên tiếp tục tìm nút "Thêm tài khoản" và văng `RuntimeError`.
4. **Báo cáo Telegram mơ hồ khiến User hiểu lầm**:
   - Trước đây `_extract_reg_error` chỉ bốc dòng lỗi chung chung `Không tìm thấy: ('Thêm tài khoản'...)`, làm User tưởng app bị lag giao diện hoặc mạng chậm thay vì nhận ra app đã đủ 8 acc.

---

## 3 Quy tắc Bất biến Bắt buộc (Mandatory Invariants)

### 1. Invariant 1: Nhận diện trần 8 Acc & Tự động kết thúc an toàn (`social_reg_v1.py`)
- Trong `tap_add_account`, trước khi tìm nút "Thêm tài khoản", BẮT BUỘC đếm số lượng node tài khoản trong dropdown (bao gồm cả resource-id `ndk`):
  ```python
  _acc_count = sum(
      1 for _n in _root.iter("node")
      if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
  )
  if _acc_count >= 8:
      log(f"   [04_add_account] Máy đã có {_acc_count} tài khoản — đạt giới hạn tối đa 8")
      keyevent(device_id, 4, wait=D_SHORT)  # dismiss dropdown
      keyevent(device_id, 3, wait=0.5)      # go home
      raise RuntimeError("[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok")
  ```

### 2. Invariant 2: Báo động đích danh Lệch Excel về Telegram (`ensure_row_accounts.py`)
- Khi bắt được mã lỗi `MACHINE_FULL_8_ACCOUNTS`, hàm `_extract_reg_error` BẮT BUỘC parse và trả về chuỗi cảnh báo đỏ trực tiếp gửi về Telegram cho User:
  `"Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)"`
- CẤM để lỗi này trôi qua như một lỗi UI thông thường. User nhìn thấy cảnh báo này sẽ lập tức đối soát lại Excel để backfill nick cũ, triệt tiêu nguy cơ reg đè.

### 3. Invariant 3: Hard Guard chống ghi đè tài sản (`deferred_tracking_writer.py` & `social_reg_v1.py`)
- Điều kiện chặn ghi đè chuẩn:
  ```python
  if (existing_id or existing_pass) and (not existing_mail or existing_mail != new_mail):
      # BẮT BUỘC CHẶN GHI ĐÈ TUYỆT ĐỐI (FAIL-CLOSED)
  ```
- Nếu hàng đã có ID hoặc Pass, mà email cũ trống HOẶC email cũ khác email mới $\rightarrow$ Lập tức trả về `BLOCKED_DATA_CONFLICT` hoặc raise `RuntimeError("CRITICAL_OVERWRITE_PREVENTED")`.
