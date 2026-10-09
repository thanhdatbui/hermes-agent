# Xử Lý Triệt Để Hiện Tượng Ký Sinh & Máy Bị Full 8 Acc (MACHINE_FULL_8_ACCOUNTS)

## 1. Bối cảnh & Hiện tượng lỗi
Khi chạy Preflight Reg bù các hàng (đặc biệt Row 8) bằng `ensure_row_accounts.py <row>`, runner báo lỗi:
- `Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)`
- `[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`
- Người dùng bức xúc vì "đã fix vụ ký sinh rồi mà sao cứ bị hoài".

---

## 2. Ba nguyên nhân cốt lõi (Root Causes)

### 🔴 Nguyên nhân 1: State file ghi nhận "DONE" ảo do tap trượt popup xác nhận Đăng xuất
- **Cơ chế lỗi:** Trong script `watchdog_idle_parasite_reconcile.py` (hoặc `do_logout_account.py`), quy trình logout điều hướng đến *Cài đặt và quyền riêng tư* -> bấm *Đăng xuất* -> hiện dialog *"Bạn có chắc chắn muốn đăng xuất?"*.
- **Bẫy UI TikTok S7:**
  - Tiêu đề popup: resource-id `a76` (`Bạn có chắc chắn muốn đăng xuất?`).
  - Text "Đăng xuất": resource-id `a6d`, nhưng `clickable='false'` (bounds `[48,1632][1032,1692]`).
  - Container bấm thực sự: `clickable='true'` (bounds `[0,1584][1080,1740]`, tâm `(540, 1664)`).
  - Script cũ tìm resource-id `a6e` hoặc `button1` -> tap bị hụt -> popup không đóng, nick **chưa hề bị out**.
  - Nhưng script naive vẫn ghi nhận `"DONE"` vào `parasite_reconcile_state.json`.
- **Hậu quả:** Các phiên sau đọc state file thấy `"DONE"` nên tự động bỏ qua (skip), khiến nick ký sinh tiếp tục kẹt mãi trên máy.
- **Quy tắc bất biến:**
  1. Selector confirm dialog bắt buộc nhận diện: `a6d`, `a6e`, `button1` hoặc container clickable bounds `[0,` tâm `(540, 1664)`.
  2. **CẤM TUYỆT ĐỐI** ghi nhận `"DONE"` vào file state nếu chưa mở lại Switcher, dump UI XML / OCR và chứng minh nick mục tiêu đã biến mất hoàn toàn.

---

### 🔴 Nguyên nhân 2: Lệch mapping Excel ↔ Thiết bị (Tài sản chính chủ bị coi nhầm là thiếu / ký sinh)
- **Cơ chế lỗi:**
  - Ví dụ Máy 24: Thiết bị thực tế **ĐÃ ĐỦ 8 NICK CHÍNH CHỦ** (tất cả đều LIVE và thuộc về M24):
    - Slot 1..6: `hodat07102`, `l.yn13956`, `trinhhien1208`, `phamchi982`, `yingsrfxb27`, `linhngo5304`
    - Slot 7: `@trinhgiang7694`
    - Slot 8: `@baomai0316`
  - Nhưng trên `taikhoan_run_safe.xlsx` và `Tik8.xlsx`, nick `@trinhgiang7694` bị rớt khỏi file, `@baomai0316` bị đẩy lên Slot 7, làm Slot 8 bị trống (`None`).
  - Preflight thấy Slot 8 trống tưởng máy còn thiếu nick -> cố tình chạy reg bù -> máy đã đủ 8 nick kịch trần nên văng `MACHINE_FULL_8_ACCOUNTS`.
- **Quy tắc bảo vệ tài sản:**
  - **CẤM TUYỆT ĐỐI** vội vàng logout nick khi thấy máy báo full 8 nick.
  - Bắt buộc đối soát với bảng `farm_account_info` và `snapshots` trong `D:/Taadaa/data/tiktok_tracker.db`.
  - Nếu nick thuộc về máy đó: BẮT BUỘC backfill đồng bộ vào cả 4 file master:
    1. `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx`
    2. `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx`
    3. `D:/OneDrive/TaadaaData/kibe/Tik7.xlsx`
    4. `D:/OneDrive/TaadaaData/kibe/Tik8.xlsx`

---

### 🔴 Nguyên nhân 3: Bẫy đếm XML: Đếm nhầm nút "Thêm tài khoản" thành nick thứ 8
- **Cơ chế lỗi:**
  - Trong hàm `tap_add_account` (`social_reg_v1.py`):
    ```python
    _acc_count = sum(
        1 for _n in _root.iter("node")
        if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
    )
    ```
  - Trên TikTok Samsung S7, nút *"Thêm tài khoản"* / *"Add account"* ở đáy Switcher cũng mang cùng `resource-id` (`lli`, `lrq`) với các hàng account.
  - Khi máy có đúng **7 tài khoản chuẩn** (ví dụ Máy 3), bộ đếm đếm được 7 nick + 1 nút thêm = 8 nodes!
  - Điều kiện `if _acc_count >= 8` bị kích hoạt giả (false positive), tự động ngộ nhận máy full và quăng `MACHINE_FULL_8_ACCOUNTS` oan uổng dù nút thêm nick đang hiển thị.
- **Giải pháp vá chuẩn:**
  ```python
  _acc_count = sum(
      1 for _n in _root.iter("node")
      if any(k in _n.attrib.get("resource-id", "") for k in ["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli", "ndk"])
      and not any(x in (_n.attrib.get("text", "") + _n.attrib.get("content-desc", "")).lower() for x in ["thêm tài khoản", "add account", "add another"])
  )
  ```

---

## 3. Quy trình chuẩn điều phối & xử lý dứt điểm khi gặp sự cố

```
[Báo cáo Máy Full 8 Acc / Lệch Excel]
               │
               ▼
[Bước 1]: Inspect O(1) Switcher bằng screencap + WinRT OCR
               │
               ▼
[Bước 2]: Đối chiếu danh sách nick trên Switcher với DB tiktok_tracker.db
               │
        ┌──────┴──────────────────────────┐
        ▼                                 ▼
[Đủ 8 nick chính chủ]            [Có nick ký sinh từ máy khác]
        │                                 │
        ▼                                 ▼
- CẤM logout                     - Giữ sáng màn hình:
- Backfill đồng bộ 4 file:         `svc power stayon true && input keyevent 224 && input keyevent 82`
  + taikhoan_dat_v2_updated      - Điều hướng Settings -> Đăng xuất
  + taikhoan_run_safe            - Tap trúng container: (540, 1664) [0,1584][1080,1740]
  + Tik7.xlsx / Tik8.xlsx        - Mở lại Switcher: dump XML / OCR xác nhận nick ĐÃ BIẾN MẤT
                                 - Chỉ set DONE vào parasite_reconcile_state.json khi đã có ảnh verify
                                 - Teardown: `svc power stayon false && am force-stop ... && input keyevent 3`
```
