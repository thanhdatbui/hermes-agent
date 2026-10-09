# Hard Invariant: Bắt Buộc Bắn Farm Alert Khi Lỗi Script Hàng Loạt (All-Repo Automation)

## 1. Nguyên Tắc Cốt Lõi
Mọi luồng tự động hóa chạy theo lô/batch (Lướt Feed, Follow Hook, Upload Video Hook, Reg, Login, 2FA, v.v.):
- **Lỗi cá lẻ (Sporadic):** Dưới ngưỡng $\rightarrow$ Xử lý an toàn, tự cách ly thiết bị dính lỗi hoặc ghi nhận vào báo cáo tổng kết.
- **Lỗi hệ thống / Hàng loạt (Systemic Script Errors):** BẮT BUỘC PHẢI BẮN CẢNH BÁO KHẨN CẤP `🚨 [FARM ALERT / BATCH ALERT: LỖI HỆ THỐNG]` về kênh Telegram Farm Alert (`-5373649734`).
- **Tuyệt đối cấm:**
  + Nuốt lỗi script hàng loạt để làm tròn thành ca chạy thành công.
  + Gom lỗi script vào mục "Bỏ qua: Khác" (Other Skipped) để che giấu thất bại.
  + In danh sách máy cộc lốc (ví dụ `Lỗi script/xác minh (3): 32, 43, 45`) mà không in rõ lý do lỗi cụ thể.

## 2. Ngưỡng Kích Hoạt Cảnh Báo Hệ Thống (Dual-Threshold Rule)
Một sự cố được xếp vào loại **LỖI HỆ THỐNG / HÀNG LOẠT** và bắt buộc bắn Farm Alert khi thỏa mãn ĐỒNG THỜI:
1. Số máy dính lỗi có cùng nhóm nguyên nhân (Error Signature): $\ge 3\text{ máy}$.
2. Tỷ lệ lỗi trên quy mô ca/batch: $\ge 15\%$ (hoặc tỷ lệ fail toàn ca $\ge 30\%$).

### Các nhóm lỗi script điển hình bắt buộc kích hoạt Alert:
- **Follow Hook:**
  + Kẹt mở tab Đang follow / Follower list trên profile Anchor (`MANUAL_REVIEW: mở tab Đã follow fail`).
  + Lệch selector nút Follow / RecyclerView khiến runner không tương tác được.
  + Script follow bị văng hoặc trả exit code != 0 trên nhiều máy.
- **Upload Video Hook:**
  + Uploader script timeout (> 20 phút) do kẹt popup không xử lý được.
  + Thiếu video rendered / lỗi đường dẫn video folder.
  + App TikTok bị văng hoặc chặn không cho chọn media tải lên.
- **Lướt Feed:**
  + Lỗi Proxy / VPN ngắt kết nối đồng loạt khiến không load được video.
  + TikTok bị văng hoặc kẹt màn hình đen / màn hình khóa.

## 3. Cấu Trúc Nội Dung Báo Cáo Cảnh Báo Bắt Buộc
Khi phát hiện lỗi script hàng loạt, nội dung tin nhắn gửi về Telegram Farm Alert phải gồm:
1. **Header cảnh báo nổi bật:** `🚨 [FARM ALERT / BATCH ALERT: LỖI HỆ THỐNG] - <Tên Ca/Batch> (Row X)`
2. **Quy mô thiệt hại:** Số lượng máy thành công / số lượng máy dính lỗi.
3. **Chi tiết từng cụm lỗi (Signature & Reason):**
   - Tên lỗi: Nêu rõ hiện tượng (ví dụ: *Kẹt mở tab Đang follow sau ladder lần 2*).
   - Danh sách máy dính lỗi: Liệt kê rõ số máy (kèm username TikTok của máy).
4. **Chỉ dẫn kiểm chứng Canary:** Nêu đích danh 1 máy đại diện để chạy probe:
   `python D:/Taadaa/tools/inspect_machine.py <M>`
5. **Khuyến nghị xử lý:** Chỉ rõ lỗi nằm ở tầng selector, proxy hay logic flow để người điều hành ra quyết định ngay.
