# Tracking Slot Chưa Có TikTok ID: Xóa Gmail Để Reg Lại (2026-09-13)

## Quy ước farm (user chốt)
- `taikhoan_dat_v2` cột TikTok ID rỗng = slot chưa có nick → `ensure_row_accounts.py`
  tự cấp mail + reg bù trước giờ feed.
- Slot chỉ có Gmail mà chưa có ID thì Gmail đó là "đặt chỗ", KHÔNG phải kết quả
  reg thành công. `social_reg_v1.py` chỉ ghi tracking khi `ok == True`
  (`upsert_tracking_account` / `write_deferred_tracking_result` sau
  `wait_login_success`); dòng Gmail-only cũ (VD M66/Tik523 từ 24/06/2026) là
  dữ liệu cấp phát từ trước, không phải bằng chứng reg thành công.

## Thao tác đã làm (M66 slot 3 / dòng 524)
- Xóa 4 cột F/G/H/I (gmail, pass mail, DOB, created), GIỮ NGUYÊN cột A (STT),
  B (Tik), J (serial) để slot đủ điều kiện trống hoàn toàn cho preflight.
- Verify sau xóa: `ensure_row_accounts.py --dry-run 3` vẫn phát hiện `[66]`
  thiếu acc; M66 bị `REG_DAILY_COOLDOWN_ACTIVE` (reg 1 acc/ngày) nên reg bù
  dời sang hôm sau — đúng chính sách, không phải bug.
- Pitfall: Gmail trong slot trống thường KHÔNG có trong `gmail_clean_v2.xlsx`
  (VD `dieuthuong210666@gmail.com`) → preflight sẽ mua mail mới hoặc dùng mail
  dư, không khôi phục Gmail cũ.
