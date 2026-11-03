# Mechanical Timeout Floor (>=300s) & Dual-Cluster SQLite Master/Replica Architecture (2026-11-03)

## 1. Sự Cố Người Dùng Chấn Chỉnh: Tự Tiện Nhồi Timeout Thấp (<300s)
- **Hiện tượng:** Coordinator tự ý truyền cờ `timeout=60` hoặc `timeout=120` vào lệnh `terminal` khi gọi `consult_advisor.py`, `claude_worker.py` hoặc `gate_b_planner.py`.
- **Hậu quả nghiêm trọng:** Claude CLI và Sol bị ngắt ngang giữa chừng khi đang đọc context, dẫn đến hiện tượng cố vấn bị timeout giả tạo hoặc văng ra khỏi phiên họp Hội đồng Cố vấn.
- **Kỷ luật cơ học bắt buộc (Gate G15):**
  * Mọi lệnh gọi tới Planner, Advisor Council hoặc Worker con BẮT BUỘC phải cấp sàn timeout $\ge 300\text{s}$ (cả ở cờ CLI `--timeout` lẫn tham số `timeout=` của tool `terminal`).
  * Đã cơ giới hóa Gate G15 trong `gate_compliance_watchdog.py`: Tự động gắn cờ vi phạm nếu bất kỳ lệnh nào chứa timeout dưới 300s đối với planner/advisor.
  * Trong `gate_b_planner.py`: Các hằng số `CLAUDE_TIMEOUT`, `GEMINI_TIMEOUT`, `SOL_TIMEOUT` được ghim cứng là `300`.

---

## 2. Kiến Trúc Dual-Cluster SQLite SSOT (Kibe & Admin)
- **Bản chất phân vùng:**
  * Farm gồm 2 cụm độc lập tuyệt đối: Kibe quản lý máy 1–80, Admin quản lý máy 201–280.
  * Không có sự chồng chéo tài khoản hoặc thiết bị giữa 2 cụm máy.
- **Mô hình vận hành tối ưu ($O(1)$ SSD Local):**
  * Cả máy Kibe và máy Admin đều lưu giữ bản sao cục bộ tại `D:/Taadaa/data/farm_master.db`.
  * Khi Kibe điều phối qua SSH: Runner Python trên máy Admin đọc và ghi trực tiếp vào `farm_master.db` trên ổ `D:` của Admin với tốc độ $0.005\text{s}$, không phụ thuộc vào độ trễ mạng hay socket SSH.
  * Loại bỏ hoàn toàn việc fallback về file Excel `taikhoan_dat_v2_updated .xlsx` khi chạy 2FA hay nuôi feed.
  * **Tính dự phòng cao (High Availability):** Nếu máy Kibe gặp sự cố phần cứng/sập nguồn, toàn bộ 80 máy cụm Admin vẫn tự chủ vận hành 100% tại chỗ.
