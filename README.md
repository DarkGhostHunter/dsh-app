# dsh-app

Electron AppImage wrapper for [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) on Linux x64. Upstream's Desktop app is deeply invested in Electron as a feature platform (updater, guests, platform view, shortcuts), so we don't reimplement any of it — we run upstream's own Desktop shell and packaging pipeline.

## How it works

Upstream ships Desktop release targets for macOS and Windows only, but its electron-builder config already declares a Linux AppImage target and its runtime-preparation layer already locks `linux-x64` interpreters. The gap is small: [patches/linux-packaging.patch](patches/linux-packaging.patch) registers a `linux-x64` release target across upstream's packaging scripts —

- `desktop-build-paths.mjs` / `package-target.ts`: accept and select the target,
- `prepare-dsh.ts` / `prepare-runtime.ts`: the Linux Electron executable layout (`electron`, not `Electron.app/Contents/MacOS/Electron`),
- `prepare-cli.ts` / `cli/dsh`: the installed `dsh` launcher resolves the Linux bundle layout,
- `desktop-package-environment.mjs` / `desktop-toolchain-preflight.ts`: no macOS/Windows signing settings on Linux,
- `smoke-packaged-runtime.ts`: smoke-test the `linux-unpacked` bundle,
- `electron-builder-config.mjs`: icon and executable name for the existing `linux: { target: ['AppImage'] }` block.

Everything else — workspace build, primary-runtime preparation (Node + Python + pnpm payload), the production `dsh` tree, electron-builder, and the packaged smoke test — is upstream's own pipeline, unmodified. Builds run `pnpm --filter @deepseek-ai/dsh-desktop run package -- linux-x64 --unsigned`: Linux needs no signing credentials, and `--unsigned` also skips upstream's Tencent COS update-feed wiring, which this repository cannot publish.

Releases follow upstream automatically:

1. **[watch-upstream.yml](.github/workflows/watch-upstream.yml)** runs hourly, polls upstream tags via the GitHub API, and dispatches a build when it finds a tag (`dsh-vX.Y.Z…`) with no matching release here yet.
2. **[build-appimage.yml](.github/workflows/build-appimage.yml)** clones upstream at that tag, applies the Linux packaging patch, runs upstream's Desktop packaging pipeline for `linux-x64`, and publishes the AppImage to a GitHub Release tagged with the same upstream tag.

Manual triggers: `workflow_dispatch` with a `tag` input, or `repository_dispatch` (`deepseek-release`, `client_payload.tag`).

## Repo layout

- `patches/linux-packaging.patch` — the diff above, applied to a pristine upstream clone at build time.
- `scripts/local-build.sh` — replica of the CI pipeline for local runs.
- `.github/workflows/` — the two workflows described above.

## Local build

Requires the devcontainer (Node 22+, pnpm 11), then:

```sh
bash scripts/local-build.sh                 # latest upstream tag
bash scripts/local-build.sh dsh-v0.2.1-rc.2 # a specific tag
```

The AppImage lands in `deepseek-harness/apps/desktop/.desktop-build/targets/linux-x64/unsigned-artifacts/`.

## Notes

- Pre-release upstream tags (e.g. `-rc.1`, `-alpha.3`) are published as pre-releases here.
- Artifacts are unsigned and carry upstream's `-unsigned` suffix, so a shared file can never pass for a release artifact — upstream's own convention.
- **Office→PDF conversion is unavailable on Linux**: upstream's `libreoffice-kit` publishes native engines for macOS and Windows only, and no Linux engine package is on the public registry. The packaging smoke test skips the conversion check on Linux accordingly.
- **Linux window behavior**: upstream's Electron window-controls overlay is GTK-dependent and breaks under decoration-managing GNOME extensions, so Linux keeps native server-side decorations (buttons follow the user's GNOME layout preference). The Application/Edit menu bar is never rendered — shortcuts dispatch through the DOM, and F12/Ctrl+Shift+I still work via hidden menu entries. Closing the window quits the application through the ordinary quit confirmation (upstream hides to a tray/Dock that Linux doesn't have).
- The auto-updater is dormant in these builds (no update feed is published). Wiring `electron-updater` to a generic feed (e.g. GitHub Releases) is a possible follow-up via the same patch.
