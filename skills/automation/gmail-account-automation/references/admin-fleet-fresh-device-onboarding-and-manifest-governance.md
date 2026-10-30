# Admin Fleet Gmail Registration: Fresh Device Onboarding Trap & Dual-Cluster SSH Orchestration

**Ngày cập nhật:** 2026-10-30  
**Bối cảnh:** Lỗi toàn bộ 15 máy trên Admin-PC rơi vào `[05_create] Không tìm thấy Tạo tài khoản/Create account`.

---

## 1. Tử Huyệt: Fresh Device (0 Account) Bị Ép Vào Sign-in Only

### A. Cơ chế gây lỗi
- Trên cụm Kibe (Máy 1-80), phần lớn máy đã có sẵn tài khoản cũ trong Gmail. Luồng mở Gmail đi vào Inbox $\rightarrow$ tap Avatar $\rightarrow$ *"Thêm tài khoản khác"* $\rightarrow$ *"Google"*. Google nhận diện đây là hành động thêm tài khoản phụ từ người dùng đã đăng nhập nên hiển thị đầy đủ nút **"Tạo tài khoản" (Create account)**.
- Trên cụm Admin (Máy 201-280), nhiều máy là **Fresh Device (0 tài khoản)**:
  1. Khi mở Gmail sau khi xóa data / fresh state, app rơi vào màn hình `setup_addresses` (*"Thiết lập email"*).
  2. Script bấm *"Thêm địa chỉ email"* $\rightarrow$ chọn *"Google"*.
  3. WebView của Google Play Services (nhất là các bản GMS cũ hơn như 26.41.x) chuyển hướng sang luồng First-time Setup / Onboarding ép cứng ở chế độ **Sign-in Only**.
  4. Màn hình chỉ render ô Email/SĐT và nút "TIẾP THEO". Góc dưới bên trái hoàn toàn **KHÔNG CÓ nút Tạo tài khoản**, kể cả khi đã vuốt cuộn WebView lên.

### B. Hướng xử lý kiến trúc
- Với máy 0 account, không đi qua Gmail First-time Onboarding flow để reg tài khoản mới.
- Khởi động trực tiếp Intent Account Manager của Android:
  `am start -a android.settings.ADD_ACCOUNT_SETTINGS --esa account_types 'com.google'`
  hoặc intent đăng ký tài khoản Google trực tiếp.

---

## 2. Quy Chuẩn Đồng Bộ Code và Phân Quyền Khi Dispatch Sang Admin-PC

### A. Canonical Code Sync Bằng Base64 Chunking
- Tuyệt đối không dùng `Copy-Item` qua PowerShell hay `shutil.copy2` trực tiếp từ UNC share nếu chưa map drive / thiếu quyền.
- Dùng script chia chunk Base64 (4000 ký tự) đẩy qua SSH execution:
  `python -c "import base64; open(dest, 'ab').write(base64.b64decode('...'))"`
- Sau khi sync, BẮT BUỘC đối soát mã SHA256 (`Get-FileHash ... -Algorithm SHA256`) giữa 2 máy.

### B. Bẫy Assignment Manifest Khi Chạy `run_all.ps1` Trên Admin
- `run_parallel.ps1` có cơ chế chốt chặn `assert_owner` và `assert_assigned` trong file manifest `register-gmail.json`.
- Khi kích hoạt `run_all.ps1` từ xa qua SSH trên cụm Admin, BẮT BUỘC phải truyền đủ:
  `-assignmentManifest 'C:\Users\Admin\AppData\Local\automation-core\assignments\register-gmail.json' -workerId 'taadaa-writer-admin-farm'`
- Nếu thiếu 2 tham số này, runner sẽ crash ngay tại dòng 565: `throw "Set GMAIL_ASSIGNMENT_MANIFEST and GMAIL_WORKER_ID before selecting targets."` hoặc văng ngoại lệ `OwnerMismatch`.
