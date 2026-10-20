# Google AI Studio API Key Provisioning & Quota Pitfalls on GPM Farm Profiles

## 1. Google AI Studio Quota Architecture: Free Tier vs Google One Pro

- **Consumer Subscription vs Developer API Separation**:
  - Gói **Google One AI Premium (Google Pro $20/tháng)** chỉ áp dụng hạn mức cho: Web (`gemini.google.com`), Google Workspace, và Antigravity IDE (`g1-pro-tier` qua internal endpoint `cloudaicompanion.googleapis.com`).
  - Google **KHÔNG** liên kết trạng thái thuê bao Pro với hạn mức API Key trên **Google AI Studio** (`generativelanguage.googleapis.com`).
- **Quota Thật của Google AI Studio Free Tier**:
  - Bất kể tài khoản là Gmail thường hay Gmail Pro, Free Tier quota luôn là:
    * **15 RPM** (Requests Per Minute)
    * **1.000.000 TPM** (Tokens Per Minute)
    * **1.500 RPD** (Requests Per Day - reset 0h UTC / 7h VN)
  - Thinking Tokens (Reasoning) của Gemini Flash Thinking Medium vẫn tính vào Output Tokens và quota TPM.
- **Để tăng quota (Pay-as-you-go)**:
  - Bắt buộc phải gắn Billing Card (Visa/Mastercard) trực tiếp trong Google Cloud Platform (GCP). Khi có billing, RPM tăng lên 1.000 - 4.000, TPM tăng lên 4M+, gỡ bỏ trần 1.500 RPD.

---

## 2. Rào Cản Tạo API Key Tự Động Trên GPM Farm Profiles (GCP Project Creation Gate)

Khi dùng Playwright CDP tự động hóa profile GPM (kể cả Group 10 `Google_Live_Ready` có session sống) để vào `aistudio.google.com/apikey`:

1. **Quy trình Onboarding**:
   - Vượt qua màn hình điều khoản: Checkbox `I acknowledge that I am at least 18 years old...` -> Bấm `Continue`.
   - Màn hình khảo sát: Có thể bấm nút `Skip` (lưu ý nút skip có class `skip-button`, phân biệt với `Skip to main content`).
2. **Bẫy GCP Cloud Project trên tài khoản Farm**:
   - Khi bấm `Create API key` -> Chọn `Create project` -> Bấm `Create project`:
   - Google AI Studio gọi ngầm API provisioning của Google Cloud Resource Manager.
   - Với tài khoản farm/nurtured chưa từng chấp thuận ToS trên Google Cloud Console (`console.cloud.google.com`) hoặc chưa xác minh định danh tin cậy, Google trả về lỗi:
     ```text
     Unable to create API key
     We were unable to create an API key and Google Cloud project for you. Please create a project in the Cloud Console.
     ```
3. **Quy tắc Vận Hành & Khuyến Nghị**:
   - **CẤM** cố gắng tự động hóa bypass lỗi này bằng cách mở `console.cloud.google.com` trên profile farm nếu không có chỉ đạo (nguy cơ kích hoạt phone checkpoint / suspicious activity do privilege escalation).
   - Đối với nhu cầu cấp API Key cho coding harness CLI (`omp`, Aider, OpenCode): Sử dụng tài khoản Google cá nhân chính chủ (đã có GCP project trust cao) lấy key thủ công trong 5 giây, hoặc tận dụng pool tài khoản Pro qua `agy.exe` native.
