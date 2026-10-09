# FARM-ASSET-001: BẢO VỆ TÀI SẢN NICK TIKTOK TRÊN THIẾT BỊ & CẤM TUYỆT ĐỐI TỰ Ý LOGOUT (HARD INVARIANT)

Mã quy chuẩn: `FARM-ASSET-001` · Mức độ: `CRITICAL / INVARIANT` · Áp dụng cho: Mọi Agent (Coordinator, Subagent Worker, Claude Code, OpenCode) và mọi automation script trên toàn bộ các repo Farm.

---

## 1. Triết Lý Cốt Lõi (Core Principles)
1. **Mọi nick TikTok đang đăng nhập trên máy farm là TÀI SẢN DOANH NGHIỆP CỦA USER:**
   - Agent chỉ có quyền sử dụng tài sản phục vụ ca chạy/nuôi acc. **Agent TUYỆT ĐỐI KHÔNG CÓ QUYỀN ĐỊNH ĐOẠT TÀI SẢN.**
2. **CẤM TUYỆT ĐỐI TỰ Ý GÁN NHÃN:**
   - Các từ *"nick lạ"*, *"nick rác"*, *"nick test"*, *"nick không rõ nguồn gốc"* **hoàn toàn vô giá trị và bị nghiêm cấm**. Trạng thái tài khoản chỉ được xác định bằng **dữ liệu đối soát lịch sử**, không theo cảm tính của Agent.
3. **Nguyên Tắc Fail-Closed:**
   - Bất kỳ nghi ngờ, mâu thuẫn dữ liệu, OCR mờ, hoặc thiếu thông tin: **MẶC ĐỊNH LÀ CẤM LOGOUT 100%**.
4. **Mất Phiên Là Mất Tài Sản Thật:**
   - Logout bừa bãi làm mất cookie, mất device trust, mất chuỗi nuôi feed, tốn công sức xác minh lại. Dừng máy chờ kiểm tra luôn rẻ hơn làm mất tài sản.

---

## 2. Bảng Ma Trận Phân Loại & Quyền Hạn Logout

| Trạng thái | Điều kiện nhận diện | Hành động được phép | Quyền Logout? |
|---|---|---|---|
| **A. Nick chính chủ** | `owner_stt == current_stt` | Nuôi / Tương tác bình thường | ❌ **CẤM TUYỆT ĐỐI** |
| **B. Nick ký sinh** | Có đúng 1 dòng trong Excel và `owner_stt != current_stt` | Đăng xuất qua `do_logout_account.py` (User đã phê duyệt) | ✅ **ĐƯỢC PHÉP** (Chỉ qua Technical Guard) |
| **C. Nick không có trong Excel** | Không tìm thấy username trong Excel tracking hiện tại | **Coi là sự cố lệch dữ liệu (Unrecorded Asset / Data Desync)**. Đóng băng máy $\rightarrow$ Truy vết backup $\rightarrow$ Báo cáo User | ❌ **CẤM TUYỆT ĐỐI** |
| **D. Nick trùng dòng** | Username xuất hiện $\ge 2$ dòng có `owner_stt` khác nhau | Giữ nguyên hiện trường $\rightarrow$ Báo cáo User xử lý Excel | ❌ **CẤM TUYỆT ĐỐI** |
| **E. Không đọc rõ danh tính** | OCR không ra username, text rỗng, fuzzy match | Dừng lại, giữ nguyên phiên | ❌ **CẤM TUYỆT ĐỐI** |

> **CHỈ CÓ DUY NHẤT TRƯỜNG HỢP (B) — NICK KÝ SINH ĐƯỢC PHÉP LOGOUT.** Mọi trường hợp khác đều bị chặn đứng ở tầng code.

---

## 3. Quy Trình Bắt Buộc Khi Gặp Nick Không Có Trong Excel (Case C - Data Desync)
1. **Bước 1 — Đóng băng hiện trường (Freeze):**
   - Dừng ngay mọi automation trên máy. CẤM logout, CẤM xóa dữ liệu (`pm clear`), CẤM gỡ app.
2. **Bước 2 — Thu thập bằng chứng:**
   - Chụp màn hình trang Profile và Switcher, chạy WinRT OCR đọc rõ username, display name.
3. **Bước 3 — Truy vết ngược:**
   - Quét ngược các file backup (`backup_clean_v2_*.xlsx`, `taikhoan_dat_v2_updated.bak*`, `gmail_clean_v2.bak*`, log `social_reg_log.txt`).
4. **Bước 4 — Báo cáo User & CHỜ CHỈ ĐẠO:**
   - Cung cấp hiện trường và nguồn gốc tìm thấy trong backup.
   - **CHỜ USER QUYẾT ĐỊNH.** Tuyệt đối không có timeout nào cho phép Agent tự tiện bấm nút Đăng xuất.

---

## 4. Technical Guard & Anti-Bypass
1. Mọi thao tác logout BẮT BUỘC phải gọi `logout_guard.evaluate_logout()` và `logout_guard.assert_logout_allowed()` trước khi chạm bất kỳ lệnh ADB nào.
2. Ném lỗi `LogoutForbidden` và ghi nhận structured audit/incident JSONL nếu phát hiện `OWN_ACCOUNT`, `UNRECORDED`, `DUPLICATE`, hoặc `UNVERIFIED`.
3. Cấm bắt `LogoutForbidden` rồi nuốt lỗi hoặc dùng script khác để bypass.
