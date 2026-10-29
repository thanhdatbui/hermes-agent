# GPM Profile Proxy Safety Invariant & Post-Reboot Resource Sync Protocol

## 1. Cấm Tuyệt Đối Chạy Profile Farm Không Có Proxy (Direct IP Leak Ban)
- **Căn nguyên sự cố:** Khi thực hiện tác vụ tự động hóa hoặc đăng ký dịch vụ (như AWS / Gmail / Hotmail / TikTok), việc tự ý tạo profile GPM mới không gắn proxy (`raw_proxy == ""`) hoặc chọn profile farm nhưng không xác thực proxy làm rò rỉ IP trực tiếp của máy host (Kibe/Admin).
- **Hậu quả:** Khiến toàn bộ dàn tài khoản nuôi bị liên đới (chain ban), cờ bot Google / AWS kích hoạt và làm hỏng tài sản farm.
- **Quy tắc bất biến:**
  1. Mọi profile GPM liên quan đến farm (Gmail, Hotmail, TikTok) BẮT BUỘC phải mang proxy di động (MobiProxy / MikroTik) hợp lệ.
  2. CẤM tạo profile mới ad-hoc/tạm bợ khi farm đã có sẵn pool profile (Gmail, Hotmail, TikTok). Bắt buộc tái sử dụng profile có sẵn.
  3. **Quyền Operator với profile Direct có sẵn:** Operator có các profile dùng IP direct máy host (test nội bộ, cá nhân). Gate cơ giới hóa KHÔNG ĐƯỢC CHẶN lệnh `start` profile (`/api/v3/profiles/start/{id}`) đối với profile có sẵn. Chỉ CHẶN TRIỆT ĐỂ lệnh tạo mới (`create`) profile thiếu proxy.
  4. Sau khi khởi động Chromium qua CDP: BẮT BUỘC điều hướng đến `https://api.ipify.org?format=json` để đọc IP thực tế và so khớp với dải IP proxy được giao trước khi điều hướng sang trang đích.

---

## 2. Đặc Tả Cơ Giới Hóa: `guard_gpm_proxy.py` (Claude Opus Approved Spec - 129 Tests Passed)
Hệ thống triển khai chốt chặn cơ giới hóa thực dụng O(1) tại `D:/Taadaa/tools/guard_gpm_proxy.py`, đi kèm bộ kiểm thử toàn diện `D:/Taadaa/tools/tests/test_guard_gpm_proxy.py`:

### A. Triết lý thiết kế (Zero-Fluff, Không Over-Engineer, Không Khóc Lóc):
- Bỏ toàn bộ các cơ chế phức tạp gây nghẽn: không ký HMAC, không token TTL, không can thiệp Windows Firewall.
- Thuần Python stdlib (`re`, `json`, `ipaddress`, `sys`), thời gian thực thi cực nhanh (< 5ms), zero network call trong hook.
- Tương thích song song cả môi trường **Hermes Hook** (in `{"action":"block",...}` và exit 0) và **Claude Code Hook** (exit code 2 khi có `hook_event_name`).

### B. Logic Chặn Cốt Lõi:
1. **Bảo toàn Profile có sẵn:** Không chặn lệnh `/api/v3/profiles/start` hoặc `/api/v3/profiles` (list/update). Các profile direct có sẵn của Operator chạy bình thường.
2. **Chặn Đứng Lệnh Tạo Mới Thiếu Proxy (`/profiles/create`):**
   - Regex nhận diện: `CREATE_RE = re.compile(r'/profiles/create(?![\w-])', re.IGNORECASE)`. Bắt được cả trường hợp ghép URL qua biến/f-string (`f"{GPM_API}/profiles/create"`).
   - Kiểm tra định dạng theo Allowlist:
     * Chặn ngay nếu chứa placeholder/biến động: `$`, `%`, `{`, `}`, hoặc từ khóa direct: `none`, `direct`, `null` (kể cả dạng `direct:8080`).
     * Tách host và port: Host bắt buộc là domain hợp lệ, IPv4 literal, hoặc IPv6 trong ngoặc vuông `[a-fA-F0-9:]+`.
     * Cấm tuyệt đối loopback và wildcard: `localhost`, `127.x.x.x`, `0.0.0.0`, `::1`.
     * Port bắt buộc là số nguyên hợp lệ trong khoảng `1 <= port <= 65535`.
3. **Phòng Thủ Lệnh Ghép & Batch (P1 Multi-Body Defense):**
   - Đếm số lượng lời gọi create: `len(CREATE_RE.findall(cmd))`.
   - Đếm số top-level JSON body hợp lệ chứa profile (`body_count`).
   - Nếu `create_calls > body_count` (ví dụ: create 1 có inline JSON nhưng create 2 dùng `-d @file.json` hoặc biến shell `$b`) $\rightarrow$ **BLOCK NGAY** theo nguyên tắc Fail-Closed.
   - Trong batch list `[A, B]` hoặc wrapper `{"profiles": [A, B]}`, từng profile body bắt buộc phải có key `raw_proxy` riêng. Nếu có dù chỉ 1 body thiếu $\rightarrow$ **BLOCK NGAY**.
4. **Fail-Closed Toàn Diện:**
   - Bọc `try/except Exception` ở `main()`: Mọi lỗi đệ quy sâu, memory error hoặc crash bất ngờ khi lệnh có chứa `/profiles/create` đều lập tức gọi `deny()`.
   - Stream UTF-8 an toàn: Tự động `reconfigure(encoding="utf-8")` và in JSON bằng `ensure_ascii=True` để không bao giờ bị `UnicodeEncodeError` trên Windows console pipe (cp1252/ascii).

---

## 3. Xử Lý Hiện Tượng GPM Đòi Cập Nhật Resource Sau Reboot Máy
- **Hiện tượng:** Sau khi máy reboot (như chu kỳ 05:20 sáng), khi gọi API khởi động profile v3, GPM trả về lỗi:
  ```json
  {"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}
  ```
- **Bản chất kỹ thuật:**
  - File thực thi và DLL trong `gpm_browser_chromium_core_142` trên đĩa vẫn nguyên vẹn 100%.
  - Khi app GPMLogin khởi động mới sau reboot, logic nội bộ yêu cầu đồng bộ trạng thái runtime/manifest với server GPMLogin trước khi Local API v3 cho phép khởi chạy profile. File version trong thư mục core có thể tạm thời hiển thị `1.0` thay vì `1.1`.
- **Quy trình kích hoạt:**
  - Không tự tiện xóa hay ghi đè lung tung vào thư mục core trình duyệt.
  - Khởi chạy app GPM với cửa sổ hiển thị, thực hiện thao tác mở profile trên app hoặc xác nhận cập nhật gói tài nguyên qua giao diện GPM để hệ thống nạp lại manifest hợp lệ.
