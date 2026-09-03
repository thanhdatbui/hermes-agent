# Application update vs. source-repository update

Use this reference when a user asks to “update” a local tool and there may be both an installed/running application and a source checkout.

## Scope gate

1. Interpret “update the app/application” as an app-operations request unless the user explicitly says repository, source, code, Git, branch, or build.
2. Do not begin with `git status`, stash, rebase, merge, pull, dependency edits, or source changes.
3. Keep app data/configuration and source-repository state as separate scopes.

## Discovery checklist

- Identify the live process and exact command line.
- Inspect the shortcut, installer, service, updater, package manager entry, or executable launch path.
- Determine whether the target is a packaged release or merely a development checkout such as `npm run dev`.
- Find the app’s own version/about/status endpoint or release channel.
- Check whether another updater is already running.
- Preserve the running instance until the app-level update path and restart requirement are known.

## Decision rules

- Packaged app: use its documented updater or installer path; verify version and health afterward.
- App launched from a source checkout: do not silently equate “update the app” with “update Git.” Ask for or report the exact app update mechanism before modifying the checkout.
- Existing dirty source files or divergent branches are not permission to merge or discard work; they are a separate repository blocker.
- A live port/listener proves only that a process is listening, not that the application is healthy. Verify an actual response and version/status after an update.
- If the user corrects the scope, stop repository operations immediately, confirm no rebase/merge is active, and acknowledge the correction briefly.

## Reporting

Report only: target identified, app-level action taken (or exact blocker), live verification result, and next required input. Avoid a long explanation of the mistaken path.
