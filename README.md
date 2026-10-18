# dsh-app

Tauri desktop wrapper that packages the [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) web frontend as a Linux AppImage, and follows upstream releases automatically.

## How it works

We don't control the upstream repo, so there is no webhook on their side. Instead:

1. **[watch-upstream.yml](.github/workflows/watch-upstream.yml)** runs hourly, polls `deepseek-ai/deepseek-harness` tags via the GitHub API, and dispatches a build when it finds a stable tag (`dsh-vX.Y.Z…`) that has no matching release in this repo yet.
2. **[build-appimage.yml](.github/workflows/build-appimage.yml)** clones upstream at that tag, builds the `@deepseek-ai/dsh-web-frontend` package (`apps/web`, vite → `dist/`), drops the output into `dist/`, wraps it with Tauri, and publishes an AppImage to a GitHub Release tagged with the same upstream tag.

You can also trigger a build manually (`workflow_dispatch` with a `tag` input) or via `repository_dispatch` with event type `deepseek-release` and a `client_payload.tag`.

## Repo layout

- `static/index.html` — fallback frontend, used only for local smoke builds. CI replaces `dist/` with the upstream build.
- `src-tauri/` — Tauri 2 shell (`tauri.conf.json` targets `appimage`, `frontendDist: ../dist`).
- `.github/workflows/` — the two workflows described above.

## Local development

```sh
npm run build:web        # copy static/ -> dist/
cargo tauri dev          # run the shell
cargo tauri build --bundles appimage
```

Building the real app locally requires the upstream monorepo (pnpm, Node 22+); the CI workflow does this for you.

## Notes

- Pre-release upstream tags (e.g. `-rc.1`, `-alpha.3`) are built as pre-releases here.
- No Tauri updater plugin is configured yet — enabling it later requires signing keys (`TAURI_SIGNING_PRIVATE_KEY`) and a `latest.json` manifest per release.
