# Google AI Studio API Key Provisioning Flow for Fresh/Farm Google Accounts

## 1. Context & Pathology
Khi mở tài khoản Google mới hoặc tài khoản nuôi farm trên GPM để lấy API Key tại Google AI Studio (`aistudio.google.com/apikey`), việc bấm trực tiếp `Create API key` -> `Create project` sẽ bị chặn bởi lỗi:
```text
Unable to create API key
We were unable to create an API key and Google Cloud project for you. Please create a project in the Cloud Console.
```
Nguyên nhân: Google chặn cơ chế tạo ngầm GCP Project tự động đối với các tài khoản mới/chưa có độ trust cao hoặc chưa từng chấp thuận Điều khoản Google Cloud (GCP Terms of Service).

---

## 2. Quy Trình Khắc Phục Chuẩn (Deterministic Provisioning Recipe)

### Bước 1: Kích hoạt GCP Terms of Service & Tạo Project trước
1. Điều hướng CDP/Playwright trực tiếp đến trang tạo project của Google Cloud Console:
   `https://console.cloud.google.com/projectcreate`
2. Nếu tài khoản chưa từng vào GCP, trang sẽ hiển thị modal **"Welcome ... Terms of Service"**:
   - Chọn quốc gia (ví dụ: `Vietnam`).
   - Tích vào checkbox điều khoản: `I agree to the Cloud Platform Terms of Service...` (`input[type="checkbox"]`).
   - Click nút `Agree and continue` (`get_by_role("button", name="Agree and continue")`).
3. Sau khi chấp thuận ToS, form `New Project` xuất hiện:
   - Project name mặc định sẵn (ví dụ: `My Project 53301`).
   - Click nút `Create` (`get_by_role("button", name="Create", exact=True)`).
   - Chờ 5-10s để GCP chuyển hướng về dashboard (`console.cloud.google.com/home/dashboard`).

### Bước 2: Nhập Project vào Google AI Studio (Import Project)
Project tạo trên GCP Console không tự động hiển thị trong dropdown tạo key của AI Studio mà phải qua bước Import:
1. Điều hướng sang `https://aistudio.google.com/api-keys`.
2. Click nút `Create API key` (`get_by_role("button", name="Create API key")`).
3. Modal `Create a new key` mở ra. Mở dropdown `Choose an imported project` (`mat-select`).
4. Click tùy chọn `Import project` (`mat-option:has-text("Import project")`).
5. Một side-panel `Import projects` sẽ mở ra ở cạnh phải màn hình (`x ~ 1110..1900`):
   - Danh sách `Projects you may want to import` sẽ liệt kê project vừa tạo ở Bước 1.
   - Tích chọn checkbox của project cần import.
   - Nút Import thực tế nằm ở góc trên bên phải header danh sách, mang text `Import\nkeyboard_return` (hoặc class `.ms-button-primary` trong panel).
   - *Lưu ý Playwright:* Nếu dialog backdrop (`cdk-overlay-backdrop`) chặn pointer event thông thường, click với `force=True` hoặc click tọa độ `mouse.click(x, y)` theo bounding rect của button.

### Bước 3: Sinh API Key & Verification
1. Sau khi import thành công, panel bên phải đóng lại.
2. Modal `Create a new key` tự động chọn project vừa import vào mục `Choose an imported project`.
3. Nút `Create key` chuyển sang trạng thái khả dụng (`aria-disabled: false`).
4. Click `Create key` và chờ 5-12s.
5. Modal `API key details` xuất hiện với mã key (dạng `AQ.Ab8...`) và project number (`projects/XXXXXXXXX`).
6. Smoke test key qua GET endpoint:
   `https://generativelanguage.googleapis.com/v1beta/models?key=<API_KEY>`
   Xác nhận HTTP 200 và danh sách model khả dụng (Gemini Flash, Pro, Thinking).
7. Đóng profile GPM via API `GET /api/v3/profiles/close/{profile_id}`.
