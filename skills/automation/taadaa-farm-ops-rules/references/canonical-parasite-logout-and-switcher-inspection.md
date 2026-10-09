# Canonical Parasite / Stray Account Logout & Switcher Inspection

## 1. Nguyên tắc cốt lõi: Dùng script có sẵn, CẤM viết lại script mới (User reprimand 25/09/2026)
- Khi cần logout tài khoản ký sinh hoặc nick lạ trên bất kỳ máy nào, **BẮT BUỘC dùng script chuẩn có sẵn**:
  - Script đơn máy: `python D:/Taadaa/tools/do_logout_account.py <mid> <username> <serial>`
  - Script hàng loạt: `D:/Taadaa/tools/run_logout_all.py`
- **CẤM TUYỆT ĐỐI** tự tiện viết script probe, script logout tạm thời (`logout_mX.py`, `temp_logout.py`) làm phân mảnh codebase và dễ gây lỗi timeout/treo process.

## 2. Kỹ thuật đối soát Switcher khi máy chạm trần 8 nick (`MACHINE_FULL_8_ACCOUNTS`)
- Khi TikTok đã có 8 tài khoản đăng nhập, nút **"Thêm tài khoản"** (`Add account`) bị ẩn hoàn toàn.
- Tài khoản thứ 8 trong menu Chuyển đổi tài khoản (Switcher) thường bị đẩy xuống mép dưới màn hình (`y >= 1850` hoặc bounds `[252, 1866][542, 1920]`), OCR có thể nhận diện sót hoặc méo chữ nếu không cuộn.
- **Thao tác chuẩn:**
  1. Mở Switcher: `reg.open_account_dropdown(serial)`
  2. Vuốt nhẹ lên 400px: `adb -s <serial> shell input swipe 540 1600 540 1200 200`
  3. Đọc danh sách tài khoản qua XML atx-agent (port 7912): `rid=com.ss.android.ugc.trill:id/ndk` hoặc `mtx`.
- **Phân loại nick thứ 8:**
  - **Nick ký sinh thực thụ:** Nick thuộc về máy khác trong `taikhoan_dat_v2_updated .xlsx` -> Bắt buộc logout trên máy thừa.
  - **Nick lạ / nick rác:** Không có trong bất kỳ dòng nào của cả 640 tài khoản trên Farm -> Phải kiểm tra kỹ profile (ngày tạo, video, mail) trước khi quyết định logout hay backfill.
  - **Nick chính chủ bị sót:** Nick đã reg cho máy đó nhưng chưa được ghi vào Excel -> Backfill dòng Excel, CẤM xóa.

## 3. Tọa độ chuẩn xác nhận popup Đăng xuất TikTok (Modern UI)
- Khi bấm **Đăng xuất** trong menu Cài đặt và quyền riêng tư, TikTok mở Bottom Sheet dialog:
  - Text: *"Bạn có chắc chắn muốn đăng xuất?"* (`rid=com.ss.android.ugc.trill:id/a76`)
  - Nút *"Chuyển đổi tài khoản"* (`y ~ 1505`)
  - Nút *"Đăng xuất"* (`rid=com.ss.android.ugc.trill:id/a6d`, bounds `[48, 1632][1032, 1692]`) -> **Tọa độ bấm chuẩn: `(540, 1662)`** (hoặc `540, 1640`).
  - Nút *"Hủy"* (`bounds [48, 1813][1032, 1870]`)
- **Lưu ý:** Tuyệt đối không dùng tọa độ legacy cũ `(750, 1100)` vì sẽ bấm trượt ra ngoài vùng modal hoặc không có tác dụng.

## 4. Bẫy màn hình tắt trên Samsung S7 (Sleep / Dozing)
- Trên Samsung Galaxy S7 (SM-G930F, Android 7), khi màn hình ở trạng thái tắt (`Display Power: state=OFF` / `mWakefulness=Dozing`), lệnh `exec-out screencap -p` sẽ trả về ảnh màu đen đồng nhất có dung lượng **~13 KB**.
- Mọi thao tác screencap/OCR bắt buộc phải đánh thức màn hình trước:
  ```bash
  adb -s <serial> shell "input keyevent 224 && input keyevent 82"
  ```
