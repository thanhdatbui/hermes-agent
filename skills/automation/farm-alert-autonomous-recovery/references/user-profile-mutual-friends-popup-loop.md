# User Profile Mutual Friends False Positive vs Share Sheet Loop Triage

## 1. Hiện tượng sự cố & Quy mô Batch
- **Cảnh báo hệ thống**: `[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM KIBE - MÁY 1-80】`
- **Tỷ lệ ảnh hưởng**: 10.0% toàn batch (8/80 máy: M4, M18, M35, M49, M58, M61, M72, M76).
- **Chữ ký lỗi (Signature)**:
  `manual-needed-popup:manual-needed:popup remained after allowed shared dismiss attempts; swipe recovery (2 swipes) still stuck`

---

## 2. Phân tích Nguyên nhân Gốc rễ (Root Cause Mechanism)

### Chuỗi sự kiện dẫn đến kẹt (Chain of Failure)
1. **Lọt vào trang Profile cá nhân**: Trong quy trình lướt feed TikTok (`feed-session-smoke`), sau khi swipe qua video chứa thẻ gợi ý kết bạn hoặc chạm vào khu vực profile, ứng dụng điều hướng vào màn hình Profile của người dùng khác (ví dụ `@trieutruc0505`).
2. **Nhận diện nhầm Popup**:
   - Trên màn hình Profile này có mục thông tin bạn bè chung: `text="Bạn bè với Kimm Ngânn, Thao Phan và 13 người khác"` và nút `class="android.widget.Button", text="Follow"`.
   - Trong `automation-core/src/automation_core/tiktok/benign_popup.py`, hàm `detect_contact_follow_suggestion(root)` quét chuỗi từ khóa và phát hiện:
     - `"bạn bè với"` -> khớp `contact_marker`.
     - `"Follow"` -> khớp `follow_marker`.
   - Cả 2 điều kiện bắt buộc đều thỏa mãn, khiến `detect_contact_follow_suggestion` kết luận đây là một popup gợi ý kết bạn danh bạ hợp lệ!
3. **Bẫy ImageView Menu góc trên bên phải (Share Sheet Trap)**:
   - Do trang Profile người dùng không có nút đóng popup ngữ nghĩa ("Đóng", "Close", nút X), cơ chế fallback `_close_candidate(filtered_elements)` được kích hoạt.
   - Hàm này tìm thấy một node `ImageView` ở góc trên bên phải màn hình:
     `bounds=[948,96][1056,204]`, `center=[1002,150]`.
   - Thực chất đây là nút **Menu tùy chọn / Chia sẻ profile** của TikTok.
   - Lệnh click vào tọa độ này khiến TikTok bung ra **Share Sheet** bottom dialog (`Gửi đến`, `Sao chép Liên kết`, `Trang tính`...).
4. **Vòng lặp bất tận & Cạn kiệt lượt dismiss**:
   - Khi Share Sheet hiện lên, hệ thống gọi `press_back` để đóng nó.
   - Khi Share Sheet biến mất, màn hình lại quay về trang Profile của `@trieutruc0505`.
   - `detect_contact_follow_suggestion` tiếp tục nhận diện trang Profile là popup -> tiếp tục bấm vào nút 3 chấm ở góc trên -> Share Sheet lại mở ra.
   - Chu trình này lặp lại cho đến khi chạm trần số lần dismiss cho phép (`allowed shared dismiss attempts`).
   - Runner kích hoạt swipe recovery (2 swipes) nhưng do vẫn ở trang Profile, recovery thất bại và ném lỗi `manual-needed-popup`.

---

## 3. Giải pháp Chuẩn hóa & Khắc phục O(1)

### A. Exclude User Profile Screens trong `detect_contact_follow_suggestion`
Trong `automation-core/src/automation_core/tiktok/benign_popup.py`:
Ngay đầu hàm `detect_contact_follow_suggestion`, trích xuất toàn bộ text/content-desc và kiểm tra các dấu hiệu đặc trưng của trang Profile cá nhân. Nếu xuất hiện, lập tức bỏ qua (`return None`):

```python
def detect_contact_follow_suggestion(root: ET.Element) -> BenignPopupMatch | None:
    elements = list(iter_elements(root))
    values = _all_values(elements)
    
    # Exclude user profile screens: Trang profile có các chỉ số follower/following hoặc các nút quản lý hồ sơ
    profile_markers = (
        "follower", "followers", "người theo dõi",
        "sửa hồ sơ", "edit profile",
        "chia sẻ hồ sơ", "share profile",
    )
    if _has_contains(values, profile_markers):
        logger.debug("detect_contact_follow_suggestion: skipping profile screen matching marker")
        return None
    
    markers: list[str] = []
    # ... logic nhận diện contact suggestion thông thường ...
```

### B. Yêu cầu Telemetry & Observability (Sol Reviewer Gate >= 85)
Khi sửa các hàm nhận diện popup:
- BẮT BUỘC có structured telemetry logging (`logger.debug(...)` hoặc `logger.info(...)`) ghi rõ lý do bỏ qua hoặc phát hiện popup. Thiếu logging sẽ bị trừ điểm nặng ở mục *Telemetry & Observability* (thường kéo điểm tổng xuống 84/100 REJECTED).
- BẮT BUỘC bao phủ cả 2 ngôn ngữ Tiếng Việt và Tiếng Anh (`"người theo dõi"` / `"followers"`, `"sửa hồ sơ"` / `"edit profile"`).

### C. Kỷ luật Dispatch Worker Subagent (`delegate_task`)
Khi dispatch worker để điều tra hoặc sửa chữa lỗi theo nhận xét của Sol Reviewer:
- BẮT BUỘC thêm vào `context`:
  `BUDGET: <= 5 tool calls, thời gian < 3 phút. Trả về kết luận/anchor rồi THOÁT NGAY.`
- Nếu thiếu chỉ thị này, guardrail `[HARD GATE #3 - INVESTIGATE ROUTE]` sẽ chặn đứng lời gọi `delegate_task`.
