# Hotmail Lifecycle WAITING Status Unblocking & Readiness Alignment

## 1. Bối Cảnh Lỗi Kẹt Tiến Trình (The 'WAITING' Starvation Pitfall)
Trong bộ lập lịch `batch_gpm_5profiles_supervisor.py`, các tài khoản ngâm ở giai đoạn `WAIT_7D` khi chưa đủ tuổi hoặc đang trong chu kỳ ngâm sẽ được hàm transition gán:
```python
"status": "COMPLETED" if ready else "WAITING"
```
Tuy nhiên, trong bộ lọc ứng viên `select_candidates()`, điều kiện loại trừ trước đây lại chặn nhầm cả `WAITING`:
```python
# LỖI: Chặn cả trạng thái WAITING khiến nick đủ 7 ngày không bao giờ được bốc lại!
if status in {"WAITING", "FAILED", "ERROR", "BLOCKED", "QUARANTINE"}:
    continue
```
Điều này dẫn đến tình trạng: Hàng trăm tài khoản đã ngâm đủ 7 ngày (thậm chí 8 - 13 ngày) và đủ điều kiện TikTok/ChatGPT vẫn bị "bỏ đói" (starved), không bao giờ được thăng cấp sang `CHANGE_INFO`.

## 2. Giải Pháp Chuẩn Hóa
1. **Gỡ bỏ `"WAITING"` khỏi danh sách loại trừ trạng thái lỗi cứng**:
   - Chỉ chặn: `{"FAILED", "ERROR", "BLOCKED", "QUARANTINE"}`.
   - Trạng thái `WAITING` là hợp lệ để bộ lập lịch tiếp tục kiểm tra điều kiện `anchor_time >= 7 days`.
2. **Kiểm tra đồng thời 3 điều kiện thăng cấp `WAIT_7D` -> `CHANGE_INFO`**:
   - `soaked`: Thời gian từ `hotmail_login_at` / `chatgpt_registered_at` / `codex_oauth_at` đã qua đủ $\ge 7 \times 86400$ giây.
   - `has_tiktok`: Cột ID và PASS TikTok có dữ liệu.
   - `has_chatgpt`: Cột 12 `PASS CHATGPT` có dữ liệu (đồng bộ tuyệt đối, không fallback sang PASS MAIL).
3. **Cơ chế Cooldown Proxy Port**:
   - Mỗi port proxy / IP chỉ xử lý 1 action `WAIT_7D` hoặc `CHANGE_INFO` trong vòng 24h để bảo toàn uy tín IP.

## 3. Quy Trình Xác Minh Bằng Chứng (Dry-Run / Live)
Trước khi bàn giao hoặc chốt phiên, bắt buộc kiểm tra danh sách candidate thực tế:
```bash
python "D:/Taadaa/GPM auto/scripts/batch_gpm_5profiles_supervisor.py" --dry-run
```
Kỳ vọng: Xuất hiện `CANDIDATES=5 DISTINCT_PROXY_PORTS=5` và danh sách nick chuyển tiếp sang `CHANGE_INFO` thay vì mảng rỗng `[]`.
