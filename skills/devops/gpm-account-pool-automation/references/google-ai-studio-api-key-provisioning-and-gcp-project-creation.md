# Google AI Studio API Key Provisioning & GCP Project Creation Protocol

## 1. Bối Cảnh & Cơ Chế Quota (API Studio vs Google One Pro vs Antigravity)
- **Tách Biệt B2C và B2B/Cloud**: Gói Google One AI Premium ($20/tháng - `g1-pro-tier`) chỉ áp dụng cho Web (`gemini.google.com`), Google Drive 2TB và Antigravity IDE (`agy.exe`). Google **không** liên kết gói Pro với hạn mức API trên Google AI Studio.
- **Quota Free Tier**: Mọi tài khoản Google (dù là Gmail thường hay Google Pro) khi tạo API Key trên Google AI Studio đều nhận cùng 1 mức Free Tier:
  - **15 RPM** (Requests Per Minute)
  - **1.000.000 TPM** (Tokens Per Minute)
  - **1.500 RPD** (Requests Per Day - reset 0h UTC)
- Muốn tăng quota API bắt buộc phải bật Cloud Billing (Pay-as-you-go) trên Google Cloud Console, không thể nâng bằng gói Google Pro thông thường.

---

## 2. Quy Trình Tự Động Hóa Lấy API Key Qua CDP (Playwright)

### Bước 1: Khởi động Profile GPM & Onboarding AI Studio
1. Khởi động profile GPM có Google session sống qua Local API (`/api/v3/profiles/start/{id}?win_scale=0.8&addination_args=--mute-audio`).
2. Kết nối Playwright qua `connect_over_cdp` tới `remote_debugging_address`.
3. Điều hướng tới `https://aistudio.google.com/apikey`.
4. Nếu tài khoản chưa từng vào AI Studio, Google tự chuyển hướng về `/onboarding`:
   - Tick checkbox: *"I acknowledge that I am at least 18 years old, and that I am a developer..."* (`input[type='checkbox']`).
   - Bấm `Continue`.
   - Trang khảo sát intent xuất hiện: Bắt buộc chọn nút Skip chính xác bằng role/class (`page.get_by_role("button", name="Skip", exact=True)`), tránh nhầm với thẻ accessibility ngầm `"Skip to main content"`.

### Bước 2: Bẫy "Unable to create API key" trên Tài Khoản Mới
Khi bấm `Create API key` ➔ `Create project`, các tài khoản Gmail nuôi farm / chưa từng kích hoạt Google Cloud sẽ bị lỗi:
> *"Unable to create API key: We were unable to create an API key and Google Cloud project for you. Please create a project in the Cloud Console."*

**Nguyên nhân**: AI Studio không có quyền tự động provision GCP project nền cho các tài khoản chưa chấp thuận ToS của Google Cloud Platform.

### Bước 3: Kích Hoạt Điều Khoản GCP & Tạo Project Thủ Công
1. Mở điều hướng sang: `https://console.cloud.google.com/projectcreate`.
2. **Xử lý ToS Modal (Welcome to Google Cloud)**:
   - Quốc gia mặc định (ví dụ `Vietnam`).
   - Checkbox: *"I agree to the Cloud Platform Terms of Service..."* (`input[type='checkbox']`).
   - Bấm `Agree and continue` (`get_by_role("button", name="Agree and continue")`).
3. **Tạo Project**:
   - Form New Project mở ra: hiển thị quota còn lại (mặc định 12 projects).
   - Tên project tự sinh (ví dụ `My Project 53301`) thuộc `No organization`.
   - Bấm `Create` (`get_by_role("button", name="Create", exact=True)`).
   - Hệ thống chuyển hướng vào GCP Dashboard (`console.cloud.google.com/home/dashboard?creatingProject=true...`).

### Bước 4: Độ Trễ Đồng Bộ (Propagation Delay) Giữa GCP và AI Studio
- GCP Console sau khi tạo project cần từ **3 – 10 phút** để Google Cloud Resource Manager index và đồng bộ metadata sang Google AI Studio.
- Ngay sau khi tạo project trên GCP, nếu quay lại AI Studio bấm `Create API key`, dropdown *"Choose an imported project"* vẫn có thể hiển thị tạm thời `No Cloud Projects Available`.
- Cần chờ polling hoặc cho tài khoản nghỉ cooldown trước khi tái kiểm tra danh sách project trong AI Studio.

---

## 3. Kỷ Luật An Toàn & Bằng Chứng Trực Quan (Gate 6)
- Mọi bước thao tác form ToS, submit project và popup lỗi bắt buộc phải tuân thủ **MAX BLIND STEPS = 1**:
  - Chụp ảnh Pre-submit (sau khi tick checkbox ToS).
  - Chụp ảnh Post-submit (kết quả phản hồi GCP / popup AI Studio).
  - Kiểm tra qua WinRT OCR trước khi phát hành `MEDIA:<path>`.
- Đóng profile GPM ngay sau khi hoàn thành phiên để tránh rò rỉ RAM và giữ an toàn proxy 4G.
