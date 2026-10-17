# Purging Legacy Injected Prompts and Atomic Config Update (18/10/2026)

## 1. Hiện Tượng & Vấn Đề
Operator yêu cầu loại bỏ hoàn toàn các nhắc lệnh lỗi thời về model cũ và subagent:
`"Là sao nữa sao vẫn còn luna nx prompt nào óc lồn v. Fix đi để thực thi đúng tao thiết kế coi"`

Khi nhận task sửa code, Coordinator có nguy cơ bị cuốn theo các chỉ thị cũ sót lại trong prompt hệ thống, dẫn đến việc gọi nhầm công cụ subagent nội tại thay vì Single Dispatch Gateway ngoài terminal.

## 2. Nguyên Nhân Gốc Rễ
1. **Residual Legacy Injected Prompt trong file cấu hình:**
   Trường `agent.system_prompt` trong file cấu hình runtime vẫn còn chứa các câu lệnh cũ phân vai cho subagent nội tại và model cũ.
   Đoạn prompt này được nạp vào đầu mỗi phiên làm việc, gây nhiễu luồng điều phối của Coordinator.

2. **Cạm bẫy ngắt dòng khi sửa cấu hình qua dòng lệnh:**
   Khi dùng công cụ cấu hình cập nhật chuỗi văn bản nhiều dòng bằng CLI argument thông thường, ký tự xuống dòng khiến trình phân giải dòng lệnh ngắt chuỗi thành nhiều câu lệnh rời rạc, gây lỗi cú pháp hoặc kích hoạt bộ lọc bảo vệ.

## 3. Quy Trình Khắc Phục Chuẩn

### A. Phân Vai Worker Chuẩn (Tiered Workflow 2.0)
- **Coordinator:** Đọc log, inspect O(1), lập contract và nghiệm thu.
- **Worker thi công code:**
  * **Tier 1 (Chính):** Claude Haiku 5.5 CLI qua `python D:/Taadaa/tools/dispatch_worker.py "<contract O(1)>" --file <file> --timeout 60` (hoặc `haiku_worker.py`).
  * **Tier 2 (Fallback):** Antigravity CLI fix (`ag_cli.py fix`) khi Claude hết hạn mức quota 5h/weekly.
  * **CẤM TUYỆT ĐỐI:** CẤM dùng `delegate_task` cho việc sửa code.

### B. Cập Nhật Cấu Hình Bằng Định Dạng JSON Thoát Chuỗi
1. Thêm key cần chỉnh sửa vào danh sách `ALLOWED_PREFIXES` trong `D:/Taadaa/tools/manage_hermes_config.py`.
2. Chuyển đổi toàn bộ văn bản nhiều dòng thành một chuỗi duy nhất với ký tự thoát `\n`, sau đó áp dụng với cờ `--type json`:
   ```bash
   python D:/Taadaa/tools/manage_hermes_config.py set agent.system_prompt '"Dòng 1\nDòng 2\nDòng 3"' --type json
   ```
   Kỹ thuật này giúp bộ phân giải JSON tự phục hồi các ký tự xuống dòng mà không làm vỡ cấu trúc câu lệnh trên Windows/MSYS.
