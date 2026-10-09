# ChatGPT Web Pool P2C Safety, Dual-Auth Pipeline & Tiered Planning Boundary (2026-09-30)

## 1. Ranh giới T1 vs T2 trong Tiered Workflow 2.0 (User Correction 2026-09-30)

- **T0 (Hiện trường / Kiểm tra):** Gemini Coordinator tự thực thi tại chỗ (đọc log, inspect ADB, check proxy, restart service) trong 5-15s. CẤM gọi Worker hay Planner.
- **T1 (Vá hiện trường / Ốc lỏng <= 15 dòng, 1 file):** **Gemini Coordinator TỰ SỬA TRỰC TIẾP KHÔNG CẦN PLAN**. CẤM gọi Sol hay Terra lập plan cho task T1 vì vi phạm triết lý chống quan liêu và làm tê liệt tốc độ phản ứng của farm.
- **T2 (Thi công phần mềm lớn > 15 dòng, >= 2 file, hoặc chạm lock/watchdog/schema):** BẮT BUỘC theo quy trình 3 bước:
  1. **Lập bản vẽ (T2 Planner):** **Sol High (`chatgpt-web/gpt-5.6-sol-high`)** lập Patch Contract O(1) chuẩn `old_string -> new_string`, anchor duy nhất `c==1`, 1 lệnh test focused <30s (chi phí 0đ quota Codex). *Terra Codex giữ vai trò dự phòng / tham vấn.*
  2. **Thợ vặn ốc (T2 Worker):** **Luna High (`codex/gpt-5.6-luna-high`)** thi công trong Lồng Vô Trùng (`cage_gate.py`, budget <= 30 dòng).
  3. **Nghiệm thu vật lý:** Chạy `python D:/Taadaa/tools/cage_gate.py` xác nhận khách quan.

## 2. Chiến lược an toàn cho ChatGPT-Web Pool (`gpt-web-sol` / `chatgpt-web-pool`)

Dưới góc nhìn bảo mật và chống lạm dụng của OpenAI/Cloudflare, pool ChatGPT-Web được thiết lập với 3 lớp giáp vững chắc:

1. **Thuật toán điều phối P2C (Power of Two Choices):**
   - Không nã tuần tự dồn dập vào 1 acc theo vòng tròn cứng (Round-Robin cố định).
   - Chọn ngẫu nhiên 2 tài khoản bất kỳ trong pool 29 tài khoản, so sánh concurrency/tải thực tế và đẩy request vào tài khoản rảnh hơn.
2. **Triệt tiêu Session Stickiness & Prompt Cache Affinity:**
   - Cấu hình OmniRoute: `disableSessionStickiness: True` và `disablePromptCacheAffinity: True`.
   - Mọi request review / plan đều được rải đều ngẫu nhiên qua toàn bộ 29 tài khoản, ngăn chặn tuyệt đối tình trạng 1 tài khoản bị dồn nhiều request liên tiếp làm nóng IP.
3. **Lớp giáp Proxy di động 4G (1-1 Per-Account Isolation):**
   - 100% tài khoản Web trong bảng `proxy_assignments` đều được map cứng với 1 cổng MobiProxy 4G độc lập (Port 5105, 5113, 5125, 5133...).
   - Mỗi request đi từ một địa chỉ IP di động nhà mạng MobiFone sạch, không bao giờ dùng IP máy chủ hay IP mạng cố định, mô phỏng hoàn hảo 29 người dùng thật độc lập trên mạng di động.

## 3. Quy trình nạp kép (Dual-Auth Pipeline: Web First -> Codex Second)

Để tối ưu hóa tài nguyên và đảm bảo Sol Web luôn có dồi dào tài khoản phục vụ review/planning:
- Khi đăng ký hoặc đăng nhập tài khoản ChatGPT trên profile GPM (cả dạng Google SSO lẫn Direct Email/Password):
  1. **Bước 1 (Nạp Web trước):** Ngay khi Chromium trên GPM vào được màn hình chính `chatgpt.com`, trích xuất ngay cookie `__Secure-next-auth.session-token` (ghép chunk `.0`, `.1` nếu có) -> Nạp vào OmniRoute provider `chatgpt-web`.
  2. **Bước 2 (Ver Codex sau):** Giữ nguyên phiên duyệt, tiếp tục chạy luồng mua số 5SIM để xác thực SMS -> lấy token OAuth nạp vào provider `codex`.
- **Lợi ích:** 1 tài khoản sinh ra phục vụ đồng thời 2 vai trò: vừa làm tài nguyên miễn phí (0đ quota Codex) cho Sol High lập bản vẽ / review, vừa làm tài nguyên thợ thi công cho Luna High qua Codex CLI!
