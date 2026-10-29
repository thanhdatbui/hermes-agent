# Quản Trị Pool Web Reverse (Gemini Web Argon / ChatGPT Sol) & Kỷ Luật Cooldown Tự Động

Tài liệu ghi nhận các bài học xương máu và quy trình chuẩn hóa từ phiên xử lý pool web reverse (:20129) ngày 29/10/2026.

---

## 1. Kỷ Luật Cooldown Tuyệt Đối (Chống Xóa / Tắt Acc Bừa Bãi)
- **Tiên đề cốt lõi:** Khi một account trong pool web bị lỗi (ví dụ HTTP 401 hết session cookie, hoặc Cloudflare Turnstile / ChatGPT Sentinel block 403, hoặc proxy mạng chập chờn):
  - **CẤM TUYỆT ĐỐI:** Tắt tài khoản vĩnh viễn (`is_active = 0`) hoặc xóa bỏ entry khỏi combo router. Hành động này làm cụt pool vĩnh viễn và triệt tiêu khả năng tự phục hồi.
  - **BẮT BUỘC:** Đưa vào cơ chế **Cooldown tạm thời**:
    - Trong OmniRoute SQLite: Set `rate_limited_until` theo chuẩn ISO UTC tương lai (ví dụ +30 phút hoặc +24h tùy mức độ lỗi).
    - Cập nhật combo: Thiết lập config `disableSessionStickiness: true` và `failoverBeforeRetry: true` để router tự động nhảy cóc qua acc lỗi, bốc acc khỏe mạnh tiếp theo thay vì ném lỗi `503 Service Unavailable`.
    - Sau khi hết thời gian cooldown, hàm `isAccountUnavailable()` của router sẽ tự động nhả acc về trạng thái sẵn sàng (`ready`) mà không cần can thiệp thủ công.

---

## 2. Quy Trình Nạp Pool Gemini Web Qua GPM CDP (Chuẩn Tự Động)
- **Bản chất xác thực:** `gemini-web` yêu cầu session cookie: `__Secure-1PSID` và `__Secure-1PSIDTS`.
- **Phương pháp trích xuất tự động qua CDP WebSocket (Không cần Playwright cồng kềnh):**
  1. Lấy danh sách profile Google Pro (`g1-pro-tier`) từ GPM API (`http://127.0.0.1:19995/api/v3/profiles`).
  2. Mở profile: `POST /api/v3/profiles/start/{id}` lấy `remote_debugging_address`.
  3. Kết nối WebSocket qua module `websockets` tới tab page (`Page.navigate` tới `https://gemini.google.com/app`).
  4. Đợi trang load và gọi `Network.getCookies` cho các domain `.google.com`.
  5. Trích xuất cookie và đóng profile: `GET /api/v3/profiles/close/{id}`.
  6. Insert vào `provider_connections` với `provider = 'gemini-web'`, gán kèm đúng proxy 1:1 từ GPM (`raw_proxy`).
  7. Đồng bộ danh sách connection vào combo `gemini-web-argon-pool`.

---

## 3. Phân Vai Hệ Thống: Coordinator vs Worker
- **Gemini Web Argon 4:**
  - **Làm Coordinator:** ❌ **Không phù hợp**. Vì chạy qua giao diện Web nên không hỗ trợ OpenAI-standard JSON Function Calling (`tool_calls: null`). Khi context dài (>20k tokens) hoặc mang theo tool schemas, model hiểu nhầm thành extension của Google (như đòi kết nối Google Drive) và không kích hoạt được công cụ hệ thống của Hermes.
  - **Làm Worker ($O(1)$ Code Surgery):** ✅ **Cực kỳ xuất sắc**. Khi bọc qua wrapper ReAct (`gemini_web_worker.py`), model phân tích diff và patch code chỉ mất **6s – 18s/task**, pass test 100%, 0đ chi phí token.
- **Antigravity CLI (Gemini 3.8 Flash High):**
  - Giữ vai trò **Coordinator** hoặc **Tier 2 Architect Worker**: Giữ context triệu token, hỗ trợ native tool-calling tuyệt đối, phòng thủ cao.
