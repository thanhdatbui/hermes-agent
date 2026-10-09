# Quy chuẩn Silent Watchdog & Phân định Lưu trữ Tri thức (Memory vs Skill/Repo)

## 1. Bài học vận hành: Silent Watchdog cho Kho Hàng & Cron Alert
### Sai lầm phổ biến:
Khi thiết kế runner kiểm tra kho định kỳ (ví dụ: `daily_manual_stock_checklive.py` chạy lúc 07:00), agent thường mắc bẫy "báo cáo rằng tôi đang bỏ qua":
```text
📊 BÁO CÁO CHECK LIVE KHO UP TAY
⏰ 30/09/2026 07:00 | Thời gian chạy: 8s
ℹ️ Các sản phẩm up tay hiện đều đang hết hàng từ các ngày trước (không có biến động mới, bỏ qua không báo lặp).
Tổng quan: Tất cả mã up tay đang hết hàng (0 tồn kho).
```
User feedback trực tiếp:
> *"Bỏ qua là k đăng nữa luôn ấy chứ k phải báo về bot đâu? Khi nào có hàng biến động ms báo"*

### Nguyên tắc chuẩn mực:
- **"Bỏ qua" (Skip) = Im lặng hoàn toàn**: Khi tập hợp các dòng báo cáo (`report_lines`) rỗng, script phải ghi log nội bộ và thoát ngay (`return 0`), tuyệt đối KHÔNG gọi API gửi tin nhắn Telegram (`send_telegram_bot`).
- **Điều kiện kích hoạt thông báo (Biến động thực tế)**:
  1. Sản phẩm còn tồn kho: `info['stock'] > 0`.
  2. Sản phẩm vừa hết hàng trong ngày: `info['stock'] == 0 and prev_stock > 0` (báo chuyển dịch trạng thái 1 lần duy nhất).
  3. Có đơn hàng bán mới: `info.get('sold_yesterday', 0) > 0` (dù tồn kho hiện tại đang bằng 0 do bán hết trong ngày).
  4. Có tài khoản DIE mới được dọn dẹp.
- **Telemetry Observability không gây spam**:
  - Ghi nhận chỉ số đo lường qua stdout dạng chuẩn:
    `[TELEMETRY_METRIC] silent_skip=1 active_products=0 skipped_products=6 elapsed_s=...`
  - Các watchdog/audit log đọc metric này mà không làm phiền người dùng trên Telegram chat.

---

## 2. Kỷ luật phân định tri thức: Memory vs Skill / Repository
User feedback trực tiếp:
> *"K cập nhật memory nặng bot, đẩy vào đúng repo của nó"*

### Quy tắc bất di bất dịch:
- **Bot Memory (`target='memory'`)**:
  - Bị giới hạn ngân sách ký tự cứng (2.200 chars).
  - Được inject tự động vào **mọi turn hội thoại** của mọi phiên làm việc.
  - **CHỈ DÙNG CHO**: Sự thật cốt lõi về con người User (tên, role, style giao tiếp), thông số môi trường bền vững khó khám phá lại (cổng proxy, socket ADB, ID cluster).
  - **CẤM TUYỆT ĐỐI**: Lưu quy tắc nghiệp vụ, giải thuật, quy trình vận hành, log task, hoặc bài học sửa code vào Memory. Làm như vậy gây "nặng bot", phình context, lãng phí token và làm chậm suy luận.
- **Skill Library (`SKILL.md` & `references/`)**:
  - Nơi lưu trữ chuẩn mực toàn bộ quy trình, logic vận hành, ma trận quyết định và bài học kinh nghiệm (pitfalls).
  - Khi phát sinh quy tắc mới, cập nhật ngay vào `SKILL.md` hoặc thêm file chuyên đề trong thư mục `references/` của skill tương ứng.
- **Codebase Repository**:
  - Mã nguồn thực thi, unit tests, script kiểm thử và tài liệu dự án phải được commit và push vào đúng git repo của nó (ở đây là `D:\Taadaa\Hermes` hoặc repo chuyên biệt).
