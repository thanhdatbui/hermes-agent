# Mechanical Precheck Gate for Code Reuse & Anti-Reinvention (2026-10-30)

## 1. Failure Mode: "Paper Rules" vs Mechanical Precheck Gates
- **The Pitfall:** Telling LLM agents or subagents in system prompts / documentation: "You must check for existing code before writing new code." 
- **The Reality:** Agents will almost never voluntarily run a search tool when asked to "fix this bug" or "write this feature". They jump directly into generating code or rewriting helpers.
- **The User Frustration:** *"Ủa chứ bữa thiết kế worker Argon 4 có sửa mấy lỗi của nó rồi mà, sao đéo tái sử dụng? Sao gate ép tái sử dụng đéo hoạt động?"*
- **Root Cause:** The reuse tool (`find_existing_logic.py`) existed as a manual standalone CLI tool, but was never wired mechanically into the precheck stage (S0) of the mandatory execution pipeline (`unified_patch_pipeline.py`).

## 2. The Mechanical Solution: Wiring Search & Context Injection at S0 Precheck
To make reuse unavoidable:
1. **Automated Search at S0 Precheck:**
   - Before any planning (S1) or patching (S2), the pipeline extracts keywords from the task and target files.
   - Runs the AST-indexed logic searcher automatically with a receipt requirement:
     ```bash
     python D:/Taadaa/tools/find_existing_logic.py <keywords> --receipt --top 5
     ```
   - Must run BEFORE the baseline git snapshot so that the receipt ledger modification does not trigger out-of-scope baseline drift violations.
2. **Context Injection into Planner (S1):**
   - Dumps top matching existing functions and classes into `existing_logic.txt`.
   - Passes `--context-file existing_logic.txt` directly to the AI Planner (`gate_b_planner.py`).
   - The planner's prompt now explicitly contains the existing functions across all repositories, eliminating excuse to reinvent.
3. **Receipt Binding in Stage State:**
   - Saves `existing_logic_receipt: "ELR-..."` in `state["stages"]["s0_precheck"]`. Any pipeline run without a verifiable receipt is rejected.
