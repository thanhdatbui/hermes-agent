# Lọc Nhiễu SystemUI Notification & Fallback Focus Package Khi Mở BottomSheet/Modal (Case 96)

## 1. Vấn đề cốt lõi (Anti-Pattern)
Khi tự động hóa UI qua Android UiAutomator XML:
- **Nhiễu SystemUI Notification:** Các thông báo hệ thống trên thanh trạng thái (như `"Thông báo của Dịch vụ Google Play: Yêu cầu đăng nhập"`) chứa từ khóa nhạy cảm (`"đăng nhập"`, `"login"`). Khi detector duyệt toàn bộ cây XML không lọc package, từ khóa này sẽ kích hoạt nhầm cờ `has_blocker`, biến một modal hợp lệ (như BottomSheet "Chuyển đổi tài khoản") thành màn hình dừng phiên `manual-needed:login`.
- **Mất Focus Khi Mở BottomSheet/Popup:** Khi Android mở BottomSheet modal hoặc popup, `dumpsys window windows` có thể trả về `mCurrentFocus=null` hoặc `com.android.systemui`. Nếu `safety_check` chỉ kiểm tra cứng danh sách màn hình mà không có fallback an toàn khi UI XML thực tế là ứng dụng mục tiêu, hệ thống sẽ ném lỗi `focused package unavailable` / `TikTok focus lost`.

## 2. Giải pháp kỹ thuật chuẩn

### A. Lọc SystemUI Elements Trước Khi Trích Xuất Values
Trong mọi hàm phân tích BottomSheet / Screen detector (như `_is_account_switcher_sheet`):
```python
def _is_account_switcher_sheet(elements: Iterable[UIElement]) -> bool:
    element_list = [
        element for element in elements
        if element.attrib.get("package") != "com.android.systemui"
        and not getattr(element, "resource_id", "").startswith("com.android.systemui:")
    ]
    values = _lower_values(element_list)
    # Tiếp tục kiểm tra switcher title, close button, selected account và blocker keywords...
```

### B. Mở Rộng Regex Window Focus Cho Thiết Bị Samsung
Bổ sung các trường trạng thái window mở rộng vào regex:
```python
_FOCUS_RE = re.compile(
    r"(?:mCurrentFocus|mFocusedApp|topResumedActivity|mTopResumedActivity|mFocusedWindow|mTopFullscreenOpaqueWindowState|mResumedActivity)"
    r"[^\n]*?(?:\s|^)([A-Za-z0-9_.]+)/(.[A-Za-z0-9_.$/]+|[A-Za-z0-9_.$/]+)"
)
```

### C. Fallback Focus Package An Toàn Trong Safety Check
- Khi `focus_pkg in SYSTEM_OVERLAY_PACKAGES` hoặc `focus_pkg is None` nhưng `xml_available=True`:
  - Cho phép gán `focus_pkg = expected` nếu màn hình thuộc `KNOWN_TIKTOK_SCREENS`, `SPONSORED_SCREENS`, hoặc các màn hình đã được phân loại rõ ràng trong `MANUAL_SCREEN_REASONS`.
  - **Lưu ý an toàn (Fail-Closed):** Tuyệt đối KHÔNG dùng wildcard `detected.startswith("manual-needed:")` vì sẽ làm mất cơ chế chặn trên các màn hình cần can thiệp thủ công thực sự (`manual-needed:login`, `manual-needed:google-account`).
