# Admin Folder Video Formula & Anti-Overwrite Guards (2026-09-21)

## Bối cảnh & Sự cố
1. **Sự cố ghi đè mất nick cũ (Overwrite Incident)**:
   - Khi chạy reg bù nạp kết quả deferred tracking (`scripts/deferred_tracking_writer.py` hoặc `social_reg_v1.py` hàm `upsert_tracking_account`), nếu logic trỏ nhầm hàng đã có nick hoặc bị lệch mapping, code cũ ghi đè thẳng tay tài khoản mới lên hàng của tài khoản cũ, xóa mất username/password/mail của acc đang hoạt động.
   - Bên Kibe bị mất 27 nick, bên Admin bị ghi đè mất 69 nick ở Folder 2 (Slot 2).

2. **Sự cố lệch số Folder Video bên Admin (2106, 2108 vs 1..640)**:
   - Bên Admin (Máy 201..280) quản lý 80 máy, các file `Tik1.xlsx` đến `Tik8.xlsx` đánh số Folder Video từ 1 đến 640.
   - Công thức chuẩn bên Admin:
     $$\text{Folder Video Admin} = (\text{STT} - 201) \times 8 + \text{Slot (1..8)}$$
     *(Ví dụ: Máy 264 là máy thứ 64 của Admin $\rightarrow$ Slot 1: 505, Slot 2: 506, Slot 4: 508, Slot 7: 511)*.
   - Nhưng khi script của Kibe đem sang chạy cho Admin, script lại áp dụng công thức của Kibe:
     $$\text{Folder Video Kibe} = (\text{STT} - 1) \times 8 + \text{Slot}$$
     $\rightarrow$ Dẫn đến Máy 264 bị ghi thành Folder `2106` và `2108`, Máy 203 bị ghi thành Folder `1624`.

---

## Giải pháp & Quy tắc Bất biến (Invariants)

### 1. Hard Guard Chống Ghi Đè Tài Khoản (Anti-Overwrite Guards)
Trong mọi hàm ghi vào sheet `Tài Khoản`:
- **Trước khi ghi**: Bắt buộc đọc `existing_id`, `existing_pass`, `existing_mail` tại hàng đích.
- **Điều kiện chặn chuẩn (Chặn cả khi email cũ trống)**:
  ```python
  # CHÚ Ý: Phải dùng `not existing_mail or existing_mail != incoming_mail`
  # Tránh lỗ hổng khi existing_mail trống (None hoặc "") mà đã có existing_id/existing_pass
  if (existing_id or existing_pass) and (not existing_mail or existing_mail != incoming_mail):
      # Trong deferred_tracking_writer.py:
      return TrackingWriteResult("BLOCKED_DATA_CONFLICT", blocker=f"OVERWRITE_REJECTED_EXISTING_ACCOUNT_{existing_id}_{existing_mail}")
      # Trong social_reg_v1.py:
      raise RuntimeError(f"CRITICAL_OVERWRITE_PREVENTED: Cannot overwrite existing account @{existing_id} ({existing_mail}) at row {row}")
  ```
- **Nguyên tắc**: Chỉ được ghi vào hàng hoàn toàn trống (`None`) hoặc hàng đã có đúng email đó (update thông tin cho cùng 1 account).

### 2. Chuẩn hóa Folder Video khi Kibe vận hành cho Admin
- **Phân lập sổ cái vật lý**: Cụm Kibe dùng `TaadaaData/kibe/`, Cụm Admin dùng `TaadaaData/admin/`.
- **Thư mục video render**:
  + Kibe: `D:\TIKTOK-videonuoinick\<1..640>`
  + Admin: `\\192.168.110.119\D\TIKTOK-videonuoinick\<1..640>`
- Cột `Folder Video` của Admin BẮT BUỘC giữ dải số chuẩn `1..640` theo `(STT - 201) * 8 + Slot`, TUYỆT ĐỐI KHÔNG dùng công thức `(STT - 1) * 8` làm phát sinh các số >1000 gây lệch kho video khi upload.
