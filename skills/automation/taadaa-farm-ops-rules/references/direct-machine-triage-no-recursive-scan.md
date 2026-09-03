# Direct Machine Triage & Ban on Recursive Directory Scanning (Anti-Pattern)

## 1. Quy tắc cốt lõi khi nhận Alert [MÁY N]
- Khi nhận được cảnh báo hoặc sự cố chỉ định số máy `[MÁY N]`, agent **BẮT BUỘC**:
  1. Tra cứu trực tiếp serial thiết bị qua `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` hoặc `D:\Taadaa\machine-config\kibe.yaml`.
  2. Truy cập thẳng thiết bị qua ADB (`-s <serial>`) để kiểm tra trạng thái màn hình hiện tại (`dumpsys window`, `uiautomator dump` hoặc `exec-out screencap -p`).
  3. Nếu cần đọc log, truy cập trực tiếp artifact của máy đó: `D:\Taadaa\runtime\kibe\machine_N` hoặc thư mục run cụ thể của máy N.

## 2. Các hành vi BỊ CẤM TUYỆT ĐỐI (Anti-Patterns)
- **CẤM:** Chạy lệnh `find`, `grep`, `rg`, `search_files`, `ls -R`, `os.walk` quét đệ quy qua thư mục `.ai-runs/`, `runtime/` hoặc toàn bộ ổ đĩa `D:\`.
  - *Hậu quả:* Gây nghẽn disk I/O, tràn context window, quét qua hàng nghìn file cũ không liên quan và làm gián đoạn quá trình xử lý sự cố.
- **CẤM:** Quét tìm file mà không chỉ định rõ target directory hoặc target machine.

## 3. Quy trình Triage Chuẩn (Checklist)
1. Map máy N -> `<serial>` (ví dụ: Máy 52 -> `ce0418243a6250430c`).
2. Screencap / Dump UI trực tiếp từ `<serial>`:
   ```bash
   "C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <serial> exec-out screencap -p > /d/Taadaa/mN_live.png
   ```
3. Xác định đúng loại popup/lỗi (System Dialog vs In-App Dialog).
4. Sửa code / Registry tương ứng -> chạy focused test -> kiểm chứng live trên máy N.
