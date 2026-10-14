# Advice to Action Workflow & Partial Scan Resolution Case Study

## 1. Trigger & Classification
- **Turn 1 (Advice Intent):** User poses an evaluative question regarding an anomaly:
  *"Ủa từ giữa đêm tới h mà +26 following à t nhớ mấy acc toàn bị khoá k cho đi follow mà"*
  - **Action:** Primary Coordinator queries database facts (verifying no accounts actually followed). Sol Advisor (:20129) evaluates the architecture, explaining the phantom delta caused by sample mismatch (partial scan of 1,019/1,254 accounts on D-1 vs full farm summary on day D), and proposes forward-fill state cumulative tracking.
- **Turn 2 (Work Intent):** User responds with short authorization (e.g., *"R làm đi"*, *"Sửa đi"*, *"Triển khai đi"*):
  - **Classification:** Strictly imperative for the remediation action. Do NOT call Advisor again; user has already approved direction. Transition directly into Tiered Workflow (dispatch worker).
  - **Advisor Planning Pitfall — Anti-Corporate Multi-Week Roadmapping ("Ủa mà sao phải làm từng tuần"):**
    * When user asks Advisor for a plan (`Gọi sol plan`, `Lên plan đi`), reasoning models often default to enterprise roadmap tropes: arbitrarily splitting tasks into multi-week milestones (*"Tuần 1: Infra, Tuần 2: Core, Tuần 3-4: Live"*).
    * User explicitly rejects artificial slow-downs: *"Ủa mà sao phải làm từng tuần"*.
    * **Discipline:** All planning must distinguish **Immediate In-Session Delivery** (code, feature map, offline mocked tests, single-device canary — done in minutes/hours today) from **Fleet Soak Windows** (24h–48h passive observation on physical devices). Never schedule code writing across weeks when it can be executed right now.
  - **Hybrid Compound Pattern ("Sửa đi + hỏi thêm"):** When user authorizes AND simultaneously asks a follow-up explanatory question (e.g. *"Sửa đi. R sao hôm nay nội bộ tăng ít trên tỉ lệ tổng tăng v..."*):
    * Immediately execute the approved remediation via worker dispatch in the background.
    * Do NOT re-invoke Advisor for the already-diagnosed task.
    * In the foreground response, answer the user's follow-up question directly using concrete database/runtime evidence (top accounts, interaction metrics, shift timeline) to provide full clarity without freezing or redundant back-and-forth.

## 2. Worker Dispatch Contract Invariant (Gate 4 & Scope Lock)
When delegating an `EDIT` task to a Worker subagent via `delegate_task`, Coordinator guards enforce strict contract markers in `context`:
```text
TASK_KIND: EDIT
FILE: <absolute_path_to_target_file>
FOCUSED_TEST: python -m pytest <path>::<node>
WORK_DIR: <absolute_path_to_repo>
```
*Failure to include exact `FILE:` or `FOCUSED_TEST: python -m pytest ...` will trigger guard refusals (`EDIT_MISSING_FILE`, `EDIT_MISSING_FOCUSED_TEST`).*

## 3. Execution Discipline (RED -> GREEN -> LIVE VERIFICATION)
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
