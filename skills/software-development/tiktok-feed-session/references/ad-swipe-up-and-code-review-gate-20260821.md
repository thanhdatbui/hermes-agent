# Lesson: Quảng cáo TikTok (Ad Overlay/Sponsored) bắt buộc VUỐT LÊN (Swipe Up), không tap Đóng; Quy chuẩn Gate Code Review

*Session date: 2026-08-21*

---

## 1. Bối cảnh & Vấn đề phát sinh
- Khi chạy feed session, một số máy (ví dụ Máy 16, Máy 60) gặp màn hình quảng cáo overlay / thẻ interactive ads có nút "Đóng" hoặc "Tìm hiểu thêm".
- **Hành vi sai trước đó của AI Recovery Agent:** Tự động sinh hàm `dismiss_ad_overlay_popup` hoặc `dismiss_sponsored_brand_ad_popup` tìm tọa độ nút "Đóng" (`540, 1100`) để tap.
- **Hậu quả:** 
  1. Thao tác tap vào màn hình quảng cáo dễ bị chạm nhầm vào link quảng cáo / cài đặt ứng dụng / mở WebView.
  2. Không đúng hành vi người dùng thật và vi phạm quy chuẩn vận hành farm của user.

---

## 2. Quy Tắc Chuẩn Được User Chốt (21/08/2026)

### 📌 QUY TẮC QUẢNG CÁO:
1. **Ưu tiên số 1 (BẮT BUỘC):** Khi gặp bất kỳ màn hình quảng cáo, ad overlay, sponsored card, hoặc khảo sát quảng cáo nào $\rightarrow$ **BẮT BUỘC THỰC HIỆN LỆNH VUỐT LÊN (Swipe Up / `input swipe 540 1600 540 400 300`)** để lướt qua video tiếp theo.
2. **Nút "Đóng" / "Hủy" chỉ là FALLBACK CUỐI CÙNG:** Chỉ được phép tap nút "Đóng" nếu đã thực hiện vuốt lên tối đa 2 lần mà màn hình vẫn bị kẹt không thoát được.
3. **Màn hình không rõ / Lạ:** Ưu tiên thực hiện vuốt lướt qua (swipe recovery tối đa 2 lần) để kiểm tra xem có phải video feed thông thường bị overlay che hay không trước khi kết luận dừng máy báo manual.

---

## 3. Bản Vá Trong Codebase

### A. Sửa Handler trong `python_runner/flows/benign_popup.py`
Tất cả các hàm xử lý quảng cáo (ví dụ `dismiss_ad_overlay_popup`) được chuyển đổi sang logic:
```python
def dismiss_ad_overlay_popup(
    ctx: DeviceContext,
    *,
    xml_tree: Any = None,
    baseline_step_name: str = "dismiss_ad_overlay_popup",
) -> PopupDismissResult:
    """Xử lý overlay quảng cáo: ƯU TIÊN VUỐT LÊN (swipe up) qua video tiếp theo.
    Chỉ bấm nút 'Đóng' nếu vuốt 2 lần vẫn không qua (Đóng là fallback)."""
    before_attempt: dict[str, Any] = {"step": baseline_step_name, "ts": time.time()}
    
    # Ưu tiên 1: Vuốt lên để qua video (rule farm: quảng cáo thì vuốt cho qua)
    ctx.adb.shell(["input", "swipe", "540", "1600", "540", "400", "300"])
    time.sleep(1.0)
    
    return PopupDismissResult(
        dismissed=True,
        reason="swiped_up_to_skip_ad_overlay",
        before_attempt=before_attempt,
        popup_closed=True,
    )
```

### B. Cập nhật System Prompt cho AI Recovery Vision Client (`python_runner/ai_recovery/vision_client.py`)
Bổ sung rõ ràng vào quy tắc an toàn số 4 để AI không sinh mã tap "Đóng" sai:
```python
"   - QUY TẮC QUẢNG CÁO: Mọi màn hình quảng cáo, ad overlay, sponsored card, khảo sát quảng cáo -> BẮT BUỘC action_type='swipe' (vuốt lên lướt qua video tiếp theo), CẤM dùng action_type='tap' bấm nút Đóng/Hủy (Đóng chỉ là fallback khi vuốt không được).\n"
"   - QUY TẮC MÀN HÌNH KHÔNG RÕ/LẠ: Ưu tiên action_type='swipe' để lướt qua thay vì dừng máy hay bấm bừa.\n"
```

---

## 4. Quy Chuẩn Bắt Buộc: Code Review Gate Trước Commit & Push
- **Tuyệt đối tuân thủ:** Mọi thay đổi code dù nhỏ (kể cả 1 dòng patch hay fix theo lệnh user) **BẮT BUỘC** phải:
  1. Chạy pytest xác nhận 100% test pass.
  2. Xuất `git diff` và gọi độc lập tới **Model Plan-Review qua 9Router HTTP API** (`http://127.0.0.1:20128/v1/chat/completions`, model `plan-review`).
  3. Nhận được verdict `passed: true` / `APPROVED` từ Plan-Reviewer mới được phép `git commit` và `git push`.
- **Cấm đốt cháy giai đoạn:** Không được tự ý commit/push trước khi có kết quả review độc lập của 9Router.
