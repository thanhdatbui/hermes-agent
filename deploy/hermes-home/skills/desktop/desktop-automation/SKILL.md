---
name: desktop-automation
description: Best practices and safety patterns for using computer-use and desktop automation.
---

# Desktop Automation Best Practices

This skill captures learnings and pitfalls for driving the user's desktop via tools like `computer_use`.

## Safety & Style Guidelines
- **User Preference:** The user expects autonomous operation but prioritizes not having their active work interrupted.
- **Do Not Disrupt:** Never close windows, log out, or perform destructive actions unless explicitly requested. Always verify the element label in a SOM capture before clicking, especially near window controls.
- **Communication:** If the AI is struggling to interact with a specific app (e.g., Chrome/Browser), stop and explain why rather than repeatedly sending potentially destructive commands.

## Pitfalls & Troubleshooting
- **Background Interaction Failures:** Background input (like `type` or keyboard shortcuts) often fails for specific window classes (e.g., `Chrome_WidgetWin_1`). 
  - *Fix:* Bring the window to front (`focus_app` or user-assisted) or explicitly request a foreground-mode action if the tool supports it.
- **Element Mapping Errors:** UI elements in SOM/AX captures can shift. Always perform a fresh `capture` immediately before a `click` or `type` action to ensure indices are valid.
- **Identifying Targets:** If an app is not found, use `list_apps` to verify the exact string expected by `cua-driver` before trying to target it with `capture` or `focus_app`.
- **Browser vs. Desktop:** Do not use desktop automation for web browsing tasks that `browser_*` tools can handle reliably. Only reach for desktop automation for native apps (Figma, Outlook, file explorers, etc.).
