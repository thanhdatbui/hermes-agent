# TikTok Cache & Storage Cleanup Automation Patterns

## Dialog Heuristics & Negative Testing
- **Downloads Dialog Matching**: When cleaning secondary items like "Tải về" (Downloads) on the storage screen, avoid loose heuristics like `("Hội thoại" in xml and "Xóa" in xml)`. Loose matching risks false positives on unrelated dialogs or UI elements.
- **Strict Heuristics**:
  - Direct prompt matches: `"Xóa mục tải về?"`, `"Clear downloads?"`
  - Co-occurrence with cancellation buttons: `("Tải về" in xml and "Xóa" in xml and "Hủy" in xml)` or `("Downloads" in xml and "Clear" in xml and "Cancel" in xml)`.
  - Qualified dialog wrappers: `("Hội thoại" in xml and "Tải về" in xml and "Xóa" in xml)` or `("Dialog" in xml and "Downloads" in xml and "Clear" in xml)`.
- **Negative Testing Requirements**:
  - Test missing actionable buttons: Verify that if a confirmation dialog appears without a matching confirm button (e.g. loading / in-progress state), the handler logs a warning and exits gracefully without crashing or throwing unhandled exceptions.
  - Test missing target row: Verify that if the target row (e.g., Downloads) is absent from the hierarchy dump, the flow safely bypasses the action.
- **Structured Telemetry**:
  - Emit structured logs (`logger.info` / `logger.debug`) for row bounds, tap points, dialog state detections, and post-clear size updates.
