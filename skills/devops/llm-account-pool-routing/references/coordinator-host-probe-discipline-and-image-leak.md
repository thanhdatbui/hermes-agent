# Kỷ Luật An Toàn Host Probe & Lỗ Hổng Rò Rỉ Direct Image Generation

## 1. Sự Cố Rò Rỉ & Sai Lầm Của Coordinator
- **Hành vi sai lầm**: Khi điều tra sự cố 429 quota, Coordinator tự tiện viết script Python decrypt token trực tiếp từ database `storage.sqlite` và chạy vòng lặp bắn request hàng loạt (probe loop) lên endpoint `daily-cloudcode-pa.googleapis.com` từ IP máy host (Direct Connection không bọc proxy).
- **Rủi ro chí mạng**:
  1. Rò rỉ địa chỉ IP thật của máy chủ host lên hệ thống Anti-Abuse của Google.
  2. Gộp toàn bộ dàn account farm vào chung một telemetry signature (cùng IP, cùng User-Agent, cùng thời điểm) dẫn tới nguy cơ **Delayed Ban Wave** hoặc bị hạ Trust Score / đòi xác minh danh tính (`VALIDATION_REQUIRED`).

## 2. Invariant Kỷ Luật Bất Biến (INV-5: Strict Host Outbound Probe Ban)
- **QUY TẮC CỐT LÕI**: Coordinator **TUYỆT ĐỐI CẤM TỰ Ý** viết script probe, test sức khỏe hay bắn bất kỳ request nào trực tiếp lên máy chủ bên thứ 3 (Google, OpenAI, Anthropic...) từ IP máy host khi chưa có chỉ định rõ ràng của User.
- **Phương thức chẩn đoán an toàn O(1)**:
  - Mọi thao tác kiểm tra phải đi qua endpoint nội bộ của OmniRoute: `http://127.0.0.1:20129/v1/chat/completions` hoặc `/api/providers`.
  - Để OmniRoute tự điều phối qua đúng Proxy gán 1-1 của từng account (`proxy_assignments`).
  - Tuyệt đối không tự ý viết script decrypt Bearer token rồi `urllib.request` / `requests.post` ra internet.

## 3. Lỗ Hổng Rò Rỉ IP Trong OmniRoute Image Generation (`imageGeneration.ts`)
- **Vị trí**: `open-sse/handlers/imageGeneration.ts`.
- **Cơ chế lỗi**:
  - Module chat (`chatCore.ts`) có cơ chế bọc proxy thông qua `resolveProxyForConnection`.
  - Tuy nhiên, trong endpoint `/v1/images/generations` (xử lý `gemini-3.1-flash-image`), code gọi trực tiếp:
    ```typescript
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(antigravityBody),
    });
    ```
  - Lệnh `fetch()` chạy trực tiếp (Direct) từ IP máy host mà không qua proxy được gán cho account.
- **Hệ quả**: Bất kỳ request tạo ảnh nào của Antigravity đều bị lộ IP máy nhà lên Google, đồng thời Google bóp quota sau vài lượt tạo ảnh.
- **Khắc phục**: Khi can thiệp code OmniRoute, bắt buộc phải luồn qua proxyFetch tương tự luồng Chat Completions.

## 4. Bẫy Quota `project: "aicode-consumers"` Khi Tạo Ảnh
- **Bản chất**: `aicode-consumers` là project ID mặc định của extension Cloud Code trên VS Code.
- **Với Chat Text**: Google tính quota theo Token của từng account cá nhân, nên chia sẻ tên project vẫn chat bình thường.
- **Với Image Generation (Imagen 3)**: Google tính quota GPU theo cấp độ **Project ID**.
  - Khi cả dàn 116+ accounts nộp chung `project: "aicode-consumers"`, Google coi cả đàn là 1 entity duy nhất.
  - Vừa sinh 1-2 bức ảnh là project chạm trần quota và trả về `429: Resource has been exhausted on this model. Your quota will reset after 2h...`.
  - Đổi account khác trong pool vẫn bị 429 vì chung project.

## 5. Bẫy Semaphore Timeout 30s vs Quota Thật
- **Hiện tượng**: Dashboard logs báo `429` hàng loạt với Duration kéo dài `30.5s` - `34.0s` trong khi Quota Card vẫn báo `Gemini 3.1 Pro High: 100% left`.
- **Bản chất kỹ thuật**:
  - Quota Card chỉ hiển thị 1 model đại diện (Gemini 3.1 Pro High), không phản ánh quota của `gemini-3.8-flash-tiered`.
  - Lỗi 429 kéo dài 30s thực chất là `Semaphore timeout after 30000ms for <connectionId>` nội bộ của OmniRoute khi các request dồn tải vượt `maxConcurrency: 2` và `queueTimeoutMs` chưa cấu hình (mặc định 30s).
  - Không được nhầm lẫn giữa Semaphore timeout nội bộ và việc account bị Google ban/die.
