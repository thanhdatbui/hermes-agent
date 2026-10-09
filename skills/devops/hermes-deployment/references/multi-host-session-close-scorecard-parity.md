# Multi-Host Session-Close Scorecard Parity (Kibe ↔ Admin)

## Bối cảnh sự cố (17/09/2026)
Sau khi đồng bộ toàn bộ 7 Shell Hooks từ Kibe sang Admin (`guard_dispatch_contract.py`, `guard_progress_supervisor.py`,...), máy Admin vẫn bỏ qua bước gọi AI Reviewer chấm điểm khi chốt phiên, chỉ chạy unit test rồi báo cáo hoàn thành ngay.

## Phân tích kỹ thuật & Cơ chế vận hành

### 1. Giới hạn của Shell Hooks trong Hermes
- Các shell hook (`hooks.pre_tool_call`, `hooks.post_tool_call`) chỉ bắt các sự kiện gọi tool (`terminal`, `read_file`, `delegate_task`, `search_files`).
- Hermes hoàn toàn không có hook bắt sự kiện nhận tin nhắn ("on_message" / "on_session_close").
- Do đó, hành động chốt phiên khi user nhắn `"chốt phiên"` hoàn toàn do **LLM Agent quyết định dựa trên System Prompt, Skills và Memory**.

### 2. Sự khác biệt giữa Kibe và Admin
| Thành phần | Máy Kibe (Chính) | Máy Admin (Phụ) |
| :--- | :--- | :--- |
| **Vai trò** | Host proxy OmniRoute (`:20129`) & 9Router (`:20128`) | Client kết nối qua IP LAN (`192.168.110.123`) |
| **Quy tắc chốt phiên** | Nằm trong Persistent Memory & System Prompt | Chưa được nạp vào System Prompt (`config.yaml`) |
| **Endpoint `sol_auditor.py`** | Mặc định gọi `127.0.0.1:20129` thành công | Bị `Connection refused` nếu không có `OMNI_ROUTE_URL` |
| **Behavior** | Tự động gom test + git diff -> Sol Web chấm Scorecard | Bị bệnh tự mãn (sycophancy): thấy unit test pass là chốt luôn |

## Giải pháp chuẩn hóa đa máy

### 1. Khóa quy tắc vào System Prompt của Admin (`config.yaml`)
Trong các cấu hình personality hoặc system prompt của bot Admin:
```yaml
# QUY TẮC CHỐT PHIÊN BẮT BUỘC (SESSION CLOSE INVARIANT):
Khi nhận lệnh 'chốt phiên', 'đóng phiên':
1. BẮT BUỘC tự thu thập git diff và test evidence thực tế.
2. BẮT BUỘC gọi Sol Auditor qua script `python D:/Taadaa/tools/sol_auditor.py` (hoặc gửi request sang OmniRoute http://192.168.110.123:20129/v1/chat/completions model review/gpt-5.6-sol-high) để lấy JSON Scorecard (thang 100đ).
3. CHỈ ĐƯỢC PHÉP báo cáo chốt phiên thành công khi Scorecard >= 85đ và ready_to_close: true.
4. CẤM TUYỆT ĐỐI tự ý tuyên bố đóng phiên khi chưa có Scorecard chính thức từ Reviewer.
```

### 2. Cấu hình biến môi trường trên Admin (`.env`)
Bổ sung vào file `%LOCALAPPDATA%\hermes\.env` trên máy Admin:
```bash
OMNI_ROUTE_URL=http://192.168.110.123:20129/v1/chat/completions
OMNIROUTE_BASE_URL=http://192.168.110.123:20129/v1
```
`sol_auditor.py` đọc `os.environ.get("OMNI_ROUTE_URL")` nên sẽ tự động trỏ sang đúng IP LAN của Kibe để chấm điểm với chi phí 0đ (Zero-Cost Web Pool).
