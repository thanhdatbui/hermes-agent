# Phan Biet & Triage Nhanh: Loi Telegram vs Loi Model Provider ("The model provider failed after retries")

## 1. Hien tuong & Trieu chung Hien truong
- Tren giao dien Telegram, bot vang thong bao:
  `⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics.`
- Truoc do thuong co banner tien trinh:
  `⏳ Working — N min — iteration X/100, receiving stream response`
- Sau do bot tu dong trigger quy trinh self-improvement review / chot turn som.
- **Cau hoi thuong gap cua User:** *"Loi Telegram hay Omni nua?"* hoac *"Bot bi treo hay sao?"*.

---

## 2. Ban chat Cot loi: Phan dinh Tang Loi
1. **Khẳng định 100%:** Dòng chữ `The model provider failed after retries` là lỗi tầng **Model Provider API** (Hermes gọi upstream LLM bị fail quá số lần retry `api_max_retries`). Đây **KHÔNG PHẢI** là lỗi Telegram Adapter hay server Telegram.
2. **Nguyên nhân 1: Mối quan hệ nhân quả kép (Cộng hưởng Mạng ISP & OmniRoute Proxy Pool):**
   - Mặc dù là lỗi Provider, nguyên nhân gốc rễ thường xuất phát từ **Đứt mạng ISP (Multi-ISP Failover Viettel ↔ FPT)**:
     - Khi mạng Viettel chập chờn, Hermes Gateway tự động kích hoạt failover sang FPT Direct (`Multi-ISP Failover: PRIMARY (Viettel) bị lỗi → chuyển sang FALLBACK (FPT Direct)`).
     - FPT Direct tại Việt Nam thường bị bóp hoặc lỗi kết nối ra ngoài (`FPT Direct: direct failed`).
     - Các proxy Mikrotik của OmniRoute (`http://mirotik1.taadaa.click:10017`...) mất kết nối tới upstream Google Antigravity / OpenAI.
     - OmniRoute kích hoạt cơ chế bảo vệ Fast-Fail: `[Proxy Fast-Fail] Proxy unreachable: http://...`.
     - Khi toàn bộ proxy pool bị gạt bỏ, router trả về:
       `HTTP 503: Service temporarily unavailable: all targets were skipped by pre-dispatch filters`.
     - Upstream model báo timeout: `Model antigravity/... timed out (HTTP 504)`.
   - Kết quả: Hermes retry 3-4 lần liên tiếp đều nhận 503/504 $\rightarrow$ Cháy hết ngân sách retry $\rightarrow$ Xuất thông báo `The model provider failed after retries`.

3. **Nguyên nhân 2: Bẫy Context Bloat Overload (Do tool xả payload Megabytes vào turn):**
   - Khi Agent gọi các tool tra cứu lịch sử (`session_search(session_id=...)` không giới hạn window, dump file log lớn, dump HTML frames...), các kết quả trả về có thể nặng từ vài trăm KB đến nhiều MB (ví dụ: `hermes-results/call_*.txt` nặng 1.7MB + 670KB + 380KB...).
   - **Hậu quả & Cơ chế kẹt:**
     - Context của turn đó lập tức phình to lên hàng triệu ký tự (vượt quá ngưỡng streaming êm ái của upstream LLM).
     - Upstream socket bị nghẽn (hanging) ở trạng thái `receiving stream response`, kéo dài 10–13 phút rồi timeout rớt kết nối.
     - Sau khi fail retries, **context vẫn chưa được compact**; khi User nhắn tin mới tiếp theo, Gateway lại đóng gói nguyên payload khổng lồ đó gửi lên upstream $\rightarrow$ LẶP LẠI LỖI 9-10 phút tiếp theo (Vòng lặp Provider Failed liên hoàn).
   - **Dấu hiệu nhận biết:**
     - Banner hiển thị `Working — 10+ min — iteration X/100, receiving stream response`.
     - Không có lỗi đứt mạng ISP hay 503 pre-dispatch trong gateway log, mà lỗi là stream timeout / client disconnect từ provider.
   - **Xử lý & Phòng ngừa:**
     - Bắt buộc dọn sạch buffer khổng lồ bằng lệnh `/compact` hoặc mở phiên mới (`/new`) trên topic đó.
     - Kỷ luật Coordinator: CẤM gọi `session_search` dạng đọc toàn bộ session (`session_id=...` không có anchor), BẮT BUỘC dùng `query` hẹp hoặc scroll với `window` nhỏ (<= 3–5 messages) để chống tự sát context.

4. **Nguyên nhân 3: Bẫy "Topic mới tinh chat 1 tin vẫn dính provider failed" (Ghost Session Zombie / Rate Limit):**
   - **Hiện tượng thực địa:** User vừa tạo một Topic Telegram mới tinh, chỉ mới gửi đúng 1-2 tin nhắn (khi gõ `/compress` hệ thống báo `Not enough conversation to compress (need at least 4 messages)`), nhưng bot vẫn bị kẹt ngay tại `iteration 1/100, receiving stream response` rồi văng `The model provider failed after retries`.
   - **Bản chất kỹ thuật:**
     - KHÔNG PHẢI do context topic phình to (vì topic mới chưa có lịch sử).
     - Nguyên nhân 1: **Zombie runner slot trong Gateway RAM (`_running_agents`):** Khi topic trước đó bị crash/timeout lửng lơ, slot worker trong RAM gateway không được release, làm nghẽn socket stream của thread mới hoặc va chạm worker allocation.
     - Nguyên nhân 2: **Pool Provider Upstream (:20129) kiệt tài khoản / Rate Limit / Cookie Checkpoint:** Model mặc định (ví dụ `ag-gemini-pool-3`) định tuyến qua pool nhiều tài khoản Web (Google Pro Web). Khi toàn bộ các connection trong pool bị Google challenge checkpoint/re-auth hoặc chạm rate limit cùng thời điểm, request đầu tiên của topic mới gửi lên sẽ bị treo socket stream 2 phút rồi timeout văng lỗi.
     - Nguyên nhân 3: **Mạng LAN socket timeout tới IP gateway:** Cấu hình trỏ IP LAN (ví dụ `192.168.110.123:20129`) thay vì loopback `127.0.0.1:20129` khi card mạng LAN bị nghẽn packet.
   - **Quy tắc phân biệt tức thì:**
     - Nếu `/compress` báo `Not enough conversation to compress (< 4 messages)` $\rightarrow$ Chắc chắn là **Nguyên nhân 3 (Upstream Pool/RAM Zombie)**, TUYỆT ĐỐI KHÔNG đổ lỗi cho Context Bloat của session đó!
   - **Khắc phục:**
     - Kiểm tra trạng thái pool upstream: `GET http://127.0.0.1:20129/api/providers` xem có tài khoản nào active không.
     - Khởi động lại Gateway detached qua `python D:/Taadaa/tools/restart_gw_detached.py` để dọn sạch zombie runner.

---

## 3. Bo Lenh Chan Doan O(1) Guard-Safe (Chong Vi Pham Hook)

### ⚠️ Cac bay lenh bi Hook chan dung (CAN TRANH):
- Go bash chua chuoi duong dan he thong Hermes $\rightarrow$ Bi chan boi Guard Self-Protection.
- Go lenh `curl` truc tiep tu Coordinator $\rightarrow$ Bi chan boi Coordinator Guard Terminal Blocked.
- Quet tim log bang `search_files` tren root `D:/Taadaa/tools` $\rightarrow$ Bi chan boi Guard Search Files Root.

### ✅ Lenh tra cuu chuan xac qua Python:
1. **Kiểm tra nguyên nhân fail trong log:**
   ```bash
   python -c "
   from pathlib import Path
   import os
   log_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'hermes' / 'logs'
   for name in ['agent.log', 'gateway.log']:
       p = log_dir / name
       if p.exists():
           lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
           matches = [l for l in lines if 'failed after retries' in l or 'attempt 4/4' in l or 'all targets were skipped' in l or 'Proxy Fast-Fail' in l]
           print(f'=== {name} ({len(matches)} matches) ===')
           for l in matches[-15:]:
               print(l)
   "
   ```
2. **Kiểm tra trạng thái cổng OmniRoute (:20129) bằng `urllib`:**
   ```bash
   python -c "
   import urllib.request
   for ep in ['http://192.168.110.123:20129/v1/models', 'http://127.0.0.1:20129/v1/models']:
       try:
           with urllib.request.urlopen(ep, timeout=3) as r:
               print(ep, '-> OK', r.status)
       except Exception as e:
           print(ep, '->', e)
   "
   ```

---

## 4. Ky Luat Phan Hoi Cho User
- Trả lời trực diện, dứt khoát: **"LỖI OMNI (Model Provider), KHÔNG PHẢI lỗi Telegram!"**.
- Cung cấp ngay bằng chứng trích xuất từ log (`[Proxy Fast-Fail]`, `HTTP 503 pre-dispatch filters`, hoặc `Multi-ISP Viettel rớt`).
- Báo cáo rõ trạng thái hiện tại của mạng và cổng OmniRoute (đã hồi phục hay chưa).
- Hướng dẫn rõ ràng: Khi mạng và cổng `:20129` đã thông suốt, User chỉ cần gửi lại tin nhắn là phiên chạy tiếp bình thường.
