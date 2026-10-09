# Advice to Action Workflow & Partial Scan Resolution Case Study

## 1. Trigger & Classification
- **Turn 1 (Advice Intent):** User poses an evaluative question regarding an anomaly:
  *"Ủa từ giữa đêm tới h mà +26 following à t nhớ mấy acc toàn bị khoá k cho đi follow mà"*
  - **Action:** Primary Coordinator queries database facts (verifying no accounts actually followed). Sol Advisor (:20129) evaluates the architecture, explaining the phantom delta caused by sample mismatch (partial scan of 1,019/1,254 accounts on D-1 vs full farm summary on day D), and proposes forward-fill state cumulative tracking.
- **Turn 2 (Work Intent):** User responds with short authorization (e.g., *"R làm đi"*, *"Sửa đi"*, *"Triển khai đi"*):
  - **Classification:** Strictly imperative for the remediation action. Do NOT call Advisor again; user has already approved direction. Transition directly into Tiered Workflow (dispatch worker).
  - **Hybrid Compound Pattern ("Sửa đi + hỏi thêm"):** When user authorizes AND simultaneously asks a follow-up explanatory question (e.g. *"Sửa đi. R sao hôm nay nội bộ tăng ít trên tỉ lệ tổng tăng v..."*):
    * Immediately execute the approved remediation via worker dispatch in the background.
    * Do NOT re-invoke Advisor for the already-diagnosed task.
    * In the foreground response, answer the user's follow-up question directly using concrete database/runtime evidence (top accounts, interaction metrics, shift timeline) to provide full clarity without freezing or redundant back-and-forth.

## 2. Execution Discipline (RED -> GREEN -> LIVE VERIFICATION)
1. **Focused Test Creation (RED):**
   - Write a self-contained unit test with temp SQLite database replicating the partial scan scenario (`test_tiktok_dashboard_history.py`).
   - Run pytest to prove test fails (`assert 1 == 2`) under existing code.
2. **Patch Contract O(1) Formulation:**
   - Locate the monolith file (`tiktok_dashboard.py`).
   - Formulate single anchor replacement converting naive `GROUP BY` and summary overrides into a chronologically ordered `forward-fill` dictionary accumulator (`users_state[username] = (follower, following, heart, video)`).
3. **Worker Dispatch (`delegate_task`):**
   - Subagent applies Patch Contract O(1) and runs focused test.
4. **Verification & Service Refresh (GREEN):**
   - Confirm test PASS (1 passed in <1s).
   - Terminate old background service process and restart `tiktok_dashboard.py --port 1905`.
5. **Visual Proof (GATE 6):**
   - Use headless browser / Playwright to interact with dashboard, open modal, switch metric, capture screenshot.
   - Verify visually via `browser_vision` that delta is clean 0 (not +26).
   - Deliver media evidence `MEDIA:<path>` directly to user.
