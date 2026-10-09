# KINH NGHIỆM VẬN HÀNH: NHẬN DIỆN ACCOUNT SWITCHER 8 NICK & CẤM CLARIFY TREO PHIÊN [05/10/2026]

## 1. CẤM TUYỆT ĐỐI GỌI `clarify` GÂY TREO PHIÊN (USER FRUSTRATION SIGNAL)
- **Triệu chứng**: Khi gặp phân vân (ví dụ: mapping row nào, chọn target account nào), Coordinator gọi `clarify` để hỏi User.
- **Hậu quả**:
  - Giao diện chat bị đóng băng, treo cứng chờ phản hồi từ người dùng.
  - Runtime dễ rơi vào orphan recovery trạng thái không xác định.
  - User cực kỳ bức xúc ("Lồn mẹ mày lí do treo", "Gọi clarify là cái lồn gì?").
- **Kỷ luật bất biến**:
  - `clarify` CHỈ ĐƯỢC DÙNG khi cần quyết định nghiệp vụ tiêu tiền thật (SMS, proxy, captcha trả phí) hoặc thao tác hủy diệt không thể đảo ngược.
  - Mọi trường hợp điều phối, sửa lỗi, chạy Canary, phân tích hiện trường: BẮT BUỘC Coordinator tự tra cứu Source of Truth (`taikhoan_run_safe.xlsx`, `Tik*.xlsx`, dumpsys, log artifact) để tự quyết định trong ngân sách L0–L2.

---

## 2. BẪY NHẬN DIỆN SWITCHER MÁY ĐỦ 8 TÀI KHOẢN (8-ACCOUNT ROSTER PITFALL)
- **Bối cảnh**: Farm chuẩn hóa 8 tài khoản/máy.
- **Hiện tượng**:
  - Script mở Switcher thành công, nhưng `classify_screen` hoặc `_is_profile_account_switcher_xml` không công nhận màn hình này là Switcher.
  - Dẫn đến việc script coi đây là popup chặn (`manual-needed:account-switcher`), dừng session và báo `manual-needed: account switcher requires manual review`.
- **Nguyên nhân gốc rễ**:
  1. **Nút "Thêm tài khoản" bị tràn màn hình**: 8 nút tài khoản chiếm trọn chiều cao 1920px của RecyclerView (`bounds="[0,252][1080,1920]"`), đẩy nút *"Thêm tài khoản"* xuống dưới đáy (off-screen). Bộ kiểm tra nếu đòi hỏi `has_add_account` sẽ fail.
  2. **Display Name có khoảng trắng**: Tài khoản active trên máy có tên hiển thị chứa khoảng trắng (ví dụ `"Diep Lam"`), khiến hàm `_looks_like_account()` trong `automation-core` từ chối (`" " not in value` fail), dẫn đến cờ `has_selected_account` bị `False`.
  3. **Fallback quá cứng nhắc**: Trong `_is_profile_account_switcher_xml` (của `feed_swipe_smoke.py`), điều kiện cũ bắt buộc `has_title and has_add_account`. Khi không thấy nút thêm tài khoản, nó rơi xuống nhánh titleless kiểm tra `has_profile_prose`, bị dính các chuỗi tiếng Việt như *"trang tính dưới cùng"* hoặc *"Diep Lam"* nên trả về `False`.
- **Giải pháp chuẩn hóa (Case Fix)**:
  - Khi XML đã có tiêu đề Switcher (`has_title` = True, ví dụ *"Chuyển đổi tài khoản"* / *"Switch account"*) VÀ có danh sách các dòng tài khoản (`account_rows`), BẮT BUỘC công nhận ngay là Switcher hợp lệ (`if has_title and (has_add_account or account_rows): return True`).
  - Unit test kiểm chứng: `test_is_profile_account_switcher_xml_accepts_eight_account_roster_without_visible_add_button` bảo vệ bất biến này.
