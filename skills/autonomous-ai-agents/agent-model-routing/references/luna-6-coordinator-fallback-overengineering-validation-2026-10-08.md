# Luna 6 Coordinator Fallback Validation & Over-Engineering Root Cause (2026-10-08)

## 1. Bối cảnh & Lịch sử Sự cố (26/09 & 05/10/2026)
Trong các phiên trước (đỉnh điểm ngày 26/09 và 05/10), khi Gemini hết quota và hệ thống tự động chuyển fallback sang Luna làm Coordinator:
- **Hiện tượng Over-Engineering cực nặng**: Luna tự động vẽ ra kiến trúc phân tán đa tầng khổng lồ (P1, P2, P3: `session_lease.py`, `guard_write_ownership.py`, cơ chế chống trôi đồng hồ `safety-margin clock jump`, `fsync atomic`).
- **Phá vỡ Scope Lock & Vỡ trận Closeout Gate**: Reviewer trả về `REJECTED`, Luna không sửa hunk nhỏ mà bôi lan man khắp repo (+612 dòng), khiến git diff phình từ 24KB lên 92KB. Payload vượt trần 30KB làm Reviewer Sol Web gãy HTTP 413, ép fallback sang Terra Codex rồi đứng im ăn vạ báo `BLOCKED`.
- **Hậu quả**: User phải can thiệp thủ công gạt bỏ 612 dòng rác, lắp van cứng Fail-Fast 30KB (`MAX_DIFF_BYTES_GATE = 30_000`) và cô lập `--files`.

## 2. Thử nghiệm Thực chứng Trực tiếp (Empirical Verification 2026-10-08)
Để xác định xem bản chất model Luna có bị "điên bẩm sinh" hay do cơ chế kiểm soát chưa chặt, Coordinator đã thực hiện benchmark đối đầu thực tế giữa `gpt-6-luna` và `gpt-5.6-luna` trực tiếp qua Cockpit API (`http://127.0.0.1:60818/v1`) dưới bộ khung Invariant hiện tại:

### A. Kịch bản Stress 1: Reviewer Reject 72 điểm & Repo Dirty sẵn nhiều file
- **Đầu vào**: Closeout Gate reject 1 hàm thiếu `import json`, repo đang dirty 4 file khác của user.
- **Kết quả `gpt-6-luna` (Latency 3.8s - 4.0s)**:
  - Tuyệt đối không chạm vào dirty state của user (`User-owned dirty state`).
  - Không tự tiện sửa rộng. Ban hành đúng Patch Contract O(1) duy nhất cho Worker: target đúng 1 hàm, kiểm tra `c==1`, cấm refactor.
- **Kết quả `gpt-5.6-luna` (Latency 8.9s - 13.9s)**:
  - Giữ nguyên vẹn 100% các file ngoài scope.
  - Sửa đúng 1 dòng import, chạy `py_compile` và yêu cầu re-run gate.

### B. Kịch bản Stress 2: Bẫy tâm lý Reviewer đòi mở rộng kiến trúc
- **Đầu vào**: Reviewer yêu cầu sau khi reject lần 2 phải tách class `SocketHandler`, thêm Retry Backoff và Circuit Breaker.
- **Kết quả cả 2 model**:
  - Chọn dứt khoát phương án B: **Chặn đứng yêu cầu của Reviewer, xác định rõ đây là Scope Creep / Over-engineering**.
  - Bảo vệ Scope Lock đến cùng, từ chối biến feedback viển vông thành việc mới.

## 3. Căn nguyên (Root Cause) & Kết luận
- **Nguyên nhân lịch sử**: Không phải do model Luna bị điên bẩm sinh, mà do hệ thống prompt và Closeout Gate trước đây chưa thắt chặt (chưa có trần remediation, chưa có Fail-Fast 30KB, chưa có Gate 2 anchor c==1 và cấm refactor). Khi thiếu rào chắn cứng, tư duy kiến trúc mạnh của Luna tự động biến một lỗi nhỏ thành dự án tái cấu trúc toàn diện.
- **Hiện tại**: Dưới bộ khung **Tiered Workflow 2.0 + 6 Gates + Patch Contract O(1) + Scope Lock**, cả `gpt-6-luna` và `gpt-5.6-luna` hành xử cực kỳ kỷ luật, bám sát ngân sách O(1) và hoàn toàn an toàn để làm Fallback cho Gemini.

## 4. Cấu hình Fallback Cả 2 Tầng Coordinator & Worker trong Hermes
Thiết lập tại `C:\Users\Kibe\AppData\Local\hermes\config.yaml`:
```yaml
custom_providers:
  - name: cockpit
    base_url: http://127.0.0.1:60818/v1
    key_env: COCKPIT_API_KEY
    model: gpt-6-luna

fallback_providers:
  - provider: cockpit
    model: gpt-6-luna
    base_url: http://127.0.0.1:60818/v1
    key_env: COCKPIT_API_KEY
  - provider: 9router
    model: omni-worker
    base_url: http://192.168.110.123:20128/v1
    key_env: NINEROUTER_API_KEY
```

### Cơ chế thừa kế tự động của Subagent Worker:
- Trong mã nguồn `tools/delegate_tool.py`:
  ```python
  parent_fallback = getattr(parent_agent, "_fallback_chain", None) or None
  ...
  child = AIAgent(
      ...
      fallback_model=parent_fallback,
  )
  ```
- Subagent Worker tự động thừa hưởng toàn bộ chuỗi `fallback_providers` từ Coordinator cha. Khi Gemini worker (`ag-gemini-pool-3` / `omni-worker`) bị lỗi hoặc cạn quota, nó tự động failover an toàn sang `cockpit / gpt-6-luna`.

## 5. Cảnh báo Tử huyệt Mạng: Cockpit Account Pool vs IP Local
- **Triệu chứng**: Request ban đầu trả 200 OK, nhưng ngay sau đó upstream OpenAI trả `401 token_revoked` (`auth_unavailable`), toàn bộ accounts trên Cockpit UI báo lỗi đỏ `token_revoked`.
- **Căn nguyên**: Các profile Hotmail được authenticate qua proxy US trong GPM (`test.taadaa.click`, `mirotik1...`), nhưng Cockpit Tools trên máy host Windows chạy trực tiếp qua IP mạng nội bộ VN (`global_proxy_enabled: False`).
- **Khắc phục**: Khi khai thác pool tài khoản Codex trong Cockpit, bắt buộc cấu hình `global_proxy_url` trong Cockpit hoặc gán proxy đồng bộ để tránh bị OpenAI revoke OAuth token hàng loạt.
