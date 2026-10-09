# Phân tích Workflow: TIKTOK - ĐỀ XUẤT VÀ TIM BẠN BÈ

- **File gốc:** `C:\Users\Kibe\Downloads\TIKTOK-ĐỀ-XUẤT-VÀ-TIM-BẠN-BÈ_Protected.gemphonefarm`
- **Output JSON giải mã:** `C:\Users\Kibe\Downloads\TIKTOK-ĐỀ-XUẤT-VÀ-TIM-BẠN-BÈ_Protected_decrypted.json`
- **Quy mô:** 193 nodes, 288 edges.

---

## 1. Tham số & Cấu hình (Variables)

| Tên biến | Kiểu / Mặc định | Ý nghĩa |
| :--- | :--- | :--- |
| `Đường_dẫn_tài_khoản` | Đường dẫn file Excel | Bảng chứa mapping thiết bị (`deviceId`) -> `taiKhoan` |
| `Số_lần_lướt` | Số nguyên | Số video lướt duyệt trong phiên chính (vòng lặp `vmyykg1`) |
| `Random1` | 1 - 2 (hoặc 3) | Lựa chọn số lần lướt mồi lúc khởi tạo feed (2, 4, 6 lượt swipe) |
| `Random2` | 1 - 100 | Tỷ lệ ngẫu nhiên cho hành động Thả Tim |
| `%_Tim` | Số nguyên (0-100) | Ngưỡng xác suất thả tim nếu video thuộc bạn bè |
| `Random3` | 1 - 100 | Tỷ lệ ngẫu nhiên cho hành động Bình luận |
| `%_Comment` | Số nguyên (0-100) | Ngưỡng xác suất bình luận |
| `Đường_dẫn_Comment` | Text file path | File chứa danh sách comment (fallback `D:\TiktokComment.txt`) |

---

## 2. Các giai đoạn thực thi (Flow Execution Stages)

### Giai đoạn 1: Dọn dẹp môi trường & Khởi động
1. Bấm phím Recents (`press-key-phone`) -> Tìm và bấm `"Đóng tất cả"` / `"ĐÓNG TẤT CẢ"` / `"CLOSE ALL"`.
2. Bấm `HOME`.
3. Đọc dữ liệu Excel sheet `TaiKhoan!B1:E9999` với khóa chính `phoneId` (gán theo `deviceId`).
4. Chạy JavaScript trích xuất:
   ```javascript
   SetVariable("taiKhoanGanChoPhoneDuocChay", RefData("googleSheets", "taiKhoan")[RefData("variables", "deviceId")]);
   ```
5. Mở package `com.ss.android.ugc.trill` -> Chờ xuất hiện `"Trang chủ"` hoặc `"Home"`.

### Giai đoạn 2: Quản lý & Chuyển đổi tài khoản (Account Switcher)
1. Chuyển sang tab `"Hồ sơ"` / `"Profile"` (`//node[@content-desc="Hồ sơ" or @content-desc="Profile"]`).
2. Tự động đóng các popup hệ thống & quảng cáo:
   - `"Xác minh email của bạn"` -> `"Đóng"`
   - `"Liên kết email"` -> `"Để sau"`
   - `"Truy cập Facebook"` -> `"Không cho phép"`
   - `"Bật lịch sử người xem"` -> `"Lưu"`
   - Slider Captcha -> `//node[@resource-id="verify-bar-close"]`
   - Dialog `"Từ Chối"` -> `"Từ Chối"`
3. So khớp username:
   - Check text `@{{taiKhoanGanChoPhoneDuocChay.taiKhoan}}`.
   - Nếu chưa đúng: Mở menu switch account `//node[@resource-id="com.ss.android.ugc.trill:id/rfm"]/node[2]/node[1]`, tìm đúng nick theo text username và chọn. Dập popup `"Để sau"`.
   - Nếu đúng: Quay lại tab `"Trang chủ"`.

### Giai đoạn 3: Duyệt Feed & Tương tác Bạn Bè (Engagement Loop)
1. **Lướt khởi tạo (Warmup Swipes):**
   - Sinh `Random1` (1-2) để rẽ nhánh điều kiện `pb7esb8`:
     - Path 1: Loop 2 lần swipe up (`b5i4i9u`).
     - Path 2: Loop 4 lần swipe up (`ypacq2w`).
     - Path 3: Loop 6 lần swipe up (`1n4nzj9`).
2. **Vòng lặp tương tác chính (`vmyykg1`):** Lặp `Số_lần_lướt` lần:
   - Swipe up chuyển video.
   - **Xác thực video Bạn Bè:**
     - Match chính: `//node[@text="Bạn bè của bạn"]`.
     - Match phụ / fallback: `//node[@text="Được follow bởi  "]` hoặc `//node[@text="Bạn bè với  "]`.
   - **Thực hiện tương tác:**
     - **Thả Tim:**
       - Kiểm tra nếu đã thích (`//node[@content-desc="Đã thích video"]`) -> Bỏ qua.
       - Nếu chưa: Roll `Random2` (1-100), nếu `Random2 <= %_Tim` -> Bấm `//node[@content-desc="Thích"]`.
       - Roll thêm điều kiện Favorite: nếu `Random2 <= 10` -> Bấm `//node[@content-desc="Thêm hoặc xóa video này khỏi mục Yêu thích."]`.
     - **Bình luận:**
       - Roll `Random3` (1-100), nếu `Random3 <= %_Comment` -> Bấm mở panel bình luận `//node[@content-desc="Đọc hoặc viết bình luận. Bóc tem bình luận"]`.
       - Đọc 1 dòng từ file comment text -> Gõ vào `//node[@text="Thêm bình luận..."]` -> Bấm `"Tán thành"` -> Đóng panel.
   - Luôn trực sẵn handler đóng Captcha (`verify-bar-close`) nếu bất ngờ xuất hiện.
