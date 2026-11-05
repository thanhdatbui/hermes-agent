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
> - `references/mobiproxy-ddns-fast-rotation-and-r3g-triage-20261105.md`: Vận hành tự động hóa đồng bộ DDNS 1 phút/lần cho 38 rule DNAT MobiProxy khi ISP Viettel xoay IP liên tục, khắc phục DNS ma Tailscale trên R3G và quy chuẩn thu hồi Peer VPS hết hạn.
> - `references/r3g-dns-fix-and-dual-cluster-kernel-dnat-20261105.md`: Khắc phục DNS ma Tailscale trên R3G & hoàn tất phủ sóng Kernel DNAT cho cả MobiProxy + R3G, kéo CPU MikroTik từ 97.6% về 1.6%.
> - `references/mobiproxy-dnat-automation-and-r3g-routing-analysis-20261105.md`: Kiến trúc Kernel DNAT toàn diện cho MobiProxy, tự động hóa đồng bộ DDNS 1 phút/lần, phân tích định tuyến Asymmetric Routing R3G và thu hồi bảo mật VPS hết hạn.
> - `references/mobiproxy-r3g-complete-kernel-dnat-and-vps-cleanup-20261105.md`: Chi tiết toàn bộ quy trình tắt pass MobiProxy bằng Playwright #access-save, gỡ kẹt DNS R3G, đồng bộ DDNS tự động và thu hồi VPS Doravo hết hạn.

