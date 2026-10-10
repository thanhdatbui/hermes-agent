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

### 4.1 Luôn tra cứu bằng `search=<email>` trước khi tạo
Endpoint `GET /api/v3/profiles?search=<keyword>` tìm kiếm trên **toàn bộ database**, không bị kẹt ở trang 1:
```python
def ensure_profile_by_email(email: str, expected_name: str, raw_proxy: str) -> str:
    # 1. Tìm kiếm theo email trên toàn bộ GPM profiles
    res = requests.get(f"{GPM_API_BASE}/profiles?search={email}", timeout=10).json()
    items = res.get("data", [])
    if items:
        # Đã có profile chứa email này -> lấy ID profile đầu tiên/mới nhất, CẤM tạo mới
        profile_id = items[0].get("id") or items[0].get("profile_id")
        return str(profile_id)

    # 2. Chưa từng có profile -> Mới được phép tạo mới
    created = requests.post(
        f"{GPM_API_BASE}/profiles/create",
        json={
            "profile_name": expected_name,
            "raw_proxy": raw_proxy,
            "group_id": 1,
            "browser_type": "Chrome"
        },
        timeout=20
    ).json()
    ...
```

### 4.2 Phân trang đầy đủ khi duyệt danh sách profile
Khi cần nạp toàn bộ danh sách profile vào bộ nhớ (như trong watchdog map):
```python
def get_all_gpm_profiles():
    profiles = []
    page = 1
    while True:
        res = requests.get(f"{GPM_API_BASE}/profiles?page={page}&per_page=50", timeout=10).json()
        items = res.get("data", [])
        if not items:
            break
        profiles.extend(items)
        pagination = res.get("pagination", {})
        total_page = pagination.get("total_page", 1)
        if page >= total_page:
            break
        page += 1
    return profiles
```

### 4.3 Deduplication Cleanup định kỳ
- Quét các email có `len(profiles) > 1`.
- Giữ lại 1 profile duy nhất (profile có `profile_path` chứa dữ liệu session mới nhất hoặc đúng port hiện tại).
- Gọi `DELETE /api/v3/profiles/delete/{id}` dọn các profile clone rỗng để tránh rác đĩa và giải phóng `AMBIGUOUS_GPM_PROFILE`.
