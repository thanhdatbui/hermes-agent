# Triage: Excel Lệch Cột Ngày Tạo (Col 8/9/7) & Tắt Gateway Busy Ack (Case 155) (2026-09-13)

## 1. Triệu Chứng Bỏ Qua Đăng Video Hàng Loạt (Safe-Skip Fail-Closed)
- **Hiện tượng:** Tại các ca nuôi nick hàng mới (Row 5, Row 6), hàng loạt máy (>80%) bị Safe-Skip đăng video với lý do:
  `account_creation_date_unverifiable`
- **Hậu quả:** Dù tài khoản đã ngâm 17-20 ngày (đủ điều kiện >= 10 ngày tuổi), hệ thống vẫn không cho đăng video do logic preflight không tìm thấy ngày tạo hợp lệ.

## 2. Nguyên Nhân Gốc Rễ: Lệch Cột Do Script Reg Ghi Thừa Ô
1. **Lệch cột trong `taikhoan_dat_v2_updated .xlsx`:**
   - Cấu trúc chuẩn 10 cột: Col 0 (Máy), Col 1 (Folder), Col 2 (ID), Col 3 (PASS), Col 4 (2FA), Col 5 (GMAIL), Col 6 (PASS MAIL), Col 7 (DOB), Col 8 (NGÀY TẠO), Col 9 (Device ID).
   - Trong `social_reg_v1.py` và `deferred_tracking_writer.py`, mảng `values` bị chèn dư một phần tử `None` trước DOB:
     `[stt, tik, id, pw, 2fa, mail, mail_pw, None, dob, created, device_id]`
   - Hậu quả: Col 8 (`NGÀY TẠO`) bị rỗng (`None`), ngày tạo thật (`23/08/2026`, `25/08/2026`) bị dạt sang Col 9 (`Device ID`), còn Device ID bị đẩy sang Col 10.
2. **Logic Preflight Cũ Thiếu Fallback:**
   - Khi tìm thấy header `NGÀY TẠO` tại Col 8, code gán cứng `probe_cols = [header_date_col]` (chỉ quét Col 8).
   - Khi Col 8 là `None`, code không quét tiếp Col 9 và Col 7, dẫn đến kích hoạt fail-closed.

## 3. Giải Pháp Kỹ Thuật Chuẩn Hóa (Case 155)
Trong `python_runner/flows/upload_preflight.py`:
- Luôn bổ sung fallback các cột `(8, 9, 7)` vào danh sách dò tìm ngay cả khi đã nhận diện cột header:
```python
probe_cols: list[int] = []
if header_date_col is not None:
    probe_cols.append(header_date_col)
for fallback_c in (8, 9, 7):
    if fallback_c not in probe_cols:
        probe_cols.append(fallback_c)
```
- Kết hợp với guard `candidate.year >= 2025` để lọc bỏ rác text/serial, nhận diện chính xác ngày tạo bị trượt cột.

---

## 4. Tắt Thông Báo Ngắt Lệnh Gateway ("Interrupting current task...")
- **Nguyên nhân xuất hiện:** Khi `config.yaml` bị lỗi cú pháp YAML (ví dụ prompt chứa chuỗi `:` không bọc nháy), Hermes Gateway tự động fallback về cấu hình mặc định (default config), reset cờ onboarding và bật thông báo ack ngắt lệnh kèm tip `/busy`.
- **Cách tắt triệt để:**
  1. Kiểm tra cú pháp YAML qua `hermes config check` đảm bảo không bị fallback.
  2. Khóa cứng trong `config.yaml`:
     ```yaml
     display:
       busy_ack_enabled: false
     ```
  3. Khóa cứng trong `.env`:
     ```env
     HERMES_GATEWAY_BUSY_ACK_ENABLED=false
     ```
