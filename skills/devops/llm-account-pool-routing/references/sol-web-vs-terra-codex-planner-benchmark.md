# Sol High (ChatGPT-Web) vs Terra (Codex) T2 Planner Benchmark & Pool Sizing

## 1. Kết Quả Giải Đấu 5 Trận (Claude Code CLI Thẩm Định)

Văn bản ghi nhận tại `D:/Taadaa/tools/plan_bench_verdict.md`.
- **Tổng điểm:**
  - 🏆 **Sol High (`chatgpt-web/gpt-5.6-sol-high`):** **85 / 100 điểm** (Thắng 5/5 trận).
  - 🥈 **Terra Codex (`codex/gpt-5.6-terra`):** **62 / 100 điểm**.
- **Lý do Sol High được chọn làm Planner T2 chính thức:**
  1. **Không bị kẹt Lock / Timeout:** Terra dính lỗi timeout 90s khi giải bài toán tranh chấp lock 70 máy; Sol phản hồi đều chằn chặn 15s - 30s.
  2. **Kỷ luật O(1) và Format chuẩn:** Sol xuất đúng định dạng `old_string` -> `new_string` cho thợ Luna thi công ngay lập tức; không bị bệnh "vẽ thêm kiến trúc mới" vượt trần 30 dòng.
  3. **Tiết kiệm 100% Quota Codex:** Chạy trên pool ChatGPT-Web hoàn toàn 0đ quota Codex, để dành toàn bộ quota Codex cho thợ vặn ốc Luna High.

## 2. Chuẩn Hóa Cân Bằng 3 Đại Pool (27 Accounts Mỗi Bên)

- **`codex-luna` (27 accs active):** Model `codex/gpt-5.6-luna-high`, timeout 90s, strategy `p2c`. Phục vụ thợ thi công code trong lồng O(1).
- **`codex-terra` (27 accs active):** Model `codex/gpt-5.6-terra`, timeout 90s, strategy `p2c`. Phục vụ Planner dự phòng.
- **`gpt-web-sol` (27 accs active):** Model `chatgpt-web/gpt-5.6-sol-high`, timeout 120s, strategy `p2c`. Phục vụ Planner T2 chính thức và Giám khảo Chốt phiên (Closeout Gate).

## 3. Lan Truyền Lỗi Banned Giữa Web và Codex

- Khi tài khoản OpenAI bị `AccountDeactivated`:
  - Web: Không thể đăng nhập, báo `{"kind": "AccountDeactivated"}`.
  - Codex: Upstream OpenAI lập tức thu hồi token (`[401]: Encountered invalidated oauth token for user`).
  - **Quy tắc dọn dẹp:** Lập tức tắt `is_active=0` và set `test_status='banned'` trên CẢ 2 provider `chatgpt-web` VÀ `codex`, đồng thời loại bỏ connectionId khỏi các combo để không làm ô nhiễm pool.

## 4. Fallback OpenCode Bridge Timeout Tuning (:20130)

- File: `D:/Taadaa/tools/opencode_bridge.py`.
- Tối thiểu: `timeout = 90` (text) và `timeout = 120` (image). Tránh để timeout 35s làm ngắt kết nối oan uổng khi context dài fallback qua OpenCode.
