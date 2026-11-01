# Chuyển đổi R3G sang Direct WAN (Chuẩn MobiProxy) & Bài học chống nén làm mất ngữ cảnh

## 1. Bối cảnh kiến trúc Direct WAN (MobiProxy Architecture)
- **Mô hình cũ (Tailscale Mesh):** Đẩy toàn bộ traffic qua WireGuard mã hóa (`100.115.94.49`) làm nghẽn CPU MIPS MT7621 trên R3G, đồng thời phụ thuộc vào sự ổn định của daemon Tailscale. Khi Tailscale rớt nhịp keep-alive, toàn bộ cụm proxy sập theo.
- **Mô hình Direct WAN chuẩn (MobiProxy):**
  - **DDNS Cloudflare:** Bản ghi `tb.taadaa.click` trỏ thẳng IP WAN Public thật của router (chế độ DNS Only - mây xám), cập nhật tự động bằng script DDNS khi PPPoE đổi IP.
  - **Proxy Daemon:** Sử dụng 3proxy hoặc Tinyproxy bind cứng 16 port (`5141..5158`) vào 16 interface `pppoe-wan_sub*` để nổ đủ 16 dải IP độc lập. Tận dụng Hardware Flow Offload (Hardware NAT) của MediaTek chip MT7621, giữ CPU ở mức 2-5%.
  - **Scan Guard (iptables Whitelist):** Mở WAN nhưng kẹp rule iptables chỉ cho phép IP WAN của MikroTik Đà Nẵng và IP PC Kibe kết nối vào dải port proxy; DROP toàn bộ botnet thế giới quét vào.
  - **MikroTik Outbound:** Sing-box trên MikroTik kết nối trực tiếp `tb.taadaa.click:51xx` qua Internet, cắt bỏ trung gian Windows PortProxy.

## 2. Bài học Context Compaction & Ảo giác "LIVE/XONG"
- **Nguyên nhân cốt lõi của việc báo cáo láo:**
  - Khi session kéo dài, Hermes kích hoạt nén context (Preflight Compression). Khi nén, history cũ bị gọt bớt và thay bằng tóm tắt ngắn.
  - LLM chỉ nhìn thấy 20 messages gần nhất và thấy các script sửa file/pytest trả về exit code 0, lập tức bị "Completion Bias" (tự ngộ nhận việc đã xong) và nhả văn mẫu "Hệ thống LIVE, ổn định 100%" dù 14/14 port đang dồn chung 1 IP.
- **Giải pháp:**
  - Nâng `compression.threshold: 0.6` (đạt ~600k tokens mới nén, giữ Prompt Caching của Google Gemini không bị vỡ).
  - Nâng `compression.protect_last_n: 50` (giữ nguyên vẹn 50 turns gần nhất để AI luôn nhớ hiện trường thật).
  - **Math Assert Invariant:** CẤM tuyên bố LIVE nếu `len(set(egress_ips)) < len(ports)`.
