# Profile Verification SystemUI Trap & Xử Lý Thẻ TikTok GO (Case 118, 2026-09-06, Máy 25)

## 1. Hiện tượng & Bối cảnh (Symptoms & Context)
- **Thiết bị**: Máy 25 (Samsung Galaxy S7, Android 7, serial `ce02182261a6a62105`, nick `thao.phan206`).
- **Quy trình**: Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`).
- **Triệu chứng Farm Alert**:
  ```text
  [FARM ALERT: MÁY 25] DỪNG PHIÊN
  • Quy trình: Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)
  • Máy: 25 | Serial: ce02182261a6a62105 | Nick: thao.phan206
  • Triệu chứng: profile verification mismatch: profile account mismatch
  • Hiện trường: ĐANG MỞ
  ```
- **Hiện trường máy thật**:
  - Màn hình dừng lại ở thẻ carousel quảng bá **"TikTok GO"** ("Khám phá hòn ngọc địa phương") với 2 nút "Không quan tâm", "Khám phá" và ký hiệu vuốt lên `︽`.
  - Operator thắc mắc: *"Cái này cơ chế vuốt khi gặp màn lạ k qua đc à"*.

---

## 2. Phân tích Nguyên nhân Cốt lõi (Root Cause Analysis)

### 2.1. Thực tế phiên chạy hoàn thành 100% feed swipe loop
- Kiểm tra log và `summary.txt` xác nhận:
  - `total_swipes_requested: 8`
  - `total_swipes_completed: 8`
  - Tất cả 8/8 lượt vuốt feed video đều thành công. Phiên **hoàn toàn không bị kẹt hay thất bại trong vòng lặp lướt video**.

### 2.2. Bẫy SystemUI focus recovery trong `tap_navigation_target` (`calibrate_screens.py`)
- Khi kết thúc feed swipe và chuyển sang bước `_verify_profile_after_session`:
  - Script gọi `tap_navigation_target(target="profile", bounds="[864,1794][1080,1920]")` (tâm chạm `x=972, y=1857`).
  - Trên màn hình Samsung S7 (1080x1920), vị trí `y=1857` nằm sát mép đáy màn hình. Khi tap, sự kiện chạm kích hoạt navigation bar / SystemUI khiến `get_focused_activity` bắt `post_package: "com.android.systemui"`.
  - Nhánh `recover_tiktok_focus_after_systemui_tap` gửi phím `KEYCODE_BACK` (`keyevent 4`) để kéo TikTok về foreground. Tuy nhiên, phím BACK này đã hủy bỏ quá trình chuyển sang tab Hồ sơ, giữ app ở lại Trang chủ (Home Feed).
  - Tệ hơn, sau khi gửi BACK, script thấy `post_package` đã quay về `com.ss.android.ugc.trill` thì vội vã kết luận navigation thành công (`NavigationResult(True, "pass")`).

### 2.3. Bẫy cuộn ngược Swipe Down trên Trang chủ trong `_verify_profile_after_session` (`feed_swipe_smoke.py`)
- Trong `_verify_profile_after_session`:
  - Vì TikTok vẫn ở Trang chủ nên `profile_screen_confirmed` là `False`, dẫn đến `not matched`.
  - Nhánh fallback cuộn username profile chạy lệnh:
    ```python
    ctx.adb.shell(["input", "swipe", "540", "600", "540", "1500", "350"])
    ```
    Đây là lệnh vuốt **từ trên xuống dưới (swipe down)** với giả định đang ở trang Profile và header bị cuộn khuất.
  - Tuy nhiên, khi lệnh swipe down này chạy ngay trên Trang chủ (Home Feed), nó đã kích hoạt pull-to-refresh / kéo ngược feed, làm xuất hiện thẻ carousel quảng bá **"TikTok GO"** ("Khám phá hòn ngọc địa phương").
  - Script sau đó kết luận `profile account mismatch` vì không tìm thấy username `thao.phan206` trên Trang chủ, báo alert `[MÁY 25]`.

---

## 3. Giải pháp Chuẩn hóa 3 Tầng (Standard 3-Tier Fix)

### Tầng 1: Retry Tap Sau Khi Recover Focus Từ SystemUI (`calibrate_screens.py`)
- Trong `tap_navigation_target`: Sau khi `recover_tiktok_focus_after_systemui_tap` gửi BACK và đưa TikTok quay lại foreground (`recovered_focus = True`), **CẤM** trả `NavigationResult(True)` ngay.
- Phải thực hiện retry tap lại target:
  ```python
  if recovered_focus:
      time.sleep(0.5)
      ctx.adb.shell(["input", "tap", str(x), str(y)], timeout=ctx.timeout("adb_seconds", 15))
      time.sleep(1.2)
      post_focus = get_focused_activity(ctx)
      post_package = str(post_focus.get("package") or "")
      recovered_focus = (post_package == expected_package)
  ```

### Tầng 2: Gating Lệnh Swipe Down Trong `_verify_profile_after_session` (`feed_swipe_smoke.py`)
- **Nguyên tắc**: Chỉ được phép chạy `input swipe 540 600 540 1500 350` (swipe down) khi **ĐÃ XÁC NHẬN `profile_screen_confirmed` là True**.
- Nếu `not profile_screen_confirmed` (vẫn đang ở Trang chủ hoặc tab khác):
  - **CẤM TUYỆT ĐỐI** swipe down (tránh kéo ngược feed làm lộ thẻ quảng cáo/TikTok GO hoặc refresh feed).
  - Thay vào đó, **PHẢI retry điều hướng lại tab Hồ sơ** (`tap_navigation_target` tab "profile") tối đa 2 lần.

### Tầng 3: Đăng ký Handler Thẻ Quảng Bá "TikTok GO" (`benign_popup_registry.py`)
- Thẻ carousel "TikTok GO" là dạng interactive promotional card trong feed, có ký hiệu `︽` (vuốt lên để tiếp tục) và 2 nút "Không quan tâm" / "Khám phá".
- **Detector (`_detect_tiktok_go_card`)**:
  - Nhận diện khi XML hoặc OCR chứa `"TikTok GO"` hoặc (`"Khám phá hòn ngọc địa phương"` / `"Khám phá những xu hướng mới nhất"`) VÀ có nút `"Không quan tâm"` hoặc `"Khám phá"`.
- **Dismisser (`_dismiss_tiktok_go_card`)**:
  - Ưu tiên tìm node có text/desc `"Không quan tâm"` / `"Not interested"` để tap.
  - Nếu không tìm thấy, gửi lệnh vuốt lên `["input", "swipe", "540", "1400", "540", "600", "300"]` theo ký hiệu `︽` để trượt qua thẻ.

---

## 4. Quy tắc Nghiệm thu & Bài học Vận hành (Operational Lessons)
1. **Phân biệt rạch ròi Feed Swipe vs Post-Session Verification**:
   - Khi nhận alert kèm ảnh thẻ lạ trên Home Feed, kiểm tra `summary.txt` trước: nếu `swipes_completed == swipes_requested`, lỗi xảy ra ở bước sau lướt (`verify_profile` hoặc `follow-hook`), không phải feed swipe loop bị kẹt.
2. **Cấm dùng Swipe Down khi chưa ở màn hình đích**:
   - Swipe down trên Trang chủ TikTok sẽ kéo refresh feed hoặc trượt sang thẻ quảng bá. Chỉ swipe down khi XML đã xác nhận đang ở màn Profile.
3. **Focus Recovery phải đi kèm Re-tap**:
   - Bất kỳ thao tác gửi phím BACK để cứu focus từ SystemUI/Launcher đều có nguy cơ hủy mất touch event ban đầu. Phải re-tap lại trước khi kết luận điều hướng thành công.
