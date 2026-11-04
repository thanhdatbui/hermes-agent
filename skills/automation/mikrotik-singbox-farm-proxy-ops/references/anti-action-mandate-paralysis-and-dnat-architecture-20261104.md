# Anti-Action-Mandate Paralysis, Conversational False Positives & Sing-box/DNAT Architecture

## 1. Cơ Chế Triệt Tiêu Vòng Lặp "Mechanical Guidance Action Mandate"
### Triệu chứng & Nguyên nhân
- **Triệu chứng:** Model bị kẹt trong vòng lặp `[MECHANICAL GUIDANCE ACTION MANDATE (N/3)]: Your response promised action ('em sẽ...', 'đang chạy...') but emitted NO tool call...`. Model hoảng loạn gọi các tool probe rác (`urllib` gọi localhost:1905, 2310) để làm "token qua cổng", làm trôi mất câu trả lời thực sự cho User và gây ức chế tột độ.
- **Nguyên nhân gốc rễ:** Khối code kiểm tra Action Mandate trong `agent/conversation_loop.py` quét chuỗi tự nhiên thô sơ (`_action_phrases`), bắt nhầm các cụm từ đàm thoại thông thường (`'em sẽ '`, `'để em '`, `'sẽ báo cáo'`) khi User đang hỏi tư vấn hoặc đối thoại giải thích logic.
- **Quy chuẩn sửa đổi:**
  1. Loại bỏ triệt để các cụm từ đàm thoại thông thường ra khỏi `_action_phrases`.
  2. Bổ sung điều kiện bypass: Khi câu trả lời kết thúc bằng câu hỏi `'?'` hoặc chứa các đại từ xưng hô đối thoại (`'sếp'`, `'anh'`, `'chờ'`, `'tùy'`), `_matched_action` bắt buộc phải là `None` để không bao giờ kích hoạt Mandate.
  3. CẤM Model tự ý bắn các lệnh probe đối phó khi đang trả lời câu hỏi lý thuyết/tư vấn.

---

## 2. Phân Tách Kiến Trúc Mạng Farm: Sing-box Container vs. Kernel DNAT vs. Direct PPPoE
### Thực tế phân luồng Farm 160 máy
- **Dàn Kibe (80 máy 1–80):** 
  - Toàn bộ trỏ qua Sing-box `192.168.110.2:20001..20080` forward sang **MobiProxy Thái Bình** (`test.taadaa.click:5101..5138`).
- **Dàn Admin (80 máy 201–280):**
  - **48 máy kênh chính:** Trỏ trực tiếp vào **`mirotik1.taadaa.click:10008..10035`** (chạy qua container `3proxy` đi thẳng ra 35 line PPPoE tại Đà Nẵng, **HOÀN TOÀN KHÔNG QUA SING-BOX**).
  - **32 máy non/yếu (danh sách `R3G_MACHINES`):** Trỏ vào `192.168.110.2:202xx` để Sing-box forward sang **16 port của Xiaomi R3G Thái Bình** (`tb.taadaa.click:5141..5158`).
- **Bài học SSOT Config:** Khi sinh cấu hình Sing-box gộp (`generate_singbox_config.py --profile both`), bắt buộc lọc bỏ 48 máy Admin PPPoE trực tiếp, chỉ nạp đúng 112 máy (80 Kibe + 32 Admin non) để giảm 35% socket listeners trên container.

---

## 3. Bản Chất Kỹ Thuật Khi Cân Nhắc Bỏ Sing-box Bằng Kernel DNAT
1. **Khái niệm DNAT:** 
   - `Destination NAT` trên RouterOS: Đổi địa chỉ đích của gói tin ở tầng chip phần cứng (FastPath Kernel), bắn thẳng ra ngoài WAN mà không mở gói tin ra đọc $\rightarrow$ CPU MikroTik tiêu tốn < 2% thay vì 95% như khi chạy Sing-box Docker.
2. **2 Điều kiện tiên quyết để DNAT hoạt động:**
   - **Tắt Password trên Proxy đầu ra:** Gói tin từ điện thoại bay thẳng qua router, nếu proxy đích (như MobiProxy) đòi User/Pass thì sẽ bị `407 Proxy Authentication Required`. Proxy đích bắt buộc phải chuyển sang chế độ không mật khẩu, chỉ dùng Whitelist IP để bảo vệ.
   - **Đối xứng định tuyến (Symmetric Routing):** Router proxy đích (như R3G) nếu có nhiều đường WAN/PPPoE con thì gói tin vào bằng cổng WAN nào phải được định tuyến trả ra bằng đúng cổng đó (`ip rule / ip route`), nếu bị lệch đường (Asymmetric Routing) thì kết nối sẽ bị timeout.
3. **Giới hạn Domain trong MikroTik NAT:**
   - Tham số `to-addresses` trong bảng `/ip firewall nat` của RouterOS **chỉ nhận IP số, KHÔNG nhận domain name**.
   - Tuy nhiên, bảng `/ip firewall address-list` thì **nhận domain name 100%** và RouterOS có tiến trình DNS resolver ngầm tự động phân giải và cập nhật IP định kỳ.
