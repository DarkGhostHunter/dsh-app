# dsh-app

An Electron AppImage wrapper for [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) on Linux x64. Upstream ships Desktop releases for macOS and Windows only. We don't reimplement a shell: we run upstream's own Desktop app through upstream's own packaging pipeline, and patch the small Linux gap.

That's the whole repository. There is no custom shell here, and there used to be a Tauri one. It's gone, and for good reason: upstream is deeply invested in Electron as a feature platform (updater, guests, platform view, shortcuts), and a second shell would fork all of it.

## How it works

Upstream's electron-builder config already declares a Linux AppImage target, and its primary runtime locks `linux-x64` interpreters. The gap is narrow. [patches/linux-packaging.patch](patches/linux-packaging.patch) applies to a pristine upstream clone and:

- Registers the `linux-x64` release target across the build paths, packaging scripts and their `.d.mts` type declarations.
- Adapts the Linux Electron executable layout (`electron`, not `Electron.app/Contents/MacOS/Electron`) in `prepare-dsh.ts`, `prepare-runtime.ts` and `smoke-packaged-runtime.ts`.
- Resolves the installed `dsh` launcher for the Linux bundle layout in `cli/dsh`.
- Gives the Linux electron-builder block an icon and the `deepseek-harness` executable name.
- Packs release tarballs with `--concurrency 4`. Upstream only passes it on macOS, and 344 packages serially cost four minutes.
- Skips the Office to PDF conversion check in the packaged smoke test on Linux (see [Notes](#notes)).
- Keeps native window decorations, hides the menu bar and makes close quit the app (see [Notes](#notes)).

Everything else is upstream's own pipeline, untouched: workspace build, primary runtime preparation (Node, Python, pnpm), the production `dsh` tree, electron-builder and the packaged smoke test that boots the Host and installs plugins.

Builds run unsigned, with `pnpm --filter @deepseek-ai/dsh-desktop run package -- linux-x64 --unsigned`. Linux needs no signing credentials anyway, and `--unsigned` also skips upstream's Tencent COS update-feed wiring, which this repository cannot publish.

> [!NOTE]
> Artifacts carry upstream's `-unsigned` suffix, so a shared file can never pass for a release artifact.

## Releases

Releases follow upstream automatically:

1. **[watch-upstream.yml](.github/workflows/watch-upstream.yml)** runs hourly, polls upstream tags through the GitHub API, and dispatches a build when it finds a `dsh-vX.Y.Z…` tag with no matching release here yet.
2. **[build-appimage.yml](.github/workflows/build-appimage.yml)** clones upstream at that tag, applies the Linux packaging patch, runs upstream's Desktop packaging pipeline for `linux-x64`, and publishes the AppImage to a GitHub Release under the same upstream tag. The pnpm store, the packaging downloads and the electron-builder tooling are cached between runs.

Manual triggers: `workflow_dispatch` with a `tag` input, or `repository_dispatch` (`deepseek-release`, `client_payload.tag`).

## Repo layout

- `patches/linux-packaging.patch` — the diff above, applied to the clone at build time.
- `scripts/local-build.sh` — replica of the CI pipeline for local runs.
- `.github/workflows/` — the two workflows described above.

## Local build

The devcontainer ships everything needed: Node 22, pnpm 11 and the shared libraries the Electron binaries load at smoke time. You also need `gh` for the default tag lookup.

```sh
bash scripts/local-build.sh                 # latest upstream tag
bash scripts/local-build.sh dsh-v0.2.1-rc.2 # a specific tag
```

The AppImage lands in `deepseek-harness/apps/desktop/.desktop-build/targets/linux-x64/unsigned-artifacts/`. Run it with `--appimage-extract-and-run` on hosts without FUSE.

## Notes

- Pre-release upstream tags (e.g. `-rc.1`, `-alpha.3`) are published as pre-releases here.
- **Office to PDF conversion is unavailable on Linux.** Upstream's `libreoffice-kit` publishes native engines for macOS and Windows only, and no Linux engine exists on the public registry. The smoke test skips the conversion check accordingly.
- **Linux window behavior.** The Electron window-controls overlay is GTK-dependent, misplaces buttons under decoration-managing GNOME extensions, and Electron plans to remove it, so Linux keeps native server-side decorations and the buttons follow the user's GNOME layout. The Application/Edit menu bar is never rendered: shortcuts dispatch through the DOM, and F12 or Ctrl+Shift+I still work through hidden menu entries. Closing the window quits the app through upstream's ordinary quit confirmation, because upstream hides to a tray or Dock that Linux does not have.
- **The auto-updater is dormant.** No update feed is published. Wiring `electron-updater` to a generic feed (e.g. GitHub Releases) is a possible follow-up through the same patch.
