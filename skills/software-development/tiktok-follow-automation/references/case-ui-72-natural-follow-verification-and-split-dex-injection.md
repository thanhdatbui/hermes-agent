# Case UI-72: Phối Hợp Xác Minh Follow Tự Nhiên & Chiến Lược Cập Nhật Split APK Tránh Văng App Toàn Dàn (2026-09-20)

## 1. BỐI CẢNH & HIỆN TRƯỜNG THỰC TẾ
- **Sự cố 1 (Follow Verification / Optimistic UI Cache & Selector Drift):**
  - Khi follow trên video hoặc profile, TikTok Android lưu trạng thái tạm thời trong RAM (`RelationCache`), hiển thị nút xám giả ("Nhắn tin" / "Đã follow"). Kể cả khi back ra ngoài màn hình danh sách Search, activity cha vẫn giữ cache cũ.
  - Tuy nhiên, nếu TikTok server âm thầm rate-limit (nhả follow ngầm), server truth chỉ lộ diện khi ép client phá cache.
  - Thử nghiệm trên máy 38 (`benghxmk3zu`) và máy 37 (`ngc.trinh6472`) cho thấy:
    - Phương án A (Pull-to-refresh có jitter tại chỗ): Cung cấp tín hiệu cảm ứng tự nhiên, không làm biến dạng đồ thị điều hướng (Session Graph).
    - Phương án B (Natural Re-entry: Back ra ngoài -> tap vào lại card): Ép mở activity mới để fetch dữ liệu mới toanh từ server, nhưng nếu lặp lại liên tục sẽ tạo ra chữ ký bot navigation loop.
  - **Phán quyết từ Sol (`gpt-5.6-sol-high`):** Tỷ lệ phối hợp tối ưu 80% Pull-to-refresh có jitter ngẫu nhiên + 20% Natural Re-entry ngẫu nhiên để phá vỡ tính lặp lại đơn điệu.
  - **Cạm bẫy Selector Drift TikTok 46.9.3 (`id/fm9`) & 47.0.3 (`id/fmp`):**
    - Cả hai nút "Follow" (nút đỏ) và "Nhắn tin" (nút xám) trên TikTok 46.9.3 đều dùng chung resource-id `id/fm9`, và trên 47.0.3 dùng chung `id/fmp`.
    - Nếu tuple `_ACTION_BUTTON_SUFFIXES` trong `verify_follow.py` thiếu một trong hai ID này: nút Follow đỏ sẽ bị `_is_profile_action_node` trả về `False` (bị bỏ qua không nhận diện). Nhưng nút "Nhắn tin" bên cạnh lại lọt qua nhờ text marker `"nhắn tin"`.
    - Hậu quả: Màn hình đang có nút Follow đỏ lòm nhưng script lại báo cáo sai thành `followed` (False Positive chí mạng)!

- **Sự cố 2 (Cập nhật đồng bộ TikTok 47.0.3 & Bẫy thiếu `split_df_a_dex`):**
  - Khi nâng cấp TikTok lên bản 47.0.3 trên dàn Samsung S7 Android 8, nếu chỉ cài 4 file APK split cơ bản (`base.apk`, `split_config.arm64_v8a.apk`, `split_config.vi.apk`, `split_config.xxhdpi.apk`), app sẽ bị crash ngay lập tức khi khởi động với lỗi:
    `ClassNotFoundException: Didn't find class "X.0gEx"` hoặc `LooperProtectEnhanceSettingAppDiffProtocol`.
  - **Nguyên nhân:** TikTok 47.0.3 tách toàn bộ bytecode thực thi chính vào file split dynamic dex: `split_df_a_dex.apk` (83.8MB).
  - Khi cài đè bằng `install-multiple` cả gói lớn qua ADB, lệnh dễ bị timeout do băng thông USB bị chia sẻ nếu chạy nhiều workers song song.
  - Trên cụm Hub USB 20-30 cổng, tốc độ truyền file 83.8MB tụt xuống ~0.3 - 0.4 MB/s, mất từ 220s - 260s/máy. Timeout mặc định 180s hay 300s sẽ bị đứt gánh. Bắt buộc đặt `timeout=450s` và `concurrency <= 3`.

---

## 2. BẢN VÁ KỸ THUẬT & QUY TRÌNH CHUẨN

### A. Triển khai Cơ chế Xác minh Hybrid (Sol Approved):
1. **Pull-to-refresh có Jitter tự nhiên (`adapter.py`):**
   - Không vuốt bằng tọa độ cố định.
   - Thêm jitter ngẫu nhiên: `cx = (w // 2) + random.randint(-25, 25)`, `y1 = 0.35h ± 30px`, `y2 = 0.78h ± 40px`, duration `500-750ms`.
2. **Hybrid Policy (`mode1_search_follow.py`):**
   - 80% trường hợp: Gọi `pull_to_refresh_profile(adapter, sleep_after=random.uniform(3.0, 4.5))`.
   - 20% trường hợp (hoặc fallback): Gọi re-entry path (back ra search -> tìm và tap card để vào lại).
   - Kiểm tra lại phân loại sau khi reload: Nếu nút chuyển đỏ (`not_followed`) $\rightarrow$ Kích hoạt `set_follow_failed()` và ngắt phiên ngay lập tức, cấm bấm tiếp nick sau.
3. **Whitelist Selector Đa Phiên Bản (`verify_follow.py`):**
   - Bắt buộc chứa cả `:id/fm9`, `id/fm9` (bản 46.9.3) và `:id/fmp`, `id/fmp` (bản 47.0.3) trong `_ACTION_BUTTON_SUFFIXES`.

### B. Quy trình Nạp Split Dex `split_df_a_dex.apk` Bằng Session (Chống Timeout & Lỗi Bóc Session ID):
Khi cần bổ sung split dex vào app TikTok đang chạy mà không làm mất dữ liệu tài khoản:
```python
import subprocess, os, time

adb_bin = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
dex_apk = r"D:\Taadaa\apks\tiktok_47_0_3\split_df_a_dex.apk"
dex_sz = os.path.getsize(dex_apk)

# 1. Push file với timeout rộng (450s) tránh nghẽn USB hub
subprocess.run([adb_bin, "-s", serial, "push", dex_apk, "/data/local/tmp/split_df_a_dex.apk"], check=True, timeout=450)

# 2. Tạo install session kế thừa package hiện tại (Bóc tách sid trực tiếp bằng Python, cấm dùng shell cut dễ rỗng)
r = subprocess.run([adb_bin, "-s", serial, "shell", "pm install-create -r -d -p com.ss.android.ugc.trill"], capture_output=True, text=True, timeout=20)
sid = r.stdout.strip().split("[")[-1].split("]")[0].strip()

# 3. Ghi file split dex vào session và commit
subprocess.run([adb_bin, "-s", serial, "shell", f"pm install-write -S {dex_sz} {sid} split_df_a_dex.apk /data/local/tmp/split_df_a_dex.apk"], check=True, timeout=120)
subprocess.run([adb_bin, "-s", serial, "shell", f"pm install-commit {sid}"], check=True, timeout=120)

# 4. Kiểm tra splits có df_a_dex và đưa về HOME
r_check = subprocess.run([adb_bin, "-s", serial, "shell", "dumpsys package com.ss.android.ugc.trill | grep splits="], capture_output=True, text=True, timeout=10)
assert "df_a_dex" in r_check.stdout
subprocess.run([adb_bin, "-s", serial, "shell", "input keyevent 3"])
```

---

## 3. CHỐNG QUÉT GIAN LẬN & BẢO VỆ TÀI SẢN NICK
- **Signature Integrity:** File APK lấy từ máy Google Play có cùng chứng thư số (`PackageSignatures{... [2606a464]}`), Android chỉ cho phép cài đè khi signature khớp 100%, bảo toàn toàn bộ 8 nick trong switcher không bị văng token.
- **Tắt Auto-Update Google Play:** Sau khi đồng bộ phiên bản hoặc ổn định dàn, bắt buộc gửi lệnh khóa tự động cập nhật ngầm:
  ```bash
  adb shell "settings put global auto_update_apps 0"
  ```
  Ngăn Google Play Store tự ý cập nhật ngầm lúc cắm sạc ban đêm làm vỡ layout selector.
