# Claude Opus CLI Recommendation: Patch Contract & Large-File Worker Coordination

Được đúc rút từ tư vấn Claude Opus CLI sau sự cố 40 phút tại Máy 25 (06/09/2026) khi xử lý monolith file khổng lồ (> 20.000 dòng như `feed_swipe_smoke.py`).

---

## 1. Nguyên Lý Cốt Lõi: Patch Contract vs Goal Mở
- **Hiện tượng lỗi (Death Loop):** Trong các file mã nguồn khổng lồ, khi Coordinator giao một goal điều tra mở ("Sửa lỗi X", "Tìm nguyên nhân Y"), Worker rơi vào vòng lặp đọc phân trang (`read_file` 25–35 lần), cạn kiệt toàn bộ ngân sách tool calls trước khi kịp sửa code.
- **Quy tắc vàng:** **Coordinator chỉ được dispatch khi đã có `old_string` và `new_string` chính xác trong tay.** CẤM giao goal điều tra mở cho worker trên monolith file.
- Coordinator dùng `grep -n` và `read_file` (đúng 20–40 dòng quanh điểm lỗi) để định vị và trích xuất diff trong 2 phút, sau đó đóng gói thành **Patch Contract** gửi Worker.

---

## 2. Cấu Trúc Patch Contract Chuẩn

```text
[PATCH CONTRACT DIRECTIVE]:
- Goal: Áp 1 patch đã soạn sẵn + chạy 1 focused test. KHÔNG điều tra, KHÔNG đọc thăm dò.
- Target File: <đường_dẫn_file_tuyệt_đối> (~dòng N)
- old_string:
<đoạn code cũ duy nhất 10-15 dòng, có mốc neo rõ ràng>
- new_string:
<đoạn code mới thay thế>
- verify_command: pytest <đường_dẫn_test>
- Rules: CẤM read_file quá 2 lần; ngân sách tối đa <= 5-8 tool calls; hoàn tất dưới 60 giây.
```

---

## 3. Ba Khuyến Nghị Bổ Sung Từ Claude Opus CLI

### 3.1. Uniqueness Check (`grep -c == 1`)
- Trước khi dispatch Worker hoặc trước khi patch, Coordinator bắt buộc kiểm tra tính duy nhất của `old_string`:
  ```bash
  grep -c "<mốc neo đặc trưng trong old_string>" "<file_đích>"
  ```
- **Yêu cầu:** Kết quả bắt buộc bằng đúng `1`. Nếu `grep -c > 1`, phải mở rộng `old_string` thêm 2–3 dòng context xung quanh để đảm bảo không bị patch nhầm vị trí hoặc dính bẫy phantom match trên Windows.

### 3.2. Investigation Escape Hatch (Chế độ thoát hiểm điều tra)
- Nếu sau 2 phút ở B1 Coordinator không thể xác định được số dòng hoặc mốc neo lỗi (do traceback mờ hoặc logic phân nhánh phức tạp):
  - **Chuyển sang Investigation Mode:** Dispatch 1 worker dạng read-only với vai trò `leaf`.
  - **Khóa ngân sách:** Tối đa `<= 10 tool calls`, thời gian `< 5 phút`.
  - **Mục tiêu duy nhất:** Tìm và trả về đúng số dòng + đoạn `old_string` 10 dòng của bug.
  - **CẤM:** Tuyệt đối không ép Coordinator hay Worker đoán mò và soạn patch mù khi chưa định vị được code.

### 3.3. Canary Fail Rollback & Triệt Tiêu Code Hỏng (B5 Rollback)
- Nếu Canary Test ở B4 thất bại (lỗi app, timeout, hoặc UI vẫn kẹt):
  1. **Lập tức khôi phục (revert):** Chạy `git checkout <file>` để xóa sạch patch hỏng trên working tree.
  2. **Giải phóng thiết bị:** Bấm HOME (`keyevent 3`), nhả lock an toàn.
  3. **Lưu trữ hiện trường:** Lưu log và screenshot của canary test thất bại vào thư mục runs để phục vụ phân tích vòng 2.
  4. **CẤM để code hỏng tồn lưu trên máy farm:** Không được để lại patch nửa vời trên branch làm ảnh hưởng tới các phiên chạy tiếp theo của các máy khác.

---

## 4. Playbook 5 Bước Chuẩn Hóa Cho Farm Alert (< 12 Phút - 1 Worker Duy Nhất)

1. **B0 (Coordinator - 90s):** Nhận alert, inspect hiện trường O(1) (`inspect_machine.py <N>`, dump XML, screencap).
2. **B1 (Coordinator - 2 phút):** Dùng `grep -n` định vị hàm/dòng lỗi, trích `old_string` 10–15 dòng, verify `grep -c == 1`.
3. **B2 (Coordinator - 2 phút):** Soạn `new_string` xử lý bug và xác định lệnh test (`pytest ...`).
4. **B3 (Worker duy nhất - 4 phút):** Dispatch 1 Worker áp patch và chạy unit test. Ngân sách `<= 8` calls.
5. **B4 (Coordinator - 2 phút):** Chạy Canary live 2–4 swipes ngẫu nhiên trên máy farm và đóng alert (hoặc rollback ngay nếu Canary fail).
