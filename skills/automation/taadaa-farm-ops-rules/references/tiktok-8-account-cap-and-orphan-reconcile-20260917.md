# TikTok 8-Account Limit Detection & Orphan Account Reconcile (2026-09-17)

## 1. Bản chất sự cố: "Lệch pha" giữa Bảng Excel ca nuôi và Máy thực tế S7
Khi ca nuôi (TikTok feed / nuoi acc) chạy, hệ thống kiểm tra bảng tính tracking `taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`).
- Nếu trên Excel một máy mới chỉ có 6 hoặc 7 dòng có `TikTok ID` (Cột C / index 2), hệ thống coi máy này **"chưa đủ 8 nick, cần reg bù"**.
- Khi launcher reg bù (`_detect_clean.py` / `_run_all_targets.py`) dispatch tiến trình reg vào máy thật:
  * TikTok trên máy mở bottom sheet dropdown chuyển đổi tài khoản (`Chuyển đổi tài khoản`).
  * Thực tế trên máy **đã có đủ 8 nick đăng nhập**.
  * TikTok tự động ẩn hoàn toàn nút "Thêm tài khoản" (`Add account`).

## 2. Pitfall obfuscated resource-ids trong `tap_add_account`
Trên các bản build TikTok Android mới, resource-id của danh sách tài khoản trong switcher bottom sheet bị obfuscate ngẫu nhiên:
- Cũ: `n72`, `lkp`
- Mới (2026): `l9b`, `lpw`, `l_z`, `lrq`, `lli`

Nếu code chỉ kiểm tra `n72` và `lkp`, bộ đếm số lượng nick ra `0` thay vì `8`. Hậu quả:
- Code không kích hoạt được ngoại lệ `MACHINE_FULL_8_ACCOUNTS`.
- Trôi xuống cuối hàm và raise lỗi sai cấu trúc:
  `RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account', ...)`
- **Quy tắc đếm chuẩn**:
  ```python
  _acc_count = sum(
      1 for _n in _root.iter("node")
      if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"])
  )
  if _acc_count >= 8:
      log(f"   [04_add_account] Máy đã có {_acc_count} tài khoản — đạt giới hạn tối đa 8")
      keyevent(device_id, 4, wait=D_SHORT)  # dismiss dropdown
      keyevent(device_id, 3, wait=0.5)      # go home
      raise RuntimeError("[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok")
  ```

## 3. Quy trình Reconcile Nick Mồ Côi / Ký Sinh trên S7
Khi gặp máy dính `MACHINE_FULL_8_ACCOUNTS`:
1. **Tuyệt đối CẤM**:
   - Không clear data TikTok bừa bãi.
   - Không tự ý logout nick cũ làm mất vết.
   - Không đè slot Excel khi chưa đối soát.
2. **Trích xuất nick mồ côi**:
   - Dump UI XML của sheet `Chuyển đổi tài khoản` để lấy danh sách 8 username trên máy thật.
   - So sánh với các username đang ghi nhận ở cột ID (Cột C) của STT máy đó trên Excel.
   - Xác định username mồ côi (`set(device_nicks) - set(excel_nicks)`).
3. **Map bù vào slot trống**:
   - Điền username mồ côi vào đúng các hàng còn trống `TikTok ID` (ví dụ Folder 215, 255, v.v.).
   - Khi Excel đủ 8/8 ID, ca nuôi sẽ chạy đủ 8 nick và scheduler sẽ ngừng gọi reg bù cho máy đó.
