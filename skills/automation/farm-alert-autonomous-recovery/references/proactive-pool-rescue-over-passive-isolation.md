# Proactive Pool Rescue Over Passive Quarantine (Chống Cô Lập Đối Phó)

> User steering invariant: "ủa chứu sao đéo cứu acc đi mà đi cô lập, mày phá v"
> Bản chất: Khi nhận cảnh báo watchdog pool (ChatGPT-Web, Codex, Antigravity, Proxies) có tài khoản lỗi/degraded, mục tiêu số 1 là **CỨU ACC VÀ TÁI KÍCH HOẠT (RESCUE & REACTIVATE)**, tuyệt đối CẤM chỉ đi cô lập (`is_active = 0`) rồi báo cáo cho có lệ.

---

## 1. Phân Biệt Giữa "Hành Vi Đối Phó" và "Hành Động Cứu Acc Thật Sự"

| Tình huống | Hành vi sai (Bị nghiêm cấm) | Hành động chuẩn hóa bắt buộc |
| :--- | :--- | :--- |
| Watchdog báo lỗi liveness / token | Kiểm tra thấy DB đã set `is_active = 0`, chụp ảnh lỗi rồi dừng lại báo cáo "đã cô lập an toàn". | Bắt buộc gọi trực tiếp test endpoint `/api/providers/{cid}/test` hoặc `/api/providers/validate` để đo liveness thời gian thực. |
| Proxy báo lỗi (502 / 403 / Reset) | Cho rằng tài khoản đã chết, bỏ mặc không điều tra proxy. | Rà soát bảng `proxy_registry`: Kiểm tra credentials (user/password có bị rỗng không như lỗi port 10006 `admin@1`), kiểm tra IP proxy có đang thông mạng không. Sửa cấu hình proxy xong test lại ngay. |
| Test trả về `valid: True` | Để nguyên trạng thái cũ vì sợ đụng chạm. | Lập tức cập nhật `UPDATE provider_connections SET is_active=1, test_status='active', last_error=NULL...` để đưa tài khoản trở lại phục vụ traffic. |
| Token hết hạn / văng phiên | Bỏ mặc hoặc deactivate tài khoản. | Kiểm tra xem profile GPM có credentials trong Excel/Workbook không. Nếu có, kích hoạt flow login tự động lấy session token mới. |
| Tài khoản bất khả kháng | Khẳng định mập mờ "lỗi OpenAI / lỗi Google". | Bắt buộc giải mã payload cụ thể (ví dụ: `{"errorCode": "account_deactivated"}`) hoặc chụp ảnh màn hình Phone Checkpoint chứng minh không thể vượt tự động, rồi mới fail-closed giữ `is_active = 0`. |

---

## 2. Quy Trình Cứu Pool 4 Bước (Triage & Reactivation Pipeline)

### Bước 1: Test Liveness Trực Tiếp Từng Tài Khoản
Không tin hoàn toàn vào trạng thái cached của watchdog vừa chạy. Gọi trực tiếp endpoint OmniRoute (:20129):
```python
# Test connection hiện tại qua proxy đã gán
req = urllib.request.Request(f"http://127.0.0.1:20129/api/providers/{cid}/test", data=b"{}", headers={"Content-Type": "application/json"})
res = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
# Hoặc validate token thô
req_v = urllib.request.Request("http://127.0.0.1:20129/api/providers/validate", data=json.dumps({"provider": "chatgpt-web", "apiKey": token}).encode(), headers={"Content-Type": "application/json"})
```

### Bước 2: Triage Hạ Tầng Trước Khi Kết Luận Tài Khoản Chết
Rà soát `proxy_assignments` và `proxy_registry`:
- Rất nhiều trường hợp "EMPTY_SESSION_TOKEN" thực chất là do proxy:
  - Proxy MikroTik đổi policy hoặc thiếu username/password trong database `proxy_registry` (`username = '', password = ''` thay vì `admin@1:admin@1`).
  - Cụm MobiProxy 4G đang trong chu kỳ đổi IP tự động (trả 502 Bad Gateway trong 3-5 giây).
- Khắc phục cấu hình proxy trong SQLite và chạy lại test liveness. Nếu test trả về `valid: True`, tài khoản hoàn toàn khỏe mạnh.

### Bước 3: Kích Hoạt Lại (Reactivate) Tức Thì
Khi đã xác minh token hợp lệ:
```sql
UPDATE provider_connections 
SET is_active = 1, 
    test_status = 'active', 
    last_error = NULL, 
    last_error_at = NULL, 
    backoff_level = 0, 
    rate_limited_until = NULL,
    updated_at = CURRENT_TIMESTAMP 
WHERE id = ?;
```

### Bước 4: Đối Soát Số Học 100% Ma Trận Pool
Sau khi xử lý, bắt buộc xuất ma trận đối soát số học chính xác:
`Active Connections + Quarantined Connections = Total Connections`.
Mọi tài khoản nằm trong nhóm Quarantined bắt buộc phải có lý do kỹ thuật đích đáng:
- Upstream Deactivated (có payload JSON chứng minh).
- Stored session expired (đã đưa vào hàng đợi supervisor để re-login).
- Google SID expired (đã lên lịch cho ca login tiếp theo).

---

## 3. Quy Chuẩn Closeout Gate Cho Phiên Vận Hành (Operational Triage)

Khi kết thúc phiên làm việc dạng operational triage (không sửa source code trong git repo):
1. **Tuyệt đối không chạy closeout_gate bằng chuỗi văn bản ngắn một dòng:** Chạy `--text "..."` chung chung sẽ bị Sol Auditor đánh 0/100 vì thiếu bằng chứng thực thi.
2. **Lập file báo cáo kiểm toán đầy đủ:** Ghi vào `D:/Taadaa/reports/operational_closeout_<date>.md` với các thành phần:
   - Scope rõ ràng (Operational triage, không đụng source code).
   - Đảm bảo an toàn giao dịch SQLite (`PRAGMA journal_mode = wal`, transaction atomic commit).
   - Chi tiết nguyên nhân gốc và trích xuất nguyên bản (verbatim output) của các phép test endpoint (kèm latency, status).
   - Ma trận đối soát số học 100% của toàn bộ các pool.
   - Bằng chứng kiểm tra sức khỏe dịch vụ và thiết bị phần cứng sau can thiệp.
3. **Thực thi Gate:** Chạy `python D:/Taadaa/tools/closeout_gate.py --input <path_to_md> --json-output` để đạt verdict APPROVED (>= 85 hoặc Grace Band >= 80).
