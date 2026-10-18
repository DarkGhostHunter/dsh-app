# dsh-app

Minimal Tauri wrapper that builds an AppImage and uses GitHub Releases for updates.

Workflow:
- Tag a release: git tag v0.1.0 && git push --tags
- GitHub Actions builds an AppImage and publishes it to the release.
- Tauri updater is configured to check a manifest.json attached to the releases (see src-tauri/tauri.conf.json).

Checklist / what's in the repo:
- package.json: minimal build scripts that copy static/ -> dist/
- static/index.html: minimal frontend used by Tauri
- src-tauri/: Tauri Rust wrapper and tauri.conf.json
- .github/workflows/release.yml: builds AppImage on tag push and creates a GitHub Release

Notes & caveats:
- The workflow generates a manifest.json per release and uploads it as a release asset.
- This is intentionally minimal and follows YAGNI / KISS / DRY.