# TikTok Reg — Session Learnings 2026-08-23

## 1. Tên hiển thị PHẢI là tiếng Việt (user rule, bắt buộc)
- **User đã nhắc và phạt:** Sau khi reg thành công, bước đặt biệt danh / tên hiển thị (flow "Tạo tên") PHẢI dùng tên tiếng Việt có nghĩa (viết hoa chữ đầu, theo bộ tên Việt: Vy, An, Kiều Lâm, Hà, Phước...).
- KHÔNG đặt tên tiếng Anh (Anderus, Eva...) cho nick TikTok farm.
- `make_tiktok_name()` trong `social_reg_v1.py` đã được cập nhật với `_VI_NAME_MAP` và `_VI_NAME_FALLBACK` để ưu tiên tên Việt.

## 2. Nhận nhầm màn đăng nhập (OTP login screen) là "đã có tài khoản"
- **Bug:** Script nhập email vào form đăng nhập (không phải đăng ký), TikTok gửi OTP đăng nhập → script thấy màn OTP → tưởng email "đã có TikTok" → dừng.
- **Thực tế:** OTP có thể là để đăng nhập vào tài khoản cũ OR để xác minh đăng ký mới. Phân biệt bằng:
  - Màn đăng nhập OTP: có link **"Đăng nhập bằng mật khẩu"** ở dưới.
  - Màn đăng ký OTP: KHÔNG có link đó, chỉ có "Gửi lại mã".
- **Cách kiểm tra thực tế:** Dùng flow "Quên mật khẩu → Đặt lại bằng email" — nếu email báo "Địa chỉ email chưa được đăng ký" thì chưa có tài khoản.
- **Root cause trên Máy 75:** Script chạy ở màn đăng nhập (không phải đăng ký), OTP xoay kẹt sau khi nhập do TikTok rate-limit IP thật (proxy die).

## 3. Proxy die → TikTok chặn ở bước OTP (không tạo được acc)
- Khi proxy die, traffic đi direct IP thật → TikTok phát hiện IP farm đã reg nhiều acc → throttle/block OTP verification → màn xoay kẹt không qua.
- **Giải pháp:** Fix proxy → chờ 2-3 ngày → reg lại. Không bị ban thiết bị vì tài khoản chưa tạo xong.
- **Lưu ý:** Tài khoản TikTok có thể đã được tạo trên server nhưng script không đọc được profile (màn xoay không qua ≠ chưa tạo). Cần kiểm tra thực tế trên thiết bị.

## 4. Backfill pass mail sau batch
- Sau mỗi batch reg, một số nick đăng ký theo flow OTP-only (không có màn tạo pass) → cột `PASS MAIL` (cột G) trong `taikhoan_dat_v2_updated .xlsx` bị trống.
- **Phải sync lại từ `gmail_clean_v2.xlsx`** (cột 3 = mail pass) vào cột G của tracking ngay sau batch:
  ```python
  import openpyxl
  wb_src = openpyxl.load_workbook(r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx", data_only=True)
  src_map = {str(r[1]).strip().lower(): str(r[2]).strip() for r in wb_src.active.iter_rows(values_only=True) if r[1] and r[2]}
  
  wb_trk = openpyxl.load_workbook(r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx")
  ws = wb_trk.active
  for r in range(2, ws.max_row + 1):
      mail = str(ws.cell(r, 6).value or "").strip().lower()
      if mail in src_map and not ws.cell(r, 7).value:
          ws.cell(r, 7, value=src_map[mail])
  wb_trk.save(...)
  ```

## 5. Pass TikTok rỗng = flow Passwordless (bình thường)
- TikTok ngày càng nhiều flow reg không bắt tạo pass (hoặc có nút "Bỏ qua").
- Cột D (`PASS`) trống = đăng nhập lại bằng OTP gửi về email. Không phải lỗi tracking.

## 6. Kiểm tra proxy chuẩn cho nhiều máy
- Xem `farm-proxy-attachment` references/reg-session-learnings-20260823 hoặc skill body.
- TÓM TẮT: `tun0 UP + ping OK` không đủ. Phải dùng broadcast `-n vn.vichanger.app/.AdbCaller` và check `result=200 + data="<IP>"`.
