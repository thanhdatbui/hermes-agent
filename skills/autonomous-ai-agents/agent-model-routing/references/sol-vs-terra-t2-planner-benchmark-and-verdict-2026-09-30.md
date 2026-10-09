# ĐỐI ĐẦU BENCHMARK PLANNER T2: SOL (CHATGPT-WEB) VS TERRA (CODEX)
*Ngày thẩm định: 30/09/2026*  
*Chánh án độc lập: Claude Code CLI (Sonnet)*  
*Hồ sơ gốc: `D:/Taadaa/tools/plan_bench_spec.json`, `plan_bench_run_results.json`, `plan_bench_verdict.md`*

---

## 1. BỐI CẢNH & MỤC TIÊU VAI TRÒ PLANNER T2

Trong Tiered Workflow 2.0:
- Thợ thi công (Worker Luna High) bị nhốt chặt trong Lồng Vô Trùng $O(1)$ (`<= 30 dòng`, 1 file, 1 focused test `< 30s`).
- Do đó, vai trò của **Planner T2 (Kiến trúc sư lập bản vẽ)** mang tính sống còn:
  1. Chốt **exact anchor duy nhất $c == 1$** (tuyệt đối không để xảy ra ambiguous match làm vỡ code lân cận).
  2. Xuất **Patch Contract $O(1)$** chuẩn chỉnh theo cặp `old_string` $\to$ `new_string` để thợ Luna High gõ mà không cần chuyển đổi.
  3. Cung cấp **đúng 1 lệnh test focused $< 30s$** chạy offline/mocked (không đụng device thật hay ADB).
  4. Phân tích bẫy rủi ro tiềm ẩn (concurrency deadlock, state loss, race condition, leak file).

---

## 2. BẢNG ĐIỂM SCORECARD ĐỐI ĐẦU 5 TRẬN (CHẤM BỞI CLAUDE CLI)

| STT | Bài toán Farm thực tế | Trọng số | Terra Codex (`codex/gpt-5.6-terra`) | Sol Web (`chatgpt-web/gpt-5.6-sol-high`) | Phán quyết chi tiết |
|:---:|---|:---:|:---:|:---:|---|
| **1** | **Concurrency & Lock JSON 70 máy** | 20 | **0đ** *(FAIL)* | **16đ** *(THẮNG)* | **Sol thắng tuyệt đối.** Terra dính timeout cứng 90s không ra được sản phẩm (treo pipeline). Sol dùng `fcntl.flock` + atomic rename file `.tmp`, đúng ngân sách dòng, cảnh báo rủi ro Windows compatibility. |
| **2** | **State & Password Loss (Bảo toàn pass)** | 20 | **15đ** | **17đ** *(THẮNG)* | **Sol thắng.** Sol ra đúng format `old_string -> new_string`, test trỏ đúng 1 case cụ thể. Terra lại dùng format git diff `*** Begin Patch` (thợ Luna không map trực tiếp vào Edit tool được). |
| **3** | **Circuit Breaker Backoff 4G Mobi** | 20 | **15đ** | **16đ** *(THẮNG)* | **Sol thắng sát nút.** Sol check `circuit.is_open()` đầu loop, backoff lũy thừa, test mock chạy `< 30s`. Cả hai cùng miss rủi ro IP rotation nhưng Sol format sạch hơn. |
| **4** | **Monolith Ambiguity (Trùng anchor 3 lần)** | 20 | **18đ** | **19đ** *(THẮNG)* | **Sol thắng.** Cả 2 đều bắt được bẫy $c=3$ (`if session.is_active:`). Terra có tư duy preflight rất tốt; Sol thực dụng hơn khi cung cấp sẵn code mock test cho file monolith không có sẵn test. |
| **5** | **Teardown & Leak Resource (Chromium/ADB)** | 20 | **14đ** | **17đ** *(THẮNG)* | **Sol thắng.** Terra phạm lỗi scope creep: vẽ thêm cả hàm `reclaim_stale_worker` và hạ tầng tracking PID (phình to task). Sol giữ đúng $O(1) \le 30$ dòng quanh `run_worker`, tách việc dọn rác lớn ra ngoài cho watchdog. |
| **TỔNG** | **5 Trận đối kháng** | **100** | **62 / 100** | **85 / 100** | 🏆 **SOL THẮNG TUYỆT ĐỐI 5 / 5 TRẬN!** |

---

## 3. SO SÁNH HIỆU NĂNG & CHI PHÍ THỰC TẾ

| Chỉ số kỹ thuật | Terra Codex | Sol ChatGPT-Web | Nhận định hệ thống |
|---|---|---|---|
| **Tỷ lệ ổn định** | 20% lỗi timeout (1/5 trận dính 90s) | **100% ổn định (0/5 lỗi)** | Planner treo là toàn bộ chuỗi $O(1)$ đứng hình. Sol cực kỳ ổn định. |
| **Thời gian sinh Plan** | 12.5s $\to$ 73.3s (TB: ~32s) | **15.6s $\to$ 30.5s (TB: ~21s)** | Sol nhanh hơn 35%, độ trễ rất đều. |
| **Format Patch Contract** | 2/5 bài tự sinh git diff | **5/5 bài đúng chuẩn `old_string` $\to$ `new_string`** | Luna High nhận Patch Contract của Sol áp dụng được ngay lập tức. |
| **Chi phí Quota** | Tốn quota Codex Developer đắt đỏ | **0đ QUOTA CODEX** | Dùng dàn pool ChatGPT-Web (20+ accs) vừa mạnh vừa tiết kiệm quota Codex cho thợ gõ. |

---

## 4. KẾT LUẬN & PHÂN VAI CHUẨN TRONG TIERED WORKFLOW 2.0

1. **Khâu T2 Planner (Lập bản vẽ):** 
   - **Primary Planner:** **Sol High (`chatgpt-web/gpt-5.6-sol-high`)** đảm nhiệm 100% việc lên plan cho các task T2 thường ngày qua script `D:/Taadaa/tools/sol_planner.py` hoặc API OmniRoute (`:20129`).
   - **Secondary / Tie-breaker:** Terra Codex làm dự phòng khi Sol gặp sự cố hoặc cần phản biện chéo bài toán concurrency khó.
2. **Khâu T2 Worker (Thợ thi công):** 
   - **Luna High (`codex/gpt-5.6-luna-high`)** thi công trong Lồng Vô Trùng $O(1)$ (`<= 30 dòng`, 1 file, 1 focused test).
3. **Khâu Closeout Gate:** 
   - **Sol High** tiếp tục giữ vai trò Đại Giám Khảo độc lập chấm điểm chốt phiên ($\ge 85/100$) trước khi push.
