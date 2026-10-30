# Passive SQLite Audit vs Active Probe Over-engineering in AI Pool Watchdogs

## 1. Context & Anti-Pattern (Active Probing Over-engineering)
Khi thiết kế watchdog giám sát sức khỏe cho các pool tài khoản LLM upstream (như OmniRoute `:20129` - pool Gemini Pro `ag-gemini-pool-3`):
- **Sai lầm (Over-engineering):** Chạy cron định kỳ lặp qua từng account và bắn request thật lên Google/Anthropic API (active probe như `scan_pro_accounts.py`).
  - Gây tốn quota/token không cần thiết.
  - Tăng nguy cơ dính rate-limit 429 hoặc rolling cooldown cho production.
  - Chạy chậm (hàng chục giây đến vài phút nếu pool có 20-30 accounts).
  - Phức tạp hóa luồng chạy ngầm (dễ bị cron timeout / auto-quarantine).

## 2. Giải pháp Tối ưu: Passive SQLite Audit (O(1)) + Focused Probe Phân Loại
OmniRoute (hoặc bất kỳ API gateway nào) đều lưu nhật ký cuộc gọi trực tiếp vào cơ sở dữ liệu cục bộ (`C:/Users/Kibe/.omniroute/storage.sqlite`, bảng `call_logs`).

### Cửa sổ thời gian tối ưu (Sweet Spot Window: 3 ngày / 72h)
- **Cửa sổ 7 ngày:** Quá trễ. Một account chết/dính validation từ thứ Hai nhưng đến Chủ Nhật mới bị phát hiện; suốt 6 ngày các account khác bị quá tải gánh thay.
- **Cửa sổ 24h:** Dễ sinh báo động giả (False Positive) vào các ngày cuối tuần hoặc khi tải hệ thống thấp.
- **Cửa sổ 3 ngày (72h):** Điểm ngọt tối ưu. Trong một pool có hàng nghìn request/ngày, bất kỳ account khỏe mạnh nào cũng phải có ít nhất vài lượt gọi thành công `200 OK`.

### Quy trình 2 bước tinh gọn (D:/Taadaa/tools/gemini_pool_watchdog.py):
1. **Bước 1 (Passive Scan < 0.05s):** Query SQLite `call_logs` trong 72h qua. Lọc ra danh sách các account trong combo có `COUNT(status = 200) == 0`.
2. **Bước 2 (Focused Probe phân loại đúng acc bị flag):**
   Chỉ bắn 1 request cực nhẹ (`max_tokens: 1`) kẹp header `x-omniroute-connection: <CID>` vào đúng các account bị flag:
   - **`BLOCKED (403)`:** Body chứa `VALIDATION_REQUIRED` hoặc `Verify your account` -> Google bắt xác thực / mã QR -> Cần mở Profile GPM quét QR/reauth.
   - **`DEAD / DOWNGRADED`:** `is_active = 0` hoặc metadata `tier = free-tier` -> Tài khoản rớt gói Pro / hết hạn -> Dọn dẹp gỡ CID khỏi combo (`--fix-remove-dead`).
   - **`HEALTHY (200 OK) / STARVED`:** Probe trả về `200 OK`. Tài khoản hoàn toàn bình thường nhưng bị "đói tải" do thuật toán điều phối `least-used` đang dồn tải cho các account mới có ít request hơn tích lũy cày bù.
