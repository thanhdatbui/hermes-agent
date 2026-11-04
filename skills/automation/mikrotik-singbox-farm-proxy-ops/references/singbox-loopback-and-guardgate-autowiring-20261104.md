# Bài Học Kỹ Thuật: Triệt Tiêu Loopback Proxy Singbox & Preflight Invariant Auto-Wiring (2026-11-04)

## 1. Bản Chất Bẫy Loopback Proxy Singbox Trên Máy Kibe (M33..M38 & M71..M80)
- **Triệu chứng sự cố:** Khi batch nuôi acc / lướt feed chạy trên 76 máy Kibe, 12 máy (`M33, M34, M36, M38, M71, M72, M73, M74, M75, M76, M77, M79`) đồng loạt fail preflight với lỗi:
  `Client.Timeout exceeded while awaiting headers` khi kết nối kiểm tra egress IP qua `ifconfig.me/ip`.
- **Nguyên nhân gốc rễ (Root Cause):**
  - Cấu hình gộp `singbox_full_160.json` (hoặc file sinh ra từ generator) bị điền nhầm phần `outbounds` của 16 máy Kibe này thành chính cổng Inbound của chúng (`server: "192.168.110.2", server_port: 200xx`).
  - Khi điện thoại Android kết nối vào cổng `200xx`, container Singbox nhận request rồi lại mở socket kết nối vào chính cổng `200xx` của chính nó (Self-Loopback).
  - Kết quả trong log RouterOS: `dial tcp 192.168.110.2:20038: connect: cannot assign requested address` (cạn socket OS) $\rightarrow$ Runner preflight bị timeout $\rightarrow$ kích hoạt Fail-Closed.
- **Quy chuẩn ánh xạ đúng (SSOT per commit 7a64c05):**
  - **14 máy Kibe:** `M33-M37`, `M71-M75`, `M77-M80` bắt buộc phải trỏ outbound về cụm MikroTik PPPoE Đà Nẵng:
    `server: "mirotik1.taadaa.click"`, `server_port: 10001..10007`, `user/pass: admin@1:admin@1`.
  - **2 máy Kibe:** `M38` và `M76` trỏ về proxy phụ trợ:
    `server: "khoalee.duckdns.org"`, `server_port: 16002`, `user/pass: 5ns08q:AmLmaMJ0`.
  - **Nạp cấu hình sang MikroTik:** Dùng minified JSON (`singbox_full_160_min.json` ~27KB) và PATCH thẳng vào `/rest/file/*8072575` (`docker/config/config.json`) rồi restart container `*6`.

## 2. Kiến Trúc Guard-Driven Preflight & Auto-Wiring Invariant Guidance
- **Vấn đề phát sinh:** GuardGate chặn commit nếu vi phạm invariant `case_invariant_require_step_by_step_structure` (code thêm mới $\ge 15$ dòng không có `# Step X` hoặc sửa logic không cập nhật test).
- **Rào cản:** Nếu Worker không được biết trước luật này, nó sẽ viết code theo thói quen cũ và bị Closeout Gate từ chối duyệt, tốn thêm 1 lượt dispatch để chữa cháy.
- **Giải pháp kiến trúc từ Hội đồng Cố vấn (Sol + Gemini):**
  - Không hardcode từng rule vào pipeline runner.
  - Xây dựng **Guidance Resolver $O(1)$** đọc trực tiếp từ `D:/Taadaa/tools/guardgate/rules.json`.
  - Trước khi dispatch Worker, trích xuất các guidance bắt buộc của target file type (như `.py`) và tiêm trực tiếp vào `[GUARDGATE INVARIANT GUIDANCE]` của contract để Worker tuân thủ ngay từ lần sinh code đầu tiên.
