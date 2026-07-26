from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = REPO_ROOT / "deploy"


def read_deploy_file(name: str) -> str:
    return (DEPLOY_DIR / name).read_text(encoding="utf-8")


def test_skill_sync_uses_canonical_source_and_safe_robocopy_flags():
    script = read_deploy_file("sync-skills.ps1")
    normalized = script.lower()

    assert "join-path $reporoot 'skills'" in normalized
    assert "'/e'" in normalized
    assert "'/mir'" not in normalized
    assert "'/purge'" not in normalized
    for flag in ("'/copy:dat'", "'/dcopy:dat'", "'/r:2'", "'/w:1'", "'/xj'"):
        assert flag in normalized
    assert "robocopy.exe" in normalized
    assert "if ($robocopyexitcode -gt 7)" in normalized
    assert "must be different directories" in normalized
    assert "must not contain one another" in normalized
    assert "reparsepoint" in normalized
    assert "get-skilldirectoryhash" in normalized
    assert "bundled_manifest" in normalized
    assert "manifest[$skillname]" in normalized
    assert "skillstobaseline" in normalized
    assert "locally modified skills" in normalized
    assert "refusing to overwrite" in normalized
    assert "unchanged machine-b" in normalized
    assert "atomic" in normalized
    assert "sourcehash -ne $destinationhash" not in normalized
    assert "v1 migration" in normalized
    assert "destinationhash -ne $sourcehash" in normalized
    assert "review, back up, or reset the local copy before retrying" in normalized
    assert normalized.index("destinationhash -ne $sourcehash") < normalized.index("robocopy.exe")
    assert normalized.index("new-item") > normalized.index("must not contain one another")
    for excluded in (
        ".hub",
        ".usage.json",
        ".usage.json.lock",
        ".curator_state",
        ".bundled_manifest",
        ".curator_suppressed",
        "index-cache",
        ".archive",
        ".curator_backups",
        "*.lock",
        "ticker*",
        ".ds_store",
    ):
        assert excluded in normalized


def test_local_skill_export_is_additive_and_excludes_runtime_metadata():
    script = read_deploy_file("sync-skills-to-repo.ps1")
    normalized = script.lower()

    assert "join-path $reporoot 'skills'" in normalized
    assert "join-path $env:localappdata 'hermes\\skills'" in normalized
    assert "robocopy.exe" in normalized
    assert "'/e'" in normalized
    assert "'/mir'" not in normalized
    assert "'/purge'" not in normalized
    for flag in ("'/copy:dat'", "'/dcopy:dat'", "'/r:2'", "'/w:1'", "'/xj'"):
        assert flag in normalized
    assert "never deletes a skill" in normalized
    assert "git -c $reporoot status --porcelain -- skills" in normalized
    assert "uncommitted changes" in normalized
    assert "symbolic-ref --quiet --short head" in normalized
    assert "rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'" in normalized
    assert "git -c $reporoot fetch --quiet --no-tags" in normalized
    assert "rev-list --left-right --count" in normalized
    assert "behind" in normalized
    assert "no configured upstream" in normalized
    assert "must not contain one another" in normalized
    assert "reparsepoint" in normalized
    for excluded in (
        "'.hub'",
        "'index-cache'",
        "'.archive'",
        "'.curator_backups'",
        "'.usage.json'",
        "'.bundled_manifest'",
        "'.curator_suppressed'",
        "'*.lock'",
        "'ticker*'",
        "'.ds_store'",
    ):
        assert excluded in normalized

def test_skill_sync_workflow_requires_pull_before_export_and_secret_review():
    readme = read_deploy_file("README.md").lower()
    workflow_line = next(
        line for line in readme.splitlines() if line.startswith("pull remote changes ->")
    )

    workflow = (
        "pull remote changes",
        "resolve conflicts",
        "export local skills",
        "inspect diff",
        "git diff --check",
        "review for secrets",
        "git add/commit",
        "git push",
    )
    positions = [workflow_line.index(step) for step in workflow]
    assert positions == sorted(positions)
    assert "additive/update-only" in readme
    assert "unchanged local copy is updated" in readme
    assert "locally modified skill is preserved and reported" in readme
    assert "origin hashes" in readme
    assert "fetches the current configured upstream" in readme
    assert "does not commit or push" in readme
    assert "never infers deletions" in readme
    assert "git rm" in readme
    assert "before `git add`/commit" in readme


def test_setup_syncs_skills_and_does_not_copy_snapshot():
    script = read_deploy_file("setup-admin.ps1")
    normalized = script.lower()

    assert "sync-skills.ps1" in normalized
    assert "& $syncskills -reporoot $reporoot" in normalized
    assert "get-childitem -literalpath $bundlehermes" not in normalized
    assert "copy-item -path (join-path $bundlecodex '*')" not in normalized
    assert not (DEPLOY_DIR / "hermes-home" / "skills").exists()


def test_setup_preserves_existing_bootstrap_credentials_and_codex_state():
    script = read_deploy_file("setup-admin.ps1").lower()

    assert "function copy-bootstrapfile" in script
    assert "-not (test-path -literalpath $destination)" in script
    for filename in (
        ".env",
        "auth.json",
        ".cockpit_codex_auth.json",
        ".codex-global-state.json",
    ):
        assert filename in script


def test_deployment_docs_and_ignore_define_one_skill_source():
    readme = read_deploy_file("README.md").lower()
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").lower()

    assert "repository root `skills/` directory is the shared git source" in readme
    assert "sync-skills.ps1" in readme
    assert "deploy/hermes-home/skills/" in gitignore
