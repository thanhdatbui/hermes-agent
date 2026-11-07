# Google Cloud Code 403 TOS_VIOLATION vs VALIDATION_REQUIRED & Appeal Runbook

## 1. Phân Định Bản Chất Lỗi 403 Cloud Code API
* **Mã lỗi 1: `403 PERMISSION_DENIED` + Reason `TOS_VIOLATION`**
  - **Nguyên nhân cốt lõi:** Google quét ra các dấu hiệu nhận diện bot / agent bên thứ ba vi phạm Terms of Service. Thủ phạm chính là chuỗi định danh tĩnh trong payload: `"You are Hermes Agent"`, `"Nous Research"`, `"https://hermes-agent.nousresearch.com/docs"` được tự động nhồi bởi `HERMES_AGENT_HELP_GUIDANCE` trong `agent/system_prompt.py`.
  - **Trạng thái tài khoản:** Gói Google AI Pro / Google One và quyền dùng Gemini Web vẫn còn sống 100%, chỉ bị khóa riêng cổng Cloud Code API (`cloudcode-pa.googleapis.com`).
  - **Quy trình giải cứu (Appeal):**
    - Mở bằng chính Profile GPM của tài khoản đó (để ăn đúng cookie đăng nhập và IP proxy gắn nick).
    - Mở link Google Form chính thức: `https://forms.gle/hGzM9MEUv2azZsrb9` (Appeal Form — Terms of Service suspension for Antigravity, Gemini CLI, and Gemini Code Assist).
    - Tích chọn xác nhận email: `Record <email> as the email to be included with my response`.
    - Tích chọn cam kết: `Yes, I understand` (Cam kết không dùng third-party tools / OpenClaw / bán lại dịch vụ).
    - Bấm **Submit**.
  - **Đặc điểm cần lưu ý:** Google Forms ghi trực tiếp vào Google Sheets nội bộ, **tuyệt đối KHÔNG gửi thư đi từ hộp thư của tài khoản** (mục Sent sẽ không có thư). Kết quả duyệt được trả về mục **Inbox** sau **24 – 72 giờ**.

* **Mã lỗi 2: `403 PERMISSION_DENIED` + Reason `VALIDATION_REQUIRED`**
  - **Nguyên nhân:** Không phải bị phạt ToS, mà là tài khoản bị hết hạn phiên đăng nhập / session expired hoặc Google nghi ngờ vị trí truy cập lạ.
  - **Xử lý:** Mở Profile GPM đăng nhập lại. Nếu Google yêu cầu xác minh 2 bước qua Galaxy S7, mở điện thoại tương ứng: Cài đặt -> Google -> Quản lý tài khoản -> Tab Bảo mật -> Mã bảo mật (Security Code 10 chữ số) để xác thực.

## 2. Kỷ Luật Context & Prompt Caching cho Coordinator
* **Prompt Caching 97.5% không miễn dịch ToS:** Cache chỉ giảm tính toán trên server Google, nhưng toàn bộ dung lượng JSON (vài MB) vẫn phải upload qua proxy mỗi lượt.
* **Cấu hình tối ưu:**
  - `threshold: 0.3`: Giữ trần 300k tokens mới nén để không làm model bị "ngu đi" (tránh mất chi tiết kỹ thuật cho task khó).
  - `protect_last_n: 6`: Giữ nguyên raw output của 3 lượt tool gần nhất để model có đủ dữ liệu suy luận bước tiếp theo, các lượt trước đó rút ruột cơ học thành 1 dòng tóm tắt (`[terminal] ran <cmd> -> exit 0`).
