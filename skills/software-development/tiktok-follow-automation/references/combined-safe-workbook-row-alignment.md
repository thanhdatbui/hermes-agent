# Combined Safe Workbook & Physical Row Alignment Invariant

## 1. Bối cảnh & Vấn đề
Hệ thống TikTok follow runner sử dụng tham số `--account-row-index` để định vị đúng slot tài khoản của từng máy trên farm (ví dụ M76 chạy row index 4).
Khi tạo file workbook hợp nhất `D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx` từ 2 nguồn (Kibe: M1-80 và Admin: M201-280):
- **Lỗi cũ (Dồn dòng):** Script lọc bỏ các dòng trống (`row[2] is None`) và loại trừ trùng lặp (`seen_uids.add(uid)`).
- **Hậu quả nghiêm trọng:** Nếu máy có slot trống (chưa nạp nick, hoặc nick die đang để trống), việc bỏ dòng làm co rút số hàng vật lý của máy đó. Dẫn đến `--account-row-index 4` trỏ nhầm sang nick của Row 5. Khi đó nick Row 5 có thể chưa đủ điều kiện video/tuổi nick (ví dụ 5 video vs 9 video), dẫn đến Dual Gate khóa `budget = 0` và runner ngắt phiên.

## 2. Quy tắc bất biến (Physical Row Preservation)
1. **Bảo tồn slot vật lý:** Tuyệt đối KHÔNG bỏ các dòng trống của từng máy trong workbook nguồn. Mọi dòng có số máy hợp lệ đều phải được giữ nguyên vị trí trong file combined.
2. **Không loại trừ trùng lặp giữa các máy:** Nếu một UID vô tình xuất hiện ở 2 máy hoặc 2 slot khác nhau, KHÔNG được drop dòng thứ hai; chỉ ghi log cảnh báo (`[WARN] Detected N duplicate UIDs across machines/slots`).
3. **Dependency Injection cho Testability:** Hàm `sync_combined_safe_workbook(kibe_path, admin_path, out_path)` phải hỗ trợ inject đường dẫn tùy biến để có thể viết unit test cô lập offline.

## 3. Canary Hook State Initialization
Khi chạy canary hook chẩn đoán ad-hoc (`--canary-hook open_following_tab`):
- `FollowEngine` bắt buộc phải nhận một instance `FollowState` thực tế (được khởi tạo với `machine` và `account_row_index`), KHÔNG được truyền `None`.
- Nếu truyền `None`, engine sẽ crash ngay tại `engine.state.budget_remaining()`.
- Telemetry đầu ra của canary hook phải ghi nhận `details.state_initialized = True` và `details.budget_remaining`.
