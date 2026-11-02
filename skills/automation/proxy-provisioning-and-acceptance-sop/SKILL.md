---
name: proxy-provisioning-and-acceptance-sop
description: "Quy chuẩn nghiệm thu cài đặt proxy router/box mới và quy trình kiểm tra 4 bước chống đổ thừa nhà mạng."
version: 1.0.0
category: automation
tags: [farm, proxy, openwrt, singbox, mikrotik, fail-closed, acceptance]
---
# Proxy Provisioning & Acceptance SOP (Chống Bệnh Đổ Thừa Nhà Mạng)

Sử dụng quy chuẩn này khi cài đặt, chuyển đổi kiến trúc mạng hoặc thêm box/router proxy mới (R3G, MobiProxy, OpenWrt, MiniPC) cho phone farm. Mục tiêu là triệt tiêu dứt điểm bệnh "cài cấu hình ngu rồi đổ thừa do nhà mạng".

## 1. Bài Học Xương Máu: Bản Chất Lỗi Cấu Hình Nội Bộ (Incident 02/11/2026)
Khi 29 máy Admin bị chặn fail-closed `blocked-proxy-vpn`, Agent vội vã kết luận "do mạng Viettel Thái Bình chập chờn / rớt line". Thực tế điều tra 100% là do **3 lỗi cấu hình ngớ ngẩn bên mình**:
1. **Lệch Cầu Nối Sing-box (Outbound Stale):** Khi chuyển sang mô hình Direct WAN (bỏ trạm PC Admin trung gian), Sing-box trên MikroTik vẫn để trỏ vào `192.168.110.119:51xx` (IP PC Admin) thay vì trỏ ra domain `tb.taadaa.click:51xx`. Kết nối sang PC Admin bị ngắt dẫn đến timeout toàn bộ.
2. **Kẹt Cờ Cách Ly Trên Sổ Cái (Quarantine Stale):** 32 máy trong `PROXYgandienthoai.xlsx` và SQLite `farm_master.db` vẫn ghi chuỗi `QUARANTINE_R3G_INVESTIGATION` từ đợt sự cố trước. Runner preflight thấy chuỗi không có port số nên chặn dừng an toàn.
3. **Lệch Quy Hoạch Cổng Inbound (Sequential 20201.. vs 20200 + M):** File Excel ghi một kiểu (`20201..20218`), file script ADB và verify lại yêu cầu `20200 + M` (M203 -> 20203).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
