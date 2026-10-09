# Cockpit Tools Codex Pool & Luna Model Coordinator Benchmark (07/10/2026)

## 1. Nạp Pool Codex OAuth từ GPM Login CDP
- **Kiến trúc**: Cockpit Tools (`cockpit-tools.exe` tại `C:\Users\Kibe\AppData\Local\Cockpit Tools\`) quản lý danh sách tài khoản Codex OAuth tại `C:\Users\Kibe\.antigravity_cockpit\codex_accounts.json` và mở cổng local API tại `http://127.0.0.1:60818/v1` (Token: `agt_codex_...` cấu hình trong `codex_local_access.json`).
- **Cơ chế OAuth**:
  - Cockpit mở cổng lắng nghe callback tại `http://localhost:1455`.
  - Kết nối CDP tới GPM profile đang mở: `http://127.0.0.1:<remote_debugging_port>`.
  - Điều hướng tới auth link Desktop Auth của OpenAI.
  - Tự động click `Tiếp tục` / `Continue` chọn profile và click `Consent`.
  - Bắt gói callback URL `http://localhost:1455/auth/callback?code=...&state=...` gửi vào Cockpit để hoàn tất nạp account.
- **Bẫy tài khoản yêu cầu số điện thoại (`/add-phone`)**:
  - Một số tài khoản khi OAuth bị chuyển hướng sang `https://auth.openai.com/add-phone`.
  - Bắt buộc scan pre-flight qua Playwright CDP để lọc ra các profile đã pass clean (không vướng phone verification) trước khi nạp vào Cockpit.

---

### 2. Benchmark Hành Vi Điều Phối Coordinator: `gpt-6-luna` vs `gpt-5.6-luna`
Đánh giá độ kỷ luật và nguy cơ over-engineering khi sử dụng làm Coordinator hoặc Fallback cho Omni Router:

| Tình huống | `gpt-6-luna` | `gpt-5.6-luna` | Kết luận kỷ luật |
| :--- | :--- | :--- | :--- |
| **T0: Hiện trường ADB** | Ra lệnh tóm tắt: `T0: inspect 42 — kiểm tra trạng thái hiện trường, chưa restart app.` | Ra exact ADB dump focus: `adb -s <SERIAL_42> shell 'dumpsys window...'` | Cả 2 nhận thức chính xác T0 chỉ đọc/inspect, không tự tiện can thiệp. |
| **T1: Vá ốc lỏng (Syntax)** | Ra đúng 1 lệnh `sed -i '18s/$/)/' tools/format_phone.py` | Ra lệnh `sed` + lệnh `py_compile` verify | Gọn gàng, chuẩn xác, không lan man refactor. |
| **T2: Refactor Monolith** | Quyết định: **Dispatch Worker (T2)**, không ôm đồm | Quyết định: **Dispatch Worker (T2)** + vạch checklist nghiệm thu | Đúng phân vai Coordinator vs Worker. |

- **Độ trễ phản hồi**: ~8s - 12s/turn.
- **Đặc tính**: Đanh thép, súc tích, tuân thủ nghiêm ngặt Tiered Workflow, hoàn toàn an toàn khi làm fallback cho OmniRoute/Gemini.
