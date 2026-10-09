# Fleet Error Budget, End-of-Batch Aggregation, Smart Lock & Canary Policy

Đúc kết từ bài toán vận hành thực tế hệ thống Taadaa Phone Farm (07/09/2026 - 08/09/2026) nhằm giải quyết triệt để vấn đề "Kiệt sức vì báo động" (Alert Fatigue), nghẽn máy do cơ chế giữ lock cũ, và chuẩn hóa quy trình Canary hoàn thiện luồng.

---

## 1. Bối Cảnh & Nguyên Nhân Gây Alert Fatigue
- **Cơ chế cũ:** Quy định *"Cứ máy nào lỗi thì giữ device lock 1h để làm hiện trường inspect"*.
- **Hậu quả trên đàn máy lớn (40–50 máy):**
  - Các lỗi tạm thời (Transient Errors) như proxy lag 5s, mạng chập chờn 1 nhịp, animation trễ hoặc frame drop trên phần cứng cũ (Samsung S7) xuất hiện ngẫu nhiên ở 1–2 máy.
  - Hệ thống liên tục réo còi Farm Alert lẻ tẻ giữa chừng, khóa cứng thiết bị 1 tiếng khiến các batch sau thiếu máy chạy.
  - Kỹ sư và Coordinator bị cuốn vào vòng xoáy điều tra, phân tích, sửa code và test canary cho những lỗi ngẫu nhiên không bao giờ lặp lại, gây lãng phí tài nguyên và kiệt sức vận hành.

---

## 2. Quy Tắc Mới: Ngân Sách Lỗi (Error Budget) & Gom Lỗi Cuối Batch

### A. Vận hành im lặng trong Batch (Silent Run)
- Trong suốt quá trình batch đang chạy, mọi lỗi đơn lẻ trên từng máy **KHÔNG ĐƯỢC BẮN ALERT GIỮA CHỪNG**.
- Khi máy gặp lỗi (Snapshot-on-fail):
  1. Chụp ảnh hiện trường (`screencap` PNG) và dump UI XML ngay tại thời điểm vấp lỗi $\rightarrow$ Lưu vào thư mục artifacts của run (`runs/<batch_id>/snapshots/<machine>/`).
  2. Tự động `am force-stop` đóng app về Home.
  3. **GIẢI PHÓNG DEVICE LOCK NGAY LẬP TỨC** (Bỏ hoàn toàn quy tắc giữ lock 1h cho lỗi transient/lẻ tẻ).
  4. Ghi nhận mã lỗi, error signature và step bị fail vào `summary.txt`, `summary.csv` hoặc `report.json`.
  5. Máy sẵn sàng cho các batch hoặc tác vụ tiếp theo.

### B. Gom lỗi sau khi kết thúc Batch (End-of-Batch Aggregation)
- Sau khi tất cả các máy trong batch hoàn tất, hệ thống gom nhóm và thống kê lỗi toàn farm theo **Ngưỡng kép (Dual Threshold)**:
  - **Trường hợp 1 — Lỗi lặt vặt rải rác (Silent Skip):**
    - Lỗi rải rác mỗi máy một kiểu hoặc tổng tỷ lệ lỗi dưới ngưỡng:
      $$\text{Tỷ lệ cùng 1 lỗi} < 10 - 15\% \quad \text{HOẶC} \quad \text{Số máy dính} < 3 \text{ máy}$$
    - **Hành động:** Bỏ qua hoàn toàn (Silent Skip), coi như hao hụt tự nhiên, ghi nhận summary nội bộ, **KHÔNG bắn alert Telegram, KHÔNG sửa code**.
  - **Trường hợp 2 — Lỗi hệ thống / Fleet-wide Pattern (BẮT BUỘC SỬA):**
    - **CÙNG MỘT MÃ LỖI / SIGNATURE** (cùng vỡ selector, cùng dính popup mới) xuất hiện thỏa mãn đồng thời:
      $$\text{Tỷ lệ cùng 1 lỗi} \ge 10 - 15\% \quad \mathbf{VÀ} \quad \text{Số máy dính} \ge 3 \text{ máy}$$
    - Lúc này xác suất 100% là app đối kháng đổi UI hoặc lỗi code hệ thống.
    - Hệ thống kích hoạt **DUY NHẤT 1 TIN FARM ALERT TỔNG HỢP** lên Telegram.

---

## 3. Bảng Error Budget Chuẩn Hóa Từng Luồng
- **TikTok Registration / Provisioning:** Ngưỡng lỗi chấp nhận **10% – 15%** (Tỷ lệ thành công mục tiêu **85% – 90%** sau 2–3 nhịp retry tự động).
- **TikTok Feed / Navigation:** Ngưỡng lỗi chấp nhận **0.5% – 2%** (Tỷ lệ thành công **98% – 99.5%**).
- **TikTok Upload Video:** Ngưỡng lỗi chấp nhận **4% – 8%** (Tỷ lệ thành công **92% – 96%**).
- **Login / 2FA / Reconcile:** Ngưỡng lỗi chấp nhận **5% – 10%** (Tỷ lệ thành công **90% – 95%**).

---

## 4. Kỹ Thuật Triển Khai Device Lock Release-on-Fail (`automation-core`)
Triển khai trong `src/automation_core/device_lock.py` đảm bảo an toàn tuyệt đối trên Windows và tương thích ngược:

1. **Cấu hình nhả lock mặc định qua Env:**
   ```python
   def _default_release_on_terminal() -> bool:
       raw = os.environ.get("AUTOMATION_CORE_RELEASE_ON_FAIL", "1").strip().lower()
       return raw in {"1", "true", "yes", "on"}
   ```
2. **Chống nuốt Exception gốc trên Windows (Pattern `ambient_exc`):**
   Khi gọi `release()` (unlink file lock) trong `__exit__` hoặc `finish()`, bọc `try/except (OSError, DeviceLockReleaseError)`.
   **BẮT BUỘC** lưu `ambient_exc = sys.exc_info()[1]` TRƯỚC khối `try:`:
   ```python
   ambient_exc = sys.exc_info()[1]
   try:
       if self.lease is not None:
           self.lease.finish(succeeded=succeeded, failure_status=failure_status)
   except (OSError, DeviceLockReleaseError) as exc:
       log.warning("device lock release failed in finish: %s", exc)
       if ambient_exc is None:
           raise
       return
   ```
   Nếu đang unwind một lỗi gốc từ context block (`ambient_exc is not None`), không bao giờ được re-raise lỗi unlink làm che mất exception gốc.
3. **Resync trạng thái trên chế độ giữ lock (Retention Opt-Out):**
   Nếu caller yêu cầu giữ lock (`release_on_terminal=False`), kiểm tra `self.lease.is_still_held()` để đồng bộ `self.status = failure_status`, tuyệt đối không clear lease vô điều kiện.

---

## 5. Quy Chuẩn Canary MỚI: BẮT BUỘC Chạy Lại Đúng Script Lỗi Hoàn Thành 100%
- **CẤM TUYỆT ĐỐI:** Sau khi sửa bug chỉ đi swipe feed vài cái cho có lệ rồi báo Canary Pass.
- **Kỷ luật Canary theo nghiệp vụ:**
  - Lỗi xảy ra ở **Flow Đăng ký (Reg)** $\rightarrow$ Canary **BẮT BUỘC chạy lại đúng script Reg** từ đầu đến cuối với 1 account mới cho đến khi hoàn tất tạo nick thành công.
  - Lỗi xảy ra ở **Flow Upload Video** $\rightarrow$ Canary **BẮT BUỘC chạy lại đúng script Upload** 1 video hoàn chỉnh cho đến khi publish thành công lên kênh.
  - Lỗi xảy ra ở **Flow 2FA / Reconcile** $\rightarrow$ Canary **BẮT BUỘC chạy lại đúng script 2FA/Login** cho đến khi verify tài khoản xanh.
- **Chỉ khi nào script nghiệp vụ đó chạy hoàn thành 100%** thì mới được coi là Canary Pass để thực hiện các bước closeout 6 Gate.

---

## 6. Kỹ Luật "Build Dựa Trên Cái Đã Có Rồi Cải Tiến Lại"
- **CẤM TUYỆT ĐỐI:** Tự ý đẻ ra các script/công cụ độc lập, rời rạc không ăn khớp với hệ thống hiện hữu.
- **Tận dụng tối đa artifacts sẵn có:**
  - `D:/Taadaa/Tiktok-video/run_tiktok_upload_batch.ps1` đã có file kết quả `summary.csv`.
  - `D:/Taadaa/tiktok-luot nuoi acc/scripts/run-feed-session.ps1` đã có `run_manifest.json` và `summary.txt`.
  - `D:/Taadaa/automation-core` đã có module `automation_core.alerts` gửi Telegram.
- **Tích hợp O(1):** Nâng cấp module `automation_core.batch_aggregator` đọc trực tiếp các file summary có sẵn, kết nối với `alerts.py`, và chỉ cần gắn đúng 1 hook CLI ở cuối mỗi batch runner.

---

## 7. Cạm Bẫy Gọi Python Trần Trong Script PowerShell (`& $python` vs `python`)
- Trong các script launcher PowerShell (như `run_tiktok_upload_batch.ps1`, `run-feed-session.ps1`), môi trường Python runtime luôn được phân giải và ghim chặt (pinned runtime) ở đầu script:
  ```powershell
  $python = (Resolve-Path $PythonPath).Path
  ```
- Khi thêm hook, nếu vô tình gọi `python -m automation_core.batch_aggregator`:
  - Lệnh sử dụng `python.exe` ngẫu nhiên từ biến môi trường `PATH` của host thay vì venv chuyên dụng.
  - Kết quả: Ném lỗi `ModuleNotFoundError: No module named 'automation_core'`, hook fail âm thầm dù code đã cài trong venv.
- **BẮT BUỘC:** Luôn dùng `& $python -m ...`.

---

## 8. Cạm Bẫy `try/catch` Nuốt Lỗi Lệnh Native Exe Trong PowerShell
- Trên **Windows PowerShell 5.1** và **PowerShell Core < 7.4**, kể cả khi đã đặt `$ErrorActionPreference = 'Stop'`, một tiến trình native (`.exe`) trả về non-zero exit code (ví dụ `exit 1`) **KHÔNG TẠO RA TERMINATING ERROR**. Khối `catch` không bao giờ fire.
- **BẮT BUỘC:** Kiểm tra `$LASTEXITCODE` tường minh kết hợp `try/catch`:
  ```powershell
  try {
      & $python -m automation_core.batch_aggregator "$summaryPath" --telegram
      if ($LASTEXITCODE -ne 0) {
          Write-Warning "batch_aggregator exit $LASTEXITCODE (summary vẫn đã ghi: $summaryPath)"
      }
  } catch {
      Write-Warning "batch_aggregator hook error: $_"
  }
  ```

---

## 9. Bất Biến Kiểu Trả Về Của Cơ Chế Chặn Alert (Alert Suppression Return Type)
- Khi bổ sung cờ chặn gửi alert đơn lẻ (`send_farm_machine_alert`) để phục vụ gom lỗi batch, nhánh bị chặn **CẤM** trả về một `dict` (truthy).
- Caller ở ngoài kiểm tra `if send_farm_machine_alert(...):` sẽ ngộ nhận là alert đã được gửi thành công lên Telegram.
- **BẮT BUỘC:** Nhánh bị chặn bắt buộc phải trả về `False` để đồng nhất với kiểu dữ liệu `bool` của hàm.

---

## 10. Kỷ Luật Thực Thi Liền Mạch Đa Phase ("Làm xong hết luôn r báo")
- Khi người dùng đã duyệt kiến trúc và ra lệnh triển khai trọn gói (*"Làm xong hết luôn r báo đừng dừng lại báo từng phase nữa"*):
- Coordinator **BẮT BUỘC** duy trì điều phối worker tự động chạy nối tiếp qua toàn bộ các phase:
  1. Patch core/primitives $\rightarrow$ Verify syntax & unit test.
  2. Implement features/aggregator $\rightarrow$ Test dual-threshold.
  3. Hook runner integration $\rightarrow$ Review Claude CLI Opus High.
- **CẤM TUYỆT ĐỐI** dừng lại ở mỗi sub-phase nhỏ để xin xác nhận hay báo cáo tiến độ lắt nhắt, làm gián đoạn dòng suy nghĩ và gây bực bội cho người vận hành.

---

## 11. Cạm Bẫy Biến Rỗng Trong PowerShell Hook & Độ Sâu Thư Mục Run Manifest
- **Cạm bẫy biến không tồn tại trong PowerShell (`$runDir`):**
  - Khi gắn hook `automation_core.batch_aggregator`, nếu chỉ copy paste snippet mẫu `if ($runDir -and (Test-Path $runDir))` mà không đối soát biến nội tại của runner (ví dụ runner dùng `$artifactRootPath`), biến `$runDir` sẽ là `$null` và PowerShell âm thầm bỏ qua khối lệnh mà không báo lỗi.
  - **BẮT BUỘC:** Đối soát đúng biến chứa đường dẫn kết quả thực tế của runner hoặc tìm thư mục con mới nhất được tạo trong `$artifactRootPath`.
- **Cạm bẫy độ sâu thư mục của `load_results_from_run_dir`:**
  - `batch_aggregator` không được giả định cấu trúc thư mục phẳng `machines/<id>/run_manifest.json`.
  - Trong thực tế chạy live, các runner (như `multi_machine_feed_session`) sinh cấu trúc lồng 2 tầng: `machines/machine_<id>/<timestamp>/run_manifest.json` hoặc lưu trực tiếp tại batch level `run_manifest.json` (chứa `multi_machine_summary`).
  - **BẮT BUỘC:** Hàm đọc run dir phải đệ quy hoặc quét linh hoạt cả 2 tầng để không bị trả về 0 kết quả (`Loaded results count: 0`).

---

## 12. Bắt Buộc Độ Phủ Fleet-Wide Cho Farm Alert Gom Lỗi
- **Yêu cầu tối thượng từ người vận hành:** Cơ chế gom lỗi diện rộng $\ge 10-15\%$ và $\ge 3$ máy **BẮT BUỘC PHẢI ÁP DỤNG CHO TẤT CẢ CÁC SCRIPT RUNNER TRÊN FARM**, không được để sót script nào:
  1. Lướt Feed (`run-feed-session.ps1` / `tiktok-luot nuoi acc`)
  2. Đăng Video (`run_tiktok_upload_batch.ps1` / `Tiktok-video`)
  3. Follow chéo (`run-follow.ps1` / `tiktok-follow`)
  4. Đăng ký TikTok (`run_night_chain_pipeline.py` / `social_reg_v1.py` / `Tiktok_Reg`)
  5. Bật 2FA (`run_batch_live_2fa.py` / `tiktok-add-bao-mat-f2a`)
  6. Đăng ký Gmail (`run_all.ps1` / `register gmail`)
- Khi hoàn thiện cơ chế gom lỗi, kiểm tra danh sách checklist trên để đảm bảo không chỉ cấu hình ở tầng chặn alert lẻ (`alerts.py`) mà phải gắn đầy đủ hook gom kết quả cuối batch ở tầng runner.

---

## 13. Kỷ Luật Minh Họa Định Dạng Báo Cáo (Tránh Nhầm Lẫn Row / Ca Chạy)
- Khi gửi mẫu định dạng mới (preview format) cho người dùng kiểm duyệt:
  - Nếu sử dụng dữ liệu cũ của ngày hôm trước (ví dụ lấy data Row 1 làm mẫu vào ngày chạy Row 2), **BẮT BUỘC PHẢI GHI RÕ NGAY ĐẦU TIN**: `[VÍ DỤ MINH HỌA ĐỊNH DẠNG - DỮ LIỆU THỰC PHIÊN HÔM QUA (ROW 1)]`.
  - Tuyệt đối không gửi tiêu đề trần `Ca 1 - Phiên 1 (Row 1)` làm người vận hành giật mình tưởng bot chạy sai lịch phân bổ chẵn/lẻ của đàn máy.

---

## 14. Quy Tắc P0 Auth/Login Alert: Bỏ Qua Ngưỡng Batch Khi Văng Account / Mất Session
- **Nguyên lý cốt lõi:** Các lỗi lag mạng, drop frame, trượt tương tác có thể tự hồi phục ở phiên tiếp theo khi nuôi đàn. Nhưng các lỗi liên quan đến **Mất Phiên Đăng Nhập / Văng Account** (`login/account screen detected`, `login-gms-verification`, bắt xác minh danh tính/checkpoint, văng ra màn hình chọn nick):
  - **Không thể tự hồi phục:** Thiết bị một khi đã rơi vào màn hình login thì 100% các phiên chạy sau đó của account/row đó đều sẽ thất bại liên tục, dẫn đến tài khoản bị "đói", không được nuôi tương tác.
  - **Rủi ro mất acc vĩnh viễn:** Nếu acc bị dính checkpoint hoặc bắt verify IP/pass mà để trôi dạt quá lâu mà không có người vào xử lý, tài khoản có nguy cơ cao bị TikTok quét ban vĩnh viễn (die acc).
- **Quy định kích hoạt Alert P0:**
  - Nhóm lỗi Auth / Login / Checkpoint **BẮT BUỘC BỎ QUA NGƯỠNG GOM LỖI BATCH (10 - 15%)**.
  - Bất kể tổng tỷ lệ lỗi của batch là bao nhiêu, chỉ cần phát hiện **$\ge 1$ máy có dấu hiệu mất phiên/văng login**:
    - Hệ thống **KÍCH HOẠT FARM ALERT NGAY LẬP TỨC** kèm cờ cảnh báo nổi bật:
      `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện máy M<id> dính màn hình login/xác minh, cần người vận hành vào cứu acc ngay!`
    - Chụp và lưu snapshot màn hình phục vụ thao tác login thủ công.

---

## 15. Quy Tắc Giám Sát Lỗi Dai Dẳng (Consecutive Session Failure Watchdog)
- **Vấn đề của ngưỡng batch đơn thuần:** Khi chạy đàn 80 máy, một máy bị tuột cáp USB, chết proxy hoặc kẹt app thường chỉ chiếm 1 máy ($\approx 1.25\% < 10\%$). Nếu chỉ nhìn vào từng batch riêng lẻ, con máy này sẽ bị Silent Skip ở cả Phiên 1, Phiên 2, Phiên 3... dẫn đến máy bị bỏ rơi cả ngày không được sửa.
- **Quy tắc phát hiện lỗi đa phiên:**
  - Theo dõi lịch sử trạng thái chạy của từng máy trong ngày (qua `feed_session_reported.json` hoặc nhật ký runtime).
  - Nếu **CÙNG 1 MÁY** (hoặc cùng 1 slot tài khoản) bị **thất bại $\ge 2$ phiên liên tiếp** trong cùng một ngày:
    - Máy này tự động bị coi là **Máy kẹt cứng (Stuck Machine / Hardware Defect)**, không còn là lỗi vãng lai (transient).
    - Hệ thống kích hoạt cảnh báo Telegram đích danh:
      `🚨 [FARM ALERT: MÁY M<id>] LỖI LIÊN TIẾP N PHIÊN (Triệu chứng: <error_reason>) - Cần kiểm tra cáp/mạng/app tại chỗ!`

---

## 16. Chuẩn Hóa Định Dạng Thống Kê Nhả Follow (Tránh Mập Mờ Số Máy vs Số Lượt)
- **Yêu cầu từ người vận hành:** Báo cáo phân nhóm nhả follow phải phản ánh rõ máy nào làm được bao nhiêu lượt rồi mới bị TikTok chặn nhả, đồng thời định dạng không được gây nhầm lẫn giữa số lượng máy và số thứ tự máy/số lượt.
- **Cấu trúc 4 tầng chuẩn hóa:**
  ```text
  • Follow chéo (X lượt follow):
    + Success (A máy hoàn thành OK): M3, M5...
    + Nhả follow (B máy):
      - Nhả liền (0 lượt - C máy): M1, M7, M10...
      - 1 - 4 lượt (D máy): M14 (1 lượt), M28 (3 lượt)...
      - 5 - 9 lượt (E máy): M4 (7 lượt), M36 (9 lượt)...
      - 10+ lượt (F máy): M2 (19 lượt), M21 (24 lượt)...
  ```
- **Quy tắc bắt buộc:**
  - Luôn có chữ `máy` sau số lượng thống kê trong ngoặc: `(7 máy)`, `(5 máy)` (CẤM ghi trần `(7)`, `(5)`).
  - Tên máy luôn có tiền tố `M` viết hoa: `M14`, `M18` (CẤM ghi số trần `14`, `18`).
  - Số lượt hoàn thành trước khi bị nhả luôn đặt trong ngoặc đơn rõ ràng: `(6 lượt)`.

---

## 17. Phân Biệt "Báo Cáo Sửa Code (Engineering)" vs "Báo Cáo Vận Hành Farm (Operations)"
- **Tình huống xảy ra lỗi nhận thức:** Người dùng vừa giao việc kỹ thuật (*"Làm luôn"*, *"Sửa đi"*, *"Gắn hook vào"*...) và sau đó hỏi:
  > *"Rồi báo cáo sao r"* / *"Xong chưa"* / *"Tình hình sao r"*
- **Phản xạ sai lầm của Agent:** Đi kiểm tra cronjob watchdog hoặc đọc thư mục live run của farm rồi gửi báo cáo vận hành thiết bị (*"📊 [TIKTOK NUÔI ACC] Ca 2 - Phiên 3 hoàn tất..."*).
- **Phản xạ chuẩn mực (BẮT BUỘC):**
  - Người dùng đang hỏi về **Tiến độ & Kết quả của tác vụ sửa code vừa giao**, KHÔNG hỏi tình trạng đàn máy tự chạy ngoài cron.
  - **Báo cáo nộp lại BẮT BUỘC là Báo Cáo Kỹ Thuật (Engineering Code Change & Verification Report)**:
    1. **Mục đích:** Tóm tắt ngắn gọn yêu cầu kỹ thuật đã thực thi.
    2. **Danh sách file & Git diff:** Nêu rõ các file đã sửa kèm `git diff --stat` (số dòng thêm/bớt).
    3. **Bằng chứng kiểm thử (Verification):** Kết quả chạy `pytest` (số test passed), `py_compile`, `git diff --check`.
    4. **Nghiệm thu thực tế:** Bằng chứng script chạy thử thành công trên dữ liệu/log thật.

---

## 18. Chuẩn Hóa Hiển Thị Tỷ Lệ Lỗi Toàn Batch vs Tỷ Lệ Signature Cục Bộ
- **Hiện tượng gây hiểu lầm (Anti-Pattern):**
  - Khi 100% số máy trong batch thất bại (ví dụ 80/80 máy fail khi tắt dàn máy: 60 máy config-error và 20 máy proxy/vpn), Batch Alert cũ chỉ ghi:
    `Signature: script-blocker:... - Tỷ lệ ảnh hưởng: 75.0% (60/80 máy)`.
  - Người vận hành nhìn vào tưởng rằng batch chỉ fail 75%, phản hồi: *"Báo cáo hơi ngáo nhé. Full máy lỗi mà lại báo cáo có 75%"*.
- **Nguyên nhân cốt lõi:**
  - Thiếu dòng tổng kết tỷ lệ thất bại toàn batch (`failed_count / total_machines`) ở header.
  - Tỷ lệ của từng signature chỉ phản ánh cụm lỗi cục bộ của signature đó trên toàn batch, không đại diện cho toàn bộ số máy chết.
- **Quy chuẩn hiển thị bắt buộc (Triển khai trong `automation_core.batch_aggregator`):**
  1. Header bắt buộc có dòng tổng quan:
     `• Tổng tỷ lệ thất bại toàn batch: {overall_fail_rate:.1%} ({failed_count}/{total_machines} máy)`
  2. Dưới mỗi Signature, tách bạch 2 dòng chỉ số rõ ràng:
     - `Tỷ lệ trên toàn batch: {batch_rate:.1%} ({len(machines)}/{total_machines} máy)`
     - `Tỷ lệ trong số máy lỗi: {fail_share:.1%} ({len(machines)}/{failed_count} máy lỗi)`

### Phân Nhóm Signature Khi Farm Đang Off Toàn Bộ (Ví Dụ 78/80 Máy = 97.5%):
- **Hiện tượng:** Khi tắt toàn bộ proxy hoặc hạ tầng, Batch Alert báo tổng fail 100% (80/80 máy), nhưng signature lỗi proxy chỉ chiếm 78/80 máy (97.5%).
- **Bản chất phép tính:** $78 / 80 = 0.975$ (đúng 97.5%). Tránh nhầm lẫn thị giác giữa 78/80 và 70/80.
- **Nguyên nhân lệch 2 máy:** 78 máy kết nối được ADB và kiểm tra thấy port proxy đóng (`port closed/refused`). 2 máy còn lại gặp lỗi ở tầng thấp hơn trước khi chạm tới bước test port (ví dụ: ADB offline, device not found, USB tuột cáp, socket timeout), dẫn đến văng lỗi riêng lẻ (sporadic) và không bị gom chung vào signature của 78 máy. Tổng thể toàn batch vẫn fail 100% đúng với trạng thái đang tắt toàn bộ.

---

## 19. Cơ Chế 5 Tầng Fallback Chụp Ảnh Cảnh Báo Hiện Trường (Multi-Layer Screencap)
- **Vấn đề:** Khi máy dừng phiên, lệnh `adb exec-out screencap -p` có thể trả về rỗng do:
  - SurfaceFlinger chặn chụp: `FB is protected: PERMISSION_DENIED`.
  - ADB transport bị treo timeout (socket nghẽn sau nhiều lệnh liên tiếp).
  - Gửi alert text trần không hình gây thiếu chứng cứ hiện trường.
- **Quy trình 5 tầng fallback chuẩn hóa (`automation_core.alerts._capture_device_screencap`):**
  1. **Tầng 1 (Primary):** `adb exec-out screencap -p` (trực tiếp qua ADB).
  2. **Tầng 2 (ATX-Agent / JSON-RPC):** Port forward sang 7912, gọi `takeScreenshot` qua JSON-RPC. Nếu nhận `HTTP Error 502: Bad Gateway` (uiautomator daemon chưa thức), tự động gửi `POST /uiautomator` để wake service rồi thử lại.
  3. **Tầng 3 (Device Reconnect):** Gọi `adb -s <serial> reconnect` để thông socket transport riêng của thiết bị đó rồi chụp lại qua ATX.
  4. **Tầng 4 (Shell Local):** Gọi `adb shell screencap -p /sdcard/__alert_screencap.png` rồi pull về.
  5. **Tầng 5 (Artifact Fallback):** Quét tìm file `screen.png` mới nhất trong thư mục artifacts của phiên vừa chạy để gắn Banner Đỏ.

---

## 20. Giới Hạn Trần Cứng Device Lock TTL (Tối Đa 1 Giờ / 3600 Giây)
- **Quy tắc tuyệt đối:** Lock giữ hiện trường khi máy lỗi BẮT BUỘC có `ttl_seconds = 3600` (1 giờ).
- **CẤM TUYỆT ĐỐI:** Tự ý nâng TTL lên 2h, 24h hoặc để `ttl = 0` (vô hạn).
- **Cơ chế tự giải phóng:** Sau 1 giờ nếu người vận hành không can thiệp, cron reaper (`reap-dead-owner-locks.py`) tự động dọn sạch file lock để máy được nhả vào danh sách chạy cho các ca/phiên tiếp theo.


