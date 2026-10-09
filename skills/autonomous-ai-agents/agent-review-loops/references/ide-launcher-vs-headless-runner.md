# IDE launcher vs headless coding runner

Use this reference when a user asks to connect a local IDE/coding app as if it were `claude -p`.

## Verified distinction

- A headless runner such as `claude -p` or `opencode run` owns the prompt loop, waits for completion, and exposes stdout/exit status.
- An IDE launcher may only open/enqueue a GUI chat and return immediately. A successful launcher exit is not proof that the agent completed, changed the requested files, or passed tests.
- Antigravity IDE is a VS Code-style Electron IDE with a launcher such as `bin/antigravity-ide.cmd chat`; its `chat` help exposes GUI-oriented modes (`ask`, `edit`, `agent`) and file context, but does not by itself establish a headless result protocol.
- The separate Antigravity Electron app and the Antigravity IDE are different integration targets. OmniRoute model pools are a third, unrelated execution path; a model-pool HTTP 200 does not prove the local IDE is connected.

## Required smoke-test evidence before claiming equivalence

1. Prompt delivery is confirmed.
2. Completion is observable and awaited.
3. Result text is captured independently of the GUI.
4. Failure produces a non-success status.
5. File diff and focused test evidence are read back after completion.

If any item is missing, report the IDE as GUI-launched rather than `claude -p`-compatible. Use a tested CDP/MCP/bridge adapter only after confirming its protocol and completion semantics; do not infer completion from process exit, a changed file, or an HTTP response alone.

## User workflow correction

Do not redirect the user to unrelated OmniRoute/model-pool details when they ask whether the local Antigravity app or IDE can be invoked like Claude CLI. Answer the requested execution surface first, then state the exact missing adapter or supported command.
