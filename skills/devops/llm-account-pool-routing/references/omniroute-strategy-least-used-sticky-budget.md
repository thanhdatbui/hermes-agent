# OmniRoute Strategy Tuning: Least-Used, Headroom Pitfall, and Subagent Sticky Budget

## 1. Headroom Strategy Pathology in Large Proxy Pools (>10 Accounts)
- **Cơ chế lý thuyết:** `headroom` tính 1 - max(util_5h, util_7d) để chọn connection có % dung lượng rảnh cao nhất.
- **Pitfall thực tế:** `orderTargetsByHeadroom` gọi `mapWithConcurrency(expandedTargets, 5, fetchSaturation)` trước mỗi request. Với pool 18-20 accounts, OmniRoute phải bắn gần 40 sub-requests kiểm tra saturation qua HTTP/Proxy sang Google.
- **Hậu quả:** Khi proxy có độ trễ hoặc cúp điện, overhead preflight vượt quá 30 giây -> Client / Hermes dính `499 Client Closed Request` hoặc timeout ngay lập tức trước khi kịp gửi prompt thật.
- **Khuyến cáo:** Tuyệt đối KHÔNG dùng `headroom` cho pool >10 accounts chạy qua proxy farm có độ trễ.

## 2. Least-Used: The Zero-Overhead Balance
- **Cơ chế:** Đọc trực tiếp từ in-memory `metrics.byTarget[executionKey].requests`. Không có network overhead (0ms).
- **Hiệu quả:**
  - Tự động ưu tiên account có ít request nhất từ sáng đến giờ (acc còn 100% quota như vừa kích hoạt hoặc chưa ai đụng).
  - Tự động hạ ưu tiên các account đã bị cày nhiều, cho thời gian nguội và hồi quota.
  - Phù hợp hoàn hảo cho cả Pool Gemini Pro và Pool Codex/Claude AG.

## 3. Session Stickiness Alignment with Worker Subagent Budget
- **Vấn đề:** 
  - Subagent worker (Codex, Claude, Luna) có ngân sách tối đa 15 tool calls per task.
  - Nếu `stickyRoundRobinLimit` quá nhỏ (ví dụ 6 turns): Subagent đang làm dở turn 7 thì bị tráo sang account khác -> Anthropic/OpenAI/Google mất Prompt Cache -> phải nạp lại toàn bộ context từ đầu, token tăng vọt và latency chậm gấp đôi.
  - Nếu `stickyRoundRobinLimit` quá lớn (>25 turns): 1 account bị dồn quá nhiều task liên tiếp.
- **Quy tắc vàng:** Đặt `stickyRoundRobinLimit: 15` khớp chính xác với ngân sách tối đa 15 calls của Worker Subagent.
  - Trọn vẹn 1 task nằm trên 1 account -> Ăn trọn 100% Prompt Cache.
  - Tự động thoát an toàn: `sessionStickiness.ts` có logic kiểm tra nếu account dính `429`, hết quota hoặc lỗi kết nối thì tự động gọi `clearStickyBinding` để tráo account ngay lập tức, không bắt client chịu trận.
  - Xong task (hết 15 calls), `least-used` tự động nhả account cũ và chọn account rảnh nhất tiếp theo cho task mới.

## 4. Pool ChatGPT Web: Sống sót là ưu tiên số 1
- **Đặc thù:** Web session tự reset request limit mỗi vài tiếng; gửi dồn dập vào 1 session sẽ bị Cloudflare hoặc OpenAI checkpoint khóa nick.
- **Cấu hình tối ưu:**
  - `strategy`: `p2c` (Power of Two Choices - bốc ngẫu nhiên 2 acc, chọn acc latency thấp và success rate cao).
  - `disableSessionStickiness`: `true` (Tắt stickiness để tản đều toàn bộ N accounts, chống dồn cục).
  - `queueTimeoutMs`: `1000` (Xếp hàng tối đa 1s, nghẽn là trượt sang account khác).
