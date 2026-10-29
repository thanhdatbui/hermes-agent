# Dashboard 80/20: Macro vs Micro Separation & Anti Master-Detail Bloat Trap

## Bối Cảnh Thực Tế (Case Study Dashboard 1905)
Trong `tiktok_dashboard.py` và `dashboard/follow_detail_component.py`, tính năng "Sổ Bệnh Án" ban đầu được thiết kế như một Popup Modal vi mô để xem quota và lịch sử follow UID của từng nick cụ thể.

Tuy nhiên, tại commit `52cd179`, tính năng này bị over-engineer thành một màn hình **Master-Detail toàn trang** (`setView('follow_records')`), bổ sung thêm một nút Toolbar ngang hàng (`btn-follow-records`) và cột trái `fd-left` chứa danh sách toàn bộ ~160 nick/máy trên farm.

## Triệu Chứng & Lỗi Trải Nghiệm (UX Conflict)
1. **Bung menu all nick khi xem 1 nick:**
   - Khi người dùng đang ở tab khác bấm vào nút `📜 Bệnh án` của 1 nick, hàm `openFollowDetailModal()` kích hoạt `setView('follow_records')`.
   - Thay vì mở một popup modal nhẹ nhàng của đúng nick đó, trang web bị reload/chuyển view sang Master-Detail.
   - Trên trình duyệt di động (Safari/Chrome điện thoại có chiều rộng `< 900px`), CSS layout `flex-direction: column` đẩy toàn bộ cột `fd-left` lên trên đỉnh (`max-height: 34vh`), hiển thị một menu dài dằng dặc các nick all farm trước khi cuộn tới chi tiết tài khoản.
2. **Xung đột & Trùng lặp 100% với tab Sức Khỏe Follow:**
   - Tab **Sức Khỏe Follow (`follow_health`)** đã có sẵn đầy đủ 5 thẻ KPI, bộ lọc trạng thái (Khỏe, Hồi phục 1/2, Cooldown, Bị nhả), bộ lọc Cụm (Kibe/Admin), bộ lọc Hàng và danh sách thẻ/bảng duyệt toàn farm.
   - Cột `fd-left` của tab **Sổ Bệnh Án (`follow_records`)** lại nhân bản lại toàn bộ hành vi duyệt, tìm kiếm và lọc nick này một lần nữa.

## Quy Tắc Thiết Kế 80/20 Cho Farm Dashboard
1. **Phân định rạch ròi 2 cấp độ:**
   - **Cấp Vĩ Mô (Macro / Farm-Level) - 80% thời gian:**
     * Nơi hiển thị bức tranh toàn cảnh: Tỷ lệ an toàn toàn dàn, dải proxy bị cầu dao ngắt, tối ưu Quota phân tầng, danh sách quản lý nick.
     * Thuộc về tab chính trên Toolbar (ví dụ: `🩺 Sức Khỏe Follow`, `🏥 Sức Khỏe Cụm Máy`).
   - **Cấp Vi Mô (Micro / Account-Level) - 20% thời gian:**
     * Nơi soi sâu chi tiết của 1 nick cụ thể: Quota thăng tiến (`Cohort`, `Proven`, `Active`, `LastFailed`), lý do lỗi, và bảng danh sách UID con đã follow.
     * BẮT BUỘC thiết kế dưới dạng **Popup Modal tại chỗ (Contextual Modal Popup)**.
2. **Luật cấm Master-Detail trên chức năng vi mô:**
   - TUYỆT ĐỐI KHÔNG biến một thao tác xem chi tiết của 1 entity thành màn hình Master-Detail chuyển view.
   - Bấm vào chi tiết của nick nào $\rightarrow$ Chỉ mở duy nhất Popup Modal của nick đó đè lên màn hình hiện tại.
   - Bấm `X` đóng lại $\rightarrow$ Giữ nguyên vị trí cuộn và trạng thái lọc của người dùng, không bao giờ làm gián đoạn luồng làm việc.
