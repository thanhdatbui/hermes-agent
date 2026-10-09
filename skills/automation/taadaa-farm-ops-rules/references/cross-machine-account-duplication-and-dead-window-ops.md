# Cross-Machine TikTok Account Duplication & Dead-Window Interventions

## 1. Hiện tượng Nick Bị Login Trùng Lặp Giữa Các Máy (Cross-Machine Parasitic Accounts)
- **Căn nguyên lịch sử:**
  - Trước khi triển khai kiểm tra độc quyền mail (`gmail_clean_v2.xlsx`), 1 tài khoản Hotmail từng bị gán/mua nhầm cho 2 máy khác nhau.
  - Khi máy thứ hai chạy quy trình login hoặc reg, nó đã đăng nhập vào tài khoản TikTok vốn thuộc về máy thứ nhất.
  - Hậu quả:
    - **Máy ký sinh (Parasitic Machine):** Bị đôn số lượng tài khoản thực tế trên app TikTok lên chạm trần 8 nick, làm ẩn nút *"Thêm tài khoản"* (`Add account`).
    - **Excel báo thiếu ảo (Phantom Missing Slot):** Trên bảng tính `taikhoan_dat_v2_updated .xlsx`, máy ký sinh vẫn có Slot 7/8 = `None` hoặc bị ghi đè trùng nick cũ.
    - **Vòng lặp lỗi Preflight / Reg Bù:** Hệ thống thấy Slot 7 = `None` $\rightarrow$ gọi reg bù $\rightarrow$ vào app TikTok bị kẹt cứng do không có nút Add account $\rightarrow$ crash `[04_add_account]`.
    - **Rủi ro cờ phạt TikTok:** Hai thiết bị vật lý khác nhau cùng lúc login chung một tài khoản TikTok.

- **Quy tắc xử lý:**
  1. Tuyệt đối không phán bừa là "nick rác ngoại lai". Phải đối chiếu UI XML của switcher với danh sách tài khoản toàn farm để xác định "máy chính chủ" (nơi tài khoản được cấp phát chính thức) và "máy ký sinh".
  2. Logout tài khoản trùng ra khỏi máy ký sinh để trả lại slot trống (hạ về 7 nick) $\rightarrow$ nút *"Thêm tài khoản"* lập tức xuất hiện trở lại.
  3. Làm sạch các dòng duplicate trong `taikhoan_dat_v2_updated .xlsx`.

---

## 2. Cạm Bẫy Ảo Giác Thời Gian & Canh Giờ Can Thiệp Farm (Anti-Stale-Clock Fallacy)

- **Cảnh giác chết người về thời gian thực (Wall-Clock Verification):**
  - Khi Coordinator đọc log của một phiên nuôi gần nhất (ví dụ: thấy `row-3-120331` vừa hoàn tất 79/80 máy), **CẤM TUYỆT ĐỐI** tự suy luận rằng "bây giờ đang là khoảng trống giữa Phiên 1 và Phiên 2 (13:00 - 14:00)".
  - Log lưu trên đĩa có thể là của một phiên đã xong từ 1-2 tiếng trước.
  - **BẮT BUỘC:** Trước khi quyết định can thiệp hoặc khẳng định "máy đang rảnh", phải chạy lệnh kiểm tra giờ hệ thống thực tế (`date` hoặc `datetime.now()`).

- **Quy hoạch khung giờ can thiệp farm an toàn (Farm Schedule Topology):**
  - **12:00 - 12:45:** Ca trưa Phiên 1 (Row 3/4). CẤM CAN THIỆP.
  - **12:45 - 13:55 (Dead-Window Ca Trưa):** Khoảng trống an toàn giữa 2 phiên nuôi, toàn farm nhả lock. Đây là thời điểm vàng để can thiệp / sửa chữa thiết bị.
  - **14:00 - 14:45:** Ca trưa Phiên 2 (Row 3/4 + Hook Upload). CẤM CAN THIỆP.
  - **14:45 - 18:00 (VÙNG NGUY HIỂM CAO):** Chuỗi `post-noon-chain-watchdog` chạy cuốn chiếu **Add 2FA TikTok (`run_batch_live_2fa.py`)** và **Reg Gmail** trên khắp các máy.
    - CẤM TUYỆT ĐỐI dispatch worker can thiệp hàng loạt trong khung giờ này vì sẽ tranh chấp ADB server, CPU và đường truyền MobiProxy, phá hỏng tiến trình 2FA của farm.
    - Nếu buộc phải xử lý khẩn cấp, CHỈ ĐƯỢC PHÉP can thiệp trên từng máy đơn lẻ sau khi đã xác minh máy đó:
      1. Đang ở Launcher (Home).
      2. Không có file lock trong `~/.codex/device-locks/`.
      3. Không nằm trong danh sách target của batch 2FA đang chạy.
