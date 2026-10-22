# OCR Username Space Artifact & Profile Subscreen Recovery (2026-10-23)

## 1. Hiện Tượng & Root Cause
### A. Lỗi Khoảng Trắng Nội Bộ Của OCR (OCR Whitespace Injection)
- **Triệu chứng:** Runner đổi tên (`do_rename_canonical_runner.py`) hoặc reconcile tài khoản TikTok trên Samsung S7 báo `exit_2` sau khi đã đổi tên thành công.
  - Trace ghi nhận: `da Luu nhung Ho so dang la @None, khong phai @<target_user>`.
- **Nguyên nhân:** WinRT OCR đôi khi quét khoảng cách giữa các ký tự username thành khoảng trắng thực sự (ví dụ: `@ngotran g7771` thay vì `@ngotrang7771`).
- **Bẫy code cũ:** Bộ lọc `is_user_line` kiểm tra cứng điều kiện `" " not in text`, khiến dòng username bị loại bỏ hoàn toàn, trả về `None, None`.

### B. Màn Hình Hồ Sơ Bị Kẹt Trong Subscreen / Scrolled State
- **Triệu chứng:** Runner kẹt ở trạng thái `PROFILE 5 lan lien tiep` rồi ném `Abort: ket o trang thai PROFILE 5 lan lien tiep`.
- **Hiện trường thị giác (Visual Evidence):**
  - Giữa dòng Bio ("Xin chào") và lưới video hoàn toàn là khoảng trắng trống trải, không hề có nút `Sửa hồ sơ` hay `+ Thêm tiểu sử`.
  - Góc trên bên trái xuất hiện icon mũi tên quay lại `<` (OCR nhận diện thành chữ `o` tại tọa độ x ~ 55, y ~ 117).
  - Đây là màn hình phụ (ví dụ: tab "Video riêng tư của bạn") hoặc trang hồ sơ bị cuộn lỡ dở.
- **Bẫy tap mù:** Khi OCR không tìm thấy text nút, script fallback tap vào tọa độ cứng `(540, 865)` hoặc `(315, 865)` 5 lần liên tiếp. Vì đang ở subscreen hoặc bị cuộn, các cú tap này rơi vào vùng trống hoặc trúng icon tab khác, không bao giờ mở được màn hình sửa hồ sơ.

---

## 2. Giải Pháp Chuẩn Hóa (Standardized Fixes)

### A. Quy Tắc Xử Lý Khoảng Trắng OCR Cho Username
- **Nguyên tắc an toàn (Chống False Positive):**
  - Tuyệt đối KHÔNG bỏ hoàn toàn điều kiện kiểm tra khoảng trắng vì sẽ nhận nhầm các đoạn caption hoặc mention khác bắt đầu bằng `@`.
  - CHỈ chấp nhận chuỗi có khoảng trắng nếu sau khi loại bỏ khoảng trắng (`compact(text)`), chuỗi đó khớp chính xác với `is_target_user()`.
- **Mã nguồn chuẩn:**
  ```python
  is_user_line = (
      text.startswith("@")
      and b[1] < 750
      and not any(
          k in normalized
          for k in ("tai khoan", "nhac den", "noi ve", "chia se", "follower", "thich")
      )
      and (" " not in text or is_target_user(compact(text)))
  )
  if is_user_line:
      if " " in text:
          print(f"   [OCR-SPACE] username OCR co khoang trang: raw={text!r} -> compact={compact(text)!r}")
      return name_above_user_box(boxes, b), compact(t)
  ```
- **Bộ Test Bắt Buộc:**
  1. *Happy-path:* Username bị OCR chèn khoảng trắng (vd: `@ngotran g7771`) phải match thành công tên và username.
  2. *Negative-path:* Dòng khác bắt đầu bằng `@` có khoảng trắng nhưng không phải target_user (vd: `@other user7771`) KHÔNG ĐƯỢC match.

### B. Quy Tắc Xử Lý Thoát Subscreen & Cuộn Về Đỉnh Profile
- Khi ở trạng thái `PROFILE` nhưng OCR không thấy nút `Sửa hồ sơ` hay `+ Thêm tiểu sử`:
  1. **Kiểm tra icon Back (`<`):** Nếu có box tại góc trên bên trái (`b[0] < 120 and b[1] < 200` có text dạng `o`, `<`, `back`), bấm vào tọa độ đó để thoát subscreen.
  2. **Vuốt về đỉnh:** Trước khi tap tọa độ fallback mù, thực hiện vuốt `SWIPE_PROFILE_TOP = (540, 400, 540, 1200, 300)` để đảm bảo các nút điều khiển được đưa vào khung nhìn.

### C. Kỷ Luật Closeout Gate Đối Với Tọa Độ Thiết Bị
- Reviewer (Sol High / closeout_gate.py) sẽ **REJECT ngay lập tức** nếu phát hiện Coordinator tự ý sửa tọa độ tap vật lý mà không có biên nhận Live Canary chạy thật trên thiết bị lỗi.
- Chỉ can thiệp sửa logic thuần túy (OCR parsing, text filtering, regex, telemetry) trừ khi có đầy đủ bằng chứng screencap + JSON receipt trên máy thật.
