# Prompt Cache vs Context Compression & Session Sticky Governance

## 1. Bản chất Prompt Cache vs Tải Upload Mạng
- **Hiểu lầm tai hại:** "Prompt Cache 97.5% nên payload nặng 400k-500k tokens cũng không sao".
- **Thực tế:** 
  - Prompt Cache chỉ giảm compute và chi phí trên TPU/GPU của Google.
  - Client (PC/OmniRoute) vẫn bắt buộc phải serialize và upload toàn bộ file JSON dung lượng vài Megabytes qua kết nối mạng.
  - Trên mạng 4G hoặc proxy có upload bandwidth thấp, payload > 400k tokens dễ gây rớt kết nối hoặc timeout (HTTP 499 / 504).

## 2. Kỷ luật cấu hình `protect_last_n` trong `context_compressor`
- **`protect_last_n = 20` (Cũ):** Quá dư thừa, giữ tới 7-8 lệnh tool thô (read_file, terminal grep) làm phình context thêm 60k-100k tokens rác.
- **`protect_last_n = 6` (Chuẩn vàng):** Tương đương 3 hành động tool gần nhất:
  - Turn $N$ (vừa chạy): Raw output 100% để LLM đọc hiểu dữ liệu.
  - Turn $N-1$ & $N-2$: Raw output để đối soát logic.
  - Từ Turn $N-3$ trở về trước: Tự động rút ruột thành 1-line summary (`[terminal] ran ... -> exit 0`), giải phóng ngay hàng chục nghìn tokens.
- **Vết xe đổ `protect_last_n = 0`:** CẤM TUYỆT ĐỐI. Nếu xóa ngay sau khi chạy, turn kế tiếp LLM không nhận được dữ liệu đầu vào -> rơi vào vòng lặp gọi lại tool hoặc ảo giác (hallucination). Ngoài ra việc sửa đổi liên tục phần đuôi sẽ phá vỡ Prompt Cache của Google.

## 3. Cân bằng Combo Router OmniRoute: Sticky vs Least-Used
- **Sticky Round Robin (`stickyRoundRobinLimit: 10-15`):** Cần thiết trong 1 lượt tương tác ReAct để toàn bộ chuỗi tool-call cùng bay về 1 tài khoản, bảo toàn 97.5% Prompt Cache.
- **Least-Used Strategy:** Tự động nhả ghim sau chu kỳ 15 turns và đẩy sang tài khoản có ít lượt gọi nhất, san đều tải (ví dụ ~200 calls/acc) thay vì dồn 70% vào 1 tài khoản duy nhất (nguy cơ kích hoạt Abuse Detection của Google).
