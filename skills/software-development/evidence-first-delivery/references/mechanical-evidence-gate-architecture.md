# Mechanical Evidence Gate & Multi-Worker Verification Architecture

Tài liệu kỹ thuật và mẫu triển khai chuẩn cho công cụ thẩm định bằng chứng thị giác cơ học: `D:\Taadaa\tools\evidence_gate_verifier.py`.

---

## 1. Bối cảnh & Các Điểm Mù Cần Triệt Tiêu (Lessons Learned)

Trong quá trình tự động hóa UI và bàn giao kết quả (Evidence-First Delivery), các lỗ hổng nhận thức và kỹ thuật thường gặp gồm:
1. **Confirmation Bias / Self-Attestation:** Agent tự tin rằng mình đã nhập đúng OTP / pass, bỏ qua vệt chữ báo lỗi cũ trên màn hình ("That code didn't work") và báo cáo thành công sai sự thật.
2. **Replay Attack (Tái Sử Dụng Ảnh):** Sử dụng lại ảnh sạch của lần chạy trước hoặc của tác vụ khác để lách qua gate.
3. **TOCTOU Race Condition:** Khi nhiều worker farm chạy song song, hai worker cùng đua dùng một ảnh hợp lệ cho hai claim khác nhau trong khoảng thời gian chạy OCR (30–60s).
4. **Fail-Open Persistence Divergence:** Lưu audit log thất bại (do lock timeout, đầy đĩa) nhưng hệ thống vẫn trả về `PASS` cho caller, dẫn đến việc sổ cái và kết quả trả về phân rã nhau.

---

## 2. Các Bất Biến Cốt Lõi (Invariants)

### Invariant 1: Unconditional Mandatory Pairing & Distinct SHA256
- Mọi thao tác đổi trạng thái (click/submit/thay đổi thông tin) **BẮT BUỘC** phải có cả cặp ảnh Pre-submit và Post-submit.
- `pre_hash != post_hash` (mã băm SHA256 phải khác nhau, cấm dùng cùng 1 file ảnh hoặc clone).
- Header định dạng ảnh vật lý hợp lệ theo chuẩn RFC: PNG (`\x89PNG`), JPEG (`\xff\xd8`), và WEBP cấu trúc container RIFF (`hdr.startswith(b'RIFF') and hdr[8:12] == b'WEBP'`), kích thước `> 1KB`.

### Invariant 2: Anti-Replay Temporal Order & Claim Binding
- **Temporal Order:** `post_mtime >= pre_mtime`, khoảng cách `interval <= 120s`, tuổi thọ `max_age <= 600s`.
- **Claim Binding:** Mã SHA256 của `post_image` sau khi đã `PASS` được ghi nhận vào sổ cái; mọi nỗ lực tái sử dụng SHA256 đó cho claim khác đều bị từ chối ngay lập tức (`ANTI_REPLAY_CLAIM_BINDING_VIOLATION`).

### Invariant 3: Atomic Two-Phase Reservation with Fail-Closed Process Liveness
- Trước khi thực thi OCR tốn thời gian, worker gọi `atomic_reserve_claim_hash(post_hash, run_id, pid)` dưới `FileLock`.
- Tránh tình trạng lease hết hạn mù (lease without liveness): Chỉ thu hồi reservation khi tiến trình OS sở hữu (`pid`) đã thực sự chết (`is_process_alive(pid) == False`).
- **Fail-Closed on Access Denied:** Nếu kiểm tra tiến trình trả về `ERROR_ACCESS_DENIED` (code 5) hoặc `PermissionError` (do tiến trình chạy dưới quyền admin/user khác), hệ thống giả định tiến trình còn sống (`return True`) để bảo vệ reservation, triệt tiêu hoàn toàn race window.

### Invariant 4: True Atomic Zero-Divergence Fail-Closed Audit Trail
- Toàn bộ thao tác tính `block_hash`, ghi file JSON audit, commit append block vào `audit_chain.jsonl`, và giải phóng reservation được thực hiện TRONG CÙNG MỘT GIAO DỊCH NGUYÊN TỬ DUY NHẤT dưới `FileLock`.
- Nếu bất kỳ bước nào thất bại, file JSON vừa tạo bị unlink `os.remove` ngay lập tức, không ghi block nào vào sổ cái, và verdict trở thành `FAIL_AUDIT_PERSISTENCE_ERROR`. Zero-divergence giữa sổ cái và return value được cam kết toán học.

### Invariant 5: Affirmative Positive Success Gating & Single-Inspection Effective OCR
- Không chỉ kiểm tra vắng mặt tín hiệu lỗi, nếu caller có claim thành công hoặc truyền `--expected-post-keywords` / `--require-positive`, hệ thống bắt buộc phải tìm thấy từ khóa thành công (`positive_indicators_found`) từ danh sách đồng bộ `COMMON_SUCCESS_MARKERS`. Nếu thiếu -> `FAIL_NO_POSITIVE_EVIDENCE`.
- **Single-Inspection Mode Support (`--allow-single-inspection`):** Trong chế độ chỉ đọc không có `post_image`, scan dương tính tự động dùng `effective_ocr = pre_ocr` làm căn cứ thẩm định, tránh lỗi false-FAIL do đọc nhầm `post_ocr` rỗng. Scan phủ quyết lỗi (veto) vẫn căn cứ trực tiếp trên `pre_ocr`.

---

## 3. Lệnh Thực Thi & Kiểm Tra Toàn Vẹn

### A. Kiểm tra một hành động giao diện:
```bash
python D:/Taadaa/tools/evidence_gate_verifier.py \
  --pre-image "D:/Taadaa/runtime/artifacts/step_pre.png" \
  --post-image "D:/Taadaa/runtime/artifacts/step_post.png" \
  --claim "Đã đổi thành công" \
  --expected-post-keywords "removed" "success" "up to date"
```

### B. Kiểm tra toàn vẹn chuỗi cryptographic audit ledger:
```bash
python D:/Taadaa/tools/evidence_gate_verifier.py --verify-chain
```
