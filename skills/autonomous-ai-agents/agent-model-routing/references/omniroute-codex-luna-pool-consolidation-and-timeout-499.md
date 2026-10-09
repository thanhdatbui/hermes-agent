# OmniRoute Codex Pool Consolidation & Timeout 499 Disconnect Analysis (2026-09-29)

## 1. Bối cảnh sự cố & Triệu chứng thực tế
Trên Dashboard OmniRoute (`:20129`), nhiều request đến `codex/gpt-5.6-luna` bị báo lỗi **HTTP 499** (Client Closed Request) tại các mốc thời gian: `45021ms`, `45790ms`, `46346ms`, `46580ms`, `47022ms`.
Đồng thời phát hiện:
- Request thực tế bị ép chạy `codex/gpt-5.6-luna-medium` thay vì `codex/gpt-5.6-luna-high` như đã chốt trong Tiered Workflow 2.0.
- Tồn tại đồng thời 2 pool song song trong database: `codex-luna` và `codex-luna-pool`.
- Số lượng tài khoản trong pool Luna chỉ có 20 accounts, trong khi pool Terra có 29 accounts và tổng tài khoản Codex trong DB là 38 accounts.

---

## 2. Nguyên nhân gốc rễ (Root Cause Analysis)

### A. Tử huyệt Timeout 45s (`targetTimeoutMs: 45000`) gây lỗi HTTP 499
- Ngày 22/09/2026, combo `codex-luna-pool` được tạo với `targetTimeoutMs: 45000` (45 giây).
- Sau đó combo `codex-luna` được tạo với `targetTimeoutMs: 90000` (90 giây), nhưng combo cha `omni-worker` (Tier 3) vẫn trỏ vào combo cũ `codex-luna-pool`.
- Khi GPT-5.6 Luna sinh thinking tokens ngầm (reasoning effort medium/high) suy nghĩ vượt quá 45 giây $\rightarrow$ OmniRoute tự động ngắt kết nối và trả về mã lỗi 499.

### B. Lệch cấu hình Model trong Pool
- Khi tạo pool vào ngày 22/09, người cấu hình gán cứng `model: "codex/gpt-5.6-luna-medium"`.
- Dù Hermes Coordinator dispatch với `model: "cx/gpt-5.6-luna-high"`, khi đi qua combo `omni-worker` $\rightarrow$ `codex-luna-pool`, OmniRoute thực thi theo model định nghĩa bên trong combo member (`gpt-5.6-luna-medium`), khiến request thực tế bị hạ cấp ngoài ý muốn.

### C. Lệch tài khoản giữa các Pool (Dual-Pool Drift)
- Trong database `storage.sqlite` có 38 kết nối Codex:
  * 7 tài khoản Hotmail vừa ver 5sim đang ngâm 48h (`is_active=0`).
  * 2 tài khoản không khả dụng (`auth.json` expired và `dinhlan` inactive).
  * 9 tài khoản Gmail sống khỏe 100% được thêm vào `codex-terra` nhưng bị bỏ quên, không được thêm vào `codex-luna`.
- Dẫn đến tình trạng `codex-luna` chỉ có 20 accounts (18 live), thiếu hụt 33% công suất so với thực tế 25 accounts live.

### D. Hiểu lầm về trạng thái "Chết" của tài khoản (Web vs Codex)
- Tài khoản `chuloan02122003@gmail.com` từng bị ghi nhận lỗi HTTP 403 trên giao diện **ChatGPT-Web** do Cloudflare Sentinel / Turnstile bot challenge.
- Tuy nhiên trên **Codex CLI**, tài khoản kết nối qua giao thức OAuth PKCE chính thức của OpenAI (`/v1/responses`), hoàn toàn không có Cloudflare Sentinel.
- Kết quả kiểm chứng thực tế: `chuloan` và 8 accounts ứng viên đều phản hồi **Status 200 OK (2.1s - 4.4s)**.

---

## 3. Quy trình chuẩn hóa & Tái cấu trúc (Standardized Architecture)

### 1. Xóa sổ Pool thừa (Single Canonical Pool)
- Chỉ duy trì duy nhất 1 combo chuẩn:
  * **`codex-luna`**: Chứa toàn bộ 25 tài khoản Codex LIVE 100%.
  * **`codex-terra`**: Chứa toàn bộ tài khoản Codex LIVE cho Terra.
- Xóa bỏ hoàn toàn các combo phụ: `codex-luna-pool` và `codex-terra-pool`.
- Cập nhật combo cha `omni-worker`: Tier 3 trỏ trực tiếp sang `codex-luna`.

### 2. Cấu hình Timeout & Model bắt buộc
```json
{
  "name": "codex-luna",
  "strategy": "cache-optimized",
  "config": {
    "targetTimeoutMs": 90000,
    "maxRetries": 1,
    "retryDelayMs": 200,
    "stickyRoundRobinLimit": 8,
    "failoverBeforeRetry": true
  },
  "models": [
    {
      "model": "codex/gpt-5.6-luna-high",
      "providerId": "codex",
      "connectionId": "<cid>"
    }
  ]
}
```

---

## 4. Checklist kiểm tra khi bảo trì Pool OmniRoute
1. **Kiểm tra timeout combo:** Mọi combo chạy thinking models (Luna/Terra/Sol) bắt buộc `targetTimeoutMs >= 90000` (90 giây). Tuyệt đối cấm để 45s.
2. **Kiểm tra độ phủ tài khoản:** Chạy đối soát giữa `provider_connections` (`is_active=1` AND `test_status='active'`) với mảng `models` trong combo để tránh bỏ sót tài khoản.
3. **Phân định rõ ranh giới Web vs OAuth:** Lỗi 403 Sentinel trên `chatgpt-web` không đồng nghĩa tài khoản chết trên `codex`. Luôn probe thực nghiệm qua API trước khi loại bỏ tài khoản khỏi pool.
