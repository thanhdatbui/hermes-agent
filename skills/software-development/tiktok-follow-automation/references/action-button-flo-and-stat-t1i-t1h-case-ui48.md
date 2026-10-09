# Case UI-48: Profile Action Button `id/flo` & Stat Counters `id/t1i`, `id/t1h` (Machine 50)

## 1. Triệu chứng & Bối cảnh
- **Farm Alert**: `🚨 [FARM ALERT: MÁY 50] DỪNG PHIÊN`
- **Script**: `tiktok-follow`
- **Máy**: 50 | Serial: `ce091609dd78991305` | Nick: `hng.th.v713`
- **Lỗi dừng**: `MANUAL_REVIEW: không thấy đúng một nút Follow trên exact profile`
- **Hiện trường XML**: `D:/Taadaa/m50_current.xml`

## 2. Root Cause
1. **TikTok UI Selector Drift trên Máy 50**:
   - Nút hành động quan hệ (Action Button) đổi sang resource-id `id/flo`:
     - Nút Follow: `text="Follow"`, `resource-id="com.ss.android.ugc.trill:id/flo"`, `bounds=[114,789][462,921]`
     - Nút Nhắn tin: `text="Nhắn tin"`, `resource-id="com.ss.android.ugc.trill:id/flo"`, `bounds=[474,789][822,921]`
   - Cụm thống kê Profile đổi sang resource-id `id/t1i` (số đếm) và `id/t1h` (nhãn):
     - `com.ss.android.ugc.trill:id/t1i` mang giá trị số: `"0"`, `"5"`, `"0"`
     - `com.ss.android.ugc.trill:id/t1h` mang nhãn: `"Đã follow"`, `"Follower"`, `"Thích"`
2. **Whitelist trong `verify_follow.py` bị thiếu**:
   - `_ACTION_BUTTON_SUFFIXES` chỉ có `("id/fds", "id/ff8", "id/fij", "id/fi6", "id/follow_button")`, thiếu `id/flo`.
   - `_STAT_COUNTER_IDS` chỉ có `("id/sdn", "id/shq", "id/svt", "id/svs", "id/suu", "id/sut", "id/svu")`, thiếu `id/t1i`, `id/t1h`.
   - Khi `classify_button(xml)` chạy, `_is_profile_action_node` trả về `False` cho các node `id/flo` vì không thuộc whitelist, dẫn đến `action_nodes` rỗng $\rightarrow$ trả về `"unknown"` $\rightarrow$ kích hoạt fail-closed `MANUAL_REVIEW: không thấy đúng một nút Follow trên exact profile`.

## 3. Bản Vá Codebase
### Sửa `follow_runner/flows/verify_follow.py`:
```python
_ACTION_BUTTON_SUFFIXES = (
    ":id/fds", ":id/ff8", ":id/fij", ":id/fi6", ":id/flo", ":id/follow_button",
    "id/fds", "id/ff8", "id/fij", "id/fi6", "id/flo", "id/follow_button",
)
_ACTION_BUTTON_IDS = _ACTION_BUTTON_SUFFIXES
_STAT_COUNTER_IDS = (
    "id/sdn", "id/shq", "id/svt", "id/svs", "id/suu", "id/sut", "id/svu",
    "id/t1i", "id/t1h",
)
```

## 4. Focused Unit Test
Thêm các test cases vào `follow_runner/tests/test_verify_follow.py`:
- `test_classify_machine50_action_button_id_flo_and_stat_t1i_t1h`: Kiểm tra cả 2 nhánh `not_followed` (nút Follow + Nhắn tin) và `followed` (nút Đã follow / Nhắn tin) với `id/flo`.
- `test_classify_rejects_stat_counter_t1i_and_t1h_as_action_button`: Đảm bảo `id/t1i` và `id/t1h` luôn bị loại khỏi `action_nodes`.
- `test_classify_m50_current_fixture_not_followed`: Đọc trực tiếp fixture dump `m50_current.xml` và xác minh phân loại đúng `not_followed`.
Lệnh chạy focused test:
```bash
python -m pytest -q follow_runner/tests/test_verify_follow.py -k "flo or t1i or m50"
```
