# Terminal wrapper timeout handling

When verification runs through Hermes' foreground terminal wrapper, keep the foreground timeout within the wrapper's enforced limit (currently 60 seconds). For commands that may exceed that limit, use a tracked background process and poll/wait for completion instead of requesting an oversized foreground timeout.

Preserve and report the exact command and its real exit result. If the wrapper rejects a command before execution, do not claim that verification ran or passed. If the exact command is required by the task, retry it through the permitted execution mode rather than substituting a different test command.
