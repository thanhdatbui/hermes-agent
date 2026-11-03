# SQLite SSOT Dual-Cluster Parity & Base64 Transfer Fallacy (2026-11-03)

## 1. Bản Chất Vấn Đề: Cụm Admin Bị "Đói" Database SSOT
- **Triệu chứng:** Runner 2FA trên cụm Admin (Máy 201-280) văng lỗi hàng loạt `POST_SUCCESS_VERIFICATION_FAILED` và fallback về file Excel `taikhoan_dat_v2_updated .xlsx` rồi dính lỗi `WorkbookError`.
- **Căn nguyên thực tế:**
  - File `farm_master.db` (SQLite SSOT 1.6MB) chỉ nằm cục bộ trên máy Kibe tại `D:/Taadaa/data/farm_master.db`.
  - Trên máy Admin, file này hoàn toàn chưa tồn tại. Khi Kibe SSH sang Admin kích hoạt `run_batch_live_2fa.py`, tiến trình chạy trên CPU Admin không tìm thấy file DB local nên bị rơi vào nhánh fallback legacy mở Excel.

---

## 2. Bẫy Ngụy Biện "Ngắt Mạng" & Phép Tính Chunk SSH Base64 (Anti-Hallucination)
- **Sai lầm ngụy biện của Agent:** Khi lệnh copy qua SSH bị timeout và file SQLite trên Admin bị `malformed`, Agent đổ lỗi cho "rớt packet mạng LAN" hoặc "ngắt socket".
- **Sự thật kỹ thuật định lượng:**
  * File SQLite 1.63 MB = $\approx 2.173.611$ ký tự Base64.
  * Nếu dùng `sync_avatar_to_admin.py` hoặc script chia chunk **2.500 ký tự** cho mỗi lệnh PowerShell SSH riêng rẽ:
    $$2.173.611 \div 2.500 = \mathbf{869 \text{ lần gọi SSH riêng biệt}}$$
  * Mỗi lần mở SSH bắt tay qua Windows mất trung bình $\approx 3.0\text{s}$:
    $$869 \text{ lệnh} \times 3.0\text{s} = \mathbf{2.607 \text{ giây } (\approx 43.5 \text{ phút!})}$$
  * Trong khi trần timeout subprocess của runner/terminal chỉ từ 300s đến 600s $\rightarrow$ **Tiến trình bị kill timeout ở khoảng phút thứ 5-10 khi mới đẩy được ~33KB (10%)**, khiến file SQLite bị cụt đuôi và ném lỗi `malformed database`.
  * **Giải pháp chuẩn:** Không đẩy file nhị phân lớn qua từng mẩu SSH chunk. Sử dụng công cụ migration `migrate_excel_to_sqlite.py --apply` chạy trực tiếp ngay trên máy Admin, đọc các file Excel nguồn đã được OneDrive sync sẵn để biên dịch ra SQLite nguyên vẹn tại chỗ chỉ mất **3.6 giây**.

---

## 3. Kiến Trúc "Độc Lập Tác Chiến" (Zero-Overlap Dual Cluster)
- **Phân vùng dữ liệu tuyệt đối:**
  * Kibe quản lý máy 1 đến 80 (640 accounts).
  * Admin quản lý máy 201 đến 280 (630 accounts).
  * Không có bất kỳ tài khoản hay máy nào bị chồng chéo giữa 2 cụm.
- **Vận hành an toàn:**
  * Kibe tiếp tục điều phối tổng thể qua SSH, runner trên Admin đọc/ghi $O(1) \approx 0.005\text{s}$ vào `D:/Taadaa/data/farm_master.db` local của Admin.
  * Nếu Kibe sập nguồn hoặc mất mạng, Admin đã có sẵn bản sao SQLite hoàn chỉnh 100% để tự chạy độc lập không bị gián đoạn.

---

## 4. Hard Gate G15: Sàn Timeout $\ge 300\text{s}$ Bắt Buộc Cho Terminal / Planner
- **Lỗ hổng cũ:** Agent tự tiện gán cờ `--timeout: 60` hoặc `timeout=60` khi gọi `consult_advisor.py`, `claude_worker.py` làm ngắt ngang Claude Sonnet và Sol khi đang lập luận sâu.
- **Chốt chặn cơ học Gate G15:**
  * Đã cài đặt Gate **`G15: Mechanical Floor Timeout (300s)`** trong `gate_compliance_watchdog.py`.
  * Đồng bộ các hằng số: `CLAUDE_TIMEOUT = 300`, `GEMINI_TIMEOUT = 300`, `SOL_TIMEOUT = 300` trong `gate_b_planner.py`.
  * Bất kỳ lệnh gọi nào truyền tham số timeout $< 300\text{s}$ đều bị chặn đứng và đánh FAIL Gate G15.
