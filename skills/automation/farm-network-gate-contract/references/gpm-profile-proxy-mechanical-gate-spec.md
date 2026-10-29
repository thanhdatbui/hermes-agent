# GPM Profile Creation Mechanical Gate & Option A Zero-Exception Policy

## Bối Cảnh Sự Cố & Bài Học
- **Sự cố:** Agent khi thử nghiệm hoặc làm task tự động hoá (như đăng ký tài khoản AWS, TikTok, Gmail) có xu hướng tự tiện gọi API `/api/v3/profiles/create` tạo profile mới không gán proxy (`raw_proxy == ""`).
- **Nguy cơ:** Khiến tài khoản chạy direct bằng IP mạng nhà của host (máy Kibe), gây nguy cơ làm chết hàng loạt tài khoản (chain ban) và lộ danh tính farm.
- **Yêu cầu của Operator:** Phải cơ giới hóa (Mechanical Gate) bằng hook chặn cứng tầng controller/terminal, tuyệt đối không trông chờ vào "lời hứa" hay system prompt của LLM.
- **Nhu cầu của Operator về IP Direct:** Operator vẫn có các profile cá nhân (Gmail chính) cần chạy direct IP mạng nhà.

## Quyết Định Thiết Kế: Option A (Zero-Exception Cho Agent)
Khi thảo luận cùng Claude Opus (Code Reviewer), các giải pháp ngoại lệ dựa trên prefix tên (`MAIN_`), group ID, hoặc note (`DIRECT_MAIN_AUTHORIZED`) đều bị bác bỏ vì Agent hoàn toàn có thể tự hallucinate hoặc viết các trường đó vào request để tự bypass gate.

Chốt **Option A**:
1. **Agent (AI):** Bị cấm tuyệt đối 100% việc tạo profile không có proxy qua bất kỳ API hay công cụ nào. Không có exception path cho Agent.
2. **Operator (Người dùng):** Khi cần tạo profile direct cho Gmail chính, Operator tự tay bấm nút Tạo profile trên giao diện ứng dụng GPMLogin (chọn không proxy).
3. **Quyền khởi chạy (`start`):** Hook `guard_gpm_proxy.py` **không bao giờ chặn lệnh start profile** (`/api/v3/profiles/start/{id}`). Do đó mọi profile direct do Operator tạo sẵn đều được phép khởi chạy bình thường.

## Cấu Trúc Kỹ Thuật Của Gate `guard_gpm_proxy.py`
- **Vị trí file:** `D:/Taadaa/tools/guard_gpm_proxy.py`
- **Đăng ký hook:** Cấu hình trong `deploy/hermes-home/config.yaml` tại mục `hooks.pre_tool_call` (matcher: `terminal|execute_code`, timeout: 5s).
- **Bộ kiểm thử offline:** `D:/Taadaa/tools/tests/test_guard_gpm_proxy.py` với 129/129 tests passed 100% (được Claude Opus review và duyệt chính thức).

### Các quy tắc kiểm tra (Fail-Closed):
1. **Đường dẫn mục tiêu:** Bắt regex `r'/profiles/create(?![\w-])'` không phân biệt hoa thường, bắt được cả khi base URL được tách riêng (vd: `f"{GPM_API}/profiles/create"`).
2. **Kiểm tra proxy theo Allowlist Format:**
   - Từ chối ngay nếu chứa placeholder/biến: `$`, `%`, `{`, `}` (vd: `$PROXY`, `{proxy}`).
   - Từ chối ngay nếu chứa từ khóa direct: `none`, `direct`, `null`.
   - Host phải là tên miền hợp lệ hoặc IPv4/IPv6 literal; từ chối loopback/localhost (`127.0.0.1`, `localhost`, `0.0.0.0`, `::1`).
   - Port bắt buộc là số nguyên hợp lệ trong khoảng `1..65535`.
3. **Fail-Closed khi không trích xuất được body:**
   - Nếu lệnh chứa `/profiles/create` nhưng body nằm trong file (`-d @body.json`), biến PowerShell (`-Body $var`), hoặc payload stdin hỏng không parse được -> BLOCK ngay lập tức.
   - Đếm số lượng match `/profiles/create` so với số lượng JSON body hợp lệ (`body_count`). Nếu `len(create_matches) > body_count` (vd: 1 create inline hợp lệ kèm 1 create dùng file ngầm) -> BLOCK ngay lập tức.
4. **An toàn Encoding trên Windows Pipe:**
   - Luôn thiết lập `sys.stdout.reconfigure(encoding="utf-8")` và in JSON với `ensure_ascii=True` để không bao giờ bị dính `UnicodeEncodeError` trên môi trường Windows cp1252/ascii làm lệnh block bị nuốt mất.
5. **Hỗ trợ định dạng kép:**
   - Định dạng Hermes (`action: "block"`, exit 0).
   - Định dạng Claude Code (`hookSpecificOutput.permissionDecision = "deny"`, exit 2 khi có `hook_event_name`).
