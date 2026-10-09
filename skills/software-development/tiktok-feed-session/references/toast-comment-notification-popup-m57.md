# Case UI Analysis: Toast Banner Thông Báo Tương Tác Bạn Bè / Bình Luận & Lỗi Phân Loại Nhầm Camera Screen (M57 Feed Smoke)

## Hiện tượng
Trong phiên nuôi acc TikTok (ví dụ Ca 1 Phiên 2 ngày 2026-09-24 trên Máy 57), thiết bị dừng với:
- `status: manual-needed`
- `detected_screen: manual-needed:popup`
- `classification_reasons: ["TikTok camera/video creation screen detected via distinct creation mode elements"]`
- `stop_reason: popup is not in the shared TikTok allowlist; manual review required`

## Dấu vết Hiện trường (UI XML & Node Attributes)
Tại step chuyển tab bạn bè hoặc lướt feed (`switch_friends_10_navigation_confirm` / `before_swipe`), xuất hiện banner thông báo tương tác bạn bè từ mép trên màn hình:
```xml
<node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.ss.android.ugc.trill" bounds="[0,0][1080,605]">
  <node index="0" text="" resource-id="com.ss.android.ugc.trill:id/lf0" ... bounds="[24,102][234,353]" />
  <node index="1" text="" resource-id="com.ss.android.ugc.trill:id/lf1" ... bounds="[234,102][1056,353]">
    <node index="0" text="Liên Lê" resource-id="com.ss.android.ugc.trill:id/lf4" class="android.widget.TextView" />
    <node index="1" text="đã bình luận: [Ảnh] ..." resource-id="com.ss.android.ugc.trill:id/lew" class="android.widget.TextView" />
  </node>
</node>
```

Đồng thời ở phần dưới màn hình vẫn là giao diện feed bình thường:
```xml
<node desc="Video" id="com.ss.android.ugc.trill:id/long_press_layout" bounds="[0,615][1080,1920]" />
<node desc="Quay" id="com.ss.android.ugc.trill:id/opd" bounds="[432,1794][648,1920]" />
<node desc="Trang chủ" id="com.ss.android.ugc.trill:id/oph" selected="true" bounds="[0,1794][216,1920]" />
<node desc="Hộp thư" id="com.ss.android.ugc.trill:id/opi" bounds="[648,1794][864,1920]" />
<node desc="Hồ sơ" id="com.ss.android.ugc.trill:id/opj" bounds="[864,1794][1080,1920]" />
```

## Root Cause Phân tích Chuyên sâu (Tại sao lại ra lỗi Camera & Unmatched Popup?)
1. **Mất dấu Top Tabs:** Banner toast che khuất vùng top tabs (`[0,0][1080,605]`), khiến `_has_selected_marker(elements, friends_terms)` không tìm thấy tab Bạn bè / Dành cho bạn.
2. **Bẫy Camera Detection False Positive:**
   - Trong `core/classifier.py`, detector màn hình Camera tìm kiếm `camera_mode_terms` (chứa `"video"` và `"quay"`).
   - Video player của feed có `content-desc="Video"` (`bounds="[0,615][1080,1920]"`), nút dấu cộng bottom navigation có `content-desc="Quay"` (`bounds="[432,1794][648,1920]"`). Cả hai đều có `bounds[3] >= 1000`.
   - Kết quả: `matched_distinct_modes` thu được `{'video', 'quay'}` $\ge 2 \rightarrow$ `classify_tiktok_screen` nhận định sai là `TikTok camera/video creation screen` và gán `manual_needed=True`.
3. **Kẹt Allowlist:**
   - Khi `switch_friends_10_navigation_confirm` nhận `manual-needed:popup`, nó gọi `dismiss_tiktok_popups` và `find_matching_handler`.
   - Trong `benign_popup_registry.py`, detector camera (`_detect_camera_creation`) có negative exclusion `if has_home and (has_inbox or has_profile): return False`, nên camera handler **không match**.
   - Chưa có handler nào nhận diện toast banner thông báo bình luận `id/lf1`.
   - Kết quả: Bị kết luận `popup is not in the shared TikTok allowlist; manual review required` và dừng phiên nuôi acc.

## Kiến trúc Sửa 2 Lớp (2-Layer Architectural Fix)

### Lớp 1: Đồng bộ Negative Exclusion trong `core/classifier.py`
Màn hình Camera thật không bao giờ có thanh điều hướng đáy (Bottom Navigation Bar). Bổ sung kiểm tra cấu trúc đáy trước khi kích hoạt camera mode detector:
```python
has_home = any("trang chủ" in (el.attrib.get("text", "") + " " + el.attrib.get("content-desc", "")).lower() for el in elements)
has_inbox = any("hộp thư" in (el.attrib.get("text", "") + " " + el.attrib.get("content-desc", "")).lower() for el in elements)
has_profile = any("hồ sơ" in (el.attrib.get("text", "") + " " + el.attrib.get("content-desc", "")).lower() for el in elements)
is_feed_or_nav = is_profile_like or (has_home and (has_inbox or has_profile))

if not is_feed_or_nav:
    # Camera / Video Creation Screen Detection
```

### Lớp 2: Đăng ký Benign Popup Handler trong `flows/benign_popup_registry.py`
Tạo handler `tiktok_inapp_notification_banner` (Priority 78):
- **Detector (`_detect_inapp_notification_banner`):**
  - Quét `com.ss.android.ugc.trill` ở nửa trên màn hình (`b[1] < 300 and b[3] <= 600`).
  - Khớp các `resource-id` (`id/lf1`, `id/lew`, `id/lf4`, `in_app_push`, `notice_view`) hoặc text/desc chứa (`đã bình luận`, `đã thích video`, `đã nhắc đến bạn`, `đã chia sẻ`, `đã gửi cho bạn`, `bình luận: `, `commented:`, `liked your video`, `mentioned you`, `sent you a message`, `shared a video`).
  - Đo latency qua `time.perf_counter()` và ghi log `logger.info`.
- **Dismisser (`_dismiss_inapp_notification_banner`):**
  - Tính tọa độ vuốt động theo độ phân giải màn hình (`x = sz[0] // 2`, `y_start = int(sz[1] * 0.15)`, `y_end = int(sz[1] * 0.03)`) thay vì hardcode 540x250.
  - Vuốt nhanh từ dưới lên trên qua tọa độ banner (`input swipe <x> <y_start> <x> <y_end> 200`) để gạt bay toast khỏi màn hình.
  - Trả về `PopupDismissResult(dismissed=True, reason="swiped_up_inapp_notification_banner", popup_closed=True)`.

## Kinh Nghiệm Vượt Closeout Gate (Sol Auditor Reviewer >= 85 điểm)
- **Tránh Hardcoded Coordinates:** Reviewer luôn trừ điểm `Farm Safety` và `Code Architecture` nếu tọa độ vuốt/chạm là số cứng (`540, 250, 50`). Phải đọc `get_screen_size()` để tính tỷ lệ phần trăm (0.15 và 0.03 chiều cao màn hình).
- **Telemetry & Latency Tracking:** Mọi handler popup allowlist mới bắt buộc phải có `time.perf_counter()` đo thời gian thực thi (ms) và log `logger.info` chi tiết (resource_id, keyword, coordinates). Thiếu telemetry sẽ bị giữ ở mức 82 điểm (REJECTED).
- **Hỗ Trợ Đa Ngôn Ngữ (Multi-lingual / Locale Resilience):** Không chỉ dựa vào text tiếng Việt đơn lẻ; phải bao phủ cả tiếng Anh (`home`/`inbox`/`profile`, `commented:`/`liked your video`) để tránh false positive khi app đổi locale.


## Pitfalls Kiểm thử Subprocess trên Host Windows (Hermes Coordinator/Worker)
1. **Lỗi `PYTHONPATH` Shadowing:**
   - Môi trường Hermes Agent có `PYTHONPATH` trỏ vào venv riêng của nó (`AppData/Local/hermes/...`), chứa package PIL/Pillow không tương thích nhị phân với Python 3.12 của hệ thống Automation (`D:/Taadaa/python-envs/automation`), dẫn đến lỗi `ImportError: cannot import name '_imaging' from 'PIL'`.
   - **Bắt buộc:** Luôn set rõ ràng `export PYTHONPATH="D:/Taadaa/tiktok-luot nuoi acc/python_runner:D:/Taadaa/automation-core/src"` trước khi chạy lệnh Python/pytest.
2. **Pytest Rootdir Hang:**
   - Nếu chạy pytest khi cwd là `C:/Users/Kibe`, pytest sẽ quét đệ quy toàn bộ thư mục user home (vô số files, AppData, VirtualBox...) làm timeout 180s.
   - **Bắt buộc:** Luôn chạy pytest từ thư mục gốc của repo (`workdir="D:/Taadaa/tiktok-luot nuoi acc/python_runner"`).
