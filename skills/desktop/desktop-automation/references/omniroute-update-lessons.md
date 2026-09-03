# OmniRoute update lessons

## Scope

When the user says “update OmniRoute”, first establish whether the target is an installed desktop package, a source checkout, or a running dev instance. In this case the launcher pointed to `C:\Users\Kibe\OmniRoute` and ran `npm run dev` on port `20129`, so the target was a repo-backed dev instance, not a separately installed binary.

## Safe sequence

1. Inspect the launcher/command line, current version, Git revision, remote revision, and live port.
2. Preserve dirty work before any overwrite. A named stash plus a backup branch gives a verifiable recovery path.
3. Update the source revision without killing unrelated services. Do not use `taskkill` as a prerequisite for `git fetch`, dependency installation, or build.
4. Install dependencies. If an optional native dependency is absent, inspect the project’s documented fallback before changing system tooling.
5. Run the build and wait for the original build process to finish. A second build may fail only because `.build/next/lock` is held by the first; inspect process state instead of deleting the lock or killing the build.
6. Start/reload the target instance only after the build completes.
7. Verify version/revision, process/port, and a live health endpoint. For OmniRoute, `/api/health` returning HTTP 200 with `status: "ok"` is direct evidence of a responding instance.

## Build-specific lessons

- OmniRoute v3.8.50 declares `better-sqlite3` optional and has a `node:sqlite` fallback for Node 22.5+. A missing native `better-sqlite3` binary can first appear as a webpack module-resolution failure; make the package resolvable, then let the runtime fallback handle the native driver path.
- The upstream v3.8.50 revision in this session contained a JSX splice defect in `src/app/(dashboard)/dashboard/endpoint/EndpointPageClient.tsx` around `ProviderModelsModal`’s `renderModelGroup`: the map callback’s `return` had been replaced by unrelated endpoint-header JSX. The smallest repair was to restore `return (` before the model row and retain the surrounding modal structure. Verify the build after this correction; do not broadly refactor the page.
- A successful production build is not enough if the live port is dead. Start the correct port and verify both redirect behavior (`/` may return 307 to `/dashboard`) and `/api/health`.

## Reporting

Use concise Vietnamese status lines: `Mục tiêu`, `Đã làm`, `Kiểm tra`, `Blocker`. Translate the relevant result instead of pasting raw English logs. Do not report “đã cập nhật” until the version, build exit code, and live health response are all verified.
