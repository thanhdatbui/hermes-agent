---
name: desktop-automation
description: Best practices and safety patterns for using computer-use and desktop automation.
---
# Desktop Automation Best Practices

This skill captures learnings and pitfalls for driving the user's desktop via tools like `computer_use`.

## Safety & Style Guidelines
- **User Preference (Action-First vs. Passive Instructions):** When the user reports an app error, freeze, failure, or annoying system tray notification (e.g. missing driver panel, update nag), they expect the agent to immediately diagnose and remediate the issue directly — DO NOT just explain the cause or list manual steps/options for the user to execute. If a quick fix exists, execute it immediately end-to-end. Asking the user to click through options or run files is considered laziness and an operational failure unless strictly impossible without user credentials/elevation.
- **Autonomous Operation:** The user expects autonomous operation but prioritizes not having their active work interrupted.
- **Do Not Disrupt:** Never close windows, log out, or perform destructive actions unless explicitly requested. Always verify the element label in a SOM capture before clicking, especially near window controls.
- **Communication:** If the AI is struggling to interact with a specific app (e.g., Chrome/Browser), stop and explain why rather than repeatedly sending potentially destructive commands.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
