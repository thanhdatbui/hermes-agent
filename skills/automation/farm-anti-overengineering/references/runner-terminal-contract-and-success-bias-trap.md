# Bẫy Success-Biased Goal, Phân Biệt Runner vs Debugger & Kỷ Luật Terminal Contract

*(Đúc kết từ sự cố ngâm phiên 1.5 tiếng ngày 07/09/2026 trên Máy 1 và thẩm định kiến trúc của Claude CLI Opus High)*

---

## 1. Hiện tượng & Triệu chứng Thực tế

Trong ca chạy Add 2FA Máy 1 lúc 11:56 ngày 07/09/2026, Coordinator dispatch Worker subagent với goal:
> *"Kích hoạt chạy Add 2FA live trên Máy 1, giám sát lấy secret thật, nhập OTP và ghi vào Excel, chụp ảnh xác nhận kết quả."*

- **Diễn biến:** Lệnh runner chạm máy thật và trả về kết quả ngay trong 60 giây:
  `1 | 5 | g************* | failed | SWITCHER_OPEN_FAILED`
- **Hành vi sa đà (Analysis Paralysis):**
  Thay vì dừng lại và báo cáo ngay kết quả thất bại, Worker subagent:
  1. Đọc ngược vào `automation-core/src/automation_core/tiktok/account_switcher.py`.
  2. Gọi `computer_use` (cố điều khiển desktop Windows, bị timeout 30s).
  3. Chạy `search_files` với đường dẫn MSYS `/d/Taadaa/...` (dính `os error 2`).
  4. Thực hiện liên tiếp 32 tool calls trong suốt 45 phút mà không gửi một cập nhật nào về session chính.
- **Hậu quả:** Người dùng bức xúc (*"Clgt t gửi từ 11h h 12h33 k xong lại tiếp tục sa đà vào over engineer r phải k"*).

---

## 2. Phân Tích Bản Chất từ Claude CLI Opus High: Tại Sao "Giảm Tool Không Ăn Thua"?

Khi Coordinator cố gắng chữa cháy bằng cách hạ `max_iterations: 12` và siết `WorkerToolGate`, người dùng đã chỉ thẳng: *"giảm tool t nghĩ đéo ăn thua"*. Claude Opus High đã xác nhận 100% nhận định này:

### A. Lỗi Định Nghĩa Definition of Done (DoD) trong Goal (Success-Biased Framing)
- Goal ghi: *"lấy secret thật, nhập OTP, có ảnh xác nhận"* $\rightarrow$ LLM tự suy ra **DoD = Phải chạy thành công.**
- Khi script trả về `failed | SWITCHER_OPEN_FAILED`, dưới góc nhìn của LLM, **nó CHƯA hoàn thành nhiệm vụ**. Nó không xem `failed` là một kết quả hợp lệ để trả về, mà xem nó là **một chướng ngại vật cần vượt qua**.
- Bản chất Agentic LLM được huấn luyện để bền bỉ theo đuổi mục tiêu (Persistence). Khi gặp lỗi và không có contract chấm dứt, default policy của nó là: *Đọc code -> Lập giả thuyết -> Thử sửa -> Thử lại.* Nó tự động chuyển vai thành Debugger.

### B. Counter-Based (Đếm lượt) vs Capability-Based (Cắt quyền từ gốc)
- **Counter-based (`READ_BUDGET=3`):** Vẫn để tool `read_file` trong schema. Worker vẫn đọc được 3 file mã nguồn, đủ để bắt đầu chu trình suy diễn và đốt hàng chục phút.
- **Capability-based:** Runner không có tool đọc/sửa file trong schema ngay từ đầu. Worker không thể điều tra dù muốn.

---

## 3. Kỷ Luật Phân Tách Dứt Khoát: Runner vs Debugger

```text
┌─────────────────────── RUNNER (Task A) ───────────────────────┐
│ INPUT:  1 lệnh runner cụ thể + danh sách TERMINAL STATES       │
│ JOB:    Chạy lệnh -> Đọc exit code/stdout -> Chụp 1 screencap │
│ DoD:    "Kết cục thực tế (dù pass hay fail) đã được ghi nhận" │
│ CẤM:    read_file, search_files, patch, write_file,           │
│         computer_use, retry, đặt giả thuyết, đọc source code. │
│ EXIT:   Ngay khi có terminal state. Báo cáo và thoát ngay.    │
└───────────────────────────────────────────────────────────────┘
        │ (kết quả failed được báo cáo về Coordinator/Tad)
        ▼
┌────────────────────── DEBUGGER (Task B) ──────────────────────┐
│ TRIGGER: CHỈ khi Coordinator/Operator ra lệnh tường minh       │
│          "phân tích nguyên nhân của <lỗi đã báo cáo>"         │
│ INPUT:  error code + log path + file scope cụ thể             │
│ JOB:    Root cause -> Soạn Patch Contract (KHÔNG tự vá live)  │
│ DoD:    "Trả về chẩn đoán + patch proposal"                   │
└───────────────────────────────────────────────────────────────┘
```

**Quy tắc sống còn:** Runner KHÔNG BAO GIỜ tự động chuyển vai sang Debugger. Việc chuyển từ A sang B là quyết định của con người hoặc Coordinator sau khi đã xem xét báo cáo.

---

## 4. Mẫu Goal Chuẩn Cho Runner (Report-Biased Template)

Khi Coordinator dispatch worker chạy automation live hoặc canary, BẮT BUỘC dùng mẫu prompt sau:

```text
GOAL RUNNER:
1. Chạy đúng 1 lệnh runner: <command>
2. Đọc dòng kết quả cuối cùng (machine | source_row | username | status | reason).
3. Chụp 1 ảnh screencap thiết bị lưu vào: <screencap_path>
4. Báo cáo kết quả và THOÁT NGAY LẬP TỨC.

TERMINAL = DONE:
- Bất kỳ kết quả nào của status (kể cả failed, SWITCHER_OPEN_FAILED, OTP_ADVANCE_BUTTON_NOT_REACHED, CAPTCHA, hay success) đều là HOÀN THÀNH 100% NHIỆM VỤ.
- Trả về báo cáo trung thực, exit code và screencap.

CẤM TUYỆT ĐỐI:
- CẤM đọc source code, cấm search_files, cấm patch/write_file.
- CẤM gọi computer_use.
- CẤM đặt giả thuyết nguyên nhân hay tự ý sửa lỗi.
Lỗi của lệnh chạy là DỮ LIỆU cần báo cáo về, KHÔNG PHẢI bài toán worker được phép tự giải.
```
