# Google AI Studio API Key Provisioning via GPM & GCP Project Import

## Context & Problem
Khi tự động hóa cấp phát Gemini API Key trên Google AI Studio (`aistudio.google.com/apikey`) cho tài khoản Google farm / profile GPM:
- Bấm **Create API key** trực tiếp thường bị lỗi:
  > *"Unable to create API key: We were unable to create an API key and Google Cloud project for you. Please create a project in the Cloud Console."*
- **Nguyên nhân**: Google AI Studio không thể tự động kích hoạt GCP project ngầm cho tài khoản mới hoặc tài khoản chưa từng chấp thuận điều khoản Google Cloud Platform (chống lạm dụng bot).

## Canonical Resolution Workflow (Zero-Human Provisioning)

### Bước 1: Kích hoạt GCP Project trên Cloud Console
1. Mở profile GPM qua Local API (`http://127.0.0.1:19995/api/v3/profiles/start/{id}`).
2. Kết nối Playwright qua CDP (`connect_over_cdp`).
3. Điều hướng đến `https://console.cloud.google.com/projectcreate`.
4. **Chấp thuận ToS nếu xuất hiện**:
   - Tích checkbox: `input[type="checkbox"]` (*"I agree to the Cloud Platform Terms of Service..."*).
   - Click button `Agree and continue`.
5. **Tạo Project mới**:
   - Click button `Create` (với Project name mặc định, ví dụ `My Project XXXXX`).
   - Đợi 5s - 10s để máy chủ Google Cloud khởi tạo xong và điều hướng về Cloud Dashboard.

### Bước 2: Đồng bộ & Import Project vào Google AI Studio
1. Điều hướng về `https://aistudio.google.com/api-keys`.
2. Click button `Create API key`.
3. Trong modal *Create a new key*, mở dropdown *Choose an imported project*.
4. Nếu dropdown chỉ có 2 mục (*Import project* và *Create project*):
   - Chọn mục **`Import project`** (có icon `cloud_download`).
   - Panel bên phải xuất hiện danh sách: *"Projects you may want to import"*.
   - Tích chọn checkbox tương ứng với project vừa tạo ở Bước 1.
   - Click button **`Import`** (nút màu xanh có text `Import\nkeyboard_return` nằm ở góc trên bên phải panel).

### Bước 3: Tạo & Trích xuất API Key
1. Sau khi Import thành công, panel tự đóng và dropdown *Choose an imported project* tự động gán project vừa import.
2. Nút **`Create key`** chuyển từ disabled sang enabled (`aria-disabled="false"`).
3. Click `Create key` và đợi 5s - 10s.
4. Trích xuất text API Key từ modal *API key details*.
5. Đóng profile GPM qua API `http://127.0.0.1:19995/api/v3/profiles/close/{id}`.

### Bước 4: Kiểm chứng Live API Key
Gọi endpoint REST công khai để xác nhận key live ngay lập tức:
```python
import urllib.request, json
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
with urllib.request.urlopen(url, timeout=10) as resp:
    data = json.loads(resp.read().decode())
    assert len(data.get("models", [])) >= 40
```
Key này thuộc Free Tier (15 RPM, 1.500 RPD), mở khóa toàn bộ Gemini 2.5/3.x Flash/Thinking/Pro, kết nối 1st-party trực tiếp với Google.
