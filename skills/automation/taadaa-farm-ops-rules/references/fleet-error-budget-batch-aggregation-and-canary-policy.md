# Fleet Error Budget, End-of-Batch Aggregation, Bỏ Auto-Lock & Canary Full Flow

Quy chuẩn vận hành mới được thống nhất ngày 07/09/2026 bởi Tad Shavershian và audit bởi Claude CLI Opus High:

## 1. Bối cảnh & Nguyên nhân cải tổ
- **Vấn đề cũ (Alert Fatigue & Device Lock Starvation):** 
  - Cơ chế cũ áp dụng "Fast Fail: lock 1h để inspect hiện trường" cho từng máy đơn lẻ.
  - Khi vận hành 40-74 máy Samsung S7 cũ qua proxy xoay vòng, các lỗi tạm thời (transient errors như proxy lag 5s, animation transition trễ, frame drop) xuất hiện ngẫu nhiên trên 1-2 máy làm réo chuông Farm Alert liên tục, máy bị giữ lock 1h làm cạn kiệt tài nguyên đàn máy cho batch tiếp theo.
- **Quy chuẩn mới:** Chuyển dịch từ cơ chế "Per-device alert" sang "Error Budget & End-of-Batch Aggregation".

## 2. Quy tắc 1: Bỏ hoàn toàn Auto-Lock 1h khi lỗi (Snapshot-on-fail -> Home -> Release)
- **Khi bất kỳ máy nào gặp lỗi trong batch:**
  1. **Chụp Forensics tức thì:** Chụp ngay 1 screencap PNG (`screen.png`) + 1 dump UI hierarchy XML (`window.xml`) lưu vào thư mục run trên đĩa (`runs/<run_id>/snapshots/<machine>/`). Tuyệt đối không chờ cuối batch mới chụp (vì màn hình sẽ trôi hoặc app tự đóng).
  2. **Dọn dẹp thiết bị:** Thực hiện `am force-stop` đóng app, bấm phím Home (`keyevent 3`) đưa máy về màn hình chính.
  3. **Nhả Device Lock ngay lập tức:** Tự động gọi `release()` nhả lock máy, không giữ trạng thái `handoff` hay lock 1h nữa. Đàn máy sẵn sàng 100% tài nguyên cho batch tiếp theo.
- **Cấu hình core:** Biến môi trường `AUTOMATION_CORE_RELEASE_ON_FAIL=1` (mặc định nhả lock khi terminal fail trong `src/automation_core/device_lock.py`).

## 3. Quy tắc 2: Gom lỗi cuối batch (End-of-Batch Error Aggregation) & Ngưỡng Kép
- **Trong lúc chạy batch:** Im lặng tuyệt đối (Silent Run). Không bắn alert lắt nhắt từng máy.
- **Khi toàn bộ batch kết thúc:**
  - Aggregator quét toàn bộ run manifest / kết quả của batch, chuẩn hóa lỗi thành **Error Signature**:
    `signature = hash(error_code + failed_step + target_element)`
  - **Bộ lọc Ngưỡng Kép (Dual Threshold):**
    Chỉ kích hoạt Farm Alert khi thỏa mãn ĐỒNG THỜI 2 điều kiện:
    1. **Tỷ lệ ảnh hưởng:** Cùng 1 signature xuất hiện trên **$\ge 10 - 15\%$** tổng số máy của batch.
    2. **Số máy tối thiểu:** Số máy dính lỗi tuyệt đối **$\ge 3$ máy** (chống báo động giả trên batch nhỏ 5-10 máy).
  - **Phân nhánh xử lý:**
    - **Dưới ngưỡng (< 10-15% hoặc < 3 máy):** Coi là nhiễu môi trường / hao hụt tự nhiên. **BỎ QUA HOÀN TOÀN**, không alert Telegram, không sửa code, chỉ ghi summary nội bộ.
    - **Đạt ngưỡng ($\ge 10-15\%$ và $\ge 3$ máy):** Kích hoạt **DUY NHẤT 1 tin Farm Alert tổng hợp** trên Telegram:
      * Ghi rõ signature lỗi, tỷ lệ %, danh sách các máy dính.
      * Đính kèm ảnh snapshot của **1–2 máy đại diện** (CẤM gửi ảnh cả nhóm làm tràn chat).
      * Chờ lệnh của operator để dispatch sửa code.

## 4. Quy tắc 3: Canary BẮT BUỘC chạy lại đúng Script của Flow bị lỗi
- **CẤM TUYỆT ĐỐI:** Không được chỉ chạy swipe feed ngẫu nhiên (`Get-Random 2-5 swipes`) cho có lệ khi canary bugfix.
- **Quy chuẩn thực chiến:**
  - Sửa bug flow **Reg (Đăng ký TikTok)** $\rightarrow$ Canary bắt buộc chạy lại đúng runner Reg với 1 account mới từ đầu đến cuối (`completed`).
  - Sửa bug flow **Upload Video** $\rightarrow$ Canary bắt buộc chạy lại đúng runner Upload 1 video hoàn chỉnh cho đến khi publish thành công.
  - Sửa bug flow **2FA / Login / Feed** $\rightarrow$ Chạy lại đúng flow tương ứng.
- **Tiêu chuẩn nghiệm thu:** Chỉ khi nào flow bị lỗi chạy lại thành công 100% trên máy thật thì mới cấp verdict CANARY PASS và tiến hành chốt phiên 6 Gate.

## 5. Python Nuance: Bẫy `sys.exc_info()[1]` trong khối `except` (Claude Review Catch)
- Khi viết hàm dọn dẹp / release lock (như `DeviceLock.finish()`):
  ```python
  # ❌ SAI: sys.exc_info()[1] bên trong khối except luôn là chính lỗi 'exc' đang xử lý, không bao giờ None!
  except (OSError, DeviceLockReleaseError) as exc:
      log.warning("release failed: %s", exc)
      if sys.exc_info()[1] is None:  # DEAD CODE! Luôn False!
          raise

  #  ĐÚNG: Phải lưu ambient exception TRƯỚC khối try:
  ambient_exc = sys.exc_info()[1]
  try:
      self.lease.finish(succeeded=succeeded, failure_status=failure_status)
  except (OSError, DeviceLockReleaseError) as exc:
      log.warning("release failed: %s", exc)
      if ambient_exc is None:
          raise  # Re-raise nếu caller gọi finish bình thường, không nuốt lỗi
  finally:
      self.lease = None
      self.acquired.clear()
  ```
