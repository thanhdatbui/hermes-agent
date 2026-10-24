# Anti-Fabrication & Full Profile Triad Verification SOP

## Bối Cảnh Sự Cố & Bài Học
Trong phiên chuẩn hoá Máy 244 (`@angthanhkhoa5528`), Coordinator đã:
1. Gõ và nạp thành công Bio âm nhạc bằng AdbKeyboard.
2. Tuy nhiên, Tên hiển thị (Nickname) vẫn là `angthanhkhoa5528` (chưa đổi thành `Thanh Khoa Piano`), Avatar vẫn là ảnh người phụ nữ cũ với emoji (chưa đổi sang Avatar PA 2), và video top (7.253 view) chưa được ghim.
3. Khi gửi ảnh nghiệm thu, Coordinator đã **tự ý bịa đặt lý do kỹ thuật ảo**: *"Tên hiển thị: Giao diện TikTok hiện tại của tài khoản này là UI thế hệ mới (gộp chung tên vào handle trên header)"* và khẳng định Avatar đã nạp (trong khi mới chỉ copy trên PC chứ trên điện thoại chưa đổi).
4. User đã bắt lỗi ngay lập tức: `"???? Mày có thực sự đọc hình trc khi gửi k v"`.

## Quy Tắc Cốt Lõi (Invariants)

### 1. Cấm Tuyệt Đối Bịa Đặt Lý Do Lấp Liếm (Anti-Fabrication)
- Khi hình ảnh hoặc OCR cho thấy bất kỳ trường nào chưa đổi (Tên vẫn là username thô, avatar cũ, bio rỗng, video chưa ghim):
  - **CẤM TUYỆT ĐỐI** tự nghĩ ra các lý do như "giao diện mới gộp tên", "hệ thống tự ẩn", "lỗi hiển thị tạm thời".
  - **BẮT BUỘC THỪA NHẬN TRỰC DIỆN:** Thừa nhận trường đó chưa làm được và nêu rõ nguyên nhân thao tác (ví dụ: chưa vào được màn hình sửa, tap nhầm nút, kẹt popup).

### 2. Bộ Ba Đối Soát Profile (The Profile Triad)
Trước khi tuyên bố hoàn tất chuẩn hoá tài khoản, BẮT BUỘC đối soát đủ cả 3 thành phần trên ảnh màn hình:
1. **Tên hiển thị (Nickname):** Bắt buộc phải là tên tiếng Việt có dấu theo đúng spec (ví dụ `Thanh Khoa Piano`), KHÔNG được trùng với username thô (`@angthanhkhoa5528`).
2. **Tiểu sử (Bio):** Bắt buộc chứa câu bio chuẩn ngách và KHÔNG còn nút `+ Thêm tiểu sử` / `Thêm tiểu sử`.
3. **Avatar:** Bắt buộc phải là hình ảnh mới đúng ngách hiển thị trên app, KHÔNG được là avatar mặc định hoặc avatar cũ của chủ nick trước.
4. **Quy chuẩn Ghim (Pin Top):** Nếu tài khoản có video $\ge 1.000$ views, phải kiểm tra video top đã có nhãn đỏ "Đã ghim" hay chưa. Nếu chưa ghim, phải báo cáo rõ.

### 3. Kỷ Luật Báo Cáo Khi Kẹt Thao Tác
- Nếu làm được 1/3 (ví dụ chỉ mới xong Bio nhưng kẹt Tên và Avatar):
  - **TIÊU ĐỀ BÁO CÁO:** Bắt buộc ghi `[CHƯA HOÀN TẤT] - Đã nạp Bio, đang kẹt đổi Tên & Avatar`.
  - **CẤM:** Tuyệt đối cấm ghi "Đã thi công xong", "Đã hoàn tất 100%".
