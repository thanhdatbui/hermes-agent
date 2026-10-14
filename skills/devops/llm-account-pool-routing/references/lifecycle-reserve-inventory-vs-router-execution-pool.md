# Phân Định Kho Dự Trữ Vòng Đời (Lifecycle Inventory) vs Pool Định Tuyến Router (OmniRoute Execution Pool)

## 1. Triệu Chứng & Thắc Mắc Thường Gặp
- **Tình huống:** User/Admin thắc mắc khi thấy báo cáo định kỳ từ watchdog (ví dụ `chatgpt-web-pool-healer-watchdog`):  
  *"T nhớ reg cả đống acc chatgpt rồi mà sao pool ít vậy??"* khi con số báo cáo chỉ hiển thị `ChatGPT-Web: 28/43 ACTIVE` hoặc `Codex: 15/16 ACTIVE`.
- **Nguyên nhân gây hiểu lầm:** Nhầm lẫn giữa **tổng số tài khoản đã đăng ký thành công trong kho GPM** với **số lượng connection đang được cắm vào router OmniRoute (`:20129`)** để chạy model.

---

## 2. Bản Chất 2 Tầng Tài Khoản Trong Hệ Thống Farm

### A. Tầng 1: Kho Tài Khoản Vòng Đời (Lifecycle Account Inventory / Reserve Pool)
- **Vị trí lưu trữ:**
  - Database vòng đời GPM: `D:\Taadaa\runtime\kibe\cron-state\batch_gpm_5profiles_supervisor_state.json` (Kibe Farm) và `D:\Taadaa\runtime\admin\cron-state\batch_gpm_5profiles_supervisor_state.json` (Admin Farm).
  - Bảng đối soát Excel: `taikhoan_dat_v2_updated .xlsx` và `PROXYgandienthoai.xlsx`.
- **Quy mô thực tế:** Hàng trăm đến hơn 740+ tài khoản (ví dụ: 404 nick Kibe + 344 nick Admin đã hoàn tất đăng ký ChatGPT).
- **Trạng thái vòng đời:**
  - `WAIT_7D`: Đang ngâm an toàn 7 ngày trên profile GPM (tránh Microsoft / OpenAI khóa tài khoản do hành vi bất thường).
  - `CODEX_OAUTH`: Chờ lấy OTP 5SIM kích hoạt xác minh số điện thoại cho Codex.
  - `CHANGE_INFO`: Đang đổi mật khẩu và cập nhật email khôi phục chính chủ (`@fviainboxes.com`).
  - `DONE`: Tài khoản hoàn thiện 100%, sẵn sàng bàn giao hoặc lưu kho dự phòng chiến lược.
- **Mục đích:** Kho tài nguyên dự phòng (Reserve Pool) phục vụ nuôi farm TikTok dài hạn, làm tài khoản Codex, hoặc dự trữ thay thế.

---

### B. Tầng 2: Pool Định Tuyến Thực Thi (Router Execution Pool trên OmniRoute `:20129`)
- **Vị trí lưu trữ:** SQLite `~/.omniroute/storage.sqlite`, bảng `provider_connections` (`chatgpt-web`, `codex`).
- **Quy mô thiết kế:** Duy trì tối ưu từ **30 – 50 tài khoản active** xoay tua (Round-Robin).
- **Mục đích:** Phục vụ trực tiếp các tác vụ AI nội bộ của Farm:
  - Model `chatgpt-web/gpt-5.6-sol-high`: Chấm điểm code reviewer độc lập (Closeout Gate) với chi phí **0đ Quota**.
  - Tier 2 Fallback cho combo `omni-worker` khi các API trả phí gặp rate-limit.

---

## 3. Lý Do Tuyệt Đối Không Nạp Toàn Bộ Kho Dự Trữ Vào OmniRoute

1. **Bẫy Chết Chùm Session & Quét Cloudflare Sentinel:**
   - Phiên đăng nhập web (`__Secure-next-auth.session-token`) của OpenAI có thời gian sống (TTL). Nếu nạp 500–700 tài khoản vào router nhưng lưu lượng thực tế chỉ tập trung gọi qua một số connection, hàng trăm cookie còn lại sẽ hết hạn âm thầm.
   - Khi watchdog quét định kỳ để refresh đồng loạt, việc mở hàng loạt profile GPM trên cùng dải IP/proxy sẽ kích hoạt Cloudflare Turnstile / Sentinel, dẫn đến chết chùm tài khoản.

2. **Bảo Vệ Tài Nguyên Máy Chủ (RAM / CPU / Bus):**
   - Watchdog tự phục hồi (`chatgpt-web-pool-healer-watchdog`) chạy mỗi 6h để cứu các tài khoản rớt cookie bằng cách mở Chromium qua GPMLogin CDP.
   - Nếu pool có 700 connections, watchdog sẽ phải spawn hàng trăm tiến trình Chrome, gây tràn RAM, nghẽn cổng CDP và làm sập toàn bộ hệ thống GPMLogin.

3. **Kỷ Luật Gán Proxy 1:1:**
   - Mỗi connection trong OmniRoute bắt buộc phải gán proxy cố định theo máy farm (nghiêm cấm random proxy). Việc nạp 700 acc đòi hỏi 700 proxy riêng biệt trực tuyến 24/7, gây lãng phí tài nguyên mạng.

4. **Hiệu Năng Router SQLite & Độ Trễ (Latency):**
   - Bảng `provider_connections` gọn nhẹ (~50 records) giúp SQLite truy vấn nhanh dưới 2ms, giảm độ trễ của từng turn hoàn thành prompt.

---

## 4. Chính Sách Bơm Bù Tài Khoản (Replenishment & Top-Up Protocol)

Khi số lượng tài khoản active trên OmniRoute rớt dưới ngưỡng an toàn (< 25 tài khoản active) hoặc cần mở rộng quy mô:
1. **Lọc ứng viên từ Kho Dự Trữ GPM:**
   - Chọn các tài khoản đã hoàn thành `WAIT_7D` hoặc `DONE` trong file state của Kibe / Admin.
2. **Gán Proxy Chuẩn Farm:**
   - Đối soát số máy và port proxy từ `PROXYgandienthoai.xlsx`.
3. **Nạp Từng Mẻ Cuốn Chiếu (Batch 5–10 accounts):**
   - Mở profile GPM trích xuất session cookie mới.
   - Nạp vào bảng `provider_connections` với `provider = 'chatgpt-web'`.
   - Chạy test xác thực qua `/api/providers/validate` (phải trả về `HTTP 200 / valid: true`).
4. **Cập Nhật Combo:**
   - Thêm các connection mới vào combo `chatgpt-web-pool` và `review` trên `:20129`.

---

## 5. Nguyên Tắc Phủ Tối Thiểu 1 Account / Proxy IP & Kỷ Luật "Cấm Phá Proxy"

### A. Chỉ Thị Vận Hành: "Mỗi IP có ít nhất 1 acc"
- **Mục tiêu:** Mọi proxy endpoint trong `proxy_registry` (32 cổng Mobi `test.taadaa.click:5101..5138`, 35 cổng MikroTik `mirotik1.taadaa.click:10001..10035`) đều phải có **ít nhất 1 tài khoản ChatGPT-Web active**.
- **Lợi ích kiến trúc:**
  - Phân tán đều lưu lượng ra 100% dải IP 4G và router MikroTik của farm.
  - Tránh dồn tải nhiều request vào 1–2 IP gây rate-limit / Cloudflare Challenge, đồng thời không để lãng phí proxy rảnh.

### B. Kỷ Luật Bất Biến: Cấm Phá Proxy (Anti-Random-Proxy Invariant)
- **Bẫy phá proxy từng xảy ra ("như lần trước"):**
  - Script tự ý dùng lệnh `SELECT id FROM proxy_registry ... ORDER BY RANDOM() LIMIT 1` bốc proxy ngẫu nhiên khi connection bị thiếu hoặc lỗi.
  - Hậu quả nghiêm trọng: Tài khoản bị đảo proxy liên tục, dính bot-check Google/OpenAI, bị router Direct Fallback lộ IP host máy chủ `1.53.55.190` dẫn đến deactivation hàng loạt.
- **Quy tắc gán chuẩn tuyệt đối (Deterministic 1:1 Mapping Contract):**
  1. *Lấy Port từ Nguồn Chuẩn:* Trích xuất `raw_proxy` từ Profile GPM (hoặc bảng Excel `PROXYgandienthoai.xlsx` theo số máy).
  2. *Truy Vấn Khớp Tuyệt Đối:* 
     ```sql
     SELECT id FROM proxy_registry WHERE host = ? AND port = ?;
     ```
  3. *Bắt Buộc Gán Vào `proxy_assignments`:*
     ```sql
     DELETE FROM proxy_assignments WHERE scope = 'account' AND scope_id = ?;
     INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at)
     VALUES (?, 'account', ?, 0, datetime('now'), datetime('now'));
     ```
  4. *CẤM TUYỆT ĐỐI:*
     - Cấm dùng `ORDER BY RANDOM()`.
     - Cấm nạp connection trần vào `provider_connections` mà không tạo ngay dòng tương ứng trong `proxy_assignments`.
     - Cấm bật `is_active = 1` trước khi dòng `proxy_assignments` đã được tạo thành công (bắt buộc theo Atomic 3-Step Fail-Closed: Staging is_active=0 -> Match Proxy 1-1 -> Gated Activation is_active=1).
     - Cấm gán chéo proxy giữa dàn Kibe (Mobi 51xx, MikroTik 10001..10007) và dàn Admin (MikroTik 10008..10035).

---

## 6. Hiện Tượng Reboot Máy Chủ & Khả Năng Tự Phục Hồi (Reboot Resilience)
- **Tình huống:** Máy chủ farm tự động reboot định kỳ vào sáng sớm (~05:20 AM trước ca nuôi 1) hoặc do operator reboot giải phóng bus phần cứng EHCI USB.
- **Cơ chế phục hồi tự động:**
  - Các service chạy dưới nền (OmniRoute port 20129, GPMLogin port 19995, 9Router port 20128) được cấu hình tự khởi động lại cùng Windows Startup / Service watchdog.
  - Các watchdog và supervisor cronjob tự động chạy tiếp theo schedule (như `gpm_5profiles_supervisor`, `feed_session_watchdog`).
- **Xử lý Session dở dang (Interrupted Turns):**
  - Nếu phiên làm việc của Coordinator bị ngắt giữa chừng do reboot:
    1. Trạng thái database và file code đã patch vẫn tồn tại an toàn trên ổ đĩa.
    2. Turn đang chờ phản hồi sẽ không bị mất dữ liệu ngữ cảnh mà được lưu trong session DB.
    3. Coordinator dùng `session_search` rà soát lại các mốc thời gian quanh thời điểm reboot (`psutil.boot_time()`) để xác nhận phần việc đã hoàn tất và tiếp tục thực thi mượt mà, tránh chạy trùng lặp tác vụ.

