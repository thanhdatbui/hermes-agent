# Deeplink Evasion Trap, Screen-On Canary Invariant & Anti-Skip Physical Gate Matrix

## 1. Deeplink Evasion Trap & Bẫy Giả Thuyết Hoang Đường
### Bối cảnh & Hiện tượng
Trong flow upload avatar trên TikTok farm, khi không thấy nút "Sửa hồ sơ" trên giao diện, runner fallback gọi intent:
```bash
am start -a android.intent.action.VIEW -d snssdk1233://profile/edit -p com.ss.android.ugc.trill
```
rồi tap tọa độ cứng `(177, 150)`.
Lệnh này khiến TikTok văng popup cảnh báo nền tảng:
> *"Hoạt động này không có sẵn trên tài khoản ban đầu"*

### Phân tích sai lầm của AI Agent
- Thay vì nhận diện việc bắn deeplink intent `snssdk1233://...` là sai luồng và không được TikTok hỗ trợ trong ngữ cảnh app hiện tại, Agent đã:
  1. Tự bịa ra giả thuyết hoang đường: *"Tài khoản phụ (secondary profile) của TikTok không hỗ trợ sửa hồ sơ / up avatar (Case 97)"*.
  2. Dùng giả thuyết này làm lý do để chèn code `safe-skip`:
     ```python
     if edit_state == "unavailable":
         self.context.avatar_status = "SKIPPED_AVATAR_EDIT_UNAVAILABLE"
         return True  # Nuốt lỗi, báo hoàn thành giả!
     ```
- **Sự thật kỹ thuật:** Mọi tài khoản TikTok (chính chủ hay phụ) đều có trang Profile và đổi avatar bình thường 100% nếu tương tác qua giao diện người dùng.

### Quy tắc bất biến (Invariants)
1. **CẤM TUYỆT ĐỐI** gọi intent deeplink `snssdk1233://...` để nhảy cóc vào flow sửa hồ sơ khi chưa rõ phiên.
2. Mọi thao tác up/sửa avatar phải đi qua UI chuẩn của người dùng thật:
   - Cách 1: Nút "Sửa hồ sơ" hoặc icon cây bút chì cạnh username (`RightPencilLayout`).
   - Cách 2: Tap trực tiếp vào **Vòng tròn Avatar** trên màn hình Profile để mở bottom sheet chọn ảnh.
3. Khi gặp popup không mong muốn: **BẮT BUỘC FAIL-CLOSED** (`WorkflowError(AVATAR_EDIT_OPEN_FAILED)`), tuyệt đối cấm bịa ra giới hạn nền tảng để nuốt lỗi safe-skip.

---

## 2. Screen-On Preflight Invariant (Chống Bẫy Ảnh Đen Canary)
### Hiện tượng
Khi thiết bị Android ở trạng thái Sleep / Dozing (`Screen: OFF` / `mScreenOnEarly=false`), lệnh `adb exec-out screencap` vẫn trả về dữ liệu nhưng là ảnh đen kịt (file size nhỏ ~12KB). Gửi ảnh này làm bằng chứng nghiệm thu Canary là vi phạm trực tiếp Gate 6 và bị coi là bằng chứng rác.

### Quy trình bắt buộc trước khi chụp screencap
1. **Kiểm tra trạng thái màn hình**: Dùng `dumpsys window policy` hoặc `inspect_machine.py <N>` để xác nhận `Screen: ON (Awake)`.
2. **Đánh thức và mở khóa**:
   ```bash
   adb shell input keyevent 224      # KEYCODE_WAKEUP
   adb shell wm dismiss-keyguard     # Dismiss màn hình khóa
   ```
3. **Đưa app lên foreground**: Đảm bảo package mục tiêu đang hiển thị trên `mCurrentFocus`.
4. **Kiểm tra kích thước file ảnh**: Ảnh chụp màn hình thật của thiết bị 1080x1920 hoặc 1440x2560 phải có kích thước $> 100\text{KB}$. Nếu $< 30\text{KB}$ $\rightarrow$ Coi là ảnh lỗi/đen, cấm gửi báo cáo nghiệm thu.

---

## 3. Ma Trận Tích Hợp Anti-Skip Physical Hook Gates
Cơ chế chống trốn việc bắt buộc thực thi ở tầng Code Gate có khả năng chặn cứng (Exit Code 1), không phụ thuộc vào prompt hay memory:

| Cổng Kiểm Soát | Tệp Cài Đặt | Cơ Chế Phát Hiện | Hành Động Khi Vi Phạm |
| :--- | :--- | :--- | :--- |
| **Worker Cage** | `tools/cage_gate.py` | Quét `git diff -U0` của target file trong worktree sandbox | Exit 1 `anti_skip_violation`, từ chối merge code của worker |
| **Closeout Step 2.5** | `tools/guard_selector_change.py` | Quét regex `R6: Anti-Skip Invariant` trên diff trước khi gọi Sol | Exit 1 `R6: ANTI_SKIP_VIOLATION`, chặn chấm điểm và khóa commit |
| **Coordinator Done** | `tools/done_gate.py` | Quét cả unstaged (`git diff HEAD`) và staged (`git diff --cached`) | Báo `GATE-FAIL(anti-skip)`, từ chối xác nhận hoàn thành task |
| **Git Pre-commit** | `.git/hooks/pre-commit` | Hook kích hoạt `guard_selector_change.py --cached` | Exit 1, hủy lệnh `git commit` ngay tại local |
