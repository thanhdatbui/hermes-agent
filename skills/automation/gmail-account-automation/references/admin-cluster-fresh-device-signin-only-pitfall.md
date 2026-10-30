# Admin Cluster Fresh Device Onboarding & Sign-In Only WebView Pitfall

## 1. Hiện Tượng (Failure Signature)
- **Triệu chứng:** Khi chạy Reg Gmail trên cụm Farm Admin (Máy 201-280), batch dừng hàng loạt ở bước `[05_create] Không tìm thấy Tạo tài khoản/Create account`.
- **Hiện trường UI XML & Screenshot:**
  - Form Google Sign-in chuẩn hiển thị bình thường: logo Google, ô nhập `identifierId`, link "Bạn quên địa chỉ email?", nút "TIẾP THEO".
  - **Khu vực góc dưới bên trái hoàn toàn trống trơn**, không có node "Tạo tài khoản" / "Create account" trong cả UI XML và visual render.
  - Vuốt cuộn màn hình lên không xuất hiện nút vì WebView không render footer đăng ký.

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)
1. **Fresh Device (0 Account) vs Multi-Account Stack:**
   - Trên máy đã có tài khoản (như Farm Kibe): Gmail mở Inbox -> tap Avatar -> "Thêm tài khoản khác" -> tap "Google". Luồng này kích hoạt intent với tham số cho phép cả Sign-in và SignUp.
   - Trên máy 0 account (Farm Admin sau reset/mới): Gmail khởi động rơi vào màn hình `setup_addresses` ("Thiết lập email"). Khi bấm "Thêm địa chỉ email" -> "Google", Gmail gọi Google Play Services WebView ở chế độ **Sign-in Account Only** (chỉ cho phép đăng nhập tài khoản có sẵn để hoàn tất setup thiết bị).
2. **Khác biệt phiên bản GMS:**
   - Cụm Kibe: GMS `26.42.31`.
   - Cụm Admin: GMS `26.41.31`.

## 3. Quy Trình Đồng Bộ Code Kibe -> Admin-PC An Toàn
- **Cấm copy qua file trung gian OneDrive:** Dễ gặp lỗi `ParseError XML` hoặc `OSError: [Errno 22] Invalid argument` do OneDrive file lock / sync lag.
- **Cơ chế Base64 Chunking Chuẩn qua SSH (`admin_ssh.py`):**
  - Chia nhỏ nội dung file nguồn thành các chunk Base64 (4000 ký tự).
  - Khởi tạo file rỗng trước: `python -c "open(r'dest_path', 'wb').close()"`.
  - Append từng chunk: `python -c "import base64; open(r'dest_path', 'ab').write(base64.b64decode('chunk'))"`.
  - Đối soát mã băm SHA256 hai đầu bằng PowerShell `Get-FileHash ... -Algorithm SHA256` trước khi kích hoạt batch.

## 4. Phân Quyền Manifest & Worker ID Khi Gọi Batch Admin
- Khi kích hoạt `run_all.ps1` trên Admin-PC từ xa:
  - Bắt buộc truyền đúng tham số phân quyền:
    `-assignmentManifest 'C:\Users\Admin\AppData\Local\automation-core\assignments\register-gmail.json' -workerId 'taadaa-writer-admin-farm'`
  - Tránh lỗi sập preflight: `Set GMAIL_ASSIGNMENT_MANIFEST and GMAIL_WORKER_ID before selecting targets` hoặc `assert_owner` mismatch.

## 5. Hướng Xử Lý Màn Hình Sign-In Only
- Không cố gắng bắt fallback tọa độ mù hoặc ép selector `android.widget.Button` khi WebView ở chế độ Sign-in Only.
- Điều hướng luồng tạo tài khoản trên thiết bị 0 account qua Intent thêm tài khoản Android trực tiếp:
  `am start -a android.settings.ADD_ACCOUNT_SETTINGS` hoặc Intent Account Authenticator của Google, tránh đi qua màn hình `setup_addresses` của app Gmail.
