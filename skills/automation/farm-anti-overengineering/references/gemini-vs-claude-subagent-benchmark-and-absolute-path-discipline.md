# Benchmark Đối Đầu Subagent: Gemini (High vs Medium) vs Claude & Kỷ Luật Đường Dẫn Tuyệt Đối (07/09/2026)

## 1. Bối cảnh Giải đấu Benchmark 2 Vòng
Sau sự cố Máy 41 bị ngâm gần 3 tiếng do subagent Gemini High cắn trần 35 turns mà không sửa file, anh Tad đã chỉ đạo tổ chức giải đấu benchmark đối đầu trực tiếp giữa 3 cấu hình:
1. **Candidate 1 (C1):** `ag-gemini-pool-3` (reasoning: `high`)
2. **Candidate 2 (C2):** `ag-gemini-pool-3` (reasoning: `medium`)
3. **Candidate 3 (C3):** `ag-claude`

---

## 2. Kết quả Thi đấu Qua 2 Vòng Thực Tế

### Vòng 1: Claude Opus High Thiết kế Đề & Chấm điểm
- **Đề bài:** Sửa lỗi retry & timeout ADB trong `worker_service.py` (Bug off-by-one thiếu 1 lần thử và Bug ném thẳng `TimeoutExpired` không retry). 2/4 test ban đầu FAIL.
- **Kết quả đo lường:**
  + **Gemini Medium:** 49.22s, 7 API calls, **4/4 PASS** -> **96/100đ (Quán quân Vòng 1)**. Phòng thủ được edge case `if last_error: raise last_error; raise AdbCommandError(...)` tránh lỗi `raise None`.
  + **Claude:** 54.88s, 5 API calls, **4/4 PASS** -> **95/100đ (Á quân Vòng 1)**. Quy trình đẹp nhất: đọc concurrent 2 file cùng lúc, đúng 5 turn, code có comment gắn root-cause `# FIX #1/#2`.
  + **Gemini High:** 53.58s, 9 API calls, **4/4 PASS** -> **87/100đ**. Quá cẩn thận, lãng phí 3 turn tìm file `TASK.md` không tồn tại.

### Vòng 2: Gemini 3.8 High Thiết kế Đề & Chấm điểm
- **Đề bài:** Sửa lỗi Phone Farm Device Lock Concurrency & Lease TTL trong `device_lock.py` (3 bug: thiếu Re-entrant renewal, timestamp `acquired_at = 0` khi preempt stale lock, security bypass ở release). 5/5 test ban đầu FAIL.
- **Kết quả đo lường:**
  + **Claude:** 50.30s, 4 API calls, **5/5 PASS** -> **98/100đ (Quán quân Vòng 2)**. 1-Shot Fix: Turn 1 đọc song song 2 file -> Turn 2 đọc vị cả 3 bug và patch chuẩn -> Turn 3 chạy test xanh 5/5 (0.14s) -> Turn 4 xuất báo cáo.
  + **Gemini High:** 89.04s, 14 API calls, **5/5 PASS** -> **82/100đ**. Tốn 6 turn probe phụ (`ls`, kiểm tra `os.stat`, chạy inline disasm bytecode) trước khi sửa file.
  + **Gemini Medium:** 94.76s, 14 API calls, **5/5 PASS** -> **80/100đ**. Cũng bị sa vào các lệnh probe phụ tương tự Gemini High.

### Bảng Tổng Sắp Chung Cuộc
| Ứng viên | Vòng 1 (Claude chấm) | Vòng 2 (Gemini chấm) | Trung bình | Xếp hạng |
|---|:---:|:---:|:---:|:---:|
| 🏆 **`ag-claude`** | 95đ | **98đ** | **96.5đ** | **Quán quân Toàn năng** |
| 🥈 **`ag-gemini-pool-3` (medium)** | **96đ** | 80đ | **88.0đ** | **Á quân** |
| 🥉 **`ag-gemini-pool-3` (high)** | 87đ | 82đ | **84.5đ** | **Hạng ba** |

---

## 3. Bài Học & Kỷ Luật Cốt Lõi

### A. Kỷ Luật Đường Dẫn Tuyệt Đối (Absolute Path Discipline)
- **Hiện tượng:** Khi prompt chỉ ghi "trong thư mục hiện tại", subagent bị ngơ vì CWD mặc định của session Hermes là `C:\Users\Kibe`. Gemini cắn sạch 15 turn chỉ để quét ổ đĩa tìm file!
- **Quy tắc:** BẮT BUỘC cung cấp **đường dẫn tuyệt đối** đầy đủ cho file mã nguồn và file test trong context dispatch:
  ```text
  THÔNG TIN FILE DỰ ÁN (ĐƯỜNG DẪN TUYỆT ĐỐI):
  - File mã nguồn cần sửa: D:/Taadaa/.../service.py
  - File test kiểm tra: D:/Taadaa/.../test_service.py
  ```
  Khi có absolute path, cả 3 ứng viên đều định vị và giải quyết bài toán dưới 1 phút.

### B. Gemini: Medium vs High
- **Tại sao nên dùng `medium` cho coding worker:**
  + `high` sinh quá nhiều thinking tokens (8k-16k), khiến turn kéo dài 60-120s, dễ bị analysis paralysis, cố tìm kiếm file phụ hoặc chạy các lệnh probe thừa mứa (`os.stat`, disasm).
  + `medium` (1k-2k thinking tokens) phản xạ nhanh gấp 2-3 lần, giảm nghẽn pool 18 accounts trên OmniRoute (:20129) và vẫn đủ thông minh để phòng thủ các edge case kỹ thuật phức tạp.

### C. Bản lĩnh 1-Shot Fix của Claude
- Claude không bao giờ lượn tìm file vu vơ. Nó luôn gom đọc concurrent các file liên quan ngay ở turn 1, phân tích thẳng vào diff và sửa dứt điểm trong 4-5 turns.
- Khi cần xử lý các case khó về concurrency / đa lỗi chồng chéo mà không muốn worker lặp probe, Claude là lựa chọn số 1.
