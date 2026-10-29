---
name: android-farm-host-operations
description: "Use when farm devices drop, USB hangs, or entering BIOS."
---
# Android Farm Host Operations

References:
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

Scripts:
- `scripts/safe_usb_guard.py` — Script nguồn mẫu giám sát và reset EHCI bus theo ngưỡng.
- `scripts/wait_admin_reboot.py` — Theo dõi tự động chu kỳ reboot Admin PC qua SSH, chờ khởi động ADB daemon và đối soát danh sách máy online.
- `scripts/admin_ssh.py` — Helper chuẩn hóa thực thi PowerShell/CMD sang Admin PC qua SSH bọc subprocess UTF-16LE EncodedCommand, chống bẫy Guard terminal.

Use when phone farm devices drop from ADB/PC, USB controllers hang, entering UEFI/BIOS fails, or setting up host-level hardware recovery on phone farm controller PCs.

## 1. Bản Chất Lỗi Văng Hàng Loạt Máy ADB / Tool Quản Lý (XiaoWei/Jiwei)
- **Sai lầm chẩn đoán:** Đổ lỗi cho "Power Balance" (High Performance, USB Selective Suspend, PCIe ASPM). Khi farm đang hoạt động, cổng USB luôn có traffic nên Windows không bao giờ tự ru ngủ cổng.
- **Nguyên nhân gốc rễ phần cứng:**
  1. Mainboard farm (như Huananzhi X99-F8D / dual Xeon) thường bị tắt chip Intel USB 3.0 xHCI trong BIOS, dồn 80 máy vào 2 controller USB 2.0 EHCI (`8D26`, `8D2D`).
  2. Băng thông USB 2.0 trần chỉ 35-40 MB/s. Khi 30-40 worker chạy đồng loạt gọi `screencap` (~2MB/ảnh PNG) hoặc kéo video/app, xuất hiện I/O spike dồn dập làm nghẽn bus, tràn endpoint, controller treo thanh ghi phần cứng $\rightarrow$ văng toàn bộ hub.
  3. Reset PC cứu được là do gửi tín hiệu System Bus Reset giải phóng thanh ghi controller, không phải do cài đặt nguồn.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
