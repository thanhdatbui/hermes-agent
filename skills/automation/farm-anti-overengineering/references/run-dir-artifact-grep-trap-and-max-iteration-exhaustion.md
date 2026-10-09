# Bẫy Grep Đĩa Vào Thư Mục Runs/Artifacts & Nguy Cơ Chạm Trần Lượt Gọi Tool (Max Iteration Exhaustion)

## 1. Bối cảnh & Nguyên nhân sự cố

Trên hệ thống Taadaa Phone Farm, các repository tự động hóa (đặc biệt là `D:/Taadaa/tiktok-luot nuoi acc`, `D:/Taadaa/Tiktok-video`, `D:/Taadaa/tiktok-follow`) tích lũy dữ liệu vận hành thực tế rất lớn:
- Thư mục `.ai-runs/`, `runs/`, `artifacts/`, `runtime/` chứa hàng nghìn thư mục con, hàng trăm gigabyte gồm: ảnh chụp màn hình `.png`, cây giao diện `.xml`, file nhật ký chi tiết `.jsonl` và tóm tắt `.txt`.
- Khi agent nhận một yêu cầu phát triển/sửa đổi tính năng (ví dụ: chặn alert lẻ trong `alerts.py`, bổ sung đọc `run_dir` trong `batch_aggregator.py`, hook vào script chạy batch):
  1. **Bẫy 1 - Grep mù quáng ở root repo:** Chạy `grep -rn <pattern> /d/Taadaa/tiktok-luot nuoi acc` hoặc ripgrep không lọc. Lệnh phải quét hàng trăm nghìn file media/dump, dẫn đến treo lệnh và dính timeout 900s (15 phút!).
  2. **Bẫy 2 - Khảo sát lan man (Analysis Paralysis):** Agent đi duyệt danh sách thư mục `.ai-runs/`, đọc từng file `run_manifest.json`, `summary.txt`, `log.jsonl` của hàng chục run cũ. Quá trình thăm dò này đốt sạch ngân sách số lượt gọi tool (Max Tool-Calling Iterations) của phiên làm việc.
  3. **Hậu quả:** Agent bị hệ thống cắt quyền gọi tool ("You've reached the maximum number of tool-calling iterations allowed") trước khi kịp ghi đĩa một dòng code hay chạy một lệnh kiểm thử nào!

---

## 2. Kỷ Luật & Quy Tắc Bắt Buộc

### A. Cấm grep mù ở Root Repo Farm — Luôn Exclude Artifacts / Trỏ Đích Danh Thư Mục Code
- **CẤM:** Tuyệt đối không chạy lệnh tìm kiếm (grep, find, ripgrep) trên toàn bộ thư mục root của các repo farm mà không loại trừ thư mục dữ liệu lớn.
- **ĐÚNG:**
  - Trỏ đích danh thư mục chứa mã nguồn:
    - Trong `tiktok-luot nuoi acc`: chỉ tìm trong `python_runner/` hoặc `scripts/`.
    - Trong `automation-core`: chỉ tìm trong `src/` hoặc `tests/`.
  - Nếu bắt buộc tìm từ root, PHẢI loại trừ thư mục dữ liệu:
    ```bash
    grep -rn --exclude-dir={.ai-runs,runs,artifacts,runtime,.git,node_modules,__pycache__} "pattern" .
    ```
  - Hoặc dùng Python script nhỏ quét có chọn lọc phần mở rộng `.py`/`.ps1`.

### B. Nguyên Tắc First-Turn Patch Execution — Code Trước, Đào Sâu Sau
- Khi yêu cầu của người dùng đã nêu rõ ràng các file cần chỉnh sửa và hợp đồng logic (ví dụ: sửa `alerts.py`, thêm method cho `batch_aggregator.py`, sửa script `.ps1`):
  - **KHÔNG ĐƯỢC** dành hàng chục turn để đi đọc lịch sử dữ liệu cũ nhằm "tham khảo thêm".
  - **THỰC THI NGAY:** Đọc đúng file mục tiêu -> Patch code -> Viết unit test -> Chạy pytest xác nhận.
  - Mọi thao tác khảo sát phụ (nếu thực sự cần cấu trúc mẫu) chỉ được cấp ngân sách tối đa **1 - 2 tool calls** trên 1 thư mục run gần nhất đã biết, tuyệt đối không lướt qua hàng loạt run.

### C. Quản Lý Ngân Sách Lượt Gọi (Tool Call Budgeting)
- Các tác vụ patch tính năng + hook script + verify thường yêu cầu ít nhất 5-8 tool calls cho các bước:
  1. Đọc file nguồn cần sửa (1-2 calls).
  2. Patch file nguồn (1-2 calls).
  3. Cập nhật/viết unit test (1 call).
  4. Chạy test suite xác nhận (1 call).
  5. Chạy lệnh review/gate verification (1 call).
- Nếu dành quá 5 calls cho việc khảo sát và tìm kiếm ban đầu, nguy cơ chạm trần vòng lặp (iteration cap) trước khi hoàn thành là cực kỳ cao.
- Phải luôn dự trù ít nhất 50% ngân sách tool calls cho pha Ghi đĩa (Write/Patch) và Nghiệm thu (Test/Review).
