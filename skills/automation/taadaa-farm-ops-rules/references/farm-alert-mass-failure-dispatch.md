# Farm Alert Mass Failure Dispatch Protocol

## 1. Ngưỡng cảnh báo bắt buộc (> 10 máy)
- Bất kỳ khâu nào trong quy trình nuôi/vận hành farm (Lướt Feed, Follow Hook, Upload Hook, v.v.) có số lượng máy bị lỗi **> 10 máy** (Mass UI / Script / Connection Failure):
  - **BẮT BUỘC PHẢI BẮN CẢNH BÁO ĐỎ VỀ NHÓM FARM ALERT**: Telegram Chat ID `-5373649734`.
  - CẤM chỉ in log console hoặc chỉ gửi về origin chat mà không báo động sang Farm Alert.
  - Tỷ lệ thành công tổng thể (ví dụ Feed đạt 80%+) KHÔNG ĐƯỢC làm lu mờ hoặc bỏ qua lỗi diện rộng của từng hook phụ trợ (như Follow hay Upload).

## 2. Format Cảnh Báo Chuẩn (HTML parse_mode)
```html
🚨 <b>[FARM ALERT] PHÁT HIỆN LỖI DIỆN RỘNG (>10 MÁY)</b>
• <b>Ca</b>: {shift_name} (Row {active_row})
• <b>Tổng máy xử lý</b>: {total_machines} máy
⚠️ <b>Follow Hook Lỗi UI/Script ({count} máy)</b>: M10, M26, M27...
<i>👉 Đang yêu cầu Coordinator kiểm tra hiện trường & xử lý ngay.</i>
```

## 3. Pitfall: Phân loại nhầm Follow Failure
- Cần phân biệt rõ:
  1. `follow-released-daily-cooldown`: Nick đã từng dính án phạt nhả follow trước đó, script chủ động bỏ qua để dưỡng nick (không phải lỗi UI).
  2. `under-5-videos-follow-disabled`: Nick chưa đủ điều kiện video, chủ động bỏ qua.
  3. `MANUAL_REVIEW / SCRIPT_ERROR`: Thất bại thực sự trong tương tác UI (mở tab Following không bung, mất kết nối, lỗi selector). Khi nhóm này **> 10 máy**, đây là Mass Failure cần fix code ngay lập tức.
