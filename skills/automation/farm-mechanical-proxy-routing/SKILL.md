---
name: farm-mechanical-proxy-routing
description: "Kiến trúc và quy chuẩn khóa cơ học (Mechanical Enforcement) định tuyến proxy và Direct IP trên toàn Farm, chống ảo tưởng memory."
version: 1.0.0
category: automation
tags: [farm, proxy, mechanical-enforcement, direct-ip, ssot, sqlite, fail-closed]
---
# Farm Mechanical Proxy Routing & Direct IP Enforcement

Use this skill when designing, maintaining, or auditing proxy routing across farm accounts (Phone Farm S7, GPM profiles, AGY CLI pools, or automation scripts).

## 1. Core Invariant: Anti-Memory Illusion (Chống Ảo Tưởng Memory)
- **Bẫy Ảo Tưởng Memory:** Khi Operator yêu cầu phân định mạng (ví dụ: tài khoản chính Direct IP, tài khoản farm 1:1 theo S7 proxy), TUYỆT ĐỐI KHÔNG ỷ lại vào text prompt, guideline Markdown hay persistent memory. Prompt không có tính cưỡng chế tại runtime và chắc chắn sẽ bị vi phạm khi chuyển ca hoặc đổi mô hình.
- **Nguyên Tắc Cơ Học Tối Cao:** Mọi chính sách phân định mạng bắt buộc phải được mã hóa cứng thành **Khóa cơ học (Mechanical Enforcement)** ở cả 3 tầng: Cơ sở dữ liệu, Module điều phối và Môi trường thực thi subprocess.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
