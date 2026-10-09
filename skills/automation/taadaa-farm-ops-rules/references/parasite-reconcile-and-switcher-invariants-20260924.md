# Parasite Account Reconcile & Switcher 8-Account Invariants (2026-09-24)

## Bối Cảnh Sự Cố & Câu Hỏi Của User:
"Ủa tao fix vụ kí sinh rồi mà sao cứ bị hoài thế?"

Sau khi điều tra và đối soát hiện trường toàn farm ngày 24/09/2026, 3 nguyên nhân cốt lõi khiến lỗi lặp lại gồm:

### 1. Báo Cáo "Hoàn Tất Dối" / State Poisoning (`parasite_reconcile_state.json`)
- **Triệu chứng**: Watchdog bỏ qua không dọn dẹp các máy dính nick ký sinh (M61 `@anggiathinh2905`, M69 `@quachtieu2106`).
- **Nguyên nhân**: Ở phiên trước, script bấm Đăng xuất nhưng bị trượt popup xác nhận của TikTok do sai lệch `resource-id` (TikTok dùng `a6d` thay vì `a6e`). Nick chưa bị out, nhưng script đã vội vàng ghi `"DONE"` vào `parasite_reconcile_state.json`. Các phiên sau đọc state file thấy `"DONE"` liền tự động skip.
- **Giải pháp**:
  - Popup xác nhận "Bạn có chắc chắn muốn đăng xuất?": Text "Đăng xuất" thường có `clickable="false"` (`[48,1632][1032,1692]`), container cha mới là `clickable="true"` (`[0,1584][1080,1740]`, center `540, 1664`).
  - Hỗ trợ regex/selector cho `resource-id` gồm `a6d`, `a6e`, `button1`, và bounds `[0,` hoặc `[48,`.
  - Nghiệm thu bằng WinRT OCR readback: Chỉ set `"DONE"` khi nick ký sinh THỰC SỰ biến mất khỏi switcher.

### 2. Bẫy False-Positive `MACHINE_FULL_8_ACCOUNTS` Do Đếm Nhầm Nút "Thêm Tài Khoản"
- **Triệu chứng**: Máy thực tế chỉ có 7 nick chuẩn (như Máy 3), nhưng runner đăng ký lại quăng lỗi `[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`.
- **Nguyên nhân**: Trên giao diện Switcher TikTok (S7 Android 7/v46+), nút "Thêm tài khoản" ở đáy danh sách mang cùng `resource-id` (`"lli"`, `"lrq"`) với các item tài khoản. Hàm đếm node ngây thơ:
  ```python
  _acc_count = sum(
      1 for _n in _root.iter("node")
      if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
  )
  ```
  sẽ đếm: 7 account nodes + 1 add button node = 8 nodes! Điều kiện `_acc_count >= 8` lập tức kích hoạt, gây ngộ nhận máy full nick.
- **Giải pháp**:
  Bắt buộc lọc bỏ nút add account trong phép đếm:
  ```python
  _acc_count = sum(
      1 for _n in _root.iter("node")
      if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
      and not any(x in (_n.attrib.get("text", "") + _n.attrib.get("content-desc", "")).lower() for x in ["thêm tài khoản", "add account", "add another"])
  )
  ```

### 3. Nhầm Lẫn Giữa "Ký Sinh" Và "Tài Sản Bị Rớt Dòng Excel" (Vụ Máy 24)
- **Triệu chứng**: Switcher Máy 24 có đủ 8 nick, nhưng Excel Row 8 để trống (`None`), Preflight báo máy thiếu và cố reg bù $\rightarrow$ quăng `MACHINE_FULL_8_ACCOUNTS`.
- **Nguyên nhân**: Nick thứ 7 `@trinhgiang7694` bị rớt dòng trong Excel, nick thứ 8 `@baomai0316` bị đẩy lên Row 7. Cả 8 nick đều là nick LIVE chính chủ của Máy 24 trong `tiktok_tracker.db`.
- **Quy tắc bất biến**:
  TUYỆT ĐỐI CẤM tự ý coi nick thứ 8 là ký sinh để đem đi logout. Phải query DB `snapshots` & `farm_account_info`: Nếu nick thuộc máy đó -> BẮT BUỘC BACKFILL vào Excel, bảo toàn trọn vẹn tài sản farm.

### 4. Giữ Sáng Màn Hình Khi Xử Lý Thiết Bị S7
- Trước các chuỗi thao tác logout / switcher dài trên S7:
  `adb shell "svc power stayon true && input keyevent 224 && input keyevent 82"`
- Trong teardown bắt buộc tắt:
  `adb shell "svc power stayon false"`
