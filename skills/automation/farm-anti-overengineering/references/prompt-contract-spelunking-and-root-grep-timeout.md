# Bài học Bẫy Quét Root Drive `/d/Taadaa/` & Thám Hiểm Thừa Mứa Khi Prompt Đã Có Sẵn Spec

*(Đúc rút từ sự cố Watchdog Avatar Task 07/09/2026: 4 lần dính timeout 900s do grep diện rộng trên ổ D làm kiệt quệ ngân sách tool calls)*

---

## 1. Hiện Tượng & Diễn Biến Sự Cố

- **Mục tiêu task**: Xây dựng script `scripts/avatar_post_feed_watchdog.py` và file kiểm thử `tests/test_avatar_post_feed_watchdog.py`, sau đó chạy pytest.
- **Dữ liệu đầu vào**: User prompt đã mô tả cực kỳ chi tiết từng hàm, từng tham số, logic thời gian (22:30 - 00:45), cơ chế xác định Row theo ngày chẵn/lẻ, và toàn bộ các đường dẫn file cụ thể:
  + State file: `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json`
  + Workbook: `D:\OneDrive\TaadaaData\kibe\Tik{row}.xlsx`
  + Manifest: `D:\CodexRuntime\tiktok-video\assignment-manifest-avatar-row{row}.json`
  + Launcher: `D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1`
  + Batch run logs: `D:\CodexRuntime\tiktok-video\batch-runs\batch_tik{row}_*` và `summary.csv`
- **Diễn biến sai lệch**:
  1. Agent dùng tool `search_files` với đường dẫn POSIX `/d/Taadaa/Tiktok-video` trên Windows host $\rightarrow$ ripgrep native ném `os error 3` (do Windows không hiểu `/d/...`).
  2. Thay vì sửa đường dẫn thành `D:\Taadaa\...` hoặc đọc trực tiếp file đã biết, agent chuyển sang dùng `terminal` và liên tiếp chạy các lệnh tìm kiếm diện rộng trên toàn ổ đĩa `/d/Taadaa/`:
     - `grep -rn "feed_session_reported" /d/Taadaa/` $\rightarrow$ **TIMEOUT 900s (15 phút)**.
     - `find /d/CodexRuntime/tiktok-video -name "summary.csv"` $\rightarrow$ **TIMEOUT 900s (15 phút)**.
     - `grep -rn "Row 5" /d/Taadaa/` $\rightarrow$ **TIMEOUT 900s (15 phút)**.
     - `grep -rn "ca3_phien3" /d/Taadaa/` $\rightarrow$ **TIMEOUT 900s (15 phút)**.
  3. Tổng thời gian ngâm phiên hơn 1 tiếng đồng hồ, tiêu tốn sạch ngân sách lượt gọi tool và chạm trần giới hạn lặp (`maximum number of tool-calling iterations allowed`) mà chưa hề ghi được một dòng code nào vào 2 file đích.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ

### 2.1. Đặc Thù Cấu Trúc Đĩa Ổ D Trên Taadaa Farm
- Thư mục `D:\Taadaa` và `D:\` không phải là một project source code đơn thuần mà là không gian lưu trữ hỗn hợp:
  + `D:\OneDrive`: Hàng trăm GB tài liệu, workbook đang đồng bộ trực tuyến.
  + `D:\Taadaa\python-envs`: Hàng chục ngàn tệp tin nhị phân của các virtualenv.
  + `D:\CodexRuntime`: Hàng vạn file log, runs, screencaps, video MP4.
  + Model AI (YOLO, Deep Learning weights): Hàng chục GB.
- **Hậu quả**: Bất kỳ lệnh `grep -rn ... /d/Taadaa/` hay `find /d/Taadaa/ ...` nào cũng phải quét qua hàng triệu file trên ổ cứng vật lý / mạng sync, chắc chắn kích hoạt timeout 900s của terminal tool.

### 2.2. Tâm Lý "Thám Hiểm Thừa Mứa" (Reconnaissance Paralysis)
- Khi user đã giao task với spec rõ ràng kèm các đường dẫn cụ thể, agent lại có khuynh hướng "đi xem các chỗ khác trong toàn bộ hệ sinh thái làm thế nào" trước khi dám viết code.
- Việc tìm kiếm vu vơ này không đem lại giá trị mới mà làm loãng ngữ cảnh và đốt cháy ngân sách thời gian/tool calls.

### 2.3. Lỗi Định Dạng Đường Dẫn Trên Windows Toolset
- Tool `search_files` được build bằng native Windows Rust binary (ripgrep).
- Truyền `/d/Taadaa/...` (cú pháp Git-Bash MSYS) vào `search_files` sẽ bị hiểu nhầm là đường dẫn tương đối trên ổ hiện tại (ví dụ `C:\d\Taadaa\...`), gây `IO error: The system cannot find the path specified (os error 3)`.
- Bắt buộc phải dùng `D:\Taadaa\...` hoặc `D:/Taadaa/...`.

---

## 3. Quy Chuẩn Kỷ Luật Bắt Buộc (Rules of Engagement)

### 3.1. Cấm Tuyệt Đối Grep / Find Trên Thư Mục Gốc Ổ D
```bash
# CẤM TUYỆT ĐỐI (100% TIMEOUT 900S):
grep -rn "..." /d/Taadaa/
grep -rn "..." /d/CodexRuntime/
find /d/Taadaa -name "..."
find /d/CodexRuntime -name "..."
```

### 3.2. Quy Tắc Tra Cứu O(1) Bằng Python One-Liner
Khi cần xác thực file cấu hình, định dạng JSON hoặc dữ liệu Excel đã có đường dẫn:
```python
# Đọc JSON mẫu O(1) < 1 giây:
python -c "import json; print(json.load(open(r'D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json', encoding='utf-8')))"

# Đọc Header Excel O(1) < 1 giây:
python -c "import openpyxl; wb = openpyxl.load_workbook(r'D:\OneDrive\TaadaaData\kibe\Tik5.xlsx', read_only=True); ws = wb.active; print([c.value for c in next(ws.iter_rows(max_row=1))]); wb.close()"
```

### 3.3. Pipeline Viết Mới Chuẩn 5 Bước (Lean 5-Step Code Delivery)
Khi được yêu cầu viết file mới theo spec:
1. **Bước 1 (1-2 calls)**: Đọc nhanh cấu trúc 1 file tương tự đã biết rõ đường dẫn (nếu cần) hoặc kiểm tra file dữ liệu O(1).
2. **Bước 2 (1 call)**: Dùng `write_file` tạo file mã nguồn chính hoàn chỉnh.
3. **Bước 3 (1 call)**: Dùng `write_file` tạo file kiểm thử unit test tương ứng.
4. **Bước 4 (1 call)**: Chạy kiểm chứng cú pháp và unit test qua pytest:
   ```bash
   pytest tests/test_<target>.py -p no:cacheprovider
   ```
5. **Bước 5 (1 call)**: Báo cáo kết quả và kết thúc.
*Tổng ngân sách toàn bộ task: <= 6 tool calls, hoàn thành dưới 3 phút!*
