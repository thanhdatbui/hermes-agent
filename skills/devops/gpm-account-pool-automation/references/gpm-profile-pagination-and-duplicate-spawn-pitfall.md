# GPMLogin Profile Pagination Trap & Duplicate Spawn Pitfall

> 📌 **Bối cảnh thực tế:**  
> Hệ thống GPM liên tục bị "đẻ" ra các profile trùng lặp cho cùng một email (có tài khoản bị clone tới 3–5 profile cùng tên). Watchdog `chatgpt-web-pool-healer-watchdog` sau đó phát hiện nhiều hơn 1 profile cho cùng email và kích hoạt lỗi `AMBIGUOUS_GPM_PROFILE`, từ chối thao tác để tránh ghi đè nhầm session.

---

## 1. Bản Chất Kỹ Thuật: Bẫy Phân Trang GPM Local API v3

### 1.1 Mặc định phân trang 50 profiles của GPMLogin v3
- Endpoint `GET /api/v3/profiles` của GPMLogin Local API (cổng 19995) mặc định trả về:
  ```json
  {
    "success": true,
    "data": [ ... 50 profiles ... ],
    "pagination": {
      "total": 690,
      "page": 1,
      "page_size": 50,
      "total_page": 14
    }
  }
  ```
- **Lỗi phổ biến trong script (supervisor / batch create)**:
  ```python
  # ❌ BẪY CHÍ MẠNG: Chỉ gọi GET không tham số
  listed = api("GET", "/api/v3/profiles")
  items = listed.get("data", [])
  for item in items:
      if item.get("name") == info["profile_name"]:
          return item["id"]
  # Không tìm thấy trong 50 profiles trang 1 -> Tự động gọi create!
  created = api("POST", "/api/v3/profiles/create", ...)
  ```
- **Hậu quả**: Khi farm có trên 50 profile (thực tế 690+ profiles chia trên 14 trang), 640 profile ở các trang 2–14 hoàn toàn vô hình với hàm kiểm tra. Mỗi chu kỳ chạy, script không thấy profile $\rightarrow$ tưởng chưa có $\rightarrow$ tạo mới tiếp một profile trùng tên!

### 1.2 GPM API không có Unique Constraint
- GPMLogin Local API cho phép tạo vô số profile có cùng `profile_name` hoặc cùng chứa một email mà không hề báo lỗi hay từ chối.
- Nếu tầng client không có cơ chế idempotency bảo vệ, việc tạo profile trùng lặp diễn ra âm thầm không giới hạn.

---

## 2. Nguyên Nhân Cốt Lõi: Script Tự Ý Tráo / Fallback Proxy Khi Thấy Down (Auto-Proxy Mutation Trap)

### 2.1 CẤM NGỘ NHẬN "USER TỰ ĐỔI PROXY" (HARD USER CORRECTION)
- **Kỷ luật bất biến**: User **KHÔNG BAO GIỜ** tự ý chuyển hay đổi proxy của các máy/tài khoản.
- **Thực tế đã xảy ra**: Do các script trong hệ thống thấy proxy bị lỗi, sập mạng, hoặc thiếu mapping đã **tự ý đổi phá**:
  1. Tự động bốc proxy ngẫu nhiên từ registry: `ORDER BY RANDOM() LIMIT 1` (ví dụ trong `chatgpt_gpm_direct_reg.py`).
  2. Tự tính toán công thức fallback port theo số máy: `5100 + machine` (ví dụ: máy 66 có port thật là 5134 nhưng script tự tính thành `5166`; máy 33 bị script tráo giữa Mobi 5133 và Mikrotik 10001).
  3. Tự fallback sang port Mikrotik `20000 + m_idx` khi không đọc được mapping (ví dụ trong `sync_gpm_lifecycle.py`).

### 2.2 Hậu quả: Lệch tên profile -> GPM sinh thêm profile clone
- Cú pháp tên profile được format theo: `{Số_máy} - {Email} - {Cổng_proxy}`.
- Khi script tự ý nhảy proxy sang port khác $\rightarrow$ Tên profile bị lệch port (ví dụ: `66 - ... - 5134` biến thành `66 - ... - 5166`) $\rightarrow$ Script so khớp chuỗi không thấy $\rightarrow$ GPM API tạo thêm profile mới toanh với port mới, làm phân mảnh session và sinh lỗi `AMBIGUOUS_GPM_PROFILE`.

### 2.3 QUY TẮC BẢO VỆ PROXY BẤT BIẾN (PROXY INVARIANT):
- **Source of Truth duy nhất**: Duy nhất file `PROXYgandienthoai.xlsx` của User.
- **Fail-Closed khi Proxy lỗi/sập**: Nếu proxy bị timeout, die, hoặc sập $\rightarrow$ BẮT BUỘC giữ nguyên mapping, log error và dừng chờ; **CẤM TUYỆT ĐỐI** tự ý đổi port, đổi proxy, fallback công thức hay random proxy khác gán vào tài khoản!

---

## 3. Hệ Quả Lên Watchdog Hồi Sinh & LLM Pool

1. **Lỗi `AMBIGUOUS_GPM_PROFILE`**:
   - Trong `cron_chatgpt_web_pool_watchdog.py`:
     ```python
     def get_unambiguous_gpm_profile(gpm_map, email):
         candidates = gpm_map.get(email, [])
         if len(candidates) == 1:
             return candidates[0]
         if len(candidates) > 1:
             return None  # AMBIGUOUS_GPM_PROFILE
     ```
   - Watchdog fail-safe dừng lại, không dám chọn bừa profile để mở browser đăng nhập vì không biết profile nào giữ cookie xịn.
2. **Spam cảnh báo định kỳ**:
   - Watchdog mỗi 6h quét lại, tiếp tục gặp lỗi ambiguous và spam cảnh báo về Telegram.

---

## 4. Giải Pháp Bắt Buộc Khi Thao Tác Với GPM Profiles

### 4.1 Luôn tra cứu bằng `search=<email>` và kiểm tra chặt chẽ email + proxy trước khi tạo
Endpoint `GET /api/v3/profiles?search=<keyword>` tìm kiếm trên **toàn bộ database**, không bị kẹt ở trang 1.
Khi đối soát các profile tìm được:
- Bắt buộc kiểm tra kết hợp: `email in name` VÀ khớp đúng `raw_proxy == expected_proxy` (hoặc profile không cấu hình proxy) để tránh nhận nhầm profile của tài khoản/máy khác.
- Tuyệt đối không gọi `POST /create` nếu đã tồn tại profile khớp email và proxy:

```python
def ensure_profile(info: Dict[str, Any]) -> str:
    if info.get("profile_id"):
        return str(info["profile_id"])
    email = str(info.get("email") or "").strip().lower()
    try:
        if email:
            import urllib.parse
            listed = api("GET", f"/api/v3/profiles?search={urllib.parse.quote(email)}")
            items = listed.get("data", listed) if isinstance(listed, dict) else listed
            for item in items or []:
                name = str(item.get("name") or "").lower()
                raw_proxy = str(item.get("raw_proxy") or "")
                if email in name and (not info.get("proxy") or raw_proxy == info["proxy"]):
                    pid = item.get("id") or item.get("profile_id")
                    if pid:
                        info["profile_id"] = str(pid)
                        return str(pid)
        else:
            listed = api("GET", "/api/v3/profiles")
            items = listed.get("data", listed) if isinstance(listed, dict) else listed
            for item in items or []:
                if str(item.get("name", "")).strip() == info.get("profile_name", ""):
                    info["profile_id"] = item.get("id") or item.get("profile_id")
                    return str(info["profile_id"])
    except Exception as exc:
        raise RuntimeError(f"GPM profile lookup failed: {exc}") from exc

    # Chỉ khi hoàn toàn không tìm thấy mới được phép tạo profile mới
    created = api("POST", "/api/v3/profiles/create", ...)
    ...
```

### 4.2 Tự Động Phân Giải Profile Khi Phát Hiện Trùng (Disk Cookie Heuristic Resolver)
Trong các watchdog (như `cron_chatgpt_web_pool_watchdog.py`), khi gặp `len(candidates) > 1`, thay vì vội vàng ném lỗi `AMBIGUOUS_GPM_PROFILE` dừng toàn bộ quy trình:
- Đọc trực tiếp kích thước file session cookie trên đĩa (`<profile_path>/Default/Network/Cookies`).
- Nếu có 1 profile có cookie thực tế lớn (>50KB) trong khi các profile clone còn lại là rỗng/nhỏ (0–45KB) $\rightarrow$ Tự động chọn profile có cookie session thật để tiếp tục vận hành.

### 4.3 Deduplication Cleanup An Toàn Có Audit & Backup
- **Quy trình dọn dẹp chuẩn:** Tool `D:\Taadaa\GPM auto\scripts\deduplicate_gpm_profiles.py` (chạy với `--apply`, mặc định dry-run).
- **Sao lưu bắt buộc:** Luôn sao lưu SQLite DB `profile_data.db.backup_<ts>` trước khi xóa.
- **Audit JSON:** Ghi nhận `deduplicate_gpm_profiles.audit.json` lưu số lượng profile đã xóa, trạng thái dry-run, và đường dẫn file backup để phục vụ kiểm toán closeout gate.
- **Tiêu chí xếp hạng giữ lại:**
  1. Kích thước file Cookies lớn nhất (`Default/Network/Cookies` > 50KB).
  2. Khớp đúng số máy (`M<mid>`) theo SoT `taikhoan_dat_v2_updated .xlsx` và cổng proxy chuẩn trong `PROXYgandienthoai.xlsx`.
  3. Thời gian cập nhật gần nhất (`mtime`).
- **Xóa kép:** Gọi API GPM `/api/v3/profiles/delete/{id}?mode=1` kết hợp dọn dẹp SQLite row để tránh dữ liệu mồ côi. Unit test bao phủ tại `tests/test_deduplicate_gpm_profiles.py`.
