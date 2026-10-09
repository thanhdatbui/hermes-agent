# Chống lag và crash WPF UI khi load 100-200 profiles trên GPMLogin

## 1. Hiện tượng & Nguyên nhân gốc rễ
- **Hiện tượng 1 (WPF Lag/Crash khi load 100-200 profiles)**: Khi chuyển số lượng hiển thị trên GPMLogin từ 50 lên 100 hoặc 200 profiles / trang, hoặc khi chuyển sang trang 2, giao diện bị đơ cứng, giật lag hoặc hiện vòng xoay tải dữ liệu vô tận (infinite loading spinner).
  - **Nguyên nhân kỹ thuật**: GPMLogin v4.3.x được xây dựng bằng WPF DataGrid (C#/.NET). Giao diện bind trực tiếp các cột hiển thị thông tin fingerprint (UserAgent, WebGL, Canvas, Audio noise, MacAddress...). Nếu trong CSDL `profile_data.db` tồn tại profile có `JsonData` thiếu trường hoặc chỉ là JSON rút gọn (chỉ có 2-6 keys như `Name` và `Proxy`), khi cuộn tới các dòng này, WPF DataGrid sẽ ném ra hàng loạt ngoại lệ ngầm `BindingExpressionException` trong luồng UI Dispatcher. Luồng render bị nghẽn dẫn đến giao diện bị treo hoàn toàn.
- **Hiện tượng 2 (Thứ tự profile bị xáo trộn M60, M42 nhảy trước M13)**:
  - Khi người dùng để chế độ xem mặc định trên GPM: `"Từ cũ đến mới"` (sort theo trường `CreatedAt` trong CSDL `profile_data.db`).
  - Nếu profile M41, M42, M60 được tạo vào các mốc giờ sớm hơn (ví dụ 11:30) so với M13 (tạo lúc 12:00), thì dù tên máy là 60 hay 42 vẫn sẽ bị đẩy lên trước M13.
  - **Khắc phục**: Chuẩn hóa toàn bộ `CreatedAt` trong SQLite `profile_data.db` theo thứ tự máy thực tế: `M01` (10:00), `M02` (10:02), ..., `M13` (10:24), ..., `M42` (11:24), ..., `M60` (12:00)... đảm bảo khi sort "Từ cũ đến mới" bảng luôn xếp thẳng tắp từ Máy 1 đến Máy 80.

---

## 2. Quy tắc bất biến khi tạo hoặc nạp profile mới
1. **TUYỆT ĐỐI CẤM** tạo profile mới với JSON rút gọn (`{"Name": ..., "Proxy": ...}`).
2. **BẮT BUỘC** clone đầy đủ **124 trường schema fingerprint chuẩn** từ donor mẫu (M01).
3. **BẮT BUỘC** randomize riêng biệt `MacAddress` và `AudioNoise` cho từng profile mới để tránh Google gắn cờ máy ảo nhân bản.
4. **Cơ chế tự động đồng bộ (Auto-Schema Sync)**:
   - Trong pipeline nạp tự động (`run_oauth_s7_pipeline.py`), hàm `resolve_profile_dir` luôn tích hợp `ensure_profile_schema_sync`.
   - **Tự động nâng cấp profile cũ (Non-destructive merge)**: Giữ nguyên các key hiện có của profile (`existing_d`), chỉ bổ sung các key thiếu từ donor. Tuyệt đối không ghi đè mất proxy cũ nếu `proxy_str` rỗng, và kiểm tra MAC/AudioNoise trên `existing_d` để tránh dùng lại MAC của donor.
   - **Tránh Nested SQLite Lock trên Windows**: Đóng hoàn toàn kết nối SQLite SELECT trước khi gọi hàm cập nhật ghi `ensure_profile_schema_sync`, tránh lỗi `sqlite3.OperationalError: database is locked`.
   - **Tự động khởi tạo profile mới**: Nếu thư mục profile tồn tại trên đĩa nhưng chưa có bản ghi trong `profile_data.db`, tự động tạo bản ghi mới đầy đủ 124 keys chuẩn (`GroupId = 1`, Proxy theo port, `CreatedAt` timestamp theo thứ tự máy, unique MAC/AudioNoise) trước khi trả về đường dẫn profile.
