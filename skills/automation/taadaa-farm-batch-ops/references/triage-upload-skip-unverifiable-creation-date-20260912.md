# Triage Hàng Loạt Máy Bị Bỏ Qua Đăng Video (`account_creation_date_unverifiable`)

## 1. Hiện tượng & Triệu chứng
Khi người dùng thắc mắc: *"Sao bị bỏ qua đăng video nhiều thế?"*, báo cáo Feed Session Watchdog của Phiên 2 (Ca 3 Row 6 hoặc Row 5) hiển thị:
```text
• Đăng Video (2/2 - 8 video đã đăng):
  + Success (8): 3, 10, 34, 59, 76, 77, 78, 79
  + Timeout/Quá giờ (0): Không có
  + Lỗi script/xác minh (0): Không có
  + Bỏ qua (58): 1, 2, 4, 5, 6, 7, 8, 9, 12, 13, 14, ...
```

---

## 2. Quy trình Điều tra O(1) (Coordinator)
Tuyệt đối **CẤM quét đĩa rộng** (`grep -rn`, `os.walk`, `find`). Điều tra nhanh theo 3 bước:
1. **Kiểm tra `upload_result.json` của 1 máy bị skip:**
   Đọc trực tiếp file tại:
   `D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>\<run-folder>\machines\machine_<N>\<run-id>\upload_result.json`
   Xác nhận nội dung:
   ```json
   {
     "machine": 1,
     "row": 6,
     "status": "skipped",
     "reason": "account_creation_date_unverifiable",
     "workbook": "Tik6.xlsx"
   }
   ```
2. **Xác định cơ chế Fail-Closed:**
   Trong `flows/upload_preflight.py` (`check_upload_cooldown_eligibility`):
   - Row 1..4: Các nick cũ đã trưởng thành -> Cho phép đăng tự do.
   - Row 5, Row 6 (và row >= 5): Bắt buộc kiểm tra ngày tạo tài khoản. Yêu cầu tuổi nick $\ge 10$ ngày (`CREATION_COOLDOWN_DAYS = 10`, `BENCHMARK_MIN_UPLOAD_DATE = 2026-09-11`).
   - Nếu `created_date is None` -> Trả về `(False, "account_creation_date_unverifiable", None)` -> Safe-Skip toàn bộ.
3. **Kiểm tra cấu trúc cột thực tế trong file Excel nguồn:**
   Đọc các dòng của Slot tương ứng trong `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`:
   - Kiểm tra xem ngày tạo nằm ở Cột 8 hay Cột 9.
   - Nhóm thành công (`Col 8` có date): Ngày tạo nằm đúng cột `NGÀY TẠO`.
   - Nhóm bị skip (`Col 9` có date): Cột 8 rỗng (`None`), ngày tạo bị dạt sang Cột 9 (`device ID`), và Device ID bị đẩy sang Cột 10.

---

## 3. Nguyên nhân gốc rễ kỹ thuật
1. **Header-Locking trong parser:**
   Hàm `load_account_creation_dates` trong `upload_preflight.py` tìm thấy tiêu đề `"NGÀY TẠO"` tại Cột 8 nên gán cứng `header_date_col = 8` và đặt `probe_cols = [header_date_col]`.
2. **Thiếu Fallback lân cận:**
   Vì `probe_cols` chỉ có 1 phần tử `[8]`, khi Cột 8 của dòng đó bằng `None`, parser không quét tiếp sang Cột 9 (nơi thực tế đang chứa chuỗi ngày `'23/08/2026'`, `'2026-08-25'`).
3. **Hậu quả:**
   Hệ thống không tìm thấy ngày tạo -> Kích hoạt chốt chặn an toàn `account_creation_date_unverifiable` -> Toàn bộ 58 nick dù đã 17-20 ngày tuổi (đủ điều kiện) vẫn bị skip oan.

---

## 4. Giải pháp Chuẩn hóa (Worker Subagent Patch Contract)
Cập nhật `flows/upload_preflight.py` trong hàm `load_account_creation_dates`:
```python
# Thay vì chỉ thăm dò 1 cột header_date_col duy nhất:
probe_cols = [header_date_col, 9, 8, 7] if header_date_col is not None else [8, 9, 7]
# Bỏ trùng lặp nhưng giữ thứ tự ưu tiên
seen_cols = set()
unique_probe_cols = [c for c in probe_cols if c is not None and not (c in seen_cols or seen_cols.add(c))]

for c_idx in unique_probe_cols:
    if c_idx < len(row):
        candidate = parse_date_safely(row[c_idx])
        if candidate and candidate.year >= 2025:
            d = candidate
            break
```
Sau khi vá, kiểm tra bằng `pytest python_runner/tests/test_upload_hook.py` để xác nhận 100% tests pass.

---

## 5. Nguyên Nhân Gốc Rễ Gây Lệch Cột Excel Trong `Tiktok_Reg` (Chèn Dư Cột None)
Khi đối soát tại sao dữ liệu Excel cứ liên tục bị lệch cột ở các mẻ reg mới:
1. **Cấu trúc bảng chuẩn (`taikhoan_dat_v2_updated .xlsx` - 10 cột):**
   - Cột 1: `Máy`
   - Cột 2: `Folder Video`
   - Cột 3: `ID`
   - Cột 4: `PASS`
   - Cột 5: `2FA`
   - Cột 6: `GMAIL`
   - Cột 7: `PASS MAIL`
   - Cột 8: `NGÀY THÁNG NĂM SINH`
   - Cột 9: `NGÀY TẠO`
   - Cột 10: `device ID`
2. **Lỗi trong mã nguồn ghi dữ liệu của `Tiktok_Reg`:**
   Tại `social_reg_v1.py` (dòng 5070) và `scripts/deferred_tracking_writer.py` (dòng 186), mảng ghi giá trị vào Excel bị chèn thừa 1 ô `None`:
   ```python
   values = [
       stt,                # 1: Máy
       int(tik_no),        # 2: Folder Video
       tiktok_id,          # 3: ID
       tiktok_pw or None,  # 4: PASS
       twofa,              # 5: 2FA
       email,              # 6: GMAIL
       mail_pw or None,    # 7: PASS MAIL
       None,               # ❌ VỊ TRÍ NÀY BỊ THỪA 1 Ô NONE!
       dob or None,        # 9: Đẩy ngày sinh sang Cột 9 (Hotmail dob=None -> ô rỗng)
       created,            # 10: ĐẨY NGÀY TẠO SANG CỘT 10 (Cột device ID)
       device_id,          # 11: ĐẨY SERIAL RA NGOÀI MÉP BẢNG CỘT 11
   ]
   ```
3. **Bài học & Phòng ngừa:**
   - Ở phía đọc (consumer như `tiktok-luot nuoi acc`): Bắt buộc cơ chế fallback `probe_cols = [header_date_col, 8, 9, 7]` để chống sập khi dữ liệu ngoài bị lệch.
   - Ở phía ghi (producer `Tiktok_Reg`): Cần chuẩn hóa mảng `values` đúng 10 cột, bỏ ô `None` thừa ở giữa `mail_pw` và `dob`.
