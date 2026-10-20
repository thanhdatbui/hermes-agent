# Google AI Studio API Key Provisioning and GCP Project Import Runbook

## 1. Bối cảnh & Hiện tượng lỗi trên Farm Accounts (GPM Profiles)

Khi tự động hóa cấp Google Gemini API Key từ [Google AI Studio](https://aistudio.google.com/api-keys) trên các profile GPM (tài khoản nuôi / tài khoản farm):
- **Tài khoản cá nhân lâu năm:** Bấm "Create API key" sẽ được Google ngầm tự động tạo GCP project trong 1 giây.
- **Tài khoản Farm / Gmail mới:** Google AI Studio chặn tạo ngầm với lỗi popup:
  > *"Unable to create API key: We were unable to create an API key and Google Cloud project for you. Please create a project in the Cloud Console."*

## 2. Quy trình khắc phục 4 bước chuẩn xác (Deterministic Workflow)

### Bước 1: Kích hoạt Điều khoản GCP & Tạo Project thủ công
1. Điều hướng trình duyệt đến: `https://console.cloud.google.com/projectcreate`.
2. Nếu hiện bảng chào mừng (*Welcome to Google Cloud* / Terms of Service):
   - Tích chọn checkbox: `I agree to the Cloud Platform Terms of Service...`
   - Bấm nút **`Agree and continue`**.
3. Điền hoặc giữ nguyên tên Project mặc định (ví dụ `My Project 53301`), tổ chức để *No organization*.
4. Bấm nút **`Create`** (mỗi tài khoản farm thường có quota 12 projects khả dụng). Chờ 5–10 giây để GCP khởi tạo.

### Bước 2: Kích hoạt panel Import Project trên Google AI Studio
1. Quay lại trang `https://aistudio.google.com/api-keys`.
2. Bấm nút **`Create API key`**.
3. Tại modal *"Create a new key"*, mục *"Choose an imported project"* sẽ hiển thị *"No Cloud Projects Available"*.
4. Mở dropdown và chọn mục **`Import project`** (có icon `cloud_download`).

### Bước 3: Thao tác trên Slide-out Panel "Import projects"
1. Google AI Studio sẽ trượt ra một panel bên phải với tiêu đề *"Import projects"*.
2. Dưới mục *"Projects you may want to import"*, tìm đúng tên project vừa tạo trên GCP (ví dụ `My Project 53301`).
3. Tích chọn checkbox của project đó (trạng thái hiển thị `1 project selected`).
4. **Cạm bẫy DOM nút Import**:
   - Nút Import thực tế nằm ở góc trên bên phải của panel với text: `Import\nkeyboard_return` (class `ms-button-primary`).
   - Lớp phủ backdrop (`cdk-overlay-backdrop`) có thể chặn sự kiện pointer thông thường. Bắt buộc dùng `force=True`, `element.click()` trong evaluate, hoặc click tọa độ chuột chính xác.

### Bước 4: Hoàn tất tạo Key
1. Sau khi Import thành công, panel tự đóng.
2. Modal *"Create a new key"* tự động điền tên project vào *"Choose an imported project"*.
3. Nút **`Create key`** chuyển từ disabled sang khả dụng (`aria-disabled="false"`).
4. Bấm **`Create key`** và chờ 5-10 giây để lấy mã API Key (`AQ.Ab8RN6...`).
5. Đóng dọn sạch Profile GPM qua Local REST API (`/api/v3/profiles/close/{id}`).

## 3. Bản chất Quota API Key vs Tài khoản Pro (Invariant)
- Hạn mức Free Tier của Google AI Studio là **15 RPM**, **1.000.000 TPM**, **1.500 RPD**.
- **Không có sự khác biệt về quota API giữa tài khoản thường và tài khoản Google One Pro ($20/tháng)**. Gói Pro chỉ có giá trị trên Web UI và Antigravity IDE (`g1-pro-tier`), không nâng quota trên `aistudio.google.com`.
- Do đó, hoàn toàn có thể dùng các profile farm Google sống để tạo API key phục vụ các harness coding như `omp` (oh-my-pi) mà không cần dùng tài khoản chính chủ.
